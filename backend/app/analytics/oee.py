"""OEE motoru — tek doğruluk kaynağı. Yalnız genel veriden (events, production +
hat tanımı) Availability/Performance/Quality/OEE hesaplar.

Tanımlar simülatör `src/metrics.py` ile BİREBİR:
- Availability = (span − union(DOWNTIME∪MICROSTOP)) / span. Örtüşen duruşlar bir kez.
- Performance  = (askı × Σ nominal tam-geçiş) / Σ PROCESS süresi.
- Quality      = Σ good / Σ intended. intended = hat tanımı askı kapasitesi (master-data);
                 yoksa iş emri başına max(loaded_qty) çıkarımı (accuracy.py deseni).
- OEE = A × P × Q.

Ayrıca utilization (planlı bakım) ayrı raporlanır; OEE'yi etkilemez.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.models.contract import LineDefinition

_DOWNTIME_TYPES = {"DOWNTIME", "MICROSTOP"}


@dataclass(frozen=True)
class OeeResult:
    availability: float
    performance: float
    quality: float
    oee: float
    utilization: float
    planned_downtime_min: float


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def union_length(intervals: list[tuple[float, float]]) -> float:
    """Aralık birleşiminin toplam uzunluğu (örtüşenler bir kez). metrics.py ile aynı."""
    if not intervals:
        return 0.0
    intervals = sorted(intervals)
    total = 0.0
    cur_start, cur_end = intervals[0]
    for start, end in intervals[1:]:
        if start > cur_end:
            total += cur_end - cur_start
            cur_start, cur_end = start, end
        else:
            cur_end = max(cur_end, end)
    total += cur_end - cur_start
    return total


def _to_minutes(ts) -> float:
    """timestamp (datetime veya ISO str veya float dakika) -> dakika ekseni.

    Birim testler float dakika geçer; gerçek veride datetime gelir ve en erken
    olaya göre göreli dakikaya çevrilir (çağıran tarafta normalize edilir)."""
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    return ts.timestamp() / 60.0


def availability_from_events(events: list[dict]) -> tuple[float, float, float]:
    """(availability, span_min, downtime_union_min). events: timestamp(min/datetime),
    duration(dk), event_type."""
    if not events:
        return 0.0, 0.0, 0.0
    starts = [_to_minutes(e["timestamp"]) for e in events]
    ends = [s + e["duration"] for s, e in zip(starts, events)]
    base = min(starts)
    span = max(ends) - base
    downtime = union_length([
        (_to_minutes(e["timestamp"]) - base, _to_minutes(e["timestamp"]) - base + e["duration"])
        for e in events
        if e["event_type"] in _DOWNTIME_TYPES
    ])
    avail = _clamp01((span - downtime) / span) if span > 0 else 0.0
    return avail, span, downtime


def _performance(events: list[dict], num_carriers: int, line: LineDefinition) -> float:
    nominal_full_pass = sum((t.time_min + t.time_max) / 2.0 for t in line.tanks)
    ideal = num_carriers * nominal_full_pass
    actual = sum(e["duration"] for e in events if e["event_type"] == "PROCESS")
    return _clamp01(ideal / actual) if actual > 0 else 0.0


def _quality(production: list[dict], line: LineDefinition) -> float:
    good = sum(p["good_count"] for p in production)
    if line.carrier_capacity:
        intended = sum(line.carrier_capacity.get(p["order_id"], 0) for p in production)
        if intended == 0:  # order_id'ler config'te yoksa çıkarıma düş
            intended = _inferred_intended(production)
    else:
        intended = _inferred_intended(production)
    return _clamp01(good / intended) if intended > 0 else 0.0


def _inferred_intended(production: list[dict]) -> int:
    """Fallback (accuracy.py deseni): iş emri başına gözlenen en büyük loaded_qty
    nominal kabul edilir; intended = Σ nominal."""
    nominal: dict[str, int] = {}
    for p in production:
        nominal[p["order_id"]] = max(nominal.get(p["order_id"], 0), p["loaded_qty"])
    return sum(nominal[p["order_id"]] for p in production)


def compute_oee(
    events: list[dict],
    production: list[dict],
    line: LineDefinition,
    planned_downtime_min: float = 0.0,
) -> OeeResult:
    if not events or not production:
        return OeeResult(0.0, 0.0, 0.0, 0.0, 0.0, planned_downtime_min)
    avail, span, _dt = availability_from_events(events)
    perf = _performance(events, len(production), line)
    qual = _quality(production, line)
    oee = avail * perf * qual
    operating = span * avail
    calendar = span + planned_downtime_min
    utilization = _clamp01(operating / calendar) if calendar > 0 else 0.0
    return OeeResult(avail, perf, qual, oee, utilization, planned_downtime_min)
