"""Tek seferlik golden fixture üreteci. Simülatör .venv'iyle çalıştırılır:

    cd simulator
    .venv/Scripts/python ../oee-platform/backend/tests/fixtures/_generate.py

Çıktı: oee-platform/backend/tests/fixtures/{lossless,baseline}/*.csv + baseline_golden.json
Tests bu statik dosyaları okur; simülatöre çalışma-zamanı bağımlılığı yoktur.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parents[4] / "simulator"
sys.path.insert(0, str(SIM))

from src.config import load_config            # noqa: E402
from src.line import run_simulation           # noqa: E402
from src.losses import load_scenario          # noqa: E402
from src.metrics import compute_oee           # noqa: E402

OUT = Path(__file__).resolve().parent
CONFIG = SIM / "config" / "line_default.yaml"
SCENARIO = SIM / "config" / "scenario_baseline.yaml"
SEED = 42


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config(CONFIG)

    # Lossless set (no scenario)
    res = run_simulation(cfg, seed=SEED)
    res.recorder.write_csvs(OUT / "lossless", res.carriers, cfg.orders)
    (OUT / "lossless" / "ground_truth.csv").unlink(missing_ok=True)

    # Baseline set (with loss scenario)
    scn = load_scenario(SCENARIO)
    res_b = run_simulation(cfg, seed=SEED, scenario=scn)
    res_b.recorder.write_csvs(OUT / "baseline", res_b.carriers, cfg.orders)
    oee = compute_oee(res_b, cfg)
    (OUT / "baseline_golden.json").write_text(json.dumps({
        "seed": SEED,
        "availability": oee.availability,
        "performance": oee.performance,
        "quality": oee.quality,
        "oee": oee.oee,
    }, indent=2))
    print("fixtures yazıldı:", OUT)


if __name__ == "__main__":
    main()
