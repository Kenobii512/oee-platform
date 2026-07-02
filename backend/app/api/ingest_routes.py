"""POST /ingest -> LoadReport. Opsiyonel `adapter` ile ham format -> sözleşme dönüşümü (H2)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.ingest.adapter import (
    AdapterError,
    adapt_dir_to_contract,
    load_adapter_config,
    resolve_profile_path,
)
from app.ingest.loader import load_csv_dir

router = APIRouter()


class IngestRequest(BaseModel):
    path: str
    adapter: str | None = None


def _check_ingest_root(path: str) -> None:
    """OEE_INGEST_ROOT set'liyse ingest yolu onun altında olmalı.

    Auth kapalı public deploy'da keyfi sunucu dizininin CSV diye okutulmasını
    engeller; env yoksa davranış eskisi gibi serbesttir (yerel/pilot kolaylığı).
    """
    root = os.environ.get("OEE_INGEST_ROOT")
    if not root:
        return
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"ingest yolu izinli kokun (OEE_INGEST_ROOT) disinda: {path}",
        )


@router.post("/ingest")
def ingest(req: IngestRequest, request: Request) -> dict:
    repo = request.app.state.repo
    _check_ingest_root(req.path)
    if not req.adapter:
        return _load(req.path, repo)
    # Adapter: ham -> sözleşme geçici dizine; TemporaryDirectory çıkışta temizler (sızıntı yok).
    try:
        mapping = _resolve_profile(req.adapter)
    except (FileNotFoundError, AdapterError) as exc:
        # AdapterError: profil dosyası var ama içeriği bozuk (YAML/tip/timezone) — 500 değil 400.
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
    profile = resolve_profile_path(adapter)
    if not profile.exists():
        raise FileNotFoundError(f"bilinmeyen adapter profili: {adapter!r} ({profile})")
    return load_adapter_config(profile)
