"""H2 — uçtan uca: ham CSV -> adapter -> ingest -> /oee.

Adapter verildiğinde önce ham events sözleşmeye çevrilir, sonra mevcut H1 ingest
doğrulamasından geçer. production/orders zaten sözleşme-şeklinde olduğu için aynen yüklenir.
"""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import RAW


def test_ingest_with_adapter_then_oee(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        r = client.post("/ingest", json={"path": str(RAW), "adapter": "generic_plant"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["accepted"]["events"] > 0
        assert body["accepted"]["production"] == 3
        oee = client.get("/oee")
        assert oee.status_code == 200
        assert 0.0 <= oee.json()["oee"] <= 1.0


def test_unknown_adapter_returns_400(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api2.duckdb"))
    with TestClient(app) as client:
        r = client.post("/ingest", json={"path": str(RAW), "adapter": "yok_boyle_profil"})
        assert r.status_code == 400
        assert "yok_boyle_profil" in r.text


def test_ingest_without_adapter_unchanged(tmp_path, monkeypatch):
    # adapter verilmezse mevcut davranış (sözleşme dizini doğrudan yüklenir)
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api3.duckdb"))
    from tests.conftest import FIXTURES

    with TestClient(app) as client:
        r = client.post("/ingest", json={"path": str(FIXTURES / "baseline")})
        assert r.status_code == 200
        assert r.json()["accepted"]["events"] > 0
