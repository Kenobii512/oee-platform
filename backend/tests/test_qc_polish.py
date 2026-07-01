"""QC cilası — H1–H9 sonrası entegrasyon boşlukları için düzeltme testleri."""
import glob
import os
import tempfile

from fastapi.testclient import TestClient

from app.ingest.loader import load_csv_dir
from app.main import app
from tests.conftest import FIXTURES, RAW, fresh_repo


def test_data_quality_summary_exposes_sufficiency(tmp_path, monkeypatch):
    # H1 coverage(sufficient) + H3 data_sufficiency artık uçtan görünür (eskiden ölüydü).
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "q.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIXTURES / "baseline")})
        d = client.get("/data-quality/summary").json()
        assert isinstance(d["sufficient"], bool)
        assert 0.0 <= d["sufficiency_score"] <= 1.0
        assert "microstop_entry_coverage" in d  # geriye uyumlu
        assert d["event_count"] > 0


def test_trend_invalid_bucket_returns_400(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "q.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIXTURES / "baseline")})
        r = client.get("/oee/trend", params={"bucket": "aylik"})
        assert r.status_code == 400
        assert "bucket" in r.json()["detail"]


def test_oee_response_has_calendar_min(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "q.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIXTURES / "baseline")})
        d = client.get("/oee").json()
        assert "calendar_min" in d and d["calendar_min"] > 0


def test_redo_exceeding_loaded_rejected(tmp_path):
    # redo_count > loaded_qty -> reddedilir (eskiden first_pass < 0 sessizce 0'a kırpılırdı).
    d = tmp_path / "data"
    d.mkdir()
    (d / "production.csv").write_text(
        "carrier_id,order_id,loaded_qty,good_count,redo_count,scrap_count\n"
        "CAR-1,ORD-1,100,100,0,0\n"      # geçerli
        "CAR-2,ORD-1,100,100,150,0\n",   # redo 150 > loaded 100
        encoding="utf-8",
    )
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    rep = load_csv_dir(d, repo).to_dict()
    assert repo.count("production") == 1
    assert rep["rejected_count"] == 1
    repo.close()


def test_adapter_ingest_cleans_tempdir(tmp_path, monkeypatch):
    # H2 adaptör geçici dizini artık TemporaryDirectory ile temizlenir (sızıntı yok).
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "q.duckdb"))
    pattern = os.path.join(tempfile.gettempdir(), "oee_adapt_*")
    before = set(glob.glob(pattern))
    with TestClient(app) as client:
        r = client.post("/ingest", json={"path": str(RAW), "adapter": "generic_plant"})
        assert r.status_code == 200
    after = set(glob.glob(pattern))
    assert after == before  # yeni geçici dizin kalmadı
