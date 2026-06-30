"""H1 — sözleşme CSV'lerine parametrik, seed'li "saha kirliliği" enjekte eder.

Amaç: gerçek sahanın kusurlu verisini (eksik/bozuk/sıra-dışı) önceden üretip
platformun zarifçe ele aldığını — reddetme/raporlama/kısmi hesap — kanıtlamak.

Kullanım (CLI):
    python -m tools.corrupt --in tests/fixtures/baseline --out /tmp/dirty --kind type_corruption --seed 42

Her kirlilik türü bağımsız bir bayrak; `corrupt_rows` saf fonksiyondur (CSV I/O
yalnız `main` içinde). Determinizm `random.Random(seed)` instance'ı ile sağlanır —
global `random` KULLANILMAZ (tekrarlanabilirlik bozulmasın diye).
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

# Hat-seviyesi olaylar için zorunlu kabul edilen alan (boşaltma testi için).
_REQUIRED_EVENT_FIELD = "event_type"
_DURATION_FIELD = "duration"
_TIMESTAMP_FIELD = "timestamp"
_REASON_FIELD = "reason_code"

# Sözleşme dışı, eşlenemeyen etiketler (unknown_reason / unknown event_type için).
_UNKNOWN_EVENT = "WIDGET_FROBNICATE"
_UNKNOWN_REASON = "gizemli_ariza_42"


def _pick(rows: list[dict], rng: random.Random, rate: float) -> list[int]:
    """Satır indekslerinden `rate` oranında deterministik bir alt küme seç (en az 1)."""
    if not rows:
        return []
    k = max(1, round(len(rows) * rate))
    return sorted(rng.sample(range(len(rows)), min(k, len(rows))))


def _missing_row(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    drop = set(_pick(rows, rng, rate))
    return [r for i, r in enumerate(rows) if i not in drop]


def _duplicate(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    out: list[dict] = []
    dup = set(_pick(rows, rng, rate))
    for i, r in enumerate(rows):
        out.append(dict(r))
        if i in dup:
            out.append(dict(r))  # birebir kopya (idempotency/dedup testi)
    return out


def _out_of_order(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    if _TIMESTAMP_FIELD not in (rows[0] if rows else {}):
        return [dict(r) for r in rows]
    out = [dict(r) for r in rows]
    # zaman damgalarını sabit tut, satır sırasını karıştır -> sıra-dışı timestamp
    rng.shuffle(out)
    return out


def _clock_skew(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    """Bir alt kümeye saat kayması/DST benzeri sıçrama uygula (timestamp metnine saat ekle)."""
    out = [dict(r) for r in rows]
    for i in _pick(rows, rng, rate):
        ts = out[i].get(_TIMESTAMP_FIELD, "")
        # "YYYY-MM-DD HH:MM:SS..." -> saati +1 kaydır (kaba, metin düzeyinde DST taklidi)
        out[i][_TIMESTAMP_FIELD] = _shift_hour(ts, rng.choice((-1, 1)))
    return out


def _partial_shift(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    """İlk/son dönemi kırparak yarım vardiya taklidi (kenardan kes)."""
    if len(rows) < 4:
        return [dict(r) for r in rows]
    cut = max(1, round(len(rows) * rate / 2))
    return [dict(r) for r in rows[cut:-cut]] or [dict(rows[0])]


def _unknown_reason(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    out = [dict(r) for r in rows]
    for i in _pick(rows, rng, rate):
        # bilinmeyen event_type VE/VEYA reason_code (eşlenemeyen saha etiketleri)
        out[i][_REQUIRED_EVENT_FIELD] = _UNKNOWN_EVENT
        if _REASON_FIELD in out[i]:
            out[i][_REASON_FIELD] = _UNKNOWN_REASON
    return out


def _empty_required(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    out = [dict(r) for r in rows]
    for i in _pick(rows, rng, rate):
        out[i][_REQUIRED_EVENT_FIELD] = ""  # zorunlu alan boş
    return out


def _type_corruption(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    out = [dict(r) for r in rows]
    for i in _pick(rows, rng, rate):
        if _DURATION_FIELD in out[i]:
            out[i][_DURATION_FIELD] = "NOTANUMBER"  # sayı yerine metin
    return out


def _negative_duration(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    out = [dict(r) for r in rows]
    for i in _pick(rows, rng, rate):
        if _DURATION_FIELD in out[i]:
            out[i][_DURATION_FIELD] = "-99.0"
    return out


def _disposition_violation(rows: list[dict], rng: random.Random, rate: float) -> list[dict]:
    """production satırında good+scrap != loaded ihlali (G12 kalite değişmezi)."""
    out = [dict(r) for r in rows]
    for i in _pick(rows, rng, rate):
        if "loaded_qty" in out[i]:
            try:
                out[i]["loaded_qty"] = str(int(out[i]["loaded_qty"]) + 7)  # toplamı boz
            except (TypeError, ValueError):
                out[i]["loaded_qty"] = "999999"
    return out


_DISPATCH = {
    "missing_row": _missing_row,
    "duplicate": _duplicate,
    "out_of_order": _out_of_order,
    "clock_skew": _clock_skew,
    "partial_shift": _partial_shift,
    "unknown_reason": _unknown_reason,
    "empty_required": _empty_required,
    "type_corruption": _type_corruption,
    "negative_duration": _negative_duration,
    "disposition_violation": _disposition_violation,
}

KINDS: tuple[str, ...] = tuple(_DISPATCH)


def corrupt_rows(
    rows: list[dict], kind: str, seed: int = 42, rate: float = 0.1
) -> list[dict]:
    """`rows`'a `kind` türü kirlilik enjekte eder (deterministik, seed'li)."""
    if kind not in _DISPATCH:
        raise ValueError(f"bilinmeyen kirlilik türü: {kind!r} (geçerli: {', '.join(KINDS)})")
    rng = random.Random(seed)
    return _DISPATCH[kind](rows, rng, rate)


def _shift_hour(ts: str, delta: int) -> str:
    """'YYYY-MM-DD HH:MM:SS...' metninde saat alanını delta kadar kaydır (kaba)."""
    try:
        date_part, time_part = ts.split(" ", 1)
        h, rest = time_part.split(":", 1)
        new_h = (int(h) + delta) % 24
        return f"{date_part} {new_h:02d}:{rest}"
    except (ValueError, IndexError):
        return ts


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return (reader.fieldnames or []), rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


# Hangi sözleşme dosyası hangi kirliliğe maruz kalır (diğerleri olduğu gibi kopyalanır).
_PRODUCTION_KINDS = {"disposition_violation"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sözleşme CSV'lerine saha kirliliği enjekte et.")
    parser.add_argument("--in", dest="in_dir", required=True, help="temiz sözleşme CSV dizini")
    parser.add_argument("--out", dest="out_dir", required=True, help="kirli çıktı dizini")
    parser.add_argument("--kind", required=True, choices=KINDS, help="kirlilik türü")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rate", type=float, default=0.1)
    args = parser.parse_args(argv)

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    target = "production.csv" if args.kind in _PRODUCTION_KINDS else "events.csv"

    for name in ("events.csv", "production.csv", "orders.csv"):
        src = in_dir / name
        if not src.exists():
            continue
        fieldnames, rows = _read_csv(src)
        if name == target:
            rows = corrupt_rows(rows, args.kind, seed=args.seed, rate=args.rate)
        _write_csv(out_dir / name, fieldnames, rows)

    print(f"kirli veri yazıldı: {out_dir} (kind={args.kind}, seed={args.seed}, rate={args.rate})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
