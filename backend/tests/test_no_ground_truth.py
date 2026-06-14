from pathlib import Path

from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"  # contains ground_truth.csv


def test_ground_truth_never_loaded(tmp_path):
    assert (FIX / "ground_truth.csv").exists()  # fixture has it
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect(); repo.init_schema()
    report = load_csv_dir(FIX, repo)
    assert "ground_truth.csv" in report.to_dict()["skipped"]
    assert repo.con.execute(
        "SELECT COUNT(*) FROM events WHERE event_type IN ('FILL_LOSS','SPEED_LOSS')"
    ).fetchone()[0] == 0
    repo.close()
