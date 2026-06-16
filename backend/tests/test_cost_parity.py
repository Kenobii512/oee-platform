"""G11 baseline TL paritesi (firewall: gerçek yalnız doğrulamada).

Kanal sınıfına göre bant (loss_tree VISIBLE/INFERRED ayrımıyla hizalı):
- Doğrudan zaman kanalları (DOWNTIME/MICROSTOP) events'ten birebir → ±%2 (sıkı).
- Çıkarım kanalları (SPEED_LOSS/FILL_LOSS) nominal kestirimle gelir → orta bant
  (native ≥%85 geri kazanım kuralıyla tutarlı; gözlenen ~%6 ve ~%11).
- Kalite kanalları (REDO/SCRAP): sim REDO maliyetine strip (sıyırma) downtime'ını,
  SCRAP'a carrier loaded_qty'sini ekler → platformun parça×oran'ı yaklaşık (REDO ~%53) → geniş bant.
- Toplam makul bant içinde (gözlenen ~%10).
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

TIME_TOL = 0.02       # doğrudan-gözlenen zaman kanalları ±%2
INFERRED_TOL = 0.15   # çıkarım kanalları (SPEED/FILL) — native ≥%85 ile tutarlı (gözlenen ~%6/%11)
QUALITY_TOL = 0.60    # kalite kanalları geniş bant (gözlenen REDO ~%53; sim strip/loaded_qty bookler)
TOTAL_TOL = 0.15      # toplam makul bant (gözlenen ~%10)


def _platform_tl(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line_def)
    costs = load_cost_config(COSTS_PATH)
    res = to_tl(tree, costs)
    repo.close()
    return {c["category"]: c["tl"] for c in res["categories"]}, res["total_tl"]


def test_direct_time_channels_tight_parity(tmp_path, line_def):
    tl, _ = _platform_tl(tmp_path, line_def)
    for cat in ("DOWNTIME", "MICROSTOP"):
        truth = baseline_truth_cost(cat)
        assert truth > 0, cat
        assert abs(tl[cat] - truth) <= TIME_TOL * truth, (cat, tl[cat], truth)


def test_inferred_channels_band(tmp_path, line_def):
    tl, _ = _platform_tl(tmp_path, line_def)
    for cat in ("SPEED_LOSS", "FILL_LOSS"):
        truth = baseline_truth_cost(cat)
        assert truth > 0, cat
        assert abs(tl[cat] - truth) <= INFERRED_TOL * truth, (cat, tl[cat], truth)


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
