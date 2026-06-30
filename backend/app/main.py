"""FastAPI uygulama girişi + repo yaşam döngüsü + pano/statik servisi."""
from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import auth
from app.api._params import BadRequest
from app.api.cost_routes import router as cost_router
from app.api.dashboard_routes import render_dashboard
from app.api.dashboard_routes import router as dashboard_router
from app.api.data_quality_routes import router as data_quality_router
from app.api.ingest_routes import router as ingest_router
from app.api.line_routes import router as line_router
from app.api.loss_tree_routes import router as loss_tree_router
from app.api.oee_routes import router as oee_router
from app.api.recommend_routes import router as recommend_router
from app.api.replay_routes import router as replay_router
from app.api.scenario_routes import router as scenario_router
from app.api.trend_routes import router as trend_router
from app.config import load_app_config
from app.ingest.loader import load_csv_dir
from app.logging_setup import setup_logging
from app.store.duckdb_repo import DuckDBRepository

_BASE = Path(__file__).resolve().parent
_req_log = logging.getLogger("oee.request")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
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


# --- Tutarlı istemci hatası (H9): bozuk parametre -> 400 (500 değil) ---
@app.exception_handler(BadRequest)
async def _bad_request_handler(request: Request, exc: BadRequest):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# --- İstek zamanlama logu (H9): her isteği method/path/status/duration_ms ile loglar ---
@app.middleware("http")
async def _timing(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    dur_ms = (time.perf_counter() - t0) * 1000.0
    _req_log.info(
        "request method=%s path=%s status=%s duration_ms=%.1f",
        request.method, request.url.path, response.status_code, dur_ms,
    )
    return response


# --- Erişim katmanı (form-tabanlı giriş; yalnız OEE_AUTH_PASS tanımlıysa aktif) ---
@app.middleware("http")
async def _auth_gate(request: Request, call_next):
    if (
        auth.enabled()
        and not auth.is_public(request.url.path)
        and not auth.verify(request.cookies.get(auth.COOKIE))
    ):
        if "text/html" in request.headers.get("accept", ""):
            return RedirectResponse("/login", status_code=303)
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
def login_get(error: int = 0) -> HTMLResponse:
    return HTMLResponse(auth.login_page(error=bool(error)))


@app.post("/login")
async def login_post(request: Request):
    username, password = auth.parse_login_form(await request.body())
    if auth.check_credentials(username, password):
        secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(
            auth.COOKIE, auth.make_token(), httponly=True, samesite="lax",
            secure=secure, max_age=60 * 60 * 12,
        )
        return resp
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/logout")
def logout() -> RedirectResponse:
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(auth.COOKIE)
    return resp


app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")

app.include_router(ingest_router)
app.include_router(oee_router)
app.include_router(loss_tree_router)
app.include_router(cost_router)
app.include_router(recommend_router)
app.include_router(trend_router)
app.include_router(data_quality_router)
app.include_router(scenario_router)
app.include_router(line_router)
app.include_router(replay_router)
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
