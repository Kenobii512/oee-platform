"""H9 — loglama: istek zamanlama + seviye env'i."""
import logging

from fastapi.testclient import TestClient

from app.logging_setup import setup_logging
from app.main import app


def test_request_is_logged(caplog):
    with caplog.at_level(logging.INFO, logger="oee.request"):
        with TestClient(app) as client:
            client.get("/health")
    msgs = [r.getMessage() for r in caplog.records if r.name == "oee.request"]
    assert any(
        "method=GET" in m and "path=/health" in m and "status=200" in m and "duration_ms=" in m
        for m in msgs
    ), msgs


def test_setup_logging_respects_env(monkeypatch):
    monkeypatch.setenv("OEE_LOG_LEVEL", "DEBUG")
    setup_logging()
    assert logging.getLogger("oee").level == logging.DEBUG
