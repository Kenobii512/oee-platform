"""GET /data-quality/summary -> operatör giriş kapsamı (yalnız genel veriden)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.analytics.data_quality import entry_coverage

router = APIRouter()


@router.get("/data-quality/summary")
def data_quality_summary(request: Request) -> dict:
    repo = request.app.state.repo
    return entry_coverage(repo.fetch_events())
