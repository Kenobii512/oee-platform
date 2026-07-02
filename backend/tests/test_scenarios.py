

def test_active_scenario_tracked(monkeypatch, tmp_path):
    # QC: ilk yuklemede pano hangi veri setine baktigini gosteremiyordu.
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "a.duckdb"))
    monkeypatch.delenv("SAMPLE_DATA_DIR", raising=False)
    with TestClient(app) as c:
        assert c.get("/scenarios").json().get("active") is None
        c.post("/scenarios/baseline/activate")
        assert c.get("/scenarios").json()["active"] == "baseline"


def test_active_scenario_set_by_startup_ingest(monkeypatch, tmp_path):
    from pathlib import Path as _P

    from fastapi.testclient import TestClient

    from app.main import app

    sample = _P(__file__).resolve().parents[1] / "tests" / "fixtures" / "scenarios" / "baseline"
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "b.duckdb"))
    monkeypatch.setenv("SAMPLE_DATA_DIR", str(sample))
    with TestClient(app) as c:
        assert c.get("/scenarios").json()["active"] == "baseline"
