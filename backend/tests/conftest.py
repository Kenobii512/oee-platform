"""Test yardımcıları: fixture CSV'lerini repo'ya yükleyip OEE girdisi hazırlar."""
from pathlib import Path

import pytest

from app.config import load_line_definition
from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LINE_CONFIG = Path(__file__).resolve().parents[2] / "config" / "line_default.yaml"


def load_fixture_into_repo(fixture_dir: Path, db_path: str):
    repo = DuckDBRepository(db_path)
    repo.connect()
    repo.init_schema()
    load_csv_dir(fixture_dir, repo)
    return repo


@pytest.fixture
def line_def():
    return load_line_definition(LINE_CONFIG)
