from app.analytics.loss_tree import extract_loss_tree
from tests.conftest import FIXTURES, baseline_truth_value, load_fixture_into_repo

# No-scrap modeli: görünür zaman kanalları events'ten birebir; QUALITY_REDO ayrık-parça
# olduğu için ground_truth döngü-hacminin altında kalır (geniş bant).
VISIBLE_TIME = ("DOWNTIME", "MICROSTOP")
REDO_MIN = 0.70


def test_visible_time_channels_match_ground_truth(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line_def)
    for cat in VISIBLE_TIME:
        truth = baseline_truth_value(cat)
        got = tree.value(cat)
        assert truth > 0, cat
        assert abs(got - truth) <= 0.01 * truth, (cat, got, truth)
    repo.close()


def test_redo_channel_recovers_distinct_parts(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line_def)
    truth = baseline_truth_value("QUALITY_REDO")
    got = tree.value("QUALITY_REDO")
    assert truth > 0
    assert got <= truth + 1e-6
    assert got / truth >= REDO_MIN, (got, truth)
    repo.close()
