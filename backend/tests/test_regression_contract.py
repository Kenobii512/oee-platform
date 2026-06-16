"""G6 regresyon sözleşmesi: parite/doğruluk eşiklerini açık sabitlerle kilitler.

Bu modül yeni davranış test etmez; mevcut garantileri (OEE parite, kayıpsız OEE,
gizli kanal geri kazanımı) tek yerde, açık sabitlerle CI kapısına bağlar.
FIREWALL: extract_loss_tree ground_truth ALMAZ; gerçek yalnız doğrulamada (conftest).
"""
import inspect
import json

import pytest

from app.analytics.loss_tree import INFERRED, VISIBLE, extract_loss_tree
from app.analytics.oee import compute_oee
from tests.conftest import FIXTURES, baseline_truth_value, load_fixture_into_repo

GOLDEN = json.loads((FIXTURES / "baseline_golden.json").read_text())

# --- Eşikler (sözleşme; değiştirmek = bilinçli karar) ---
PARITY_TOL = 0.01       # OEE baseline paritesi: ±%1
VISIBLE_TOL = 0.01      # Görünür kanallar ground_truth ile ±%1
LOSSLESS_MIN = 0.95     # Kayıpsız sette OEE >= %95
INFERRED_MIN = 0.85     # Gizli kanal (FILL/SPEED) geri kazanımı >= %85

pytestmark = pytest.mark.regression


def test_firewall_extract_loss_tree_has_no_ground_truth():
    # Tam imza kontrolü test_loss_tree_firewall.py'de; burada yalnız firewall
    # özelliğini doğruluyoruz (imza meşru biçimde büyürse stabil kalsın).
    sig = inspect.signature(extract_loss_tree)
    assert "ground_truth" not in sig.parameters


def test_visible_channels_within_tolerance(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line_def)
    for cat in VISIBLE:
        truth = baseline_truth_value(cat)
        assert truth > 0, cat
        assert abs(tree.value(cat) - truth) <= VISIBLE_TOL * truth, (cat, tree.value(cat), truth)
    repo.close()


def test_inferred_channels_recover_min(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    tree = extract_loss_tree(repo.fetch_events(), repo.fetch_production(), line_def)
    for cat in INFERRED:
        truth = baseline_truth_value(cat)
        assert truth > 0, cat
        assert tree.value(cat) / truth >= INFERRED_MIN, (cat, tree.value(cat), truth)
    repo.close()


def test_lossless_oee_min(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "lossless", str(tmp_path / "l.duckdb"))
    oee = compute_oee(repo.fetch_events(), repo.fetch_production(), line_def)
    assert oee.oee >= LOSSLESS_MIN, oee.oee
    repo.close()


def test_oee_baseline_parity(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    result = compute_oee(repo.fetch_events(), repo.fetch_production(), line_def)
    for field in ("availability", "performance", "quality", "oee"):
        platform = getattr(result, field)
        golden = GOLDEN[field]
        assert abs(platform - golden) <= PARITY_TOL, (field, platform, golden)
    repo.close()
