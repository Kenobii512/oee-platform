"""G7 replay: determinizm + final parite.

Son snapshot (to=max timestamp) tüm veriyi tek seferde işlemekle BİREBİR; pencere monoton büyür.
FIREWALL: ground_truth ingest edilmez (load_fixture_into_repo da atlar).
"""
from app.analytics.replay import iter_snapshots, snapshot_at
from app.config import load_cost_config, load_recommend_config
from tests.conftest import FIXTURES, load_fixture_into_repo

COSTS = FIXTURES.parents[2] / "config" / "costs.yaml"
RECO = FIXTURES.parents[2] / "config" / "recommend.yaml"


def test_final_snapshot_matches_full(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "r.duckdb"))
    costs, rc = load_cost_config(COSTS), load_recommend_config(RECO)
    snaps = list(iter_snapshots(repo, line_def, costs, rc, n_steps=20))
    assert len(snaps) == 20
    counts = [s["event_count"] for s in snaps]
    assert counts == sorted(counts)  # monoton büyüyen pencere
    full = snapshot_at(repo, line_def, costs, rc, None)  # tüm veri
    assert snaps[-1]["event_count"] == full["event_count"]
    assert abs(snaps[-1]["oee"]["oee"] - full["oee"]["oee"]) < 1e-9  # final == tam
    assert abs(snaps[-1]["cost"]["total_tl"] - full["cost"]["total_tl"]) < 1e-9
    repo.close()


def test_window_grows_tl_and_downtime(tmp_path, line_def):
    # Pencere ilerledikçe biriken TL artar (canlı anlatının özü).
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "g.duckdb"))
    costs, rc = load_cost_config(COSTS), load_recommend_config(RECO)
    snaps = list(iter_snapshots(repo, line_def, costs, rc, n_steps=10))
    totals = [s["cost"]["total_tl"] for s in snaps]
    assert totals == sorted(totals)  # TL monoton artar
    assert totals[-1] > totals[0]
    repo.close()
