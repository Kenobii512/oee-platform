from app.analytics.oee import union_length, availability_from_events


def test_union_length_disjoint():
    assert union_length([(0.0, 2.0), (5.0, 7.0)]) == 4.0


def test_union_length_overlapping_counted_once():
    assert union_length([(0.0, 5.0), (2.0, 7.0)]) == 7.0
    assert union_length([(0.0, 10.0), (3.0, 4.0)]) == 10.0


def test_union_length_empty():
    assert union_length([]) == 0.0


def test_availability_subtracts_downtime_union_once():
    events = [
        {"timestamp": 0.0, "duration": 0.0, "event_type": "LOAD", "station_id": None},
        {"timestamp": 10.0, "duration": 20.0, "event_type": "DOWNTIME", "station_id": None},
        {"timestamp": 20.0, "duration": 20.0, "event_type": "DOWNTIME", "station_id": None},
        {"timestamp": 100.0, "duration": 0.0, "event_type": "QC", "station_id": None},
    ]
    a, span, dt = availability_from_events(events)
    assert span == 100.0
    assert dt == 30.0  # not 40
    assert a == 0.70
