"""POST /ingest -> LoadReport. Opsiyonel `adapter` ile ham format -> sözleşme dönüşümü (H2)."""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.ingest.adapter import AdapterError, apply_mapping, load_adapter_config
from app.ingest.loader import load_csv_dir

router = APIRouter()

# Eşleme profilleri repo-kökü config/adapters/ altında (app/api/ -> backend -> repo kökü).
_ADAPTERS_DIR = Path(__file__).resolve().parents[3] / "config" / "adapters"
# Adapter verildiğinde sözleşmeye çevrilen dosya; diğerleri aynen kopyalanır.
_ADAPTED_FILE = "events.csv"
_PASSTHROUGH_FILES = ("production.csv", "orders.csv")


class IngestRequest(BaseModel):
    path: str
    adapter: str | None = None


@router.post("/ingest")
def ingest(req: IngestRequest, request: Request) -> dict:
    repo = request.app.state.repo
    source = req.path
    if req.adapter:
        try:
            source = _adapt_to_contract(req.path, req.adapter)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except AdapterError as exc:
            raise HTTPException(status_code=400, detail=f"adapter eşleme hatası: {exc}")
    try:
        report = load_csv_dir(source, repo)
    except NotADirectoryError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return report.to_dict()


def _adapt_to_contract(raw_dir: str, adapter: str) -> str:
    """Ham dizini sözleşme dizinine çevirir; geçici dizin yolunu döndürür.

    `events.csv` profil ile eşlenir; `production/orders` zaten sözleşme-şeklinde
    kabul edilip aynen kopyalanır. Geçici dizin TemporaryDirectory yerine kalıcı
    mkdtemp ile açılır (load_csv_dir tüketene kadar yaşamalı; süreç sonunda OS temizler).
    """
    profile = _ADAPTERS_DIR / f"{adapter}.yaml"
    if not profile.exists():
        raise FileNotFoundError(f"bilinmeyen adapter profili: {adapter!r} ({profile})")
    mapping = load_adapter_config(profile)

    raw = Path(raw_dir)
    out_dir = Path(tempfile.mkdtemp(prefix="oee_adapt_"))

    raw_events = raw / _ADAPTED_FILE
    if raw_events.exists():
        with open(raw_events, newline="", encoding="utf-8-sig", errors="replace") as f:
            rows = apply_mapping(list(csv.DictReader(f)), mapping)
        _write_contract_events(out_dir / _ADAPTED_FILE, rows)

    for name in _PASSTHROUGH_FILES:
        src = raw / name
        if src.exists():
            (out_dir / name).write_bytes(src.read_bytes())
    return str(out_dir)


_EVENT_FIELDS = (
    "timestamp", "line_id", "carrier_id", "station_id", "event_type",
    "duration", "reason_code", "operator_entered_reason", "operator_entry_ts",
)


def _write_contract_events(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_EVENT_FIELDS, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in _EVENT_FIELDS})
