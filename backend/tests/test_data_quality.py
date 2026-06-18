from app.analytics.data_quality import entry_coverage
from tests.conftest import FIXTURES, load_fixture_into_repo


def test_entry_coverage_synthetic():
    # G10: yalnız MICROSTOP operatör kapsamı ölçülür (duruş sistemce otomatik).
    events = [
        {"event_type": "DOWNTIME", "operator_entered_reason": "ariza"},
        {"event_type": "DOWNTIME", "operator_entered_reason": None},
        {"event_type": "MICROSTOP", "operator_entered_reason": ""},
        {"event_type": "MICROSTOP", "operator_entered_reason": "x"},
        {"event_type": "PROCESS", "operator_entered_reason": None},
    ]
    cov = entry_coverage(events)
    assert cov == {"microstop_entry_coverage": 0.5}


def test_entry_coverage_empty():
    cov = entry_coverage([])
    assert cov == {"microstop_entry_coverage": 0.0}


def test_entry_coverage_baseline(tmp_path):
    # baseline fixture: operatör mikro duruşların çoğunu girmez (düşük kapsam) — bu
    # ürünün satış argümanı (tek manuel girdi). Duruş artık ölçülmez (sistemce bilinir).
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    cov = entry_coverage(repo.fetch_events())
    assert set(cov) == {"microstop_entry_coverage"}
    assert 0.0 < cov["microstop_entry_coverage"] < 0.30
    repo.close()
