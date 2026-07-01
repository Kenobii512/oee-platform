"""POST /ingest -> LoadReport. Opsiyonel `adapter` ile ham format -> sözleşme dönüşümü (H2)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.ingest.adapter import AdapterError, adapt_dir_to_contract, load_adapter_config
from app.ingest.loader import load_csv_dir

router = APIRouter()

# Eşleme profilleri repo-kökü config/adapters/ altında (app/api/ -> backend -> repo kökü).
_ADAPTERS_DIR = Path(__file__).resolve().parents[3] / "config" / "adapters"


class IngestRequest(BaseModel):
    path: str
    adapter: str | None = None


@router.post("/ingest")
def ingest(req: IngestRequest, request: Request) -> dict:
    repo = request.app.state.repo
    if not req.adapter:
        return _load(req.path, repo)
    # Adapter: ham -> sözleşme geçici dizine; TemporaryDirectory çıkışta temizler (sızıntı yok).
    try:
        mapping = _resolve_profile(req.adapter)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    with tempfile.TemporaryDirectory(prefix="oee_adapt_") as tmp:
        try:
            adapt_dir_to_contract(req.path, mapping, Path(tmp))
        except AdapterError as exc:
            raise HTTPException(status_code=400, detail=f"adapter eşleme hatası: {exc}")
        return _load(tmp, repo)


def _load(source: str, repo) -> dict:
    try:
        return load_csv_dir(source, repo).to_dict()
    except NotADirectoryError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _resolve_profile(adapter: str):
    profile = _ADAPTERS_DIR / f"{adapter}.yaml"
    if not profile.exists():
        raise FileNotFoundError(f"bilinmeyen adapter profili: {adapter!r} ({profile})")
    return load_adapter_config(profile)
