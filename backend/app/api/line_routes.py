"""POST /line/validate -> hat-tanımı (line dict) doğrulama sonucu (H7).

Doğrulama SONUCU veridir; geçersiz tanım 4xx değil 200 + {valid:false, errors:[...]} döner
(istemci hataları okuyup düzeltir). Ham YAML'ı istemci JSON'a çevirip gönderir.
"""
from __future__ import annotations

from fastapi import APIRouter, Body

from app.config_validate import validate_line_dict

router = APIRouter()


@router.post("/line/validate")
def validate_line(raw: dict = Body(...)) -> dict:
    errors = validate_line_dict(raw)
    return {"valid": not errors, "errors": errors}
