"""Pilot rapor aracı testleri: veri çekirdeği (build_report_data) + HTML render + CLI.

Rapor karar VERMEZ (doctor'ın işi); belgeler — eşik ihlali ✗ olarak görünür.
Veri çekirdeği saf dict üretir (HTML bilmez); render veri kaynağını bilmez.
"""
import pytest

from app.config import load_line_definition
from tests.conftest import FIXTURES, LINE_CONFIG, RAW
from tools.pilot_report import build_report_data

SCENARIOS = FIXTURES / "scenarios"
STORM = SCENARIOS / "breakdown_storm"


@pytest.fixture(scope="module")
def line_def_m():
    return load_line_definition(LINE_CONFIG)


@pytest.fixture(scope="module")
def storm_data(line_def_m):
    return build_report_data(STORM, line_def_m)


# ---- build_report_data: mutlu yol (golden senaryo) ---------------------------


def test_storm_has_data_and_oee(storm_data):
    assert storm_data["has_data"] is True
    oee = storm_data["oee"]
    assert oee is not None
    assert 0.0 < oee["oee"] <= 1.0


def test_storm_losses_tl_descending_with_bands(storm_data):
    cats = storm_data["losses"]["categories"]
    assert cats[0]["category"] == "DOWNTIME"  # senaryonun adlı baskın kaybı
    tls = [c["tl"] for c in cats]
    assert tls == sorted(tls, reverse=True)
    for c in cats:
        assert {"tl_low", "tl_high", "kind", "confidence"} <= set(c)
    assert storm_data["losses"]["total_tl"] > 0


def test_storm_recommendations_have_ranges(storm_data):
    recs = storm_data["recommendations"]
    assert recs["total_gain_tl"] > 0
    top = recs["items"][0]
    assert 0 < top["estimated_gain_tl_low"] <= top["estimated_gain_tl_high"]


def test_storm_trend_and_quality(storm_data):
    assert len(storm_data["trend"]) >= 1
    q = storm_data["quality"]
    assert q["event_count"] > 0
    assert q["sufficiency"] > 0.0
    assert q["reject_rate"] == 0.0  # temiz golden fixture


def test_storm_criteria_auto_evaluation(storm_data):
    crit = storm_data["criteria"]
    for key in ("k1", "k2", "k3"):
        assert isinstance(crit[key]["auto_pass"], bool)
        assert crit[key]["detail"]  # gerekçe metni boş değil
    assert crit["k2"]["auto_pass"] is True  # total_gain > 0 + low > 0
    assert crit["k3"]["auto_pass"] is True  # red 0 <= %5, H3 yeterli


# ---- build_report_data: kenarlar ---------------------------------------------


def test_empty_dir_report_still_builds(tmp_path, line_def_m):
    empty = tmp_path / "bos"
    empty.mkdir()
    data = build_report_data(empty, line_def_m)
    assert data["has_data"] is False
    assert data["oee"] is None
    assert data["losses"] is None
    assert data["trend"] == []
    # Değerlendirilemedi (None) — sahte ✓/✗ yok.
    assert data["criteria"]["k1"]["auto_pass"] is None


def test_adapter_raw_report_data(line_def_m):
    data = build_report_data(RAW, line_def_m, adapter="generic_plant")
    assert data["has_data"] is True
    assert data["quality"]["accepted"].get("events", 0) > 0
