from app.store.duckdb_repo import DuckDBRepository


def test_connect_and_close(tmp_path):
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect()
    assert repo.con is not None
    # connection usable
    assert repo.con.execute("SELECT 1").fetchone()[0] == 1
    repo.close()
    assert repo.con is None
