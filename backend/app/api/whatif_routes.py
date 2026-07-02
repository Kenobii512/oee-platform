"""GET /whatif -> azaltım oranlarıyla önce/sonra OEE + TL kazanç (analitik what-if).

cost_routes ile aynı veri hattı (loss_tree + to_tl, H3 bantlı); üstüne
`analytics.whatif.compute_whatif`. Oranlar 0..1 dışıysa 400. FIREWALL aynen.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.analytics.confidence import data_sufficiency
from app.analytics.cost import to_tl
from app.analytics.loss_tree import extract_loss_tree
from app.analytics.whatif import KEYS, compute_whatif
from app.api._params import BadRequest, validate_range
from app.config import load_confidence_config, load_cost_config, load_line_definition

router = APIRouter()


@router.get("/whatif")
def get_whatif(
    request: Request,
    downtime: float = Query(0.0),
    microstop: float = Query(0.0),
    speed_loss: float = Query(0.0),
    quality_redo: float = Query(0.0),
    fill_loss: float = Query(0.0),
    frm: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> dict:
    reductions = {
        "downtime": downtime,
        "microstop": microstop,
        "speed_loss": speed_loss,
        "quality_redo": quality_redo,
        "fill_loss": fill_loss,
    }
    for key in KEYS:
        v = reductions[key]
        if not (0.0 <= v <= 1.0):
            raise BadRequest(f"gecersiz azaltim orani ({key}={v}); 0..1 araliginda olmali")
    frm, to = validate_range(frm, to)
    repo = request.app.state.repo
    cfg = request.app.state.config
    line = load_line_definition(cfg.line_config_path)
    costs = load_cost_config(cfg.cost_config_path)
    conf = load_confidence_config(cfg.confidence_config_path)
    events = repo.fetch_events(frm, to)
    production = repo.fetch_production(frm, to)
    tree = extract_loss_tree(events, production, line)
    sufficiency = data_sufficiency(events, production, line)
    cost_tree = to_tl(tree, costs, confidence_cfg=conf, sufficiency=sufficiency)
    return compute_whatif(events, production, line, cost_tree, reductions)
