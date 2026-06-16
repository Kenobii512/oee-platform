from app.analytics.cost import to_tl
from app.analytics.loss_tree import LossEntry, LossTree
from app.config import CostConfig

COSTS = CostConfig(
    downtime_tl_per_min=50.0, microstop_tl_per_min=50.0, speed_tl_per_min=20.0,
    fill_tl_per_part=2.0, redo_tl_per_part=3.0, scrap_tl_per_part=8.0,
)


def _tree():
    return LossTree({
        "DOWNTIME": LossEntry(minutes=10.0),
        "MICROSTOP": LossEntry(minutes=4.0),
        "SPEED_LOSS": LossEntry(minutes=5.0),
        "FILL_LOSS": LossEntry(parts=20.0),
        "QUALITY_REDO": LossEntry(parts=6.0),
        "QUALITY_SCRAP": LossEntry(parts=3.0),
    })


def test_unit_conversions():
    res = to_tl(_tree(), COSTS)
    tl = {c["category"]: c["tl"] for c in res["categories"]}
    assert tl["DOWNTIME"] == 10.0 * 50.0
    assert tl["MICROSTOP"] == 4.0 * 50.0
    assert tl["SPEED_LOSS"] == 5.0 * 20.0
    assert tl["FILL_LOSS"] == 20.0 * 2.0
    assert tl["QUALITY_REDO"] == 6.0 * 3.0
    assert tl["QUALITY_SCRAP"] == 3.0 * 8.0


def test_total_is_sum_of_categories():
    res = to_tl(_tree(), COSTS)
    assert res["total_tl"] == sum(c["tl"] for c in res["categories"])
    assert res["total_tl"] == 500 + 200 + 100 + 40 + 18 + 24


def test_sorted_descending_by_tl():
    res = to_tl(_tree(), COSTS)
    tls = [c["tl"] for c in res["categories"]]
    assert tls == sorted(tls, reverse=True)
    assert res["categories"][0]["category"] == "DOWNTIME"


def test_entries_carry_axis_value_kind():
    res = to_tl(_tree(), COSTS)
    by = {c["category"]: c for c in res["categories"]}
    assert by["DOWNTIME"]["axis"] == "minutes" and by["DOWNTIME"]["kind"] == "visible"
    assert by["FILL_LOSS"]["axis"] == "parts" and by["FILL_LOSS"]["kind"] == "inferred"
    assert by["DOWNTIME"]["value"] == 10.0
