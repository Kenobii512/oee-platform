from app.analytics.loss_tree import VISIBLE, extract_loss_tree
from tests.conftest import FIXTURES, baseline_truth_value, load_fixture_into_repo


def test_visible_channels_match_ground_truth(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line_def)
    for cat in VISIBLE:
        truth = baseline_truth_value(cat)
        got = tree.value(cat)
        assert truth > 0, cat
        assert abs(got - truth) <= 0.01 * truth, (cat, got, truth)
    repo.close()
