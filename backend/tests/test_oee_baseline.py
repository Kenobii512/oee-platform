import json

from app.analytics.oee import compute_oee
from tests.conftest import FIXTURES, load_fixture_into_repo

GOLDEN = json.loads((FIXTURES / "baseline_golden.json").read_text())


def test_baseline_matches_simulator_within_1pct(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    events = repo.fetch_events()
    production = repo.fetch_production()
    result = compute_oee(events, production, line_def)
    for field in ("availability", "performance", "quality", "oee"):
        platform = getattr(result, field)
        golden = GOLDEN[field]
        assert abs(platform - golden) <= 0.01, (field, platform, golden)
    repo.close()
