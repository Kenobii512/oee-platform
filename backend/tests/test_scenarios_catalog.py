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


def test_scenarios_have_narrative_and_highlight(tmp_path, monkeypatch):
    """H6: her senaryo demo anlatısı (boş değil) + vurgu grafiği taşır."""
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "s.duckdb"))
    valid_highlights = {"cost", "loss_tree", "trend", "oee"}
    with TestClient(app) as client:
        for s in client.get("/scenarios").json()["scenarios"]:
            assert s.get("narrative"), f"{s['id']}: narrative boş"
            assert s.get("highlight") in valid_highlights, f"{s['id']}: geçersiz highlight"


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


def test_activate_replaces_not_accumulates(tmp_path, monkeypatch):
    """Senaryo değişiminde veri birikmemeli (reset): ikinci aktivasyon ilkini değiştirir."""
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "s.duckdb"))
    with TestClient(app) as client:
        client.post("/scenarios/breakdown_storm/activate")
        downtime_storm = _downtime_minutes(client)
        client.post("/scenarios/baseline/activate")
        downtime_base = _downtime_minutes(client)
        # baseline duruşu storm'dan belirgin küçük olmalı; birikmiş olsaydı ≥ storm olurdu.
        assert downtime_base < downtime_storm


def _downtime_minutes(client) -> float:
    cats = client.get("/loss-tree").json()["categories"]
    return next(c["value"] for c in cats if c["category"] == "DOWNTIME")
