"""H1 — corrupt.py kirlilik üreteci birim testleri.

Üreteç deterministik (seed) ve her kirlilik türü ayrı bayrak. Sözleşme satırları
(list[dict]) üzerinde çalışır; CSV I/O yalnız CLI'da.
"""
from tools.corrupt import KINDS, corrupt_rows


def _events(n: int) -> list[dict]:
    return [
        {
            "timestamp": f"2026-01-01 00:0{i}:00.000",
            "line_id": "LINE-01",
            "carrier_id": f"CAR-{i:04d}",
            "station_id": "",
            "event_type": "MICROSTOP",
            "duration": "30.0",
            "reason_code": "jam",
            "operator_entered_reason": "",
            "operator_entry_ts": "",
        }
        for i in range(n)
    ]


def test_out_of_order_is_deterministic():
    rows = _events(6)
    a = corrupt_rows(rows, "out_of_order", seed=7)
    b = corrupt_rows(rows, "out_of_order", seed=7)
    assert a == b  # aynı seed -> aynı çıktı
    assert [r["timestamp"] for r in a] != [r["timestamp"] for r in rows]  # sıra değişti
    assert sorted(r["timestamp"] for r in a) == sorted(
        r["timestamp"] for r in rows
    )  # küme korunur


def test_duplicate_adds_rows():
    rows = _events(1)
    out = corrupt_rows(rows, "duplicate", seed=1, rate=1.0)
    assert len(out) == 2 and out[0] == out[1]


def test_missing_row_drops_rows():
    rows = _events(10)
    out = corrupt_rows(rows, "missing_row", seed=3, rate=0.5)
    assert 0 < len(out) < len(rows)


def test_type_corruption_breaks_duration():
    rows = _events(5)
    out = corrupt_rows(rows, "type_corruption", seed=2, rate=1.0)
    # en az bir satırda duration sayısal değil
    assert any(not _is_floatable(r["duration"]) for r in out)


def test_negative_duration():
    rows = _events(5)
    out = corrupt_rows(rows, "negative_duration", seed=2, rate=1.0)
    assert any(float(r["duration"]) < 0 for r in out)


def test_empty_required_blanks_field():
    rows = _events(5)
    out = corrupt_rows(rows, "empty_required", seed=2, rate=1.0)
    # zorunlu alan (event_type) en az bir satırda boş
    assert any(r["event_type"] == "" for r in out)


def test_unknown_reason_uses_unmapped_label():
    rows = _events(5)
    out = corrupt_rows(rows, "unknown_reason", seed=2, rate=1.0)
    assert any(r["event_type"] not in {"MICROSTOP", "LOAD", "DOWNTIME"} for r in out)


def test_all_kinds_registered():
    # her bilinen tür çağrılabilir ve çökme yok
    rows = _events(8)
    for kind in KINDS:
        corrupt_rows(rows, kind, seed=1, rate=0.5)


def _is_floatable(v) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False
