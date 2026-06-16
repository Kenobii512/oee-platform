from pathlib import Path

from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_second_load_no_duplicates(tmp_path):
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect()
    repo.init_schema()
    load_csv_dir(FIX, repo)
    e1, p1, o1 = repo.count("events"), repo.count("production"), repo.count("orders")
    load_csv_dir(FIX, repo)  # load again
    assert (repo.count("events"), repo.count("production"), repo.count("orders")) == (e1, p1, o1)
    repo.close()
