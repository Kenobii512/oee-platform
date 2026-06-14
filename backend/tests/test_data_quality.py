from app.analytics.data_quality import entry_coverage
from tests.conftest import FIXTURES, load_fixture_into_repo


def test_entry_coverage_synthetic():
    events = [
        {"event_type": "DOWNTIME", "operator_entered_reason": "ariza"},
        {"event_type": "DOWNTIME", "operator_entered_reason": None},
        {"event_type": "MICROSTOP", "operator_entered_reason": ""},
        {"event_type": "MICROSTOP", "operator_entered_reason": "x"},
        {"event_type": "PROCESS", "operator_entered_reason": None},
    ]
    cov = entry_coverage(events)
    assert cov["downtime_entry_coverage"] == 0.5
    assert cov["microstop_entry_coverage"] == 0.5


def test_entry_coverage_empty():
    cov = entry_coverage([])
    assert cov == {"downtime_entry_coverage": 0.0, "microstop_entry_coverage": 0.0}


def test_entry_coverage_baseline(tmp_path):
    # baseline fixture: DOWNTIME 7/8 dolu, MICROSTOP 12/60 dolu (operatör gürültüsü)
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    cov = entry_coverage(repo.fetch_events())
    assert abs(cov["downtime_entry_coverage"] - 0.875) < 1e-9
    assert abs(cov["microstop_entry_coverage"] - 0.20) < 1e-9
    repo.close()
