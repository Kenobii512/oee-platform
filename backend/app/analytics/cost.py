"""Kayıp ağacını ortak birime (TL) çevirir → kategoriler-arası tek Pareto + parasal toplam.

Birim maliyetler CostConfig'ten gelir (config/costs.yaml); kodda gömülü sayı YOK.
Maliyet modeli simülatör `costs` bloğuyla hizalıdır (parite için):
  DOWNTIME/MICROSTOP = dk × downtime/microstop oranı, SPEED_LOSS = dk × speed oranı,
  FILL/REDO/SCRAP = parça × ilgili parça oranı.
FIREWALL: yalnız genel kayıp ağacı + config maliyetleri kullanılır; ground_truth ALMAZ.
"""
from __future__ import annotations

from app.analytics.loss_tree import CATEGORIES, LossTree, axis_of, kind_of
from app.config import CostConfig

# Kategori -> CostConfig alanı. Tek doğruluk kaynağı (DRY).
_RATE_FIELD = {
    "DOWNTIME": "downtime_tl_per_min",
    "MICROSTOP": "microstop_tl_per_min",
    "SPEED_LOSS": "speed_tl_per_min",
    "FILL_LOSS": "fill_tl_per_part",
    "QUALITY_REDO": "redo_tl_per_part",
    "QUALITY_SCRAP": "scrap_tl_per_part",
}


def category_tl(category: str, tree: LossTree, costs: CostConfig) -> float:
    """Tek kategorinin TL karşılığı (doğal eksen × ilgili birim oran)."""
    rate = getattr(costs, _RATE_FIELD[category])
    return tree.value(category) * rate


def to_tl(tree: LossTree, costs: CostConfig) -> dict:
    """Kayıp ağacını TL'ye çevirir; TL'ye göre AZALAN sıralı liste + total_tl döner.

    Dönen yapı:
      {"categories": [{category, axis, value, tl, kind}, ...], "total_tl": float}
    """
    cats = [
        {
            "category": c,
            "axis": axis_of(c),
            "value": tree.value(c),
            "tl": category_tl(c, tree, costs),
            "kind": kind_of(c),
        }
        for c in CATEGORIES
    ]
    cats.sort(key=lambda x: x["tl"], reverse=True)
    return {"categories": cats, "total_tl": sum(c["tl"] for c in cats)}
