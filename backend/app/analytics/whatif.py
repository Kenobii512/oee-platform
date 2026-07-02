"""What-if analitiği: kategori bazlı azaltım oranları → önce/sonra OEE + TL kazanç.

Satış/karar destek: "duruşu %30 azaltsam ne olur?" sorusuna ANALİTİK cevap
(simülatör koşulmaz; formüller şeffaf ve oee.py'nin yardımcılarını kullanır —
metrik mantığı kopyalanmaz, tek doğruluk kaynağı korunur):

- A' = clamp((span − union')/span);  union' = clamp(union − DT·p_dt − MS·p_ms, 0, union)
- P' = clamp(ideal / max(ideal, actual − SPEED·p_speed));  actual = Σ PROCESS süresi
- Q' = clamp((loaded − redo·(1−p_redo)) / loaded)
- OEE' = A'·P'·Q';  FILL yalnız TL kazancına katkı (G12: doluluk Q'da değil)
- Kazanç: kategori başına tl·p, bant tl_low·p – tl_high·p (H3 bantları taşınır)

Dürüstlük: kalemler bağımsız kabul edilir (örtüşebilir) — UI çekincesi zorunlu.
"""
from __future__ import annotations

from app.analytics.nominal import nominal_full_pass
from app.analytics.oee import _clamp01, availability_from_events
from app.models.contract import LineDefinition

# reductions anahtarları (API query paramlarıyla birebir).
KEYS = ("downtime", "microstop", "speed_loss", "quality_redo", "fill_loss")
_CAT = {  # reductions anahtarı -> kayıp ağacı kategorisi
    "downtime": "DOWNTIME",
    "microstop": "MICROSTOP",
    "speed_loss": "SPEED_LOSS",
    "quality_redo": "QUALITY_REDO",
    "fill_loss": "FILL_LOSS",
}


def compute_whatif(
    events: list[dict],
    production: list[dict],
    line: LineDefinition,
    cost_tree: dict,
    reductions: dict[str, float],
) -> dict:
    """(baseline, adjusted, gain) döndürür. Boş veri → sıfırlar (çökme yok)."""
    tl_by_cat = {c["category"]: c for c in cost_tree["categories"]}

    def _val(key: str) -> float:
        return float(tl_by_cat.get(_CAT[key], {}).get("value", 0.0))

    # --- baseline bileşenleri (oee.py yardımcılarıyla) ---
    if events and production:
        avail, span, union = availability_from_events(events)
        ideal = len(production) * nominal_full_pass(line)
        actual = sum(e["duration"] for e in events if e["event_type"] == "PROCESS")
        perf = _clamp01(ideal / actual) if actual > 0 else 0.0
        loaded = sum(p["loaded_qty"] for p in production)
        redo = sum(p["redo_count"] for p in production)
        qual = _clamp01((loaded - redo) / loaded) if loaded > 0 else 0.0
    else:
        avail = perf = qual = 0.0
        span = union = ideal = actual = 0.0
        loaded = redo = 0

    baseline = {
        "availability": avail,
        "performance": perf,
        "quality": qual,
        "oee": avail * perf * qual,
    }

    # --- azaltılmış bileşenler ---
    p = {k: float(reductions.get(k, 0.0)) for k in KEYS}
    if span > 0:
        dt_red = _val("downtime") * p["downtime"] + _val("microstop") * p["microstop"]
        # Görünür DT+MS toplamı örtüşme yüzünden union'ı aşabilir -> [0, union] kelepçesi.
        union_adj = min(union, max(0.0, union - dt_red))
        a2 = _clamp01((span - union_adj) / span)
    else:
        a2 = 0.0
    if actual > 0 and ideal > 0:
        actual_adj = max(ideal, actual - _val("speed_loss") * p["speed_loss"])
        p2 = _clamp01(ideal / actual_adj)
    else:
        p2 = 0.0
    if loaded > 0:
        q2 = _clamp01((loaded - redo * (1.0 - p["quality_redo"])) / loaded)
    else:
        q2 = 0.0

    adjusted = {"availability": a2, "performance": p2, "quality": q2, "oee": a2 * p2 * q2}

    # --- TL kazancı (H3 bantları oranla taşınır) ---
    per = []
    for key in KEYS:
        cat = _CAT[key]
        entry = tl_by_cat.get(cat)
        if entry is None or p[key] <= 0:
            continue
        per.append({
            "category": cat,
            "reduction": p[key],
            "gain_tl": entry["tl"] * p[key],
            "gain_tl_low": entry.get("tl_low", entry["tl"]) * p[key],
            "gain_tl_high": entry.get("tl_high", entry["tl"]) * p[key],
            "kind": entry.get("kind", "visible"),
        })
    gain = {
        "total_tl": sum(x["gain_tl"] for x in per),
        "total_tl_low": sum(x["gain_tl_low"] for x in per),
        "total_tl_high": sum(x["gain_tl_high"] for x in per),
        "per_category": per,
    }
    return {"baseline": baseline, "adjusted": adjusted, "gain": gain}
