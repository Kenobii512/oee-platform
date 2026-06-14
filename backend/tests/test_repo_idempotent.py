from app.store.duckdb_repo import DuckDBRepository


def _repo(tmp_path):
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect()
    repo.init_schema()
    return repo


def test_events_insert_idempotent_on_source_and_ordinal(tmp_path):
    repo = _repo(tmp_path)
    rows = [
        {"row_ordinal": 0, "timestamp": "2026-01-05 06:00:00", "line_id": "L",
         "station_id": None, "event_type": "LOAD", "duration": 0.0,
         "reason_code": None, "operator_entered_reason": None, "operator_entry_ts": None},
        {"row_ordinal": 1, "timestamp": "2026-01-05 06:00:00", "line_id": "L",
         "station_id": "HOIST", "event_type": "MOVE", "duration": 0.5,
         "reason_code": None, "operator_entered_reason": None, "operator_entry_ts": None},
    ]
    repo.insert_events(rows, source_file="events.csv")
    repo.insert_events(rows, source_file="events.csv")  # second load
    assert repo.count("events") == 2  # no duplicates
    repo.close()


def test_identical_events_both_kept(tmp_path):
    repo = _repo(tmp_path)
    rows = [
        {"row_ordinal": 0, "timestamp": "2026-01-05 06:00:00", "line_id": "L",
         "station_id": None, "event_type": "LOAD", "duration": 0.0,
         "reason_code": None, "operator_entered_reason": None, "operator_entry_ts": None},
        {"row_ordinal": 1, "timestamp": "2026-01-05 06:00:00", "line_id": "L",
         "station_id": None, "event_type": "LOAD", "duration": 0.0,
         "reason_code": None, "operator_entered_reason": None, "operator_entry_ts": None},
    ]
    repo.insert_events(rows, source_file="events.csv")
    assert repo.count("events") == 2
    repo.close()


def test_production_upsert_updates(tmp_path):
    repo = _repo(tmp_path)
    repo.upsert_production([{"carrier_id": "C1", "order_id": "O1",
                            "loaded_qty": 100, "good_count": 90, "redo_count": 0, "scrap_count": 10}])
    repo.upsert_production([{"carrier_id": "C1", "order_id": "O1",
                            "loaded_qty": 100, "good_count": 95, "redo_count": 0, "scrap_count": 5}])
    assert repo.count("production") == 1
    rows = repo.fetch_production()
    assert rows[0]["good_count"] == 95
    repo.close()


def test_orders_upsert_idempotent(tmp_path):
    repo = _repo(tmp_path)
    o = [{"order_id": "O1", "product_id": "P", "target_cycle": 40.0, "planned_qty": 4000}]
    repo.upsert_orders(o)
    repo.upsert_orders(o)
    assert repo.count("orders") == 1
    repo.close()
