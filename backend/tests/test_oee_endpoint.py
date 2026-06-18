from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_oee_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIX)})
        r = client.get("/oee")
        assert r.status_code == 200
        body = r.json()
        assert set(body) >= {"availability", "performance", "quality", "oee",
                             "utilization", "planned_downtime_min", "final_yield"}
        assert 0.0 <= body["oee"] <= 1.0
        # No-scrap: nihai verim ≈%100 (her şey eninde sonunda iyi).
        assert 0.99 <= body["final_yield"] <= 1.0
