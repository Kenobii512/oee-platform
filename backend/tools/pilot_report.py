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

import argparse
import html as _html
import math
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import yaml

from app.analytics.confidence import data_sufficiency
from app.analytics.cost import to_tl
from app.analytics.data_quality import coverage
from app.analytics.loss_tree import extract_loss_tree
from app.analytics.oee import compute_oee
from app.analytics.recommend import RatioGainEstimator, generate_recommendations
from app.analytics.trend import bucket_oee_series
from app.config import (
    line_definition_from_dict,
    load_app_config,
    load_confidence_config,
    load_cost_config,
    load_recommend_config,
)
from app.config_validate import validate_line_dict
from app.ingest.adapter import (
    AdapterError,
    adapt_dir_to_contract,
    load_adapter_config,
    resolve_profile_path,
)
from app.ingest.loader import load_csv_dir
from app.models.contract import LineDefinition
from app.store.duckdb_repo import DuckDBRepository
from tools.pilot_doctor import (
    DEFAULT_MAX_REJECT,
    DEFAULT_MIN_SUFFICIENCY,
    _eprint,
    rejection_rate,
)

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


# ---- render: SVG + kendine-yeten HTML ---------------------------------------
# Görsel dil: Foundry Gauge light (üst dizin DESIGN.md token'ları gömülü).
# Harici istek YOK: font @import yok (system-ui düşüşü), CDN yok, script yok.

# Frontend styles/theme.ts CATEGORY_LABEL ile birebir (pano-rapor tutarlılığı).
CATEGORY_LABEL = {
    "DOWNTIME": "Duruş",
    "MICROSTOP": "Mikro duruş",
    "QUALITY_REDO": "Yeniden işleme",
    "FILL_LOSS": "Eksik doluluk",
    "SPEED_LOSS": "Hız kaybı",
}

_MARK = {True: "✓", False: "✗", None: "—"}

# Güvensiz metin (hat adı, dosya yolu, öneri metni) HTML'e daima kaçışlanarak girer.
_esc = _html.escape

# DESIGN.md renk token'ları.
_C = {
    "accent": "#1f5da6",
    "amber": "#b5832f",
    "green": "#237a5c",
    "red": "#a8443a",
    "bg": "#edf1f5",
    "surface": "#ffffff",
    "inset": "#f2f5f8",
    "ink": "#16202b",
    "muted": "#58626f",
    "line": "#e2e7ec",
}


def _cat(code: str) -> str:
    return CATEGORY_LABEL.get(code, code)


def _tl_fmt(v: float) -> str:
    """Türkçe binlik ayraç + ₺: 12345.6 -> '12.346 ₺'."""
    return f"{v:,.0f}".replace(",", ".") + " ₺"


def _pct_fmt(v: float, digits: int = 1) -> str:
    """Oran (0-1) -> Türkçe ondalık virgüllü yüzde: 0.601 -> '60,1%'."""
    return f"{v * 100:.{digits}f}".replace(".", ",") + "%"


def _svg_pareto(categories: list[dict]) -> str:
    """TL Pareto: yatay çubuklar (azalan) + tl_low-tl_high aralık çizgisi."""
    w, bar_h, gap, label_w, pad = 680, 26, 12, 150, 8
    max_tl = max((c["tl_high"] for c in categories), default=0.0) or 1.0
    scale = (w - label_w - 120) / max_tl
    rows = []
    for i, c in enumerate(categories):
        y = pad + i * (bar_h + gap)
        bw = max(1.0, c["tl"] * scale)
        color = _C["accent"] if c["kind"] == "visible" else _C["amber"]
        lo_x = label_w + c["tl_low"] * scale
        hi_x = label_w + c["tl_high"] * scale
        badge = "" if c["kind"] == "visible" else " (çıkarımsal)"
        rows.append(
            f'<text x="{label_w - 8}" y="{y + bar_h / 2 + 4}" text-anchor="end" '
            f'class="cat">{_esc(_cat(c["category"]))}{badge}</text>'
            f'<rect class="bar" x="{label_w}" y="{y}" width="{bw:.1f}" '
            f'height="{bar_h}" rx="2" fill="{color}" opacity="0.9"/>'
            f'<line x1="{lo_x:.1f}" x2="{hi_x:.1f}" y1="{y + bar_h / 2}" '
            f'y2="{y + bar_h / 2}" stroke="{_C["ink"]}" stroke-width="2" opacity="0.55"/>'
            f'<text x="{label_w + bw + 8:.1f}" y="{y + bar_h / 2 + 4}" class="val">'
            f"{_esc(_tl_fmt(c['tl']))}</text>"
        )
    h = pad * 2 + len(categories) * (bar_h + gap)
    return (
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="TL Pareto">'
        f"{''.join(rows)}</svg>"
    )


def _svg_trend(trend: list[dict]) -> str:
    """Günlük/haftalık OEE çizgisi (>=3 nokta; azı çağıran notla ele alır)."""
    w, h, pad_l, pad_b, pad_t = 680, 190, 46, 26, 12
    n = len(trend)
    xs = [pad_l + i * (w - pad_l - 16) / max(1, n - 1) for i in range(n)]
    ys = [pad_t + (1.0 - p["oee"]) * (h - pad_t - pad_b) for p in trend]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{_C["accent"]}"/>'
        for x, y in zip(xs, ys)
    )
    grid = "".join(
        f'<line x1="{pad_l}" x2="{w - 16}" '
        f'y1="{pad_t + (1 - g) * (h - pad_t - pad_b):.1f}" '
        f'y2="{pad_t + (1 - g) * (h - pad_t - pad_b):.1f}" '
        f'stroke="{_C["line"]}" stroke-width="1"/>'
        f'<text x="{pad_l - 6}" y="{pad_t + (1 - g) * (h - pad_t - pad_b) + 4:.1f}" '
        f'text-anchor="end" class="val">{_pct_fmt(g, 0)}</text>'
        for g in (0.0, 0.25, 0.5, 0.75, 1.0)
    )
    first, last = trend[0]["period"], trend[-1]["period"]
    return (
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="OEE trend">{grid}'
        f'<polyline points="{pts}" fill="none" stroke="{_C["accent"]}" stroke-width="2.5"/>'
        f"{dots}"
        f'<text x="{pad_l}" y="{h - 6}" class="val">{_esc(str(first))}</text>'
        f'<text x="{w - 16}" y="{h - 6}" text-anchor="end" class="val">{_esc(str(last))}</text>'
        "</svg>"
    )


_NO_DATA = '<p class="nodata">veri yok — bu bölüm hesaplanamadı</p>'


def _sec_oee(oee: dict | None) -> str:
    if oee is None:
        return _NO_DATA
    cells = [
        ("OEE", oee["oee"], _C["ink"]),
        ("Kullanılabilirlik", oee["availability"], _C["green"]),
        ("Performans", oee["performance"], "#535f8a"),
        ("Kalite (ilk geçiş)", oee["quality"], _C["red"]),
    ]
    big = "".join(
        f'<div class="kpi"><div class="kpi-label">{_esc(k)}</div>'
        f'<div class="kpi-value" style="color:{c}">{_pct_fmt(v)}</div></div>'
        for k, v, c in cells
    )
    return (
        f'<div class="kpis">{big}</div>'
        f'<p class="note">Kullanım (takvime göre): {_pct_fmt(oee["utilization"])} · '
        f'Nihai verim: {_pct_fmt(oee["final_yield"])} · '
        f'Planlı duruş: {oee["planned_downtime_min"]:.0f} dk</p>'
    )


def _sec_losses(losses: dict | None) -> str:
    if losses is None:
        return _NO_DATA
    rows = "".join(
        f"<tr><td>{_esc(_cat(c['category']))}</td>"
        f"<td>{'görünür' if c['kind'] == 'visible' else 'çıkarımsal'}</td>"
        f"<td class=\"num\">{_esc(_tl_fmt(c['tl']))}</td>"
        f"<td class=\"num\">{_esc(_tl_fmt(c['tl_low']))} – {_esc(_tl_fmt(c['tl_high']))}</td>"
        f"<td>{'düşük güven' if c['low_confidence'] else ''}</td></tr>"
        for c in losses["categories"]
    )
    return (
        _svg_pareto(losses["categories"])
        + '<table><thead><tr><th>Kayıp</th><th>Tür</th><th>TL</th>'
        "<th>Aralık</th><th></th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f'<p class="note">Toplam kayıp: <b>{_esc(_tl_fmt(losses["total_tl"]))}</b> '
        "(nokta toplam; çıkarımsal kalemlerde aralık geçerli)</p>"
    )


def _sec_recs(recs: dict | None) -> str:
    if recs is None:
        return _NO_DATA
    rows = "".join(
        f"<tr><td><b>{_esc(r['title'])}</b><br><span class=\"muted\">"
        f"{_esc(r['action'])}</span></td>"
        f"<td class=\"num\">{_esc(_tl_fmt(r['estimated_gain_tl_low']))} – "
        f"{_esc(_tl_fmt(r['estimated_gain_tl_high']))}</td></tr>"
        for r in recs["items"]
    )
    return (
        "<table><thead><tr><th>Öneri</th><th>Tahmini kazanç (aralık)</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f'<p class="note">Toplam tahmini kazanç: <b>{_esc(_tl_fmt(recs["total_gain_tl"]))}</b> — '
        "<b>üst sınır</b>; kalemler örtüşebilir, aynı vardiyada tamamı birden gerçekleşmeyebilir.</p>"
    )


def _sec_criteria(criteria: dict) -> str:
    row_meta = [
        ("1 — Bilinmeyen kayıp", "k1",
         'Ekip onayı: "bu kaybı takip etmiyorduk" ____'),
        ("2 — TL tasarruf fırsatı", "k2", "____"),
        ("3 — Güvenilir veri akışı", "k3", "Saha gözlemi: uçlar &lt; 2 sn ____"),
    ]
    rows = "".join(
        f"<tr><td>{_esc(name)}</td>"
        f'<td class="mark">{_MARK[criteria[key]["auto_pass"]]}</td>'
        f"<td>{_esc(criteria[key]['detail'])}</td>"
        f"<td>{manual}</td></tr>"
        for name, key, manual in row_meta
    )
    return (
        "<table><thead><tr><th>Kriter</th><th>Otomatik</th>"
        "<th>Ölçüm</th><th>Elle doldurulacak</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        '<p class="fill">Pilot süresi: ____ – ____ &nbsp;·&nbsp; Değerlendiren: ____</p>'
        '<p class="fill"><b>Genel karar:</b> ☐ GO &nbsp; ☐ İyileştir &nbsp; ☐ Durdur '
        "&nbsp;·&nbsp; Gerekçe: ____</p>"
    )


def render_html(data: dict) -> str:
    """Rapor dict'ini kendine-yeten tek HTML dosyasına çevirir (veri kaynağını bilmez)."""
    meta = data["meta"]
    q = data["quality"]
    reject = q["reject_rate"]
    trend = data["trend"]
    trend_html = (
        _svg_trend(trend)
        if len(trend) >= 3
        else '<p class="nodata">trend için yeterli geçmiş yok (en az 3 dönem gerekli)</p>'
    )
    title = _esc(meta.get("line_name") or meta.get("line_id") or "Hat")
    window = meta.get("window") or {}
    win_txt = (
        f"{_esc(window.get('from') or 'başlangıç')} – {_esc(window.get('to') or 'son')}"
        if (window.get("from") or window.get("to"))
        else "verinin tamamı"
    )
    guven = (
        '<p>Bu rapordaki kayıplar iki türdür: <b>görünür</b> (doğrudan ölçülen: duruş, '
        "mikro duruş, yeniden işleme) ve <b>çıkarımsal</b> (veriden türetilen: eksik doluluk, "
        "hız kaybı). Çıkarımsal kalemler nokta değer yerine <b>aralıkla</b> (alt–üst sınır) "
        "raporlanır; veri yeterliliği düştükçe aralık genişler ve kalem 'düşük güven' işareti "
        "alır. <b>Abartı yok:</b> kazançlar üst sınırdır, kalemler örtüşebilir — bu rapor "
        "kesinlik değil <b>görünürlük</b> satar.</p>"
        f'<p class="note">Veri yeterliliği (H3): <b>{q["sufficiency"]:.2f}</b> · '
        f"Reddedilen satır oranı: <b>{_pct_fmt(reject) if reject is not None else '—'}</b> · "
        f"Olay sayısı: {q['event_count']} · Kapsanan süre: {q['span_min']:.0f} dk</p>"
    )
    gen = _esc(meta.get("generated_at") or "____")
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pilot Raporu — {title}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: {_C["bg"]}; color: {_C["ink"]};
         font: 400 0.92rem/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  .page {{ max-width: 820px; margin: 0 auto; padding: 28px 20px 60px; }}
  header {{ border-bottom: 3px solid {_C["accent"]}; padding-bottom: 14px; margin-bottom: 22px; }}
  h1 {{ font-size: 1.7rem; letter-spacing: -0.01em; margin: 0 0 4px; }}
  h2 {{ font-size: 0.78rem; font-weight: 700; letter-spacing: 0.14em;
        text-transform: uppercase; color: {_C["muted"]};
        border-bottom: 1px solid {_C["line"]}; padding-bottom: 6px; margin: 30px 0 12px; }}
  .meta {{ color: {_C["muted"]}; font-size: 0.85rem; }}
  section {{ background: {_C["surface"]}; border: 1px solid {_C["line"]};
             border-radius: 10px; padding: 16px 18px; margin-bottom: 14px; }}
  .kpis {{ display: flex; gap: 14px; flex-wrap: wrap; }}
  .kpi {{ flex: 1 1 140px; background: {_C["inset"]}; border-radius: 8px; padding: 10px 12px; }}
  .kpi-label {{ font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em;
                text-transform: uppercase; color: {_C["muted"]}; }}
  .kpi-value {{ font-size: 1.9rem; font-weight: 800; letter-spacing: -0.01em; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.88rem; }}
  th {{ text-align: left; font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase;
       color: {_C["muted"]}; border-bottom: 1px solid {_C["line"]}; padding: 6px 8px; }}
  td {{ border-bottom: 1px solid {_C["line"]}; padding: 7px 8px; vertical-align: top; }}
  td.num {{ text-align: right; white-space: nowrap;
            font-family: ui-monospace, Consolas, monospace; font-size: 0.84rem; }}
  td.mark {{ font-size: 1.1rem; text-align: center; }}
  .muted {{ color: {_C["muted"]}; }}
  .note {{ color: {_C["muted"]}; font-size: 0.84rem; }}
  .nodata {{ color: {_C["amber"]}; font-style: italic; }}
  .fill {{ letter-spacing: 0.02em; }}
  svg {{ width: 100%; height: auto; display: block; margin: 6px 0; }}
  svg text {{ font: 600 12px system-ui, sans-serif; fill: {_C["ink"]}; }}
  svg text.cat {{ font-weight: 700; }}
  svg text.val {{ font: 500 11px ui-monospace, Consolas, monospace; fill: {_C["muted"]}; }}
  footer {{ margin-top: 26px; color: {_C["muted"]}; font-size: 0.78rem; }}
  @media print {{ body {{ background: #fff; }} section {{ border: none; padding: 0 0 8px; }} }}
</style>
</head>
<body><div class="page">
<header>
  <h1>Pilot Raporu — {title}</h1>
  <div class="meta">Pencere: {win_txt} · Üretildi: {gen} ·
  Hat: {_esc(str(meta.get("line_id") or ""))}{" · adaptör: " + _esc(meta["adapter"]) if meta.get("adapter") else ""}</div>
</header>
<section><h2>OEE</h2>{_sec_oee(data["oee"])}</section>
<section><h2>En büyük kayıplar (TL Pareto)</h2>{_sec_losses(data["losses"])}</section>
<section><h2>TL fırsatı — öneriler</h2>{_sec_recs(data["recommendations"])}</section>
<section><h2>Trend (OEE)</h2>{trend_html}</section>
<section><h2>Güven notu</h2>{guven}</section>
<section><h2>Başarı kriterleri değerlendirmesi</h2>{_sec_criteria(data["criteria"])}</section>
<footer>Bu rapor <code>python -m tools.pilot_report</code> ile üretildi ·
OEE Platform pilot kiti (Faz 3 artefaktı) · Yazdır → PDF için tarayıcı yazdırma kullanılabilir.</footer>
</div></body>
</html>
"""


# ---- CLI -------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pilot_report",
        description="Faz 3 pilot raporu: tek dosya, kendine-yeten HTML artefakti.",
    )
    parser.add_argument("data_dir", help="sozlesme CSV dizini (adapter verilirse ham dizin)")
    parser.add_argument("--adapter", default=None, help="config/adapters/<AD>.yaml profili")
    parser.add_argument("--line", default=None,
                        help="hat tanimi YAML (vars. OEE_LINE_CONFIG env ya da "
                             "config/line_default.yaml - sunucuyla ayni cozum)")
    parser.add_argument("--from", dest="frm", default=None,
                        help="pencere baslangici (ISO, orn. 2026-01-06)")
    parser.add_argument("--to", dest="to", default=None, help="pencere sonu (ISO)")
    parser.add_argument("--bucket", choices=("day", "week"), default="day",
                        help="trend kovasi (vars. day)")
    parser.add_argument("-o", "--out", default="pilot-raporu.html",
                        help="cikti HTML yolu (vars. ./pilot-raporu.html)")
    parser.add_argument("--generated-at", default=None,
                        help="kunyedeki uretim zamanini sabitle (tekrar-uretilebilir "
                             "ornek/test icin); vars. simdiki zaman")
    args = parser.parse_args(argv)

    # Kullanim hatalari (exit 2): rapor uretilemeden once dogrulanir.
    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        _eprint(f"HATA: veri dizini yok ya da dizin degil: {data_dir}")
        return 2
    line_path = Path(args.line) if args.line else Path(load_app_config().line_config_path)
    if not line_path.is_file():
        _eprint(f"HATA: hat tanimi dosyasi yok: {line_path}")
        return 2
    if args.adapter and not resolve_profile_path(args.adapter).is_file():
        _eprint(f"HATA: bilinmeyen adapter profili: {args.adapter!r}")
        return 2
    try:
        frm = datetime.fromisoformat(args.frm) if args.frm else None
        to = datetime.fromisoformat(args.to) if args.to else None
    except ValueError as exc:
        _eprint(f"HATA: tarih ISO bicimde olmali (orn. 2026-01-06): {exc}")
        return 2

    # Hat tanimi: rapor gecerli hat olmadan uretilemez (teshis icin pilot_doctor kullanin).
    try:
        with open(line_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        _eprint(f"HATA: hat YAML okunamadi/bozuk: {exc}")
        return 2
    errors = validate_line_dict(raw) if isinstance(raw, dict) else ["kok yapi nesne degil"]
    if errors:
        _eprint("HATA: hat tanimi gecersiz: " + "; ".join(errors))
        return 2
    line = line_definition_from_dict(raw)

    try:
        data = build_report_data(
            data_dir, line, adapter=args.adapter, frm=frm, to=to, bucket=args.bucket
        )
    except AdapterError as exc:
        _eprint(f"HATA: adapter eslemesi basarisiz (once pilot_doctor kosun): {exc}")
        return 2

    data["meta"]["generated_at"] = args.generated_at or datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )
    out = Path(args.out)
    out.write_text(render_html(data), encoding="utf-8", newline="\n")
    print(f"OK: {out}")  # ASCII konsol mesaji (cp1252 guvenli)
    return 0


if __name__ == "__main__":
    sys.exit(main())
