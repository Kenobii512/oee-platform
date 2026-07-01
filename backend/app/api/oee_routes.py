"""GET /oee?from=&to= -> OeeResult (yalnız genel veriden)."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query, Request

from app.analytics.calendar import calendar_minutes
from app.analytics.oee import compute_oee
from app.api._params import validate_range
from app.config import load_calendar, load_line_definition, load_planned_maintenance

router = APIRouter()


def _window(events: list[dict], frm: str | None, to: str | None):
    """Utilization penceresi: frm/to verilirse onlar; yoksa olayların min/max zamanı."""
    from datetime import datetime

    def _dt(v):
        return v if isinstance(v, datetime) else datetime.fromisoformat(str(v))

    if not events:
        return None, None
    ts = [_dt(e["timestamp"]) for e in events]
    start = _dt(frm) if frm else min(ts)
    end = _dt(to) if to else max(ts)
    return start, end


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
    frm, to = validate_range(frm, to)
    repo = request.app.state.repo
    cfg = request.app.state.config
    line = load_line_definition(cfg.line_config_path)
    events = repo.fetch_events(frm, to)
    production = repo.fetch_production(frm, to)
    planned = _planned_downtime(cfg.line_config_path, frm, to)
    # H8: utilization gerçek takvim-zamanından (vardiya−mola−bakım).
    cal = load_calendar(cfg.line_config_path)
    win_start, win_end = _window(events, frm, to)
    cal_min = calendar_minutes(win_start, win_end, cal) if win_start and win_end else None
    result = compute_oee(
        events, production, line, planned_downtime_min=planned, calendar_min=cal_min
    )
    out = asdict(result)
    out["calendar_min"] = cal_min  # utilization paydası (takvim dakikaları); şeffaflık için
    return out
