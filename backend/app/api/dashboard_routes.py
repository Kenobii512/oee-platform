"""Jinja panosu (legacy). React SPA varsa kök '/' onu sunar, Jinja '/legacy'de fallback kalır.

Tüm veri tarayıcıdan API ile çekilir. main.py SPA dist'i bulamazsa render_dashboard'u '/'ta sunar.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

_templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "templates")
)


def render_dashboard(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(request, "dashboard.html")


@router.get("/legacy", response_class=HTMLResponse)
def legacy_dashboard(request: Request) -> HTMLResponse:
    return render_dashboard(request)
