"""POST /ingest -> LoadReport."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.ingest.loader import load_csv_dir

router = APIRouter()


class IngestRequest(BaseModel):
    path: str


@router.post("/ingest")
def ingest(req: IngestRequest, request: Request) -> dict:
    repo = request.app.state.repo
    try:
        report = load_csv_dir(req.path, repo)
    except NotADirectoryError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return report.to_dict()
