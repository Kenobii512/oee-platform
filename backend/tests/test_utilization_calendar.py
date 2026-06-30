"""H8 — utilization gerçek takvimden; A/P/Q/OEE değişmez."""
from datetime import datetime

from fastapi.testclient import TestClient

from app.analytics.calendar import calendar_minutes
from app.analytics.oee import compute_oee
from app.config import load_calendar
from app.main import app
from tests.conftest import FIXTURES, LINE_CONFIG, load_fixture_into_repo


def _events_window(events):
    ts = [e["timestamp"] if isinstance(e["timestamp"], datetime)
          else datetime.fromisoformat(str(e["timestamp"])) for e in events]
    return min(ts), max(ts)


def test_calendar_utilization_changes_only_utilization(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "u.duckdb"))
    events, production = repo.fetch_events(), repo.fetch_production()
    repo.close()
    cal = load_calendar(LINE_CONFIG)
    start, end = _events_window(events)
    cal_min = calendar_minutes(start, end, cal)
    assert cal_min > 0

    base = compute_oee(events, production, line_def)  # MVP utilization
    cald = compute_oee(events, production, line_def, calendar_min=cal_min)

    # A/P/Q/OEE/final_yield AYNI (yalnız utilization değişir)
    assert (cald.availability, cald.performance, cald.quality, cald.oee, cald.final_yield) == (
        base.availability, base.performance, base.quality, base.oee, base.final_yield
    )
    assert 0.0 < cald.utilization <= 1.0


def test_oee_endpoint_utilization_present_and_bounded(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIXTURES / "baseline")})
        r = client.get("/oee")
        assert r.status_code == 200
        util = r.json()["utilization"]
        assert 0.0 < util <= 1.0
