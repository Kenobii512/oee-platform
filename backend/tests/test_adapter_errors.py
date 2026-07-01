"""H2 — adaptör hata yolları: eksik kolon / eşlenemeyen değer açık hata verir."""
import pytest

from app.ingest.adapter import AdapterError, apply_mapping, load_adapter_config
from tests.conftest import ADAPTERS


def _cfg():
    return load_adapter_config(str(ADAPTERS / "generic_plant.yaml"))


def test_missing_required_column_raises():
    raw = [{"machine": "LINE-01", "evt": "STOP", "dur_s": "120", "cause": "Sıkışma"}]  # ts yok
    with pytest.raises(AdapterError) as exc:
        apply_mapping(raw, _cfg())
    assert "ts" in str(exc.value)  # eyleme dönük: hangi kolon eksik


def test_unmappable_event_type_raises():
    raw = [
        {"ts": "01/01/2026 09:00:00", "machine": "LINE-01", "carrier": "C1",
         "evt": "GIZEMLI", "dur_s": "10", "cause": "Sıkışma"}
    ]
    with pytest.raises(AdapterError) as exc:
        apply_mapping(raw, _cfg())
    assert "GIZEMLI" in str(exc.value)


def test_unmappable_reason_raises():
    raw = [
        {"ts": "01/01/2026 09:00:00", "machine": "LINE-01", "carrier": "C1",
         "evt": "STOP", "dur_s": "10", "cause": "BilinmeyenNeden"}
    ]
    with pytest.raises(AdapterError) as exc:
        apply_mapping(raw, _cfg())
    assert "BilinmeyenNeden" in str(exc.value)


def test_non_numeric_duration_raises():
    raw = [
        {"ts": "01/01/2026 09:00:00", "machine": "LINE-01", "carrier": "C1",
         "evt": "STOP", "dur_s": "abc", "cause": "Sıkışma"}
    ]
    with pytest.raises(AdapterError):
        apply_mapping(raw, _cfg())


# ---- profil İÇERİK hataları: sessiz traceback değil AdapterError -------------


def test_malformed_profile_yaml_raises_adapter_error(tmp_path):
    p = tmp_path / "bozuk.yaml"
    p.write_text("column_map: [acik, kalan", encoding="utf-8")  # kapanmayan flow -> YAMLError
    with pytest.raises(AdapterError):
        load_adapter_config(p)


def test_empty_profile_raises_adapter_error(tmp_path):
    p = tmp_path / "bos.yaml"
    p.write_text("", encoding="utf-8")  # safe_load -> None (dict değil)
    with pytest.raises(AdapterError):
        load_adapter_config(p)


def test_invalid_timezone_raises_adapter_error_at_load(tmp_path):
    # ZoneInfoNotFoundError KeyError'dan türer; yakalanmazsa eşleme sırasında
    # satır-başına traceback olur. Profil yüklemede fail-fast AdapterError.
    p = tmp_path / "kotu_tz.yaml"
    src = (ADAPTERS / "generic_plant.yaml").read_text(encoding="utf-8")
    p.write_text(src.replace("timezone: null", "timezone: Europe/Istanbulll"), encoding="utf-8")
    with pytest.raises(AdapterError) as exc:
        load_adapter_config(p)
    assert "timezone" in str(exc.value)
