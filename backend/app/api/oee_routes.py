"""GET /oee?from=&to= -> OeeResult (yalnız genel veriden)."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query, Request

from app.analytics.oee import compute_oee
from app.config import load_line_definition, load_planned_maintenance

router = APIRouter()


def _planned_downtime(path: str, frm: str | None, to: str | None) -> float:
    """Planlı bakım pencerelerinin [frm,to] ile kesişimi (dakika)."""
    from datetime import datetime, timedelta

    windows = load_planned_maintenance(path)
    total = 0.0
    f = datetime.fromisoformat(frm) if frm else None
    t = datetime.fromisoformat(to) if to else None
    for w in windows:
        start = w.start
        end = w.start + timedelta(minutes=w.duration_min)
        lo = max(start, f) if f else start
        hi = min(end, t) if t else end
        if hi > lo:
            total += (hi - lo).total_seconds() / 60.0
    return total


@router.get("/oee")
def get_oee(
    request: Request,
    frm: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> dict:
    repo = request.app.state.repo
    cfg = request.app.state.config
    line = load_line_definition(cfg.line_config_path)
    events = repo.fetch_events(frm, to)
    production = repo.fetch_production(frm, to)
    planned = _planned_downtime(cfg.line_config_path, frm, to)
    result = compute_oee(events, production, line, planned_downtime_min=planned)
    return asdict(result)
