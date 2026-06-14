"""OEE trendi — yüklü veriyi gün/hafta pencerelerine bölüp pencere bazında OEE.

NOT (G5 MVP): `events.csv`'de carrier_id yok → production (askı sayımları) zaman
pencerelerine bölünemez. Bu yüzden Performance ve Quality dönem-geneli (sabit) alınır;
pencere bazında yalnız Availability (event tabanlı) değişir ve
`OEE_pencere = A_pencere × P_dönem × Q_dönem`. Dönem-doğru üretim atfı ayrı bir görev
(G4.1). Trend, kayıpların zaman içindeki seyrini Availability ekseninde gösterir.
"""
from __future__ import annotations

from datetime import datetime

from app.analytics.oee import availability_from_events, compute_oee
from app.models.contract import LineDefinition


def _to_datetime(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(str(ts))


def _bucket_key(dt: datetime, bucket: str) -> str:
    if bucket == "week":
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return dt.date().isoformat()


def bucket_oee_series(
    events: list[dict],
    production: list[dict],
    line: LineDefinition,
    bucket: str = "day",
) -> list[dict]:
    """Pencere bazında OEE serisi (artan dönem sırasıyla)."""
    if not events or not production:
        return []
    period = compute_oee(events, production, line)  # dönem-geneli P, Q

    groups: dict[str, list[dict]] = {}
    for e in events:
        key = _bucket_key(_to_datetime(e["timestamp"]), bucket)
        groups.setdefault(key, []).append(e)

    series: list[dict] = []
    for key in sorted(groups):
        avail, _span, _dt = availability_from_events(groups[key])
        series.append(
            {
                "period": key,
                "availability": avail,
                "performance": period.performance,
                "quality": period.quality,
                "oee": avail * period.performance * period.quality,
            }
        )
    return series
