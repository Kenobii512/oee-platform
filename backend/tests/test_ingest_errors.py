
import pytest
from fastapi.testclient import TestClient

from app.ingest.loader import load_csv_dir
from app.main import app
from app.store.duckdb_repo import DuckDBRepository


def test_loader_raises_on_missing_dir(tmp_path):
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect()
    repo.init_schema()
    with pytest.raises(NotADirectoryError):
        load_csv_dir(tmp_path / "no_such_dir", repo)
    repo.close()


def test_ingest_endpoint_404_on_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        r = client.post("/ingest", json={"path": str(tmp_path / "no_such_dir")})
        assert r.status_code == 404
