"""GET /recommendations?from=&to= -> TL'ye göre sıralı, kural tabanlı iyileştirme önerileri.

Öneriler kayıp ağacı (G4) + TL lensi (G11) üstüne kurulur: cost-tree TL azalan alınır,
her kategori için config/recommend.yaml şablonu doldurulur. Tahmini kazanç modüler
GainEstimator arkasındadır (varsayılan: oran tabanlı). FIREWALL: ground_truth ALMAZ.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.analytics.confidence import data_sufficiency
from app.analytics.cost import to_tl
from app.analytics.loss_tree import extract_loss_tree
from app.analytics.recommend import RatioGainEstimator, generate_recommendations
from app.config import (
    load_confidence_config,
    load_cost_config,
    load_line_definition,
    load_recommend_config,
)

router = APIRouter()


@router.get("/recommendations")
def get_recommendations(
    request: Request,
    frm: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> dict:
    repo = request.app.state.repo
    cfg = request.app.state.config
    line = load_line_definition(cfg.line_config_path)
    costs = load_cost_config(cfg.cost_config_path)
    rec_cfg = load_recommend_config(cfg.recommend_config_path)
    conf = load_confidence_config(cfg.confidence_config_path)
    events = repo.fetch_events(frm, to)
    production = repo.fetch_production(frm, to)
    tree = extract_loss_tree(events, production, line)
    sufficiency = data_sufficiency(events, production, line)
    cost_tree = to_tl(tree, costs, confidence_cfg=conf, sufficiency=sufficiency)
    recommendations = generate_recommendations(
        cost_tree, events, rec_cfg, RatioGainEstimator(rec_cfg)
    )
    return {
        "recommendations": recommendations,
        "total_estimated_gain_tl": sum(r["estimated_gain_tl"] for r in recommendations),
    }
