import concurrent.futures

from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository
from tests.conftest import FIXTURES


def test_concurrent_reads_do_not_crash(tmp_path):
    # Pano endpoint'leri paralel istek atar; tek DuckDB bağlantısının eşzamanlı
    # erişimi kilitle güvenli olmalı (aksi halde segfault).
    repo = DuckDBRepository(str(tmp_path / "c.duckdb"))
    repo.connect()
    repo.init_schema()
    load_csv_dir(FIXTURES / "baseline", repo)

    def work(_):
        return (
            len(repo.fetch_events())
            + len(repo.fetch_production())
            + repo.count("events")
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(work, range(40)))

    assert all(r > 0 for r in results)
    repo.close()
