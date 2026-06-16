"""Konfigürasyon yükleme: env + hat tanımı YAML.

Hat tanımı simülatörün `line_default.yaml` formatını esas alır; platform onu
config olarak okur (ground-truth değil, mühendislik master-data'sı).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from app.models.contract import LineDefinition, TankDef


@dataclass(frozen=True)
class MaintenanceWindow:
    start: datetime
    duration_min: float


@dataclass(frozen=True)
class AppConfig:
    duckdb_path: str
    line_config_path: str
    cost_config_path: str
    recommend_config_path: str


def load_app_config() -> AppConfig:
    """Env'den uygulama ayarlarını okur (varsayılanlarla)."""
    config_dir = Path(__file__).resolve().parents[2] / "config"
    return AppConfig(
        duckdb_path=os.environ.get("OEE_DUCKDB_PATH", "oee.duckdb"),
        line_config_path=os.environ.get(
            "OEE_LINE_CONFIG", str(config_dir / "line_default.yaml")
        ),
        cost_config_path=os.environ.get(
            "OEE_COST_CONFIG", str(config_dir / "costs.yaml")
        ),
        recommend_config_path=os.environ.get(
            "OEE_RECOMMEND_CONFIG", str(config_dir / "recommend.yaml")
        ),
    )


def load_line_definition(path: str | Path) -> LineDefinition:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    tanks = [
        TankDef(
            id=t["id"],
            name=t.get("name", ""),
            time_min=float(t["time_min"]),
            time_max=float(t["time_max"]),
            capacity=int(t.get("capacity", 1)),
            bottleneck=bool(t.get("bottleneck", False)),
            max_hold_min=float(t.get("max_hold_min", 9999.0)),
        )
        for t in raw["tanks"]
    ]
    carrier_capacity = {
        o["order_id"]: int(o["carrier_qty"])
        for o in raw.get("orders", [])
        if "carrier_qty" in o
    }
    return LineDefinition(
        id=raw["line"]["id"],
        name=raw["line"].get("name", ""),
        tanks=tanks,
        carrier_capacity=carrier_capacity,
    )


def load_planned_maintenance(path: str | Path) -> list[MaintenanceWindow]:
    """Calendar'dan planlı bakım pencerelerini okur (utilization metriği için)."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    out: list[MaintenanceWindow] = []
    for m in raw.get("calendar", {}).get("planned_maintenance", []):
        start = m["start_datetime"]
        if not isinstance(start, datetime):
            start = datetime.strptime(str(start), "%Y-%m-%d %H:%M")
        out.append(MaintenanceWindow(start=start, duration_min=float(m["duration_min"])))
    return out


@dataclass(frozen=True)
class CostConfig:
    """Kategori bazında birim maliyetler (TL). Kodda gömülü sayı yok — daima config'ten."""

    downtime_tl_per_min: float
    microstop_tl_per_min: float
    speed_tl_per_min: float
    fill_tl_per_part: float
    redo_tl_per_part: float
    scrap_tl_per_part: float


def load_cost_config(path: str | Path) -> CostConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return CostConfig(
        downtime_tl_per_min=float(raw["downtime_tl_per_min"]),
        microstop_tl_per_min=float(raw["microstop_tl_per_min"]),
        speed_tl_per_min=float(raw["speed_tl_per_min"]),
        fill_tl_per_part=float(raw["fill_tl_per_part"]),
        redo_tl_per_part=float(raw["redo_tl_per_part"]),
        scrap_tl_per_part=float(raw["scrap_tl_per_part"]),
    )


@dataclass(frozen=True)
class CategoryRule:
    recovery_ratio: float
    title: str
    action: str
    assumption: str


@dataclass(frozen=True)
class RecommendConfig:
    default_recovery_ratio: float
    rules: dict[str, CategoryRule]


def load_recommend_config(path: str | Path) -> RecommendConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    default_ratio = float(raw.get("defaults", {}).get("recovery_ratio", 0.2))
    rules = {
        cat: CategoryRule(
            recovery_ratio=float(r.get("recovery_ratio", default_ratio)),
            title=r["title"],
            action=r["action"],
            assumption=r["assumption"],
        )
        for cat, r in raw.get("categories", {}).items()
    }
    return RecommendConfig(default_recovery_ratio=default_ratio, rules=rules)
