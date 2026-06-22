"""GET /replay/stream?scenario=&speed=&steps= -> snapshot'ları SSE ile yayınlar.

Senaryoyu AYRI bir in-memory DuckDB'ye yükler (paylaşılan pano DB'sine dokunmaz; firewall:
ground_truth ingest edilmez), büyüyen 'şimdiye kadar' snapshot'larını gerçek-zaman temposuyla
(tick = base/speed) push eder. Her snapshot to_thread'de üretilir (senkron repo/analytics event
loop'u bloklamasın). İzolasyon sayesinde replay, /oee panosunun verisini değiştirmez.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.analytics.replay import snapshot_at, time_steps
from app.api.scenario_routes import _BACKEND_ROOT
from app.config import (
    load_cost_config,
    load_line_definition,
    load_recommend_config,
    load_scenario_catalog,
)
from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

router = APIRouter()

_BASE_TICK = 0.2  # saniye/snapshot @ speed=1


@router.get("/replay/stream")
async def replay_stream(
    request: Request,
    scenario: str = Query(...),
    speed: float = Query(1.0, gt=0),
    steps: int = Query(60, gt=0, le=600),
) -> StreamingResponse:
    cfg = request.app.state.config
    cat = {s.id: s for s in load_scenario_catalog(cfg.scenario_config_path)}
    info = cat.get(scenario)
    if info is None:
        raise HTTPException(status_code=404, detail=f"bilinmeyen senaryo: {scenario}")
    data_dir = (_BACKEND_ROOT / info.data_dir).resolve()
    if not data_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"veri yok: {info.data_dir}")

    # İZOLASYON: replay paylaşılan repo'yu (pano /oee aynı tabloları okur) ASLA değiştirmez.
    # Her istek için ayrı in-memory DuckDB; akış bitince atılır → pano verisi temiz kalır.
    # (Eskiden app.state.repo üzerinde reset()+ingest yapıp /oee'yi senaryoya kaydırıyordu.)
    temp = DuckDBRepository(":memory:")
    temp.connect()
    temp.init_schema()
    load_csv_dir(data_dir, temp)
    line = load_line_definition(cfg.line_config_path)
    costs = load_cost_config(cfg.cost_config_path)
    rc = load_recommend_config(cfg.recommend_config_path)

    async def gen():
        try:
            all_events = await asyncio.to_thread(temp.fetch_events, None, None)
            stamps = [e["timestamp"] for e in all_events if e.get("timestamp") is not None]
            for cut in time_steps(stamps, steps):
                snap = await asyncio.to_thread(snapshot_at, temp, line, costs, rc, cut)
                yield f"data: {json.dumps(snap)}\n\n"
                await asyncio.sleep(_BASE_TICK / speed)
            yield "event: done\ndata: {}\n\n"
        finally:
            temp.close()  # in-memory DB'yi serbest bırak (paylaşılan repo'ya dokunulmadı)

    return StreamingResponse(gen(), media_type="text/event-stream")
