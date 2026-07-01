"""Pilot Doctor — Faz 0-1 hazırlık kontrollerini tek GO/NO-GO raporunda otomatikler.

Runbook (docs/pilot-kit/04-pilot-runbook.md) Faz 0-1 kapısının otomasyonu (A->B
sözleşmesi): hat doğrulama (H7) + adaptör (H2) + smoke ingest (H1) + OEE anlamlılığı
+ veri-yeterlilik skoru (H3) + red oranı -> tek "hazır mı?" kararı.

Kullanım (CLI):
    python -m tools.pilot_doctor <veri-dizini> [--adapter <profil>] [--json]

Tasarım (bkz. docs/superpowers/specs/2026-07-01-pilot-kiti-B-pilot-doctor-design.md):
- In-process: backend fonksiyonları doğrudan çağrılır; sunucu gerekmez. Tüm ingest
  GEÇİCİ DuckDB'ye gider — gerçek `oee.duckdb`'ye ASLA dokunulmaz.
- Import hijyeni: yalnız app.config/app.config_validate/app.ingest/app.store/
  app.analytics — ASLA app.api/app.main (FastAPI yok).
- Saf çekirdek (check_* fonksiyonları) I/O'suz; dosya/DB yalnız `run_doctor`/`main`'de.
- Konsol çıktısı ASCII (Windows cp1252 Türkçe karakterde UnicodeEncodeError verir);
  eşikler runbook varsayılanı (yeterlilik 0.6, red 0.05) — config/confidence.yaml'daki
  0.5 pano "düşük güven" rozetinin eşiğidir, AYRI amaç.

Exit kodları: 0 = GO, 1 = NO-GO, 2 = kullanım hatası.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from app.analytics.confidence import data_sufficiency
from app.analytics.oee import OeeResult, compute_oee
from app.config import load_line_definition
from app.config_validate import validate_line_dict
from app.ingest.adapter import AdapterError, adapt_dir_to_contract, load_adapter_config
from app.ingest.loader import load_csv_dir
from app.ingest.report import LoadReport
from app.models.contract import LineDefinition
from app.store.duckdb_repo import DuckDBRepository

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"

# Runbook Faz 1 kapı varsayılanları (CLI bayraklarıyla ezilebilir).
DEFAULT_MIN_SUFFICIENCY = 0.6
DEFAULT_MAX_REJECT = 0.05

# ASCII katlama: cp1252 konsolda Türkçe karakter UnicodeEncodeError verir.
_ASCII_FOLD = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")


def _ascii(text: str) -> str:
    return text.translate(_ASCII_FOLD).encode("ascii", "replace").decode("ascii")


@dataclass(frozen=True)
class CheckResult:
    name: str  # line | adapter | ingest | oee | sufficiency | rejection
    status: str  # PASS | FAIL | SKIP
    detail: str  # eyleme dönük özet (raporda ASCII'ye katlanır)
    value: float | None = None  # ölçülen değer (oee, skor, oran)
    threshold: float | None = None


@dataclass
class DoctorReport:
    checks: list[CheckResult] = field(default_factory=list)
    ingest: dict | None = None  # LoadReport.to_dict()
    oee: dict | None = None  # asdict(OeeResult)

    def go(self) -> bool:
        return decide(self.checks)

    def to_dict(self) -> dict:
        return {
            "go": self.go(),
            "checks": [asdict(c) for c in self.checks],
            "ingest": self.ingest,
            "oee": self.oee,
        }


# ---- saf kontroller ------------------------------------------------------


def check_line(raw: object) -> CheckResult:
    """Hat tanımı ham dict'ini H7 doğrulayıcısından geçirir."""
    if not isinstance(raw, dict):
        return CheckResult("line", FAIL, "hat tanimi bir YAML nesnesi olmali (line/tanks)")
    errors = validate_line_dict(raw)
    if errors:
        return CheckResult("line", FAIL, "hat tanimi gecersiz: " + "; ".join(errors))
    return CheckResult("line", PASS, "hat tanimi gecerli (0 hata)")


def check_oee(result: OeeResult) -> CheckResult:
    """OEE anlamlı mı: sıfır olmayan ve [0,1] içinde (runbook 1.2)."""
    detail = (
        f"oee={result.oee:.3f} (A={result.availability:.2f} "
        f"P={result.performance:.2f} Q={result.quality:.2f}) [0 < oee <= 1]"
    )
    ok = 0.0 < result.oee <= 1.0
    return CheckResult("oee", PASS if ok else FAIL, detail, value=result.oee)


def check_sufficiency(score: float, minimum: float) -> CheckResult:
    """H3 veri-yeterlilik skoru esik ustunde mi (runbook 1.3)."""
    ok = score >= minimum
    op = ">=" if ok else "<"
    detail = f"{score:.3f} {op} {minimum:.3f}"
    return CheckResult("sufficiency", PASS if ok else FAIL, detail, value=score, threshold=minimum)


def rejection_rate(accepted: dict[str, int], rejected_count: int) -> float | None:
    """Red orani; hic satir yoksa None (payda sifir)."""
    total = sum(accepted.values()) + rejected_count
    if total == 0:
        return None
    return rejected_count / total


def check_rejection(report: LoadReport, maximum: float) -> CheckResult:
    """Kirli-satir orani kabul edilebilir mi (runbook 1.4).

    Oran TAM `rejected` listesinden — to_dict()'in `max_errors`'ta kirpilan
    `errors`'indan DEGIL (kirpilmis sayi orani sessizce dusuk gosterirdi).
    """
    rejected = len(report.rejected)
    rate = rejection_rate(report.accepted, rejected)
    if rate is None:
        return CheckResult("rejection", FAIL, "hic satir yok (bos veri dizini?)", threshold=maximum)
    total = sum(report.accepted.values()) + rejected
    ok = rate <= maximum
    op = "<=" if ok else ">"
    detail = f"{rate:.1%} {op} {maximum:.1%} ({rejected}/{total})"
    return CheckResult("rejection", PASS if ok else FAIL, detail, value=round(rate, 4), threshold=maximum)


def check_ingest(report: LoadReport) -> CheckResult:
    """Smoke ingest: en az bir satir kabul edildi mi (runbook 1.1)."""
    total = sum(report.accepted.values())
    parts = " ".join(f"{k}={v}" for k, v in sorted(report.accepted.items()))
    skipped = ", ".join(report.skipped) if report.skipped else "-"
    detail = f"accepted: {parts or 'yok'} | skipped: {skipped}"
    return CheckResult("ingest", PASS if total > 0 else FAIL, detail)


def decide(checks: list[CheckResult]) -> bool:
    """GO = hic FAIL yok (SKIP notr)."""
    return all(c.status != FAIL for c in checks)


# ---- orkestrasyon (I/O burada) ---------------------------------------------


def _line_stage(line_path: Path) -> tuple[LineDefinition | None, CheckResult]:
    """Hat YAML'ını oku + doğrula + yükle; (LineDefinition|None, kontrol) döner."""
    try:
        with open(line_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        return None, CheckResult("line", FAIL, f"hat YAML okunamadi/bozuk: {exc}")
    res = check_line(raw)
    if res.status != PASS:
        return None, res
    try:
        return load_line_definition(line_path), res
    except (KeyError, TypeError, ValueError) as exc:
        # Defans: doğrulayıcı ile yükleyici resmen bağlaşık değil.
        return None, CheckResult("line", FAIL, f"hat tanimi yuklenemedi: {exc}")


_SKIP_NO_LINE = "hat tanimi gecersiz oldugu icin atlandi"
_SKIP_NO_DATA = "veri yok (ingest bos satir kabul etti) - atlandi"
_SKIP_ADAPTER_FAIL = "adapter eslemesi basarisiz oldugu icin atlandi"

# Eşleme profilleri repo-kökü config/adapters/ altında (tools/ -> backend -> repo kökü).
_ADAPTERS_DIR = Path(__file__).resolve().parents[2] / "config" / "adapters"


def adapter_profile_path(name: str) -> Path:
    return _ADAPTERS_DIR / f"{name}.yaml"


def _adapter_stage(name: str, data_dir: Path, tmp_path: Path) -> tuple[CheckResult, Path]:
    """Ham dizini profil ile sözleşmeye çevirir; (kontrol, ingest_dizini) döner.

    Profil dosyasının VARLIĞI `main`'de doğrulanır (yoksa kullanım hatası, exit 2);
    burada içerik/eşleme hataları FAIL kontrolüne dönüşür.
    """
    mapping = load_adapter_config(adapter_profile_path(name))
    out = tmp_path / "adapted"
    out.mkdir()
    try:
        adapt_dir_to_contract(data_dir, mapping, out)
    except AdapterError as exc:
        return CheckResult("adapter", FAIL, f"adapter eslemesi basarisiz: {exc}"), data_dir
    return CheckResult("adapter", PASS, f"profil '{name}' uygulandi -> sozlesme dizini"), out


def run_doctor(
    data_dir: Path,
    line_path: Path,
    adapter: str | None = None,
    min_sufficiency: float = DEFAULT_MIN_SUFFICIENCY,
    max_reject: float = DEFAULT_MAX_REJECT,
) -> DoctorReport:
    """Faz 0-1 kontrollerini koşar; GEÇİCİ DuckDB kullanır (gerçek DB'ye dokunmaz).

    Bağımlılık: line FAIL -> oee+sufficiency SKIP (ingest/rejection yine koşar);
    adapter FAIL -> ingest/oee/sufficiency/rejection SKIP.
    """
    checks: list[CheckResult] = []
    line_def, line_check = _line_stage(Path(line_path))
    checks.append(line_check)

    with tempfile.TemporaryDirectory(
        prefix="oee_doctor_", ignore_cleanup_errors=True
    ) as tmp:
        tmp_path = Path(tmp)
        ingest_dir = Path(data_dir)
        if adapter:
            adapter_check, ingest_dir = _adapter_stage(adapter, Path(data_dir), tmp_path)
            checks.append(adapter_check)
            if adapter_check.status == FAIL:
                # Sözleşme-şekilli veri yok -> aşağı akış kontrolleri anlamsız.
                for name in ("ingest", "oee", "sufficiency", "rejection"):
                    checks.append(CheckResult(name, SKIP, _SKIP_ADAPTER_FAIL))
                return DoctorReport(checks=checks, ingest=None, oee=None)
        else:
            checks.append(CheckResult("adapter", SKIP, "adapter verilmedi"))

        # Smoke ingest — geçici DB; close() cleanup'tan ÖNCE (Windows dosya kilidi).
        repo = DuckDBRepository(str(tmp_path / "doctor.duckdb"))
        repo.connect()
        repo.init_schema()
        try:
            report = load_csv_dir(ingest_dir, repo)
            events = repo.fetch_events()
            production = repo.fetch_production()
        finally:
            repo.close()

    checks.append(check_ingest(report))

    oee_dict: dict | None = None
    if line_def is None:
        checks.append(CheckResult("oee", SKIP, _SKIP_NO_LINE))
        checks.append(CheckResult("sufficiency", SKIP, _SKIP_NO_LINE))
    elif not events or not production:
        checks.append(CheckResult("oee", SKIP, _SKIP_NO_DATA))
        checks.append(CheckResult("sufficiency", SKIP, _SKIP_NO_DATA))
    else:
        oee_res = compute_oee(events, production, line_def)
        oee_dict = asdict(oee_res)
        checks.append(check_oee(oee_res))
        checks.append(check_sufficiency(data_sufficiency(events, production, line_def), min_sufficiency))

    checks.append(check_rejection(report, max_reject))
    return DoctorReport(checks=checks, ingest=report.to_dict(), oee=oee_dict)


# ---- insan-okur rapor ----------------------------------------------------


def format_report(
    rep: DoctorReport,
    data_dir: str,
    line_path: str,
    adapter: str | None,
    max_errors: int = 5,
) -> str:
    """ASCII kontrol listesi + SONUC satiri (kutu-cizim karakteri yok)."""
    lines = [
        "Pilot Doctor -- Faz 0-1 hazirlik kontrolu",
        f"data dir : {data_dir}",
        f"line     : {line_path}",
        f"adapter  : {adapter or '(yok)'}",
        "",
    ]
    for c in rep.checks:
        lines.append(f"[{c.status}] {c.name:<11} {c.detail}")
        if c.status == FAIL and c.name == "rejection" and rep.ingest:
            for err in (rep.ingest.get("errors") or [])[:max_errors]:
                # Çok satırlı doğrulama mesajını tek satıra sıkıştır (okunabilirlik).
                msg = " ".join(str(err.get("error", "")).split())
                if len(msg) > 160:
                    msg = msg[:157] + "..."
                lines.append(f"    - {err.get('file')}:{err.get('row')}: {msg}")
    verdict = "GO (exit 0)" if rep.go() else "NO-GO (exit 1)"
    lines += ["", f"SONUC: {verdict}"]
    return _ascii("\n".join(lines))


# ---- CLI -------------------------------------------------------------------

_DEFAULT_LINE = Path(__file__).resolve().parents[2] / "config" / "line_default.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pilot_doctor",
        description="Faz 0-1 pilot hazirlik kontrolleri: tek GO/NO-GO raporu.",
    )
    parser.add_argument("data_dir", help="sozlesme CSV dizini (adapter verilirse ham dizin)")
    parser.add_argument("--line", default=str(_DEFAULT_LINE), help="hat tanimi YAML yolu")
    parser.add_argument("--adapter", default=None, help="config/adapters/<AD>.yaml profili")
    parser.add_argument("--min-sufficiency", type=float, default=DEFAULT_MIN_SUFFICIENCY,
                        help="H3 veri-yeterlilik esigi (vars. 0.6)")
    parser.add_argument("--max-reject", type=float, default=DEFAULT_MAX_REJECT,
                        help="kirli-satir orani esigi (vars. 0.05)")
    parser.add_argument("--max-errors", type=int, default=5,
                        help="raporda gosterilecek ilk N ret detayi (vars. 5)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="makine-okur JSON cikti")
    args = parser.parse_args(argv)

    # Kullanim hatalari (exit 2): kontroller kosmadan once, eksik dosya/dizin/profil.
    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"HATA: veri dizini yok ya da dizin degil: {data_dir}", file=sys.stderr)
        return 2
    line_path = Path(args.line)
    if not line_path.is_file():
        print(f"HATA: hat tanimi dosyasi yok: {line_path}", file=sys.stderr)
        return 2
    if args.adapter and not adapter_profile_path(args.adapter).is_file():
        print(
            f"HATA: bilinmeyen adapter profili: {args.adapter!r} "
            f"({adapter_profile_path(args.adapter)})",
            file=sys.stderr,
        )
        return 2

    rep = run_doctor(
        data_dir,
        line_path,
        adapter=args.adapter,
        min_sufficiency=args.min_sufficiency,
        max_reject=args.max_reject,
    )
    exit_code = 0 if rep.go() else 1
    if args.as_json:
        payload = {
            "exit_code": exit_code,
            "data_dir": str(data_dir),
            "line_config": str(line_path),
            "adapter": args.adapter,
            "thresholds": {
                "min_sufficiency": args.min_sufficiency,
                "max_reject": args.max_reject,
            },
            **rep.to_dict(),
        }
        print(json.dumps(payload))  # ensure_ascii varsayilani cp1252-guvenli
    else:
        print(format_report(rep, str(data_dir), str(line_path), args.adapter, args.max_errors))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
