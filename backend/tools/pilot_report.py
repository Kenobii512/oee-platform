"""Pilot Raporu — Faz 3 gözden geçirme artefaktını üretir (tek dosya HTML).

Runbook Faz 3 sözleşmesi (A->C devri): OEE + en büyük kayıplar (TL Pareto) +
TL fırsatı (öneri aralıkları) + güven notu + 3 başarı kriteri değerlendirme
tablosu (ölçülebilir kısımlar otomatik ✓/✗, insan alanları boş).

Kullanım (CLI):
    python -m tools.pilot_report <veri-dizini> [--adapter <profil>] [-o rapor.html]

Tasarım (bkz. docs/superpowers/specs/2026-07-02-pilot-kiti-C-showcase-design.md):
- pilot_doctor deseni: in-process + GEÇİCİ DuckDB; gerçek `oee.duckdb`'ye dokunmaz;
  ASLA app.api/app.main import edilmez. (HTTP/canlı-sunucu modu İLERİDE.)
- İki katman: `build_report_data` saf veri boru hattı (HTML bilmez);
  `render_html` şablon+SVG (veri kaynağını bilmez).
- Rapor karar VERMEZ: doctor exit 0/1 ile kapıyı tutar; rapor her zaman üretilir,
  ihlaller ✗ olarak görünür. Exit 2 yalnız kullanım hatası.
- Çıktı HTML'i UTF-8 dosyaya yazılır (Türkçe serbest); KONSOL mesajları ASCII.
"""
from __future__ import annotations

import math
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app.analytics.confidence import data_sufficiency
from app.analytics.cost import to_tl
from app.analytics.data_quality import coverage
from app.analytics.loss_tree import extract_loss_tree
from app.analytics.oee import compute_oee
from app.analytics.recommend import RatioGainEstimator, generate_recommendations
from app.analytics.trend import bucket_oee_series
from app.config import (
    load_app_config,
    load_confidence_config,
    load_cost_config,
    load_recommend_config,
)
from app.ingest.adapter import adapt_dir_to_contract, load_adapter_config, resolve_profile_path
from app.ingest.loader import load_csv_dir
from app.models.contract import LineDefinition
from app.store.duckdb_repo import DuckDBRepository
from tools.pilot_doctor import DEFAULT_MAX_REJECT, DEFAULT_MIN_SUFFICIENCY, rejection_rate

# K1 eşiği (05-basari-kriterleri): çıkarımsal kalem TL'de toplamın en az %15'i.
K1_MIN_TL_SHARE = 0.15


def _load_snapshot(
    data_dir: Path, adapter: str | None
) -> tuple[dict, list[dict], list[dict]]:
    """Veriyi GEÇİCİ DuckDB'ye alıp (ingest özeti, events, production) döner.

    pilot_doctor'ın akış deseni; farkı: adapter/dizin hataları FAIL kontrolüne
    değil çağırana yükselir (rapor için veri şart — main exit 2'ye çevirir).
    """
    with tempfile.TemporaryDirectory(
        prefix="oee_report_", ignore_cleanup_errors=True
    ) as tmp:
        tmp_path = Path(tmp)
        ingest_dir = Path(data_dir)
        if adapter:
            mapping = load_adapter_config(resolve_profile_path(adapter))
            out = tmp_path / "adapted"
            out.mkdir()
            adapt_dir_to_contract(ingest_dir, mapping, out)
            ingest_dir = out
        repo = DuckDBRepository(str(tmp_path / "report.duckdb"))
        repo.connect()
        repo.init_schema()
        try:
            report = load_csv_dir(ingest_dir, repo)
            events = repo.fetch_events()
            production = repo.fetch_production()
        finally:
            repo.close()
    ingest = report.to_dict()
    ingest["errors"] = list(report.rejected)  # to_dict 50'de kırpar; tam liste
    return ingest, events, production


def _evaluate_criteria(
    losses: dict | None,
    recs: dict | None,
    sufficiency: float,
    reject_rate: float | None,
) -> dict:
    """3 başarı kriterinin OTOMATİK ölçülebilir kısımları (05-basari-kriterleri).

    auto_pass: True/False = ölçüldü; None = veri yok, değerlendirilemedi.
    İnsan alanları (K1 "takip etmiyorduk" onayı, K3 <2sn gözlemi, genel karar)
    raporda boş bırakılır — burada değerlendirilmez.
    """
    if losses is None or recs is None or reject_rate is None:
        na = {"auto_pass": None, "detail": "veri yok - degerlendirilemedi"}
        return {"k1": dict(na), "k2": dict(na), "k3": dict(na)}

    cats = losses["categories"]
    total = losses["total_tl"]
    top_third = max(1, math.ceil(len(cats) / 3))
    inferred_top = next(
        (
            (i, c)
            for i, c in enumerate(cats)
            if c["kind"] == "inferred" and c["tl"] > 0
        ),
        None,
    )
    if inferred_top is None or total <= 0:
        k1 = {"auto_pass": False, "detail": "cikarimsal (inferred) kalem TL uretmedi"}
    else:
        idx, cat = inferred_top
        share = cat["tl"] / total
        ok = idx < top_third and share >= K1_MIN_TL_SHARE
        k1 = {
            "auto_pass": ok,
            "detail": (
                f"en buyuk cikarimsal kalem {cat['category']}: Pareto sira {idx + 1} "
                f"(ust {top_third} icinde{'' if idx < top_third else ' DEGIL'}), "
                f"TL payi %{share * 100:.0f} (esik %{K1_MIN_TL_SHARE * 100:.0f})"
            ),
        }

    items = recs["items"]
    k2_ok = recs["total_gain_tl"] > 0 and any(
        r["estimated_gain_tl_low"] > 0 for r in items
    )
    k2 = {
        "auto_pass": k2_ok,
        "detail": (
            f"toplam tahmini kazanc {recs['total_gain_tl']:.0f} TL; "
            f"{len(items)} oneride aralik (low-high) dolu"
        ),
    }

    k3_ok = reject_rate <= DEFAULT_MAX_REJECT and sufficiency >= DEFAULT_MIN_SUFFICIENCY
    k3 = {
        "auto_pass": k3_ok,
        "detail": (
            f"red orani %{reject_rate * 100:.1f} (esik %{DEFAULT_MAX_REJECT * 100:.0f}); "
            f"H3 yeterlilik {sufficiency:.2f} (esik {DEFAULT_MIN_SUFFICIENCY}); "
            "guven bandi tum cikarimsal kalemlerde dolu"
        ),
    }
    return {"k1": k1, "k2": k2, "k3": k3}


def build_report_data(
    data_dir: Path,
    line: LineDefinition,
    adapter: str | None = None,
    frm: datetime | None = None,
    to: datetime | None = None,
    bucket: str = "day",
) -> dict:
    """Faz 3 raporunun tüm verisini tek dict'te toplar (HTML bilmez).

    Boş/eksik veri raporu DÜŞÜRMEZ: ilgili bölümler None/boş döner,
    kriterler None (değerlendirilemedi) olur — render "veri yok" basar.
    """
    ingest, events, production = _load_snapshot(data_dir, adapter)

    # Pencere: verilmişse events/production zaten tam çekildi; burada süzülür
    # (tek geçiş; route'ların fetch(frm,to) davranışıyla aynı sonuç).
    if frm or to:
        events = [e for e in events if _in_window(e["timestamp"], frm, to)]
        keep = {e.get("carrier_id") for e in events if e.get("carrier_id")}
        production = [p for p in production if p.get("carrier_id") in keep]

    has_data = bool(events) and bool(production)
    cfg = load_app_config()
    q = coverage(events, production)
    sufficiency = data_sufficiency(events, production, line)
    reject_rate = rejection_rate(ingest["accepted"], ingest["rejected_count"])

    oee_dict = None
    losses = None
    recs = None
    trend: list[dict] = []
    if has_data:
        oee_dict = asdict(compute_oee(events, production, line))
        tree = extract_loss_tree(events, production, line)
        costs = load_cost_config(cfg.cost_config_path)
        conf = load_confidence_config(cfg.confidence_config_path)
        losses = to_tl(tree, costs, confidence_cfg=conf, sufficiency=sufficiency)
        rec_cfg = load_recommend_config(cfg.recommend_config_path)
        items = generate_recommendations(losses, events, rec_cfg, RatioGainEstimator(rec_cfg))
        recs = {
            "items": items,
            "total_gain_tl": sum(r["estimated_gain_tl"] for r in items),
        }
        trend = bucket_oee_series(events, production, line, bucket=bucket)

    return {
        "meta": {
            "line_id": line.id,
            "line_name": line.name,
            "data_dir": str(data_dir),
            "adapter": adapter,
            "window": {
                "from": frm.isoformat() if frm else None,
                "to": to.isoformat() if to else None,
            },
            "generated_at": None,  # main doldurur (--generated-at ile ezilebilir)
        },
        "has_data": has_data,
        "quality": {
            "event_count": q["event_count"],
            "span_min": q["span_min"],
            "microstop_entry_coverage": q["microstop_entry_coverage"],
            "sufficiency": sufficiency,
            "accepted": ingest["accepted"],
            "rejected_count": ingest["rejected_count"],
            "reject_rate": reject_rate,
            "skipped": ingest["skipped"],
        },
        "oee": oee_dict,
        "losses": losses,
        "recommendations": recs,
        "trend": trend,
        "criteria": _evaluate_criteria(losses, recs, sufficiency, reject_rate),
    }


def _in_window(ts, frm: datetime | None, to: datetime | None) -> bool:
    dt = ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts))
    if frm and dt < frm:
        return False
    if to and dt > to:
        return False
    return True
