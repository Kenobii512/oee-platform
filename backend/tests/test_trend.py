from app.analytics.trend import bucket_oee_series
from tests.conftest import FIXTURES, load_fixture_into_repo


def test_day_buckets_count_and_range(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    series = bucket_oee_series(
        repo.fetch_events(), repo.fetch_production(), line_def, "day"
    )
    # baseline fixture spans 2026-01-05 and 2026-01-06
    assert [s["period"] for s in series] == ["2026-01-05", "2026-01-06"]
    for s in series:
        for k in ("availability", "performance", "quality", "oee"):
            assert 0.0 <= s[k] <= 1.0, (s["period"], k, s[k])
    repo.close()


def test_week_bucket_single(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    series = bucket_oee_series(
        repo.fetch_events(), repo.fetch_production(), line_def, "week"
    )
    assert len(series) == 1
    assert series[0]["period"] == "2026-W02"
    repo.close()


def test_empty_input_returns_empty(line_def):
    assert bucket_oee_series([], [], line_def, "day") == []
