from app.analytics.loss_tree import INFERRED, extract_loss_tree
from tests.conftest import FIXTURES, baseline_truth_value, load_fixture_into_repo


def test_inferred_channels_recover_at_least_85pct(tmp_path, line_def):
    # Gizli kanallar (FILL/SPEED) yalnız çıkarımla kazanılır; eşik >= %85.
    # Simülatör referansı ~%89 FILL, ~%94 SPEED.
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line_def)
    for cat in INFERRED:
        truth = baseline_truth_value(cat)
        got = tree.value(cat)
        assert truth > 0, cat
        recovery = got / truth
        assert recovery >= 0.85, (cat, got, truth, recovery)
    repo.close()
