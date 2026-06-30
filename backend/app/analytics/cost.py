"""Kayıp ağacını ortak birime (TL) çevirir → kategoriler-arası tek Pareto + parasal toplam.

Birim maliyetler CostConfig'ten gelir (config/costs.yaml); kodda gömülü sayı YOK.
Maliyet modeli simülatör `costs` bloğuyla hizalıdır (parite için):
  DOWNTIME/MICROSTOP = dk × downtime/microstop oranı, SPEED_LOSS = dk × speed oranı,
  FILL/REDO = parça × ilgili parça oranı (no-scrap: hurda kanalı yok).
FIREWALL: yalnız genel kayıp ağacı + config maliyetleri kullanılır; ground_truth ALMAZ.
"""
from __future__ import annotations

from app.analytics.confidence import band
from app.analytics.loss_tree import CATEGORIES, LossTree, axis_of, kind_of
from app.config import ConfidenceConfig, CostConfig

# Kategori -> CostConfig alanı. Tek doğruluk kaynağı (DRY). No-scrap: hurda yok.
_RATE_FIELD = {
    "DOWNTIME": "downtime_tl_per_min",
    "MICROSTOP": "microstop_tl_per_min",
    "SPEED_LOSS": "speed_tl_per_min",
    "FILL_LOSS": "fill_tl_per_part",
    "QUALITY_REDO": "redo_tl_per_part",
}


def category_tl(category: str, tree: LossTree, costs: CostConfig) -> float:
    """Tek kategorinin TL karşılığı (doğal eksen × ilgili birim oran)."""
    rate = getattr(costs, _RATE_FIELD[category])
    return tree.value(category) * rate


def to_tl(
    tree: LossTree,
    costs: CostConfig,
    confidence_cfg: ConfidenceConfig | None = None,
    sufficiency: float = 1.0,
) -> dict:
    """Kayıp ağacını TL'ye çevirir; TL'ye göre AZALAN sıralı liste + total_tl döner.

    Dönen yapı:
      {"categories": [{category, axis, value, tl, kind,
                       tl_low, tl_high, confidence, low_confidence}, ...],
       "total_tl": float}

    Belirsizlik (H3): `confidence_cfg` verilirse ÇIKARIM kanalları (FILL/SPEED) için
    nokta TL etrafında bant + `sufficiency`'den güven üretilir; GÖRÜNÜR kanallar tam
    güven (bant=nokta). `total_tl` daima NOKTA toplamdır (değişmez). cfg yoksa geriye
    uyumlu: bant=nokta, confidence=1.
    """
    cats = []
    for c in CATEGORIES:
        tl = category_tl(c, tree, costs)
        kind = kind_of(c)
        tl_low, tl_high, confidence = _band_for(tl, kind, confidence_cfg, sufficiency)
        threshold = confidence_cfg.sufficiency_threshold if confidence_cfg else 0.0
        cats.append({
            "category": c,
            "axis": axis_of(c),
            "value": tree.value(c),
            "tl": tl,
            "kind": kind,
            "tl_low": tl_low,
            "tl_high": tl_high,
            "confidence": confidence,
            "low_confidence": confidence < threshold,
        })
    cats.sort(key=lambda x: x["tl"], reverse=True)
    return {"categories": cats, "total_tl": sum(c["tl"] for c in cats)}


def _band_for(
    tl: float, kind: str, cfg: ConfidenceConfig | None, sufficiency: float
) -> tuple[float, float, float]:
    """(tl_low, tl_high, confidence). Görünür kanal: tam güven, bant=nokta.
    Çıkarım kanalı (cfg varsa): nokta TL etrafında bant + güven = yeterlilik skoru."""
    if cfg is None or kind != "inferred":
        return tl, tl, 1.0
    low, high = band(tl, sufficiency, cfg)
    return low, high, max(0.0, min(1.0, sufficiency))
