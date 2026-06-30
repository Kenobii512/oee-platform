"""GET /loss-tree?from=&to= -> kategori bazında kayıp ağacı (yalnız genel veriden).

Kategoriler farklı eksende (dakika vs parça) döner; ortak birim (TL) ve Pareto
sıralaması G11'dedir. Burada yalnız native değerler sunulur.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.analytics.loss_tree import CATEGORIES, axis_of, extract_loss_tree, kind_of
from app.api._params import validate_range
from app.config import load_line_definition

router = APIRouter()


@router.get("/loss-tree")
def get_loss_tree(
    request: Request,
    frm: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> dict:
    frm, to = validate_range(frm, to)
    repo = request.app.state.repo
    cfg = request.app.state.config
    line = load_line_definition(cfg.line_config_path)
    # Dönem-doğru (G4.1): from/to hem events'e hem üretime (carrier zaman atfı) uygulanır.
    events = repo.fetch_events(frm, to)
    production = repo.fetch_production(frm, to)
    tree = extract_loss_tree(events, production, line)
    return {
        "categories": [
            {
                "category": c,
                "axis": axis_of(c),
                "value": tree.value(c),
                "kind": kind_of(c),
            }
            for c in CATEGORIES
        ]
    }
