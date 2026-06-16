import csv
from pathlib import Path

from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def _count_csv_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # minus header


def test_baseline_loads_and_row_counts_match(tmp_path):
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect()
    repo.init_schema()
    report = load_csv_dir(FIX, repo)
    assert repo.count("events") == _count_csv_rows(FIX / "events.csv")
    assert repo.count("production") == _count_csv_rows(FIX / "production.csv")
    assert repo.count("orders") == _count_csv_rows(FIX / "orders.csv")
    assert report.to_dict()["rejected_count"] == 0
    repo.close()
