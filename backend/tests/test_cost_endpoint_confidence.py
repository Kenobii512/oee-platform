"""H3 — /loss-tree/cost belirsizlik alanlarını yüzeye çıkarır."""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import FIXTURES


def test_cost_endpoint_exposes_confidence(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIXTURES / "baseline")})
        r = client.get("/loss-tree/cost")
        assert r.status_code == 200
        cats = r.json()["categories"]
        assert cats
        for c in cats:
            assert {"tl_low", "tl_high", "confidence", "low_confidence"} <= set(c)
            assert c["tl_low"] <= c["tl"] <= c["tl_high"]
            assert 0.0 <= c["confidence"] <= 1.0
            if c["kind"] == "inferred":
                # çıkarım kanalı: nokta etrafında bant (asimetrik), görünür değil
                assert c["tl_low"] < c["tl_high"] or c["tl"] == 0.0
            else:
                assert c["confidence"] == 1.0
                assert c["tl_low"] == c["tl"] == c["tl_high"]
