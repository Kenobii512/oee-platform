"""FastAPI uygulama girişi + repo yaşam döngüsü + pano/statik servisi."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.cost_routes import router as cost_router
from app.api.dashboard_routes import render_dashboard
from app.api.dashboard_routes import router as dashboard_router
from app.api.data_quality_routes import router as data_quality_router
from app.api.ingest_routes import router as ingest_router
from app.api.loss_tree_routes import router as loss_tree_router
from app.api.oee_routes import router as oee_router
from app.api.recommend_routes import router as recommend_router
from app.api.scenario_routes import router as scenario_router
from app.api.trend_routes import router as trend_router
from app.config import load_app_config
from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

_BASE = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = load_app_config()
    repo = DuckDBRepository(cfg.duckdb_path)
    repo.connect()
    repo.init_schema()
    app.state.repo = repo
    app.state.config = cfg
    # Demo kolaylığı: SAMPLE_DATA_DIR verilirse açılışta otomatik ingest.
    sample = os.environ.get("SAMPLE_DATA_DIR")
    if sample and Path(sample).is_dir():
        load_csv_dir(sample, repo)
    try:
        yield
    finally:
        repo.close()


app = FastAPI(title="OEE Platform", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")

app.include_router(ingest_router)
app.include_router(oee_router)
app.include_router(loss_tree_router)
app.include_router(cost_router)
app.include_router(recommend_router)
app.include_router(trend_router)
app.include_router(data_quality_router)
app.include_router(scenario_router)
app.include_router(dashboard_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# SPA servisi: React build (frontend_dist) varsa kök '/' onu sunar (Jinja '/legacy'de).
# Build yoksa (dev/test) Jinja panosu '/'ta fallback kalır. Mount EN SONA eklenir ki
# /health ve API route'larını gölgelemesin (Starlette sıra-bazlı eşler).
_FRONTEND_DIST = _BASE / "frontend_dist"

if (_FRONTEND_DIST / "index.html").is_file():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="spa")
else:
    @app.get("/", response_class=HTMLResponse)
    def root(request: Request) -> HTMLResponse:
        return render_dashboard(request)
