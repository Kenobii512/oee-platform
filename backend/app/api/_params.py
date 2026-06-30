"""H9 — istek parametre doğrulama. Bozuk girdi açık 400 verir (sessiz 500 değil)."""
from __future__ import annotations

from datetime import datetime


class BadRequest(ValueError):
    """İstemci girdi hatası → 400 (main.py global handler ile)."""


def validate_range(
    frm: str | None, to: str | None
) -> tuple[str | None, str | None]:
    """from/to tarihlerini doğrular (passthrough); geçersiz format → BadRequest."""
    return _check(frm, "from"), _check(to, "to")


def _check(v: str | None, name: str) -> str | None:
    if v is None or v == "":
        return None
    try:
        datetime.fromisoformat(v)
    except (ValueError, TypeError):
        raise BadRequest(
            f"geçersiz tarih ({name}): {v!r} — beklenen biçim 'YYYY-MM-DD HH:MM'"
        ) from None
    return v
