"""Paylaşılan nominal/çıkarım yardımcıları.

`oee.py` (Performance + Quality fallback) ve `loss_tree.py` (FILL/SPEED çıkarımı)
aynı nominal hesaplarını kullanır; tek doğruluk kaynağı burasıdır (DRY).
"""
from __future__ import annotations

from app.models.contract import LineDefinition


def inferred_nominal_per_order(production: list[dict]) -> dict[str, int]:
    """İş emri başına gözlenen en büyük loaded_qty → nominal askı kapasitesi çıkarımı.

    Doluluk kaybı (FILL_LOSS) ve config kapasitesi yoksa Quality paydası bu nominali
    kullanır (accuracy.py deseni). Gerçek kapasite public veride yok; en dolu askı
    nominal kabul edilir.
    """
    nominal: dict[str, int] = {}
    for p in production:
        nominal[p["order_id"]] = max(nominal.get(p["order_id"], 0), p["loaded_qty"])
    return nominal


def nominal_full_pass(line: LineDefinition) -> float:
    """Nominal tam-geçiş süresi (dk): Σ (time_min+time_max)/2, tüm tanklar üzerinden."""
    return sum((t.time_min + t.time_max) / 2.0 for t in line.tanks)
