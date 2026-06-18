from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_cost_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "cost.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIX)})
        r = client.get("/loss-tree/cost")
        assert r.status_code == 200
        body = r.json()
        cats = body["categories"]
        assert len(cats) == 5
        assert {c["category"] for c in cats} == {
            "DOWNTIME", "MICROSTOP", "QUALITY_REDO",
            "FILL_LOSS", "SPEED_LOSS",
        }
        for c in cats:
            assert set(c) >= {"category", "axis", "value", "tl", "kind"}
        tls = [c["tl"] for c in cats]
        assert tls == sorted(tls, reverse=True)
        assert cats[0]["category"] == "DOWNTIME"
        assert body["total_tl"] == sum(tls)
