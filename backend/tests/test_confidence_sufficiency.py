"""H3 — veri-yeterlilik skoru davranışı: bol veri yüksek, seyrek/kısmi düşük."""
import inspect

from app.analytics.confidence import data_sufficiency
from tests.conftest import FIXTURES, fresh_repo


def _ev(i: int) -> dict:
    return {
        "timestamp": f"2026-01-01 06:{i % 60:02d}:00",
        "duration": 1.0,
        "event_type": "PROCESS",
        "carrier_id": f"CAR-{i}",
    }


def test_full_baseline_high_sufficiency(tmp_path, line_def):
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    from app.ingest.loader import load_csv_dir

    load_csv_dir(FIXTURES / "baseline", repo)
    s = data_sufficiency(repo.fetch_events(), repo.fetch_production(), line_def)
    assert s >= 0.8
    repo.close()


def test_sparse_low_sufficiency(line_def):
    events = [_ev(i) for i in range(3)]
    production = [{"order_id": "ORD-1", "loaded_qty": 10, "good_count": 10,
                   "redo_count": 0, "scrap_count": 0}]
    s = data_sufficiency(events, production, line_def)
    assert s <= 0.4


def test_empty_is_zero(line_def):
    assert data_sufficiency([], [], line_def) == 0.0


def test_firewall_no_ground_truth_param():
    # FIREWALL: belirsizlik katmanı gerçeği görmez.
    assert "ground_truth" not in inspect.signature(data_sufficiency).parameters
