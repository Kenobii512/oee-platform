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


def test_ingest_root_restricts_paths(monkeypatch, tmp_path):
    # QC: auth kapali public deploy'da POST /ingest keyfi sunucu dizinini okuyabiliyordu.
    # OEE_INGEST_ROOT set'liyse path onun altinda olmak zorunda (vars. eski davranis).
    from fastapi.testclient import TestClient

    from app.main import app
    from tests.conftest import FIXTURES

    allowed = FIXTURES / "baseline"
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "r.duckdb"))
    monkeypatch.setenv("OEE_INGEST_ROOT", str(FIXTURES))
    with TestClient(app) as c:
        ok = c.post("/ingest", json={"path": str(allowed)})
        assert ok.status_code == 200
        bad = c.post("/ingest", json={"path": str(tmp_path)})  # kok disinda
        assert bad.status_code == 400
        assert "OEE_INGEST_ROOT" in bad.json()["detail"]
