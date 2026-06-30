"""H4 — çok-seed istatistiksel doğrulama (regresyon kapısı).

Pariteyi tek seed yerine DAĞILIM olarak kanıtlar: platform OEE motoru her seed'de
simülatör-referans OEE'ye ±tol uyar (ortalama ±%1, hiçbir seed taban-altı değil) ve
gizli kanal (FILL/SPEED) çıkarım geri kazanımının MEDYANI eşik üstündedir.

Platform CANLI kodla yeniden hesaplar (commit'li CSV fixture'larından); simülatöre
çalışma-zamanı bağımlılığı YOK. ground_truth yalnız test-tarafı doğrulamada.
"""
from statistics import mean, median

import pytest

from app.analytics.loss_tree import INFERRED, extract_loss_tree
from app.analytics.oee import compute_oee
from app.config import load_line_definition
from tests.conftest import (
    LINE_CONFIG,
    MULTISEED,
    load_fixture_into_repo,
    multiseed_golden,
    truth_value_from,
)

pytestmark = pytest.mark.regression

# Eşikler (test_regression_contract ile hizalı + dağılım toleransı).
PARITY_TOL = 0.01  # ortalama |platform - sim| OEE
SEED_FLOOR_TOL = 0.02  # tek seed'de izin verilen maksimum sapma (hiçbiri taban-altı değil)
INFERRED_MIN = 0.85  # gizli kanal geri kazanım medyanı

GOLDEN = multiseed_golden()
SEEDS = GOLDEN["seeds"]


def _line():
    return load_line_definition(LINE_CONFIG)


def test_oee_parity_distribution(tmp_path):
    line = _line()
    diffs = []
    for s in SEEDS:
        repo = load_fixture_into_repo(MULTISEED / f"seed_{s}", str(tmp_path / f"s{s}.duckdb"))
        res = compute_oee(repo.fetch_events(), repo.fetch_production(), line)
        repo.close()
        g = GOLDEN["per_seed"][str(s)]
        d = abs(res.oee - g["oee"])
        diffs.append(d)
        assert d <= SEED_FLOOR_TOL, f"seed {s}: OEE sapması {d:.4f} > {SEED_FLOOR_TOL}"
    assert mean(diffs) <= PARITY_TOL, f"ortalama OEE sapması {mean(diffs):.4f} > {PARITY_TOL}"


def test_inferred_recovery_distribution(tmp_path):
    line = _line()
    recoveries = {c: [] for c in INFERRED}
    for s in SEEDS:
        seed_dir = MULTISEED / f"seed_{s}"
        repo = load_fixture_into_repo(seed_dir, str(tmp_path / f"r{s}.duckdb"))
        tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line)
        repo.close()
        for cat in INFERRED:
            truth = truth_value_from(seed_dir / "ground_truth.csv", cat)
            if truth > 0:
                recoveries[cat].append(tree.value(cat) / truth)
    for cat in INFERRED:
        med = median(recoveries[cat])
        assert med >= INFERRED_MIN, f"{cat} geri kazanım medyanı {med:.3f} < {INFERRED_MIN}"
