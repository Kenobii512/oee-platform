"""GET /replay/timeline: hat tanımı + zaman-sıralı ham olay dökümü; izolasyon; 404.
Canlı hat animasyonunun veri beslemesi — iş kuralı YOK, frontend indirgeyici tüketir."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_timeline_returns_line_and_sorted_events(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "tl.duckdb"))
    with TestClient(app) as client:
        r = client.get("/replay/timeline?scenario=baseline")
        assert r.status_code == 200
        body = r.json()
        # Hat YAML sırasında gelir; adlar frontend'e gömülmez.
        ids = [t["id"] for t in body["line"]]
        assert ids[0] == "yagsizlandirma" and ids[-1] == "kurutma"
        assert all(set(t) == {"id", "name"} and t["name"] for t in body["line"])
        evs = body["events"]
        assert len(evs) > 100
        assert set(evs[0]) == {
            "timestamp", "carrier_id", "station_id", "event_type", "duration", "reason_code",
        }
        stamps = [e["timestamp"] for e in evs]
        assert stamps == sorted(stamps)
        types = {e["event_type"] for e in evs}
        assert {"LOAD", "MOVE", "PROCESS", "UNLOAD"} <= types


def test_timeline_unknown_scenario_404(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "tl404.duckdb"))
    with TestClient(app) as client:
        r = client.get("/replay/timeline?scenario=yok_boyle")
        assert r.status_code == 404


def test_timeline_does_not_mutate_dashboard(tmp_path, monkeypatch):
    """İzolasyon: timeline (in-memory) paylaşılan DB'yi/pano /oee'yi değiştirmemeli."""
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "tliso.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIX)})
        before = client.get("/oee").json()
        client.get("/replay/timeline?scenario=breakdown_storm")
        after = client.get("/oee").json()
        assert before == after
