"""Hızlandırılmış replay: olayları zaman-sıralı 'şimdiye kadar' pencerelerinde özetler.

Mevcut analytics yeniden kullanılır (yeni iş kuralı YOK). FIREWALL: ground_truth ALMAZ.
G4.1 sınırı: pencere yalnız events'e uygulanır → Availability + kayıp-zaman kanalları + TL
ilerledikçe BÜYÜR (canlı anlatının özü); P/Q dönem-geneli kalır (carrier dönem damgası yok).
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.analytics.cost import to_tl
from app.analytics.loss_tree import extract_loss_tree
from app.analytics.oee import compute_oee
from app.analytics.recommend import RatioGainEstimator, generate_recommendations


def time_steps(timestamps: list[Any], n_steps: int) -> list[Any]:
    """Olay zaman damgalarından artan N kesim noktası (ilk→son). Determinist (indeks tabanlı)."""
    if not timestamps or n_steps <= 0:
        return []
    ts = sorted(timestamps)
    last = len(ts) - 1
    cuts = []
    for i in range(n_steps):
        j = min(last, round((i + 1) * last / n_steps))
        cuts.append(ts[j])
    return cuts


def snapshot_at(repo, line, costs, rec_cfg, to) -> dict:
    """Tek 'şimdiye kadar' snapshot'ı (to dahil). to=None → tüm veri."""
    events = repo.fetch_events(None, to)
    production = repo.fetch_production()
    oee = compute_oee(events, production, line)
    tree = extract_loss_tree(events, production, line)
    cost = to_tl(tree, costs)
    recs = generate_recommendations(cost, events, rec_cfg, RatioGainEstimator(rec_cfg))
    return {
        "to": str(to) if to is not None else None,
        "oee": {
            "oee": oee.oee,
            "availability": oee.availability,
            "performance": oee.performance,
            "quality": oee.quality,
        },
        "cost": cost,
        "total_estimated_gain_tl": sum(r["estimated_gain_tl"] for r in recs),
        "event_count": len(events),
    }


def iter_snapshots(repo, line, costs, rec_cfg, n_steps: int = 60) -> Iterator[dict]:
    """N adımlı 'şimdiye kadar' snapshot dizisi (zaman ilerledikçe büyüyen pencere)."""
    all_events = repo.fetch_events(None, None)
    stamps = [e["timestamp"] for e in all_events if e.get("timestamp") is not None]
    for cut in time_steps(stamps, n_steps):
        yield snapshot_at(repo, line, costs, rec_cfg, cut)
