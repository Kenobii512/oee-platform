"""FastAPI uygulama girişi."""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="OEE Platform")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
