"""Veri sözleşmesi — platformun sahadan beklediği genel CSV şemaları.

Şema simülatörün çıktı şemasıyla birebir aynıdır ama burada BAĞIMSIZ sözleşme
olarak tanımlanır; platform verinin kaynağını bilmez.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class EventType(str, Enum):
    LOAD = "LOAD"
    PROCESS = "PROCESS"
    MOVE = "MOVE"
    UNLOAD = "UNLOAD"
    QC = "QC"
    OVER_RESIDENCE = "OVER_RESIDENCE"
    DOWNTIME = "DOWNTIME"
    MICROSTOP = "MICROSTOP"
    STRIP = "STRIP"


class EventRow(BaseModel):
    timestamp: datetime
    line_id: str
    # Askıya bağlı olaylarda dolu; hat-seviyesi olaylarda (DOWNTIME/MICROSTOP) boş/None.
    # Dönem-doğru üretim atfı (G4.1) için: production'ı carrier'ın zaman penceresine bağlar.
    carrier_id: Optional[str] = None
    station_id: Optional[str] = None
    event_type: EventType
    duration: float
    reason_code: Optional[str] = None
    operator_entered_reason: Optional[str] = None
    operator_entry_ts: Optional[datetime] = None

    @field_validator("duration")
    @classmethod
    def _non_negative_duration(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"duration negatif olamaz: {v}")
        return v


class ProductionRow(BaseModel):
    carrier_id: str
    order_id: str
    loaded_qty: int
    good_count: int
    redo_count: int
    scrap_count: int

    @model_validator(mode="after")
    def _check_disposition(self) -> "ProductionRow":
        if self.good_count + self.scrap_count != self.loaded_qty:
            raise ValueError(
                f"good_count + scrap_count ({self.good_count}+{self.scrap_count}) "
                f"!= loaded_qty ({self.loaded_qty})"
            )
        # redo, yüklenen ayrık parça sayısını aşamaz (aşarsa ilk-geçiş kalite < 0 sessizce 0'a kırpılır).
        if self.redo_count > self.loaded_qty:
            raise ValueError(
                f"redo_count ({self.redo_count}) > loaded_qty ({self.loaded_qty})"
            )
        return self


class OrderRow(BaseModel):
    order_id: str
    product_id: str
    target_cycle: float
    planned_qty: int


class TankDef(BaseModel):
    id: str
    name: str = ""
    time_min: float
    time_max: float
    capacity: int = 1
    bottleneck: bool = False
    max_hold_min: float = 9999.0


class LineDefinition(BaseModel):
    """Hat tanımı: nominal tank süreleri + askı kapasitesi (master-data).

    `carrier_capacity`: order_id -> askı başına nominal parça. Quality paydası için
    kullanılır. Boş ise OEE motoru çıkarım fallback'ine düşer.
    """
    id: str
    name: str = ""
    tanks: list[TankDef]
    carrier_capacity: dict[str, int] = {}
