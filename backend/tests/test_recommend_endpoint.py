from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_recommend_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "rec.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIX)})
        r = client.get("/recommendations")
        assert r.status_code == 200
        body = r.json()
        recs = body["recommendations"]
        assert len(recs) >= 3
        # TL azalan sıralı; en üst DOWNTIME hedefli.
        tls = [c["tl"] for c in recs]
        assert tls == sorted(tls, reverse=True)
        assert recs[0]["category"] == "DOWNTIME"
        # Her öneride zorunlu alanlar dolu.
        for c in recs:
            assert set(c) >= {
                "category", "tl", "estimated_gain_tl",
                "title", "action", "assumption",
            }
            assert c["tl"] > 0
            assert c["estimated_gain_tl"] >= 0
        assert body["total_estimated_gain_tl"] == sum(
            c["estimated_gain_tl"] for c in recs
        )
