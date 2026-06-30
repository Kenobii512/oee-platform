"""H2 — konfigürasyonla ingest adaptörü: "saha dili" ham olay logunu sözleşme
events satırlarına çevirir.

Sözleşme SABİT kalır; bu katman tesisin verebildiği ham formatı (PLC/SCADA export,
sayaç logu, MES/ERP CSV) YAML eşleme profiliyle sözleşmeye köprüler. Eşleme = kolon
adı, zaman formatı/timezone, süre birimi, reason_code sözlüğü, event_type türetme,
varsayılan/eksik politikası. Eşlenemeyen değer / eksik zorunlu kolon SESSİZ yanlış
değil, açık `AdapterError` verir. Yeni profil = yeni YAML, kod değil.

Çıktı satırları H1 loader doğrulamasından (`load_csv_dir`) ayrıca geçer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

# Sözleşme events kolonları (apply_mapping çıktısının tam şekli).
_CONTRACT_EVENT_FIELDS = (
    "timestamp",
    "line_id",
    "carrier_id",
    "station_id",
    "event_type",
    "duration",
    "reason_code",
    "operator_entered_reason",
    "operator_entry_ts",
)


class AdapterError(ValueError):
    """Eşleme başarısız: eksik zorunlu kolon ya da eşlenemeyen değer (eyleme dönük mesaj)."""


@dataclass(frozen=True)
class AdapterConfig:
    column_map: dict[str, str]  # ham_kolon -> sözleşme_kolon
    timestamp_format: str | None
    timezone: str | None
    duration_unit: str  # "s" | "min" (ham birim; sözleşme = dakika)
    reason_map: dict[str, str]
    event_type_rule: dict[str, str]
    required: tuple[str, ...]
    defaults: dict[str, str]


def load_adapter_config(path: str | Path) -> AdapterConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AdapterConfig(
        column_map=dict(raw.get("column_map", {})),
        timestamp_format=raw.get("timestamp_format") or None,
        timezone=raw.get("timezone") or None,
        duration_unit=str(raw.get("duration_unit", "min")),
        reason_map=dict(raw.get("reason_map", {})),
        event_type_rule=dict(raw.get("event_type_rule", {})),
        required=tuple(raw.get("required", [])),
        defaults=dict(raw.get("defaults", {})),
    )


def apply_mapping(raw_rows: list[dict], mapping: AdapterConfig) -> list[dict]:
    """Ham satırları sözleşme events satırlarına çevirir (deterministik, satır bazlı)."""
    return [_map_row(raw, i, mapping) for i, raw in enumerate(raw_rows)]


def _map_row(raw: dict, idx: int, m: AdapterConfig) -> dict:
    # 1) zorunlu ham kolonlar dolu mu?
    for col in m.required:
        if not (raw.get(col) or "").strip():
            raise AdapterError(
                f"satır {idx}: zorunlu ham kolon eksik/boş: {col!r} (profil 'required')"
            )

    # 2) kolon adlarını sözleşmeye çevir
    contract: dict[str, str] = {}
    for ham_col, dst in m.column_map.items():
        if ham_col in raw:
            contract[dst] = raw[ham_col]

    # 3) event_type türet (eşlenemeyen -> açık hata)
    rawet = (contract.get("event_type") or "").strip()
    if rawet not in m.event_type_rule:
        raise AdapterError(
            f"satır {idx}: eşlenemeyen event_type: {rawet!r} "
            f"(profil 'event_type_rule': {', '.join(sorted(m.event_type_rule))})"
        )
    contract["event_type"] = m.event_type_rule[rawet]

    # 4) reason_code eşle (boş -> boş; dolu ama eşlenemeyen -> hata)
    rawcause = (contract.get("reason_code") or "").strip()
    if rawcause:
        if rawcause not in m.reason_map:
            raise AdapterError(
                f"satır {idx}: eşlenemeyen reason_code: {rawcause!r} (profil 'reason_map')"
            )
        contract["reason_code"] = m.reason_map[rawcause]
    else:
        contract["reason_code"] = ""

    # 5) süre birimi -> dakika
    contract["duration"] = _convert_duration(contract.get("duration"), m.duration_unit, idx)

    # 6) timestamp normalize (format + timezone -> ISO)
    contract["timestamp"] = _normalize_ts(contract.get("timestamp"), m, idx)

    # 7) eksik sözleşme alanlarını default/boş ile doldur
    for field in _CONTRACT_EVENT_FIELDS:
        if field not in contract or contract[field] is None:
            contract[field] = m.defaults.get(field, "")
    return contract


def _convert_duration(value, unit: str, idx: int) -> float:
    try:
        seconds_or_min = float(value)
    except (TypeError, ValueError):
        raise AdapterError(f"satır {idx}: süre sayısal değil: {value!r}") from None
    return seconds_or_min / 60.0 if unit == "s" else seconds_or_min


def _normalize_ts(value, m: AdapterConfig, idx: int) -> str:
    if value is None or str(value).strip() == "":
        raise AdapterError(f"satır {idx}: timestamp boş")
    text = str(value).strip()
    try:
        dt = datetime.strptime(text, m.timestamp_format) if m.timestamp_format else datetime.fromisoformat(text)
    except ValueError as exc:
        raise AdapterError(f"satır {idx}: timestamp ayrıştırılamadı ({text!r}): {exc}") from None
    if m.timezone:
        dt = dt.replace(tzinfo=ZoneInfo(m.timezone)).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return dt.isoformat()
