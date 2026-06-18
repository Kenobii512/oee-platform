"""OEE trendi — yüklü veriyi gün/hafta pencerelerine bölüp pencere bazında OEE.

G4.1 (dönem-doğru üretim atfı): `events.csv`'de artık `carrier_id` var → her askı,
kendisine ait olayların EN GEÇ zaman damgasına (hattı terk ettiği an) göre bir pencereye
atfedilir. Böylece Performance ve Quality pencere bazında DOĞRU değişir (yalnız
Availability değil). Her pencere için tam `compute_oee(pencere_events, pencere_production)`
hesaplanır. Üretimi olmayan pencerede P/Q (çıktı yok) düşer; bu dürüst bir sonuçtur.
"""
from __future__ import annotations

from datetime import datetime

from app.analytics.oee import compute_oee
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


def _carrier_times(events: list[dict]) -> dict[str, datetime]:
    """Her askının temsil zamanı = ona ait olayların EN GEÇ timestamp'i (çıkış anı)."""
    times: dict[str, datetime] = {}
    for e in events:
        cid = e.get("carrier_id")
        if not cid:
            continue
        dt = _to_datetime(e["timestamp"])
        prev = times.get(cid)
        if prev is None or dt > prev:
            times[cid] = dt
    return times


def bucket_oee_series(
    events: list[dict],
    production: list[dict],
    line: LineDefinition,
    bucket: str = "day",
) -> list[dict]:
    """Pencere bazında OEE serisi (artan dönem sırasıyla). P/Q pencere-doğru (G4.1)."""
    if not events or not production:
        return []

    carrier_times = _carrier_times(events)

    event_groups: dict[str, list[dict]] = {}
    for e in events:
        key = _bucket_key(_to_datetime(e["timestamp"]), bucket)
        event_groups.setdefault(key, []).append(e)

    prod_groups: dict[str, list[dict]] = {}
    for p in production:
        ts = carrier_times.get(p.get("carrier_id"))
        if ts is None:
            continue
        key = _bucket_key(ts, bucket)
        prod_groups.setdefault(key, []).append(p)

    series: list[dict] = []
    for key in sorted(event_groups):
        ev = event_groups[key]
        pr = prod_groups.get(key, [])
        res = compute_oee(ev, pr, line)
        series.append(
            {
                "period": key,
                "availability": res.availability,
                "performance": res.performance,
                "quality": res.quality,
                "final_yield": res.final_yield,
                "oee": res.oee,
            }
        )
    return series
