"""H9 — tutarlı hata yönetimi: bozuk tarih -> 400 (500 değil), açık detail."""
import pytest
from fastapi.testclient import TestClient

from app.api._params import BadRequest, validate_range
from app.main import app
from tests.conftest import FIXTURES


def test_validate_range_passthrough_and_raise():
    assert validate_range(None, None) == (None, None)
    assert validate_range("2026-01-05 06:00", None) == ("2026-01-05 06:00", None)
    with pytest.raises(BadRequest) as exc:
        validate_range("BOZUK", None)
    assert "from" in str(exc.value)


@pytest.mark.parametrize("ep", ["/oee", "/loss-tree", "/loss-tree/cost", "/oee/trend", "/recommendations"])
def test_bad_date_returns_400(ep, tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "e.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIXTURES / "baseline")})
        r = client.get(ep, params={"from": "DEGIL-TARIH"})
        assert r.status_code == 400, f"{ep}: {r.status_code}"
        assert "detail" in r.json() and "tarih" in r.json()["detail"].lower()


def test_valid_date_still_works(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "e2.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIXTURES / "baseline")})
        r = client.get("/oee", params={"from": "2026-01-05 06:00"})
        assert r.status_code == 200
