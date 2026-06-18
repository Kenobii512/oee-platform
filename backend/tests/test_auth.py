"""Form-tabanlı erişim katmanı: OEE_AUTH_PASS yoksa kapalı, varsa kapı çalışır."""
from fastapi.testclient import TestClient

from app.main import app


def test_auth_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("OEE_AUTH_PASS", raising=False)
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "a.duckdb"))
    with TestClient(app) as c:
        assert c.get("/health").status_code == 200
        # auth kapalı: kök doğrudan erişilir (login'e yönlenmez)
        r = c.get("/", headers={"accept": "text/html"}, follow_redirects=False)
        assert r.status_code != 303


def test_auth_gates_and_login_flow(monkeypatch, tmp_path):
    monkeypatch.setenv("OEE_AUTH_USER", "patron")
    monkeypatch.setenv("OEE_AUTH_PASS", "gizli123")
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "b.duckdb"))
    with TestClient(app) as c:
        # /health her zaman public
        assert c.get("/health").status_code == 200
        # giriş yapmadan: HTML navigasyonu login'e yönlenir, API 401
        r = c.get("/", headers={"accept": "text/html"}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"
        r = c.get("/oee", headers={"accept": "application/json"}, follow_redirects=False)
        assert r.status_code == 401
        # login sayfası açılır ve formu içerir
        page = c.get("/login")
        assert page.status_code == 200 and 'name="password"' in page.text
        # yanlış parola -> hata ile login'e geri
        r = c.post("/login", data={"username": "patron", "password": "yanlis"},
                   follow_redirects=False)
        assert r.status_code == 303 and "error=1" in r.headers["location"]
        # doğru parola -> ana sayfaya yönlendirir + çerez set eder
        r = c.post("/login", data={"username": "patron", "password": "gizli123"},
                   follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/"
        # çerez TestClient'ta saklandı -> artık korunan yol erişilebilir
        assert c.get("/oee", follow_redirects=False).status_code == 200
        # logout -> çerez silinir, tekrar kapı
        c.get("/logout", follow_redirects=False)
        r = c.get("/oee", headers={"accept": "application/json"}, follow_redirects=False)
        assert r.status_code == 401
