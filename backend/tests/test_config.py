from pathlib import Path

from app.config import load_line_definition

CONFIG = Path(__file__).resolve().parents[2] / "config" / "line_default.yaml"


def test_loads_tanks_in_order():
    line = load_line_definition(CONFIG)
    assert line.id == "LINE-01"
    assert [t.id for t in line.tanks][0] == "yagsizlandirma"
    assert any(t.bottleneck for t in line.tanks)


def test_nominal_full_pass_minutes():
    line = load_line_definition(CONFIG)
    nominal = sum((t.time_min + t.time_max) / 2.0 for t in line.tanks)
    assert nominal == 36.75  # (3.5+1.25+2.5+1.25+22.5+1.25+4.5)


def test_carrier_capacity_from_orders():
    line = load_line_definition(CONFIG)
    assert line.carrier_capacity["ORD-0001"] == 100
    assert line.carrier_capacity["ORD-0002"] == 100
