"""Veri güvenilirliği — operatörün tek manuel girdisi: mikro duruş kapsamı (G10).

Saha modeli: operatör YALNIZ mikro duruşları elle girer; duruş/hız/doluluk/kalite
sistemce (PLC/sayaç/kalite istasyonu) otomatik ölçülür. Bu yüzden tek anlamlı veri-kalite
göstergesi `microstop_entry_coverage` = `operator_entered_reason` DOLU olan MICROSTOP
olaylarının oranı. Düşük çıkması beklenir (operatör çoğunu girmez) — içgörü, kusur değil;
ürünün manuel-takibe karşı satış argümanı (neredeyse hiç manuel girdi). `ground_truth` KULLANMAZ.
"""
from __future__ import annotations


def _coverage(events: list[dict], event_type: str) -> float:
    sub = [e for e in events if e["event_type"] == event_type]
    if not sub:
        return 0.0
    filled = sum(
        1 for e in sub if (e.get("operator_entered_reason") or "").strip()
    )
    return filled / len(sub)


def entry_coverage(events: list[dict]) -> dict[str, float]:
    """Operatörün tek manuel kanalı: mikro duruş giriş kapsamı (G10)."""
    return {
        "microstop_entry_coverage": _coverage(events, "MICROSTOP"),
    }
