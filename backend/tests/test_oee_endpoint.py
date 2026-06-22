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
                             "utilization", "planned_downtime_min", "final_yield",
                             "loaded_qty", "good_count", "redo_count",
                             "span_min", "downtime_union_min"}
        assert 0.0 <= body["oee"] <= 1.0
        # No-scrap: nihai verim ≈%100 (her şey eninde sonunda iyi).
        assert 0.99 <= body["final_yield"] <= 1.0
        # Yeni bağlam metrikleri: ham sayımlar tutarlı, pencere/duruş pozitif.
        assert body["loaded_qty"] > 0
        assert 0 <= body["good_count"] <= body["loaded_qty"]
        assert 0 <= body["redo_count"] <= body["loaded_qty"]
        assert body["span_min"] > 0
        assert body["downtime_union_min"] >= 0
        # first_pass kalite = (loaded − redo) / loaded ile tutarlı.
        assert abs(body["quality"] - (body["loaded_qty"] - body["redo_count"]) / body["loaded_qty"]) < 1e-6
