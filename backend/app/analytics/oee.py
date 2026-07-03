"""OEE motoru — tek doğruluk kaynağı. Yalnız genel veriden (events, production +
hat tanımı) Availability/Performance/Quality/OEE hesaplar.

Tanımlar simülatör `src/metrics.py` ile BİREBİR:
- Availability = (span − union(DOWNTIME∪MICROSTOP)) / span. Örtüşen duruşlar bir kez.
- Performance  = (askı × Σ nominal tam-geçiş) / Σ PROCESS süresi.
- Quality      = ilk-geçiş kalite (first_pass) = (Σ loaded − Σ redo) / Σ loaded. No-scrap
                 modelinde redo'dan geçen parça (sonunda iyi olsa da) ilk geçişte iyi
                 sayılmaz → Q'yu düşürür (OEE standardı, rework cezası). Doluluk kaybı
                 Q'da değil, ayrı FILL_LOSS kanalındadır.
- final_yield  = Σ good / Σ loaded = nihai verim (no-scrap → ≈%100); OEE'yi etkilemez,
                 ayrı raporlanır (no-scrap sözünü görünür kılar).
- OEE = A × P × Q.

Ayrıca utilization (planlı bakım) ayrı raporlanır; OEE'yi etkilemez.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.analytics.nominal import nominal_full_pass
from app.models.contract import LineDefinition

_DOWNTIME_TYPES = {"DOWNTIME", "MICROSTOP"}


@dataclass(frozen=True)
class OeeResult:
    availability: float
    performance: float
    quality: float       # ilk-geçiş kalite (first_pass) — OEE'nin Q'su
    oee: float
    utilization: float
    planned_downtime_min: float
    final_yield: float = 1.0  # Σ good / Σ loaded (no-scrap → ≈%100)
    # Vardiya künyesi bağlamı: ham toplamlar + gözlem penceresi (dk).
    loaded_qty: float = 0.0
    good_count: float = 0.0
    redo_count: float = 0.0
    span_min: float = 0.0


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


def _norm(ts):
    """timestamp'i karşılaştırılabilir tipe getirir: float dakika ya da datetime.
    ISO str -> datetime. Epoch'a çevirmez (DST/saat-dilimi güvenli)."""
    if isinstance(ts, (int, float)):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts)
    return ts


def _minute_offsets(events: list[dict]) -> list[float]:
    """Her olayın başlangıç dakikasını en erken olaya göre döndürür.

    datetime'larda fark doğrudan datetime üzerinden alınır (`total_seconds`),
    yerel epoch dönüşümü yapılmaz; böylece çok-günlük/DST geçişli pencerede
    span bozulmaz. float dakika (birim testler) aynen kullanılır."""
    raw = [_norm(e["timestamp"]) for e in events]
    base = min(raw)
    offsets: list[float] = []
    for r in raw:
        if isinstance(r, (int, float)):
            offsets.append(float(r) - float(base))
        else:
            offsets.append((r - base).total_seconds() / 60.0)
    return offsets


def availability_from_events(events: list[dict]) -> tuple[float, float, float]:
    """(availability, span_min, downtime_union_min). events: timestamp(min/datetime),
    duration(dk), event_type. Süreler en erken olaya göre dakika eksenine taşınır."""
    if not events:
        return 0.0, 0.0, 0.0
    starts = _minute_offsets(events)
    ends = [s + e["duration"] for s, e in zip(starts, events)]
    span = max(ends) - min(starts)
    downtime = union_length([
        (s, s + e["duration"])
        for s, e in zip(starts, events)
        if e["event_type"] in _DOWNTIME_TYPES
    ])
    avail = _clamp01((span - downtime) / span) if span > 0 else 0.0
    return avail, span, downtime


def _performance(events: list[dict], num_carriers: int, line: LineDefinition) -> float:
    ideal = num_carriers * nominal_full_pass(line)
    actual = sum(e["duration"] for e in events if e["event_type"] == "PROCESS")
    return _clamp01(ideal / actual) if actual > 0 else 0.0


def _quality_metrics(production: list[dict]) -> tuple[float, float, float, float, float]:
    """(first_pass, final_yield, loaded, redo, good) döndürür (no-scrap modeli).

    first_pass = (Σ loaded − Σ redo) / Σ loaded → ilk geçişte iyi oranı (OEE'nin Q'su;
    redo'dan geçen parça cezalandırılır). final_yield = Σ good / Σ loaded → nihai verim
    (no-scrap → ≈%100). Doluluk kaybı Q'da değil; ayrı FILL_LOSS kanalındadır.
    Ham toplamlar vardiya künyesi için yüzeye çıkar (OeeResult bağlam alanları).
    """
    loaded = sum(p["loaded_qty"] for p in production)
    redo = sum(p["redo_count"] for p in production)
    good = sum(p["good_count"] for p in production)
    if loaded <= 0:
        return 0.0, 0.0, loaded, redo, good
    return _clamp01((loaded - redo) / loaded), _clamp01(good / loaded), loaded, redo, good


def compute_oee(
    events: list[dict],
    production: list[dict],
    line: LineDefinition,
    planned_downtime_min: float = 0.0,
    calendar_min: float | None = None,
) -> OeeResult:
    """A/P/Q/OEE + utilization. `calendar_min` verilirse (H8) utilization gerçek
    takvim-zamanından (vardiya−mola−bakım) hesaplanır; yoksa eski MVP (span+planned).
    A/P/Q/OEE her iki yolda da AYNIDIR — yalnız utilization değişir."""
    if not events or not production:
        return OeeResult(0.0, 0.0, 0.0, 0.0, 0.0, planned_downtime_min, 0.0)
    avail, span, _dt = availability_from_events(events)
    perf = _performance(events, len(production), line)
    qual, final_yield, loaded, redo, good = _quality_metrics(production)
    oee = avail * perf * qual
    operating = span * avail
    if calendar_min is not None and calendar_min > 0:
        utilization = _clamp01(operating / calendar_min)
    else:
        calendar = span + planned_downtime_min
        utilization = _clamp01(operating / calendar) if calendar > 0 else 0.0
    return OeeResult(
        avail, perf, qual, oee, utilization, planned_downtime_min, final_yield,
        loaded_qty=float(loaded), good_count=float(good), redo_count=float(redo),
        span_min=float(span),
    )
