"""G8 kalibrasyon kapısı: her senaryo, kataloğunda beyan ettiği kaybı DOĞAL EKSENİNDE
baskın göstermeli.

Doğal-eksen kuralı (kullanıcı kararı): TL ağırlıkları dengesiz (DOWNTIME 50 pahalı; SPEED 20,
REDO 3, FILL 2 ucuz), bu yüzden ucuz kanallar TL'de #1 olamaz. Bunun yerine adlı kayıp, KENDİ
ekseninde (zaman kanalları → dakika; malzeme kanalları → parça) en yüksek değere sahip olmalı. Bu hem gerçekçi (FILL'in TL'si küçük kalır) hem okunabilir (pano zaten zaman/parça
kayıplarını ayrı grafiklerde gösterir).

FIREWALL: yalnız platform analitiği (/loss-tree); ground_truth ingest edilmez. Parametreler bu
kapı yeşil olana dek scenario YAML'larında ayarlanır.
"""
import pytest
from fastapi.testclient import TestClient

from app.config import load_app_config, load_scenario_catalog
from app.main import app

CATALOG = load_scenario_catalog(load_app_config().scenario_config_path)


@pytest.mark.parametrize("info", CATALOG, ids=[s.id for s in CATALOG])
def test_scenario_dominant_loss(info, tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / f"{info.id}.duckdb"))
    with TestClient(app) as client:
        client.post(f"/scenarios/{info.id}/activate")
        cats = client.get("/loss-tree").json()["categories"]

    by_cat = {c["category"]: c for c in cats}
    expected = by_cat[info.expected_top_loss]
    axis = expected["axis"]
    # Aynı eksendeki kanallar arasında en yüksek doğal değer adlı kayıp olmalı.
    same_axis = [c for c in cats if c["axis"] == axis]
    top = max(same_axis, key=lambda c: c["value"])
    assert top["category"] == info.expected_top_loss, (
        info.id, axis, top["category"],
        {c["category"]: round(c["value"]) for c in same_axis},
    )
