"""What-if analitiği: azaltım oranları → önce/sonra OEE bileşenleri + TL kazanç.

Tek doğruluk kaynağı ilkesi: compute_whatif, oee.py'nin YARDIMCILARINI kullanır
(availability_from_events, nominal_full_pass, üretim toplamları) — formül kopyalamaz.
"""
import pytest

from app.analytics.cost import to_tl
from app.analytics.loss_tree import extract_loss_tree
from app.analytics.oee import compute_oee
from app.analytics.whatif import compute_whatif
from app.config import load_cost_config, load_line_definition
from tests.conftest import CONFIG_DIR, FIXTURES, LINE_CONFIG, load_fixture_into_repo

ZERO = {"downtime": 0.0, "microstop": 0.0, "speed_loss": 0.0,
        "quality_redo": 0.0, "fill_loss": 0.0}


@pytest.fixture(scope="module")
def baseline_ctx(tmp_path_factory):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path_factory.mktemp("wi") / "w.duckdb"))
    events, production = repo.fetch_events(), repo.fetch_production()
    repo.close()
    line = load_line_definition(LINE_CONFIG)
    tree = extract_loss_tree(events, production, line)
    cost = to_tl(tree, load_cost_config(CONFIG_DIR / "costs.yaml"))
    return events, production, line, cost


def _wi(ctx, **over):
    events, production, line, cost = ctx
    return compute_whatif(events, production, line, cost, {**ZERO, **over})


def test_zero_reductions_equal_baseline(baseline_ctx):
    events, production, line, _ = baseline_ctx
    base = compute_oee(events, production, line)
    r = _wi(baseline_ctx)
    for k, v in (("availability", base.availability), ("performance", base.performance),
                 ("quality", base.quality), ("oee", base.oee)):
        assert abs(r["baseline"][k] - v) < 1e-9
        assert abs(r["adjusted"][k] - v) < 1e-9
    assert r["gain"]["total_tl"] == 0.0


def test_downtime_reduction_moves_only_availability(baseline_ctx):
    r = _wi(baseline_ctx, downtime=0.3)
    assert r["adjusted"]["availability"] > r["baseline"]["availability"]
    assert r["adjusted"]["performance"] == pytest.approx(r["baseline"]["performance"])
    assert r["adjusted"]["quality"] == pytest.approx(r["baseline"]["quality"])
    assert r["adjusted"]["oee"] > r["baseline"]["oee"]


def test_speed_reduction_moves_only_performance(baseline_ctx):
    r = _wi(baseline_ctx, speed_loss=0.5)
    assert r["adjusted"]["performance"] > r["baseline"]["performance"]
    assert r["adjusted"]["availability"] == pytest.approx(r["baseline"]["availability"])
    assert r["adjusted"]["quality"] == pytest.approx(r["baseline"]["quality"])


def test_redo_reduction_moves_only_quality(baseline_ctx):
    r = _wi(baseline_ctx, quality_redo=0.4)
    assert r["adjusted"]["quality"] > r["baseline"]["quality"]
    assert r["adjusted"]["availability"] == pytest.approx(r["baseline"]["availability"])
    assert r["adjusted"]["performance"] == pytest.approx(r["baseline"]["performance"])


def test_fill_reduction_gains_tl_but_not_oee(baseline_ctx):
    r = _wi(baseline_ctx, fill_loss=0.5)
    assert r["adjusted"]["oee"] == pytest.approx(r["baseline"]["oee"])
    assert r["gain"]["total_tl"] > 0


def test_full_reduction_clamps(baseline_ctx):
    r = _wi(baseline_ctx, downtime=1.0, microstop=1.0, speed_loss=1.0, quality_redo=1.0)
    adj = r["adjusted"]
    assert 0.0 <= adj["availability"] <= 1.0
    assert 0.0 <= adj["performance"] <= 1.0
    assert 0.0 <= adj["quality"] <= 1.0
    assert adj["oee"] >= r["baseline"]["oee"]


def test_gain_is_tl_times_reduction(baseline_ctx):
    events, production, line, cost = baseline_ctx
    r = _wi(baseline_ctx, downtime=0.3, fill_loss=0.2)
    tl = {c["category"]: c for c in cost["categories"]}
    expected = tl["DOWNTIME"]["tl"] * 0.3 + tl["FILL_LOSS"]["tl"] * 0.2
    assert r["gain"]["total_tl"] == pytest.approx(expected)
    per = {p["category"]: p for p in r["gain"]["per_category"]}
    assert per["DOWNTIME"]["gain_tl"] == pytest.approx(tl["DOWNTIME"]["tl"] * 0.3)
    assert per["DOWNTIME"]["gain_tl_low"] <= per["DOWNTIME"]["gain_tl_high"]


def test_empty_data_graceful(baseline_ctx):
    _, _, line, cost = baseline_ctx
    r = compute_whatif([], [], line, cost, dict(ZERO))
    assert r["baseline"]["oee"] == 0.0
    assert r["adjusted"]["oee"] == 0.0


# ---- endpoint ----------------------------------------------------------------


def test_whatif_endpoint_shape_and_validation(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "w.duckdb"))
    monkeypatch.setenv("SAMPLE_DATA_DIR", str(FIXTURES / "baseline"))
    with TestClient(app) as c:
        r = c.get("/whatif", params={"downtime": 0.3})
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"baseline", "adjusted", "gain"}
        assert body["adjusted"]["availability"] > body["baseline"]["availability"]
        assert c.get("/whatif", params={"downtime": 1.5}).status_code == 400
        assert c.get("/whatif", params={"downtime": -0.1}).status_code == 400
