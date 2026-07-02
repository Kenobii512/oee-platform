"""Showcase landing: GET /tanitim public (auth açıkken bile), kendine-yeten HTML."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

_LANDING = Path(__file__).resolve().parents[2] / "docs" / "showcase" / "landing.html"


def test_tanitim_serves_landing(monkeypatch, tmp_path):
    monkeypatch.delenv("OEE_AUTH_PASS", raising=False)
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "t.duckdb"))
    with TestClient(app) as c:
        r = c.get("/tanitim")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "OEE" in r.text


def test_tanitim_public_even_with_auth(monkeypatch, tmp_path):
    # Landing satis icindir: parola arkasina saklanamaz (/health deseni).
    monkeypatch.setenv("OEE_AUTH_PASS", "gizli123")
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "t2.duckdb"))
    with TestClient(app) as c:
        r = c.get("/tanitim", headers={"accept": "text/html"}, follow_redirects=False)
        assert r.status_code == 200  # 303 login yonlendirmesi YOK
        r = c.get("/tanitim/ornek-rapor", follow_redirects=False)
        assert r.status_code == 200
        assert "Pilot Raporu" in r.text


def test_landing_file_is_self_contained():
    text = _LANDING.read_text(encoding="utf-8")
    assert "http://" not in text and "https://" not in text  # CDN/font istegi yok
    assert "<script" not in text
    assert "ornek-rapor" in text  # ornek rapora link


def test_tanitim_missing_file_is_404(monkeypatch, tmp_path):
    monkeypatch.delenv("OEE_AUTH_PASS", raising=False)
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "t3.duckdb"))
    monkeypatch.setattr("app.api.showcase_routes._SHOWCASE_DIR", tmp_path / "yok")
    with TestClient(app) as c:
        assert c.get("/tanitim").status_code == 404


def test_og_card_served_as_png(monkeypatch, tmp_path):
    monkeypatch.delenv("OEE_AUTH_PASS", raising=False)
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "t4.duckdb"))
    with TestClient(app) as c:
        r = c.get("/tanitim/og-card.png")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
