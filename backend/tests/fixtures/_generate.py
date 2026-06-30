"""Tek seferlik golden fixture üreteci. Simülatör .venv'iyle çalıştırılır:

    cd simulator
    .venv/Scripts/python ../oee-platform/backend/tests/fixtures/_generate.py

Çıktı (hepsi seed 42, no-scrap model + events.csv carrier_id'li):
- oee-platform/backend/tests/fixtures/{lossless,baseline}/*.csv
- oee-platform/backend/tests/fixtures/baseline_golden.json
- oee-platform/backend/tests/fixtures/scenarios/<id>/*.csv  (6 demo senaryosu)

Tests bu statik dosyaları okur; simülatöre çalışma-zamanı bağımlılığı yoktur.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parents[4] / "simulator"
sys.path.insert(0, str(SIM))

from src.config import load_config  # noqa: E402
from src.line import run_simulation  # noqa: E402
from src.losses import load_scenario  # noqa: E402
from src.metrics import compute_oee  # noqa: E402

OUT = Path(__file__).resolve().parent
CONFIG = SIM / "config" / "line_default.yaml"
SCENARIO = SIM / "config" / "scenario_baseline.yaml"
SCENARIO_DIR = SIM / "config" / "scenarios"
SEED = 42
# H4: çok-seed parite/geri-kazanım dağılımı için sabit seed listesi (N=10).
MULTISEEDS = (42, 7, 123, 1, 999, 2024, 13, 77, 256, 8)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config(CONFIG)

    # Lossless set (no scenario)
    res = run_simulation(cfg, seed=SEED)
    res.recorder.write_csvs(OUT / "lossless", res.carriers, cfg.orders)
    (OUT / "lossless" / "ground_truth.csv").unlink(missing_ok=True)

    # Baseline set (with loss scenario) + golden OEE
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
        "final_yield": oee.final_yield,
    }, indent=2))

    # Demo senaryo kataloğu (G8): her senaryo kendi dizinine.
    for path in sorted(SCENARIO_DIR.glob("*.yaml")):
        sid = path.stem
        s = load_scenario(path)
        r = run_simulation(cfg, seed=SEED, scenario=s)
        r.recorder.write_csvs(OUT / "scenarios" / sid, r.carriers, cfg.orders)

    # H4: çok-seed golden seti — her seed baseline senaryosuyla; CSV + sim OEE özeti.
    per_seed: dict[str, dict] = {}
    for s in MULTISEEDS:
        r = run_simulation(cfg, seed=s, scenario=scn)
        r.recorder.write_csvs(OUT / "multiseed" / f"seed_{s}", r.carriers, cfg.orders)
        o = compute_oee(r, cfg)
        per_seed[str(s)] = {
            "availability": o.availability,
            "performance": o.performance,
            "quality": o.quality,
            "oee": o.oee,
            "final_yield": o.final_yield,
        }
    (OUT / "multiseed_golden.json").write_text(json.dumps(
        {"seeds": list(MULTISEEDS), "per_seed": per_seed}, indent=2
    ))

    print("fixtures yazildi:", OUT)


if __name__ == "__main__":
    main()
