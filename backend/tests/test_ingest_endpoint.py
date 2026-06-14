from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_ingest_endpoint_returns_report(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        r = client.post("/ingest", json={"path": str(FIX)})
        assert r.status_code == 200
        body = r.json()
        assert body["accepted"]["production"] > 0
        assert "ground_truth.csv" in body["skipped"]
