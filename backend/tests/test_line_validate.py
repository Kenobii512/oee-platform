"""H7 — hat-tanımı doğrulayıcı: geçerli geçer, her geçersizlik açık mesajla yakalanır."""
import copy

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config_validate import validate_line_dict
from app.main import app
from tests.conftest import LINE_CONFIG

VALID = yaml.safe_load(LINE_CONFIG.read_text(encoding="utf-8"))


def _set_two_bottlenecks(d):
    for t in d["tanks"]:
        t["bottleneck"] = True


def test_real_line_default_is_valid():
    # Mevcut config/line_default.yaml geçerli olmalı (regresyon yok).
    assert validate_line_dict(VALID) == []


@pytest.mark.parametrize(
    "mutate,needle",
    [
        (lambda d: d["tanks"][0].pop("time_min"), "time_min"),
        (lambda d: _set_two_bottlenecks(d), "bottleneck"),
        (lambda d: d["tanks"][0].update(capacity=0), "capacity"),
        (lambda d: d["tanks"][0].update(time_min=99, time_max=1), "time_min"),
        (lambda d: [t.update(bottleneck=False) for t in d["tanks"]], "bottleneck"),
        (lambda d: d.pop("tanks"), "tanks"),
        (lambda d: d["orders"][0].update(carrier_qty=0), "carrier_qty"),
        (lambda d: d["line"].pop("id"), "line.id"),
    ],
)
def test_invalid_line_caught(mutate, needle):
    d = copy.deepcopy(VALID)
    mutate(d)
    errs = validate_line_dict(d)
    assert any(needle in e for e in errs), f"{needle} hatası bekleniyordu, gelen: {errs}"


def test_validate_endpoint_valid():
    with TestClient(app) as client:
        r = client.post("/line/validate", json=VALID)
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True and body["errors"] == []


def test_validate_endpoint_invalid():
    d = copy.deepcopy(VALID)
    d["tanks"][0].update(capacity=0)
    with TestClient(app) as client:
        r = client.post("/line/validate", json=d)
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert any("capacity" in e for e in body["errors"])
