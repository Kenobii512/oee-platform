"""Veri güvenilirliği — operatörün tek manuel girdisi: mikro duruş kapsamı (G10).

Saha modeli: operatör YALNIZ mikro duruşları elle girer; duruş/hız/doluluk/kalite
sistemce (PLC/sayaç/kalite istasyonu) otomatik ölçülür. Bu yüzden tek anlamlı veri-kalite
göstergesi `microstop_entry_coverage` = `operator_entered_reason` DOLU olan MICROSTOP
olaylarının oranı. Düşük çıkması beklenir (operatör çoğunu girmez) — içgörü, kusur değil;
ürünün manuel-takibe karşı satış argümanı (neredeyse hiç manuel girdi). `ground_truth` KULLANMAZ.
"""
from __future__ import annotations

from app.analytics.oee import availability_from_events

# Yetersiz-veri eşikleri: bu altında çıkarım/OEE güvenilmez sayılır (açık sinyal).
_MIN_EVENTS = 10
_MIN_SPAN_MIN = 5.0


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


def coverage(events: list[dict], production: list[dict]) -> dict:
    """Veri-yeterlilik özeti: olay yoğunluğu + kapsanan süre + manuel giriş kapsamı.

    `sufficient=False` → "yetersiz/güvenilmez veri": kısmi/boş pencerede çıkarım ve OEE
    sessizce 0/NaN dönmek yerine açıkça işaretlenir. Eşikler şeffaf sabit (H3 köprüsü).
    `ground_truth` KULLANMAZ.
    """
    event_count = len(events)
    span_min = availability_from_events(events)[1] if events else 0.0
    sufficient = (
        event_count >= _MIN_EVENTS and span_min >= _MIN_SPAN_MIN and bool(production)
    )
    return {
        **entry_coverage(events),
        "event_count": event_count,
        "span_min": span_min,
        "sufficient": sufficient,
    }
