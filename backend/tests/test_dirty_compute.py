"""H1 — kirli/kısmi/boş pencerede analitik çökmeden çalışır + "yetersiz veri" sinyali.

Boş ya da seyrek pencerede 0/NaN sessizce dönmek yerine `coverage(...)["sufficient"]`
açıkça False olur (H3 güven katmanına köprü).
"""
from app.analytics.data_quality import coverage
from app.analytics.loss_tree import extract_loss_tree
from app.analytics.oee import compute_oee
from tests.conftest import DIRTY, fresh_repo


def _ev(ts: str, dur: float, et: str, carrier: str = "CAR-1") -> dict:
    return {"timestamp": ts, "duration": dur, "event_type": et, "carrier_id": carrier}


def test_empty_window_no_crash_and_insufficient(line_def):
    res = compute_oee([], [], line_def)
    assert res.oee == 0.0  # çökmez, makul sıfır
    cov = coverage([], [])
    assert cov["sufficient"] is False
    assert cov["event_count"] == 0


def test_sparse_window_is_insufficient(line_def):
    events = [_ev("2026-01-01 00:00:00", 5.0, "PROCESS")]
    cov = coverage(events, [])
    assert cov["sufficient"] is False  # tek olay -> yetersiz


def test_full_baseline_is_sufficient(tmp_path):
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    from app.ingest.loader import load_csv_dir

    load_csv_dir(DIRTY.parent / "baseline", repo)
    cov = coverage(repo.fetch_events(), repo.fetch_production())
    assert cov["sufficient"] is True
    assert cov["event_count"] > 100
    repo.close()


def test_dirty_baseline_compute_does_not_crash(tmp_path, line_def):
    # bilinmeyen reason/eksik satır içeren kirli baseline'da loss_tree çökmez
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    from app.ingest.loader import load_csv_dir

    load_csv_dir(DIRTY / "missing_row", repo)
    tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line_def)
    assert tree is not None  # çökmeden bir sonuç üretti
    repo.close()
