"""H9 — performans smoke: ~12 haftalık ölçekli veride pano uçları bütçe altında.

Büyük fixture commit'lemeden: baseline'ı K haftalık-ofsetli kopyayla ölçekler
(carrier_id'ler benzersizleştirilir). En ağır uç /oee/trend (gün başına compute_oee).
"""
import csv
import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import FIXTURES

PERF_BUDGET_S = 2.0
WEEKS = 6  # baseline ~2 hafta × 6 ≈ 12 hafta (~9.5k olay)


def _shift_ts(value: str, weeks: int) -> str:
    if not value:
        return value
    dt = datetime.fromisoformat(value) + timedelta(weeks=weeks)
    return dt.isoformat(sep=" ")


def _scale_baseline(tmp_path, weeks: int):
    src = FIXTURES / "baseline"
    out = tmp_path / "scaled"
    out.mkdir()

    # events: her hafta kopyası — timestamp ofset + carrier_id suffix
    with open(src / "events.csv", encoding="utf-8") as f:
        ev_rows = list(csv.DictReader(f))
        ev_cols = ev_rows[0].keys()
    with open(out / "events.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ev_cols), lineterminator="\n")
        w.writeheader()
        for k in range(weeks):
            for r in ev_rows:
                nr = dict(r)
                nr["timestamp"] = _shift_ts(r["timestamp"], k)
                if r.get("operator_entry_ts"):
                    nr["operator_entry_ts"] = _shift_ts(r["operator_entry_ts"], k)
                if r.get("carrier_id"):
                    nr["carrier_id"] = f"{r['carrier_id']}-W{k}"
                w.writerow(nr)

    # production: carrier_id benzersizleştir (her hafta)
    with open(src / "production.csv", encoding="utf-8") as f:
        pr_rows = list(csv.DictReader(f))
        pr_cols = pr_rows[0].keys()
    with open(out / "production.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pr_cols), lineterminator="\n")
        w.writeheader()
        for k in range(weeks):
            for r in pr_rows:
                nr = dict(r)
                nr["carrier_id"] = f"{r['carrier_id']}-W{k}"
                w.writerow(nr)

    # orders: aynen (order_id paylaşılır)
    (out / "orders.csv").write_bytes((src / "orders.csv").read_bytes())
    return out


@pytest.mark.perf
def test_dashboard_endpoints_under_budget(tmp_path, monkeypatch):
    scaled = _scale_baseline(tmp_path, WEEKS)
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "perf.duckdb"))
    with TestClient(app) as client:
        rep = client.post("/ingest", json={"path": str(scaled)})
        assert rep.status_code == 200
        assert rep.json()["accepted"]["events"] > 5000  # gerçekten ölçekli
        for ep in ("/oee", "/loss-tree/cost", "/oee/trend?bucket=day"):
            t0 = time.perf_counter()
            r = client.get(ep)
            elapsed = time.perf_counter() - t0
            assert r.status_code == 200, f"{ep}: {r.status_code}"
            assert elapsed < PERF_BUDGET_S, f"{ep}: {elapsed:.2f}s >= {PERF_BUDGET_S}s"
