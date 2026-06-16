
from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository


def test_bad_rows_rejected_good_rows_loaded(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "events.csv").write_text(
        "timestamp,line_id,station_id,event_type,duration,reason_code,operator_entered_reason,operator_entry_ts\n"
        "2026-01-05 06:00:00.000,LINE-01,,LOAD,0.0,,,\n"
        "2026-01-05 06:00:01.000,LINE-01,,BOGUS,1.0,,,\n"
    )
    (d / "production.csv").write_text(
        "carrier_id,order_id,loaded_qty,good_count,redo_count,scrap_count\n"
        "CAR-1,ORD-1,100,100,0,0\n"
        "CAR-2,ORD-1,100,90,0,5\n"
    )
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect()
    repo.init_schema()
    report = load_csv_dir(d, repo)
    assert repo.count("events") == 1
    assert repo.count("production") == 1
    rd = report.to_dict()
    assert rd["rejected_count"] == 2
    assert any(e["file"] == "events.csv" for e in rd["errors"])
    assert any(e["file"] == "production.csv" for e in rd["errors"])
    repo.close()
