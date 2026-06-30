"""H1 — sıra-dışı / duplicate timestamp'te span ve union doğruluğu.

availability_from_events, olayları en erken olaya göre dakika eksenine taşır ve
union_length aralıkları içeride sıralar; bu yüzden girdi sırası sonucu DEĞİŞTİRMEZ.
"""
from app.analytics.oee import availability_from_events, union_length


def _ev(ts: float, dur: float, et: str = "PROCESS") -> dict:
    return {"timestamp": ts, "duration": dur, "event_type": et}


def test_span_and_union_invariant_to_order():
    ordered = [
        _ev(0.0, 5.0, "DOWNTIME"),
        _ev(10.0, 5.0, "PROCESS"),
        _ev(20.0, 5.0, "MICROSTOP"),
        _ev(30.0, 5.0, "PROCESS"),
    ]
    shuffled = [ordered[2], ordered[0], ordered[3], ordered[1]]  # sıra-dışı
    a_ord = availability_from_events(ordered)
    a_shuf = availability_from_events(shuffled)
    assert a_ord == a_shuf  # (availability, span, union) sıradan bağımsız
    assert a_ord[1] == 35.0  # span = max_end(35) - min_start(0)
    assert a_ord[2] == 10.0  # union(DOWNTIME 0-5 + MICROSTOP 20-25) = 10


def test_union_dedup_overlapping_and_duplicate():
    # örtüşen + birebir duplicate aralıklar bir kez sayılır
    assert union_length([(0.0, 10.0), (5.0, 15.0), (0.0, 10.0)]) == 15.0


def test_duplicate_timestamp_does_not_double_count_union():
    evs = [
        _ev(0.0, 10.0, "DOWNTIME"),
        _ev(0.0, 10.0, "DOWNTIME"),  # duplicate
        _ev(20.0, 5.0, "PROCESS"),
    ]
    _, span, union = availability_from_events(evs)
    assert union == 10.0  # duplicate iki kez sayılmaz
    assert span == 25.0
