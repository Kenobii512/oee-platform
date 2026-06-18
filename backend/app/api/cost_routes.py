"""GET /loss-tree/cost?from=&to= -> kayıp ağacının TL Pareto'su (azalan) + total_tl.

Native /loss-tree ile aynı dönem mantığı (G4 MVP: from/to yalnız events'e). Birim
maliyetler config'ten (CostConfig); ground_truth ALMAZ (firewall).
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.analytics.cost import to_tl
from app.analytics.loss_tree import extract_loss_tree
from app.config import load_cost_config, load_line_definition

router = APIRouter()


@router.get("/loss-tree/cost")
def get_loss_tree_cost(
    request: Request,
    frm: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> dict:
    repo = request.app.state.repo
    cfg = request.app.state.config
    line = load_line_definition(cfg.line_config_path)
    costs = load_cost_config(cfg.cost_config_path)
    events = repo.fetch_events(frm, to)
    production = repo.fetch_production(frm, to)
    tree = extract_loss_tree(events, production, line)
    return to_tl(tree, costs)
