"""GET /scenarios -> katalog; POST /scenarios/{id}/activate -> o senaryonun verisini ingest et.

Aktivasyon, mevcut loader'ı kullanır (ground_truth firewall'u korunur — loader
`ground_truth*` dosyalarını açmadan atlar). data_dir backend rootuna görelidir.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.config import load_scenario_catalog
from app.ingest.loader import load_csv_dir

router = APIRouter()

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


@router.get("/scenarios")
def list_scenarios(request: Request) -> dict:
    cat = load_scenario_catalog(request.app.state.config.scenario_config_path)
    return {"scenarios": [s.__dict__ for s in cat]}


@router.post("/scenarios/{scenario_id}/activate")
def activate_scenario(scenario_id: str, request: Request) -> dict:
    cat = {s.id: s for s in load_scenario_catalog(request.app.state.config.scenario_config_path)}
    info = cat.get(scenario_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"bilinmeyen senaryo: {scenario_id}")
    data_dir = (_BACKEND_ROOT / info.data_dir).resolve()
    if not data_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"veri yok: {info.data_dir}")
    report = load_csv_dir(data_dir, request.app.state.repo)
    return {"activated": scenario_id, "ingest": report.to_dict()}
