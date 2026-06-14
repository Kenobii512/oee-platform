from app.analytics.oee import compute_oee
from tests.conftest import FIXTURES, load_fixture_into_repo


def test_lossless_oee_at_least_95(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "lossless", str(tmp_path / "l.duckdb"))
    events = repo.fetch_events()
    production = repo.fetch_production()
    result = compute_oee(events, production, line_def)
    assert result.oee >= 0.95, result
    repo.close()
