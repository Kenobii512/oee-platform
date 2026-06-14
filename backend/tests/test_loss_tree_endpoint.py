from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_loss_tree_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIX)})
        r = client.get("/loss-tree")
        assert r.status_code == 200
        cats = r.json()["categories"]
        assert len(cats) == 6
        assert {c["category"] for c in cats} == {
            "DOWNTIME", "MICROSTOP", "QUALITY_REDO",
            "QUALITY_SCRAP", "FILL_LOSS", "SPEED_LOSS",
        }
        for c in cats:
            assert set(c) >= {"category", "axis", "value", "kind"}
            assert c["axis"] in ("minutes", "parts")
            assert c["kind"] in ("visible", "inferred")
        by = {c["category"]: c for c in cats}
        assert by["DOWNTIME"]["axis"] == "minutes"
        assert by["DOWNTIME"]["kind"] == "visible"
        assert by["DOWNTIME"]["value"] > 0
        assert by["FILL_LOSS"]["axis"] == "parts"
        assert by["FILL_LOSS"]["kind"] == "inferred"
