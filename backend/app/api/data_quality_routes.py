"""GET /data-quality/summary -> veri güvenilirliği özeti (yalnız genel veriden).

H1 `coverage` (olay yoğunluğu + kapsanan süre + yeterli-mi) ve H3 `data_sufficiency`
(0–1 skor) tek yanıtta birleşir; pano güvenilirlik göstergesini bundan besler.
`ground_truth` KULLANMAZ (firewall).
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.analytics.confidence import data_sufficiency
from app.analytics.data_quality import coverage
from app.api._params import validate_range
from app.config import load_line_definition

router = APIRouter()


@router.get("/data-quality/summary")
def data_quality_summary(
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
    # coverage: microstop_entry_coverage + event_count + span_min + sufficient
    result = coverage(events, production)
    result["sufficiency_score"] = data_sufficiency(events, production, line)
    return result
