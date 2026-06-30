"""H3 — güven aralığı: low ≤ value ≤ high; baseline'da çıkarım bandı ground_truth'u KAPSAR.

Kritik kabul kriteri: sahada ground-truth olmadan üretilen bandın, doğrulamada
bilinen gerçeği içermesi (low ≤ gerçek ≤ high). Çıkarım sistematik olarak eksik sayar
→ gerçek nokta tahminin üstündedir; band yukarı asimetrik olduğu için kapsar.
"""
import inspect

from app.analytics.confidence import band, data_sufficiency
from app.analytics.loss_tree import extract_loss_tree
from app.config import load_confidence_config
from tests.conftest import CONFIG_DIR, FIXTURES, baseline_truth_value, fresh_repo

_CFG = load_confidence_config(str(CONFIG_DIR / "confidence.yaml"))


def test_point_within_band_full_sufficiency():
    low, high = band(100.0, 1.0, _CFG)
    assert low <= 100.0 <= high


def test_lower_sufficiency_widens_band():
    lo_full, hi_full = band(100.0, 1.0, _CFG)
    lo_low, hi_low = band(100.0, 0.3, _CFG)
    assert lo_low < lo_full and hi_low > hi_full  # düşük güven -> daha geniş


def test_firewall_no_ground_truth_param():
    assert "ground_truth" not in inspect.signature(band).parameters


def test_baseline_inferred_band_covers_truth(tmp_path, line_def):
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    from app.ingest.loader import load_csv_dir

    load_csv_dir(FIXTURES / "baseline", repo)
    events, production = repo.fetch_events(), repo.fetch_production()
    tree = extract_loss_tree(events, production, line_def)
    s = data_sufficiency(events, production, line_def)
    for channel in ("FILL_LOSS", "SPEED_LOSS"):
        value = tree.value(channel)
        truth = baseline_truth_value(channel)
        low, high = band(value, s, _CFG)
        assert low <= truth <= high, f"{channel}: {low:.1f} <= {truth:.1f} <= {high:.1f} değil"
    repo.close()
