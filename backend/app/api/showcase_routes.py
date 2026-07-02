"""Showcase: GET /tanitim (landing) + /tanitim/ornek-rapor — public satış vitrinleri.

Dosyalar repo-kökü docs/showcase/ altında commit'lidir (araçla üretilen örnek rapor
+ elle bakımı yapılan landing); rota yalnız FileResponse ile sunar. Auth istisnası
`app.auth._PUBLIC`'te (/health deseni): satış sayfası parola arkasına saklanamaz.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# app/api/ -> backend -> repo kökü.
_SHOWCASE_DIR = Path(__file__).resolve().parents[3] / "docs" / "showcase"


def _serve(name: str, media_type: str = "text/html") -> FileResponse:
    path = _SHOWCASE_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"showcase dosyası yok: {name}")
    return FileResponse(path, media_type=media_type)


@router.get("/tanitim")
def tanitim() -> FileResponse:
    return _serve("landing.html")


@router.get("/tanitim/ornek-rapor")
def ornek_rapor() -> FileResponse:
    return _serve("ornek-pilot-raporu.html")


@router.get("/tanitim/og-card.png")
def og_card() -> FileResponse:
    """Sosyal önizleme görseli (landing'in og:image'ı buna göreli işaret eder)."""
    return _serve("og-card.png", media_type="image/png")
