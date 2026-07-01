from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_root_returns_html(tmp_path, monkeypatch):
    # '/' SPA varsa React, yoksa Jinja sunar; her iki durumda 200 HTML.
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]


def test_legacy_dashboard_returns_jinja(tmp_path, monkeypatch):
    # Jinja panosu daima '/legacy'de (SPA fallback).
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        r = client.get("/legacy")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "OEE" in r.text
        assert "/static/dashboard.js" in r.text


def test_trend_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIX)})
        r = client.get("/oee/trend?bucket=day")
        assert r.status_code == 200
        series = r.json()
        assert len(series) == 2
        assert {"period", "availability", "performance", "quality",
                "final_yield", "oee"} <= set(series[0])
        assert all(0.0 <= s["oee"] <= 1.0 for s in series)


def test_data_quality_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIX)})
        r = client.get("/data-quality/summary")
        assert r.status_code == 200
        body = r.json()
        # G10: mikro duruş kapsamı (duruş sistemce otomatik bilinir) + QC: H1/H3 yeterlilik.
        assert 0.0 < body["microstop_entry_coverage"] < 0.30
        assert isinstance(body["sufficient"], bool)
        assert 0.0 <= body["sufficiency_score"] <= 1.0


def test_sample_data_dir_autoingest(tmp_path, monkeypatch):
    # SAMPLE_DATA_DIR verilirse açılışta otomatik ingest (manuel /ingest yok).
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    monkeypatch.setenv("SAMPLE_DATA_DIR", str(FIX))
    with TestClient(app) as client:
        r = client.get("/oee")
        assert r.status_code == 200
        assert r.json()["oee"] > 0
