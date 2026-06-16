"""G9 baseline öncelik testi: en üst öneri DOWNTIME hedefli; liste TL'ye göre azalan.

Öneriler kayıp ağacı + TL lensi (G11) üstüne kurulur. Baseline'da en büyük TL kaybı
DOWNTIME olduğundan (bkz test_cost_parity.test_downtime_is_largest_tl_loss) en üstteki
öneri DOWNTIME hedefli olmalı. FIREWALL: ground_truth kullanılmaz.
"""
from app.analytics.cost import to_tl
from app.analytics.loss_tree import extract_loss_tree
from app.analytics.recommend import RatioGainEstimator, generate_recommendations
from app.config import load_cost_config, load_recommend_config
from tests.conftest import FIXTURES, load_fixture_into_repo

COSTS_PATH = FIXTURES.parents[2] / "config" / "costs.yaml"
RECOMMEND_PATH = FIXTURES.parents[2] / "config" / "recommend.yaml"


def _recommend(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "r.duckdb"))
    events = repo.fetch_events()
    tree = extract_loss_tree(events, repo.fetch_production(), line_def)
    cost_tree = to_tl(tree, load_cost_config(COSTS_PATH))
    rec_cfg = load_recommend_config(RECOMMEND_PATH)
    recs = generate_recommendations(cost_tree, events, rec_cfg, RatioGainEstimator(rec_cfg))
    repo.close()
    return recs


def test_top_recommendation_targets_downtime(tmp_path, line_def):
    recs = _recommend(tmp_path, line_def)
    assert recs, "öneri üretilmedi"
    assert recs[0]["category"] == "DOWNTIME"


def test_list_sorted_by_tl_descending(tmp_path, line_def):
    recs = _recommend(tmp_path, line_def)
    tls = [r["tl"] for r in recs]
    assert tls == sorted(tls, reverse=True)


def test_at_least_three_recommendations(tmp_path, line_def):
    recs = _recommend(tmp_path, line_def)
    assert len(recs) >= 3
