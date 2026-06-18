"""GET /oee/trend?bucket=day|week -> pencere bazında OEE serisi."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.analytics.trend import bucket_oee_series
from app.config import load_line_definition

router = APIRouter()


@router.get("/oee/trend")
def oee_trend(
    request: Request,
    bucket: str = Query("day"),
    frm: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> list[dict]:
    repo = request.app.state.repo
    cfg = request.app.state.config
    line = load_line_definition(cfg.line_config_path)
    if bucket not in ("day", "week"):
        bucket = "day"
    events = repo.fetch_events(frm, to)
    production = repo.fetch_production(frm, to)
    return bucket_oee_series(events, production, line, bucket)
