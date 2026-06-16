"""G7 SSE: /replay/stream artan snapshot'ları yayınlar; bilinmeyen senaryo 404."""
import json

from fastapi.testclient import TestClient

from app.main import app


def test_replay_stream_emits_growing_snapshots(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "rs.duckdb"))
    with TestClient(app) as client:
        with client.stream(
            "GET", "/replay/stream?scenario=baseline&speed=1000&steps=10"
        ) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            datas = [
                ln for ln in r.iter_lines()
                if ln.startswith("data: ") and ln != "data: {}"
            ]
        assert len(datas) >= 5
        # Snapshot'lar geçerli JSON ve event_count artan (büyüyen pencere).
        snaps = [json.loads(ln[len("data: "):]) for ln in datas]
        counts = [s["event_count"] for s in snaps]
        assert counts == sorted(counts)
        assert snaps[-1]["event_count"] > snaps[0]["event_count"]


def test_replay_stream_unknown_scenario_404(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "rs.duckdb"))
    with TestClient(app) as client:
        r = client.get("/replay/stream?scenario=yok_boyle&speed=1000&steps=5")
        assert r.status_code == 404
