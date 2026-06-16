"""G11 baseline TL paritesi (firewall: gerçek yalnız doğrulamada).

Zaman kanalları (DOWNTIME/MICROSTOP/SPEED) ground_truth est_cost_tl ile sıkı (±%2);
kalite kanalları (REDO/SCRAP) sim'in ek bookleme'leri nedeniyle geniş bant;
toplam makul bant içinde.
"""
from app.analytics.cost import to_tl
from app.analytics.loss_tree import extract_loss_tree
from app.config import load_cost_config
from tests.conftest import (
    FIXTURES,
    baseline_truth_cost,
    load_fixture_into_repo,
)

COSTS_PATH = FIXTURES.parents[2] / "config" / "costs.yaml"

TIME_TOL = 0.02      # zaman kanalları ±%2
QUALITY_TOL = 0.60   # kalite kanalları geniş bant; gözlenen: QUALITY_REDO ~%53 (sim ek bookleme)
TOTAL_TOL = 0.15     # toplam makul bant; gözlenen: ~%10


def _platform_tl(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line_def)
    costs = load_cost_config(COSTS_PATH)
    res = to_tl(tree, costs)
    repo.close()
    return {c["category"]: c["tl"] for c in res["categories"]}, res["total_tl"]


def test_time_channels_tight_parity(tmp_path, line_def):
    tl, _ = _platform_tl(tmp_path, line_def)
    for cat in ("DOWNTIME", "MICROSTOP", "SPEED_LOSS"):
        truth = baseline_truth_cost(cat)
        assert truth > 0, cat
        assert abs(tl[cat] - truth) <= TIME_TOL * truth, (cat, tl[cat], truth)


def test_quality_channels_wide_band(tmp_path, line_def):
    tl, _ = _platform_tl(tmp_path, line_def)
    for cat in ("QUALITY_REDO", "QUALITY_SCRAP"):
        truth = baseline_truth_cost(cat)
        assert truth > 0, cat
        assert abs(tl[cat] - truth) <= QUALITY_TOL * truth, (cat, tl[cat], truth)


def test_total_within_reasonable_band(tmp_path, line_def):
    tl, total = _platform_tl(tmp_path, line_def)
    truth_total = sum(
        baseline_truth_cost(c)
        for c in ("DOWNTIME", "MICROSTOP", "SPEED_LOSS",
                  "FILL_LOSS", "QUALITY_REDO", "QUALITY_SCRAP")
    )
    assert abs(total - truth_total) <= TOTAL_TOL * truth_total, (total, truth_total)


def test_downtime_is_largest_tl_loss(tmp_path, line_def):
    tl, _ = _platform_tl(tmp_path, line_def)
    assert tl["DOWNTIME"] == max(tl.values())
