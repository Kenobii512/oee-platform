"""Test yardımcıları: fixture CSV'lerini repo'ya yükleyip OEE girdisi hazırlar."""
import csv
from pathlib import Path

import pytest

from app.config import load_line_definition
from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LINE_CONFIG = Path(__file__).resolve().parents[2] / "config" / "line_default.yaml"

# Kayıp ağacı doğrulamasında doğal eksen (dakika vs parça) seçimi.
_MINUTES = {"DOWNTIME", "MICROSTOP", "SPEED_LOSS"}


def load_fixture_into_repo(fixture_dir: Path, db_path: str):
    repo = DuckDBRepository(db_path)
    repo.connect()
    repo.init_schema()
    load_csv_dir(fixture_dir, repo)
    return repo


def baseline_truth_value(category: str) -> float:
    """ground_truth.csv'den kategori bazında GERÇEK kayıp (doğal eksende).

    Yalnız doğrulama (test) içindir — firewall sadece extract_loss_tree için geçerli;
    ground_truth gerçeği test tarafında kullanılabilir (accuracy.py `compare` deseni).
    """
    minutes = 0.0
    parts = 0.0
    with open(FIXTURES / "baseline" / "ground_truth.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["event_type"] == category:
                minutes += float(r["duration"])
                parts += float(r["qty"])
    return minutes if category in _MINUTES else parts


@pytest.fixture
def line_def():
    return load_line_definition(LINE_CONFIG)
