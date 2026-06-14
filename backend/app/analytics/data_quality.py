"""Veri güvenilirliği — operatör neden-giriş kapsamı (yalnız genel veriden).

Pano için tek bir "veri güvenilirliği" göstergesi: `operator_entered_reason` DOLU olan
DOWNTIME/MICROSTOP olaylarının oranı. Mikro duruşlarda düşük çıkması beklenir (operatör
çoğunu girmez) — bu bir içgörüdür, kusur değil. Tam panel G10. `ground_truth` KULLANMAZ.
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
    """DOWNTIME/MICROSTOP için operatör giriş kapsamı oranları."""
    return {
        "downtime_entry_coverage": _coverage(events, "DOWNTIME"),
        "microstop_entry_coverage": _coverage(events, "MICROSTOP"),
    }
