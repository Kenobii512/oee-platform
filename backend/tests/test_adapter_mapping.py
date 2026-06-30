"""H2 — konfigürasyonla ingest adaptörü: ham → sözleşme eşleme birimleri."""
from app.ingest.adapter import apply_mapping, load_adapter_config
from tests.conftest import ADAPTERS


def _cfg():
    return load_adapter_config(str(ADAPTERS / "generic_plant.yaml"))


def test_apply_mapping_basic():
    raw = [
        {
            "ts": "01/01/2026 09:00:00",
            "machine": "LINE-01",
            "carrier": "CAR-1",
            "evt": "STOP",
            "dur_s": "120",
            "cause": "Sıkışma",
        }
    ]
    out = apply_mapping(raw, _cfg())
    row = out[0]
    assert row["event_type"] == "MICROSTOP"  # event_type_rule: STOP->MICROSTOP
    assert row["duration"] == 2.0  # 120 sn -> 2.0 dk (sözleşme birimi = dakika)
    assert row["reason_code"] == "jam"  # reason_map: Sıkışma->jam
    assert row["line_id"] == "LINE-01"
    assert row["carrier_id"] == "CAR-1"
    assert row["timestamp"].startswith("2026-01-01T09:00:00")


def test_apply_mapping_fills_defaults():
    raw = [
        {
            "ts": "02/01/2026 10:00:00",
            "machine": "LINE-01",
            "carrier": "",
            "evt": "RUN",
            "dur_s": "30",
            "cause": "",
        }
    ]
    out = apply_mapping(raw, _cfg())
    row = out[0]
    assert row["event_type"] == "PROCESS"  # RUN->PROCESS
    assert row["reason_code"] == ""  # boş neden -> boş (hata değil)
    # tüm sözleşme kolonları mevcut (eksikler default/boş)
    assert set(row) >= {
        "timestamp", "line_id", "carrier_id", "station_id", "event_type",
        "duration", "reason_code", "operator_entered_reason", "operator_entry_ts",
    }
