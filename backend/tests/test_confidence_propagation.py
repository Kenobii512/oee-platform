"""H3 — cost/recommend belirsizliği tutarlı taşır.

to_tl her kategoriye tl_low/tl_high/confidence/low_confidence ekler; çıkarım kanalı
düşük yeterlilikte düşük güven, görünür kanal tam güven. total_tl (nokta toplam) DEĞİŞMEZ.
recommend düşük güvenli kalemi işaretler.
"""
from app.analytics.cost import to_tl
from app.analytics.loss_tree import extract_loss_tree
from app.analytics.recommend import RatioGainEstimator, generate_recommendations
from app.config import (
    load_confidence_config,
    load_cost_config,
    load_recommend_config,
)
from tests.conftest import CONFIG_DIR, FIXTURES, fresh_repo

_CONF = load_confidence_config(str(CONFIG_DIR / "confidence.yaml"))
_COST = load_cost_config(str(CONFIG_DIR / "costs.yaml"))
_REC = load_recommend_config(str(CONFIG_DIR / "recommend.yaml"))


def _baseline_tree(tmp_path, line_def):
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    from app.ingest.loader import load_csv_dir

    load_csv_dir(FIXTURES / "baseline", repo)
    events = repo.fetch_events()
    tree = extract_loss_tree(events, repo.fetch_production(), line_def)
    repo.close()
    return tree, events


def test_to_tl_carries_band_and_confidence(tmp_path, line_def):
    tree, _ = _baseline_tree(tmp_path, line_def)
    point = to_tl(tree, _COST)  # cfg yok -> geriye uyumlu (nokta)
    out = to_tl(tree, _COST, confidence_cfg=_CONF, sufficiency=0.3)
    # total_tl değişmez (nokta toplam korunur)
    assert abs(out["total_tl"] - point["total_tl"]) < 1e-6
    for c in out["categories"]:
        assert c["tl_low"] <= c["tl"] <= c["tl_high"]
        if c["kind"] == "inferred":
            assert c["confidence"] < 1.0
            assert c["low_confidence"] is True  # 0.3 < eşik 0.5
        else:
            assert c["confidence"] == 1.0
            assert c["low_confidence"] is False


def test_recommend_flags_low_confidence(tmp_path, line_def):
    tree, events = _baseline_tree(tmp_path, line_def)
    cost_tree = to_tl(tree, _COST, confidence_cfg=_CONF, sufficiency=0.3)
    recs = generate_recommendations(cost_tree, events, _REC, RatioGainEstimator(_REC))
    inferred = [r for r in recs if r["kind"] == "inferred"]
    assert inferred, "çıkarım kanalı önerisi bekleniyor"
    assert any(r["low_confidence"] for r in inferred)
