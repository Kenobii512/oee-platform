"""G8: senaryo kataloğu (GET /scenarios) + aktivasyon (POST /scenarios/{id}/activate)."""
from fastapi.testclient import TestClient

from app.main import app


def test_list_scenarios(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "s.duckdb"))
    with TestClient(app) as client:
        r = client.get("/scenarios")
        assert r.status_code == 200
        ids = {s["id"] for s in r.json()["scenarios"]}
        assert {"baseline", "breakdown_storm", "speed_bottleneck"} <= ids
        for s in r.json()["scenarios"]:
            assert set(s) >= {"id", "title", "description", "expected_top_loss"}


def test_activate_scenario_loads_data(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "s.duckdb"))
    with TestClient(app) as client:
        r = client.post("/scenarios/breakdown_storm/activate")
        assert r.status_code == 200
        assert r.json()["activated"] == "breakdown_storm"
        # Aktivasyon sonrası OEE hesaplanabilir olmalı (veri yüklendi).
        oee = client.get("/oee").json()
        assert 0.0 < oee["oee"] < 1.0


def test_activate_unknown_scenario_404(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "s.duckdb"))
    with TestClient(app) as client:
        r = client.post("/scenarios/yok_boyle/activate")
        assert r.status_code == 404
