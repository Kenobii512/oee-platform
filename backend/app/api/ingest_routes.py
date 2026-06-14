"""POST /ingest -> LoadReport."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.ingest.loader import load_csv_dir

router = APIRouter()


class IngestRequest(BaseModel):
    path: str


@router.post("/ingest")
def ingest(req: IngestRequest, request: Request) -> dict:
    repo = request.app.state.repo
    report = load_csv_dir(req.path, repo)
    return report.to_dict()
