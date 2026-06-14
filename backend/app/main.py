"""FastAPI uygulama girişi + repo yaşam döngüsü."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.ingest_routes import router as ingest_router
from app.api.loss_tree_routes import router as loss_tree_router
from app.api.oee_routes import router as oee_router
from app.config import load_app_config
from app.store.duckdb_repo import DuckDBRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = load_app_config()
    repo = DuckDBRepository(cfg.duckdb_path)
    repo.connect()
    repo.init_schema()
    app.state.repo = repo
    app.state.config = cfg
    try:
        yield
    finally:
        repo.close()


app = FastAPI(title="OEE Platform", lifespan=lifespan)
app.include_router(ingest_router)
app.include_router(oee_router)
app.include_router(loss_tree_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
