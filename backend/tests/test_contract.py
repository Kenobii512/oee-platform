import pytest
from pydantic import ValidationError

from app.models.contract import EventRow, EventType, OrderRow, ProductionRow


def test_valid_event_row():
    row = EventRow(
        timestamp="2026-01-05 06:00:30.000",
        line_id="LINE-01",
        station_id="yagsizlandirma",
        event_type="PROCESS",
        duration=3.91,
        reason_code=None,
        operator_entered_reason=None,
        operator_entry_ts=None,
    )
    assert row.event_type is EventType.PROCESS
    assert row.station_id == "yagsizlandirma"


def test_event_type_enum_has_nine_values():
    assert {e.value for e in EventType} == {
        "LOAD", "PROCESS", "MOVE", "UNLOAD", "QC",
        "OVER_RESIDENCE", "DOWNTIME", "MICROSTOP", "STRIP",
    }


def test_bad_event_type_rejected():
    with pytest.raises(ValidationError):
        EventRow(timestamp="2026-01-05 06:00:30.000", line_id="L", event_type="BOGUS", duration=1.0)


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError):
        EventRow(line_id="L", event_type="LOAD", duration=1.0)  # no timestamp


def test_valid_production_row():
    row = ProductionRow(carrier_id="CAR-0001", order_id="ORD-0001",
                        loaded_qty=92, good_count=92, redo_count=0, scrap_count=0)
    assert row.good_count == 92


def test_production_count_invariant_violation_rejected():
    with pytest.raises(ValidationError):
        ProductionRow(carrier_id="C", order_id="O",
                      loaded_qty=100, good_count=90, redo_count=0, scrap_count=5)  # 90+5 != 100


def test_production_redo_not_in_invariant():
    row = ProductionRow(carrier_id="C", order_id="O",
                        loaded_qty=100, good_count=98, redo_count=7, scrap_count=2)
    assert row.redo_count == 7


def test_valid_order_row():
    row = OrderRow(order_id="ORD-0001", product_id="PRD-A", target_cycle=40.0, planned_qty=4000)
    assert row.planned_qty == 4000
