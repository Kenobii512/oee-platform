"""Soyut veri erişim arayüzü (DuckDB→Postgres geçişi için tek sınır).

İş mantığı (ingest, analytics) yalnız bu Protocol'e bağlıdır; somut DuckDB'yi
import etmez. G2/G3'te ingest/sorgu metotları eklenir.
"""
from __future__ import annotations

from typing import Protocol


class Repository(Protocol):
    def connect(self) -> None: ...
    def close(self) -> None: ...
    def init_schema(self) -> None: ...

    # G2'de eklenir:
    #   insert_events(rows: list[dict], source_file: str) -> int
    #   upsert_production(rows: list[dict]) -> int
    #   upsert_orders(rows: list[dict]) -> int
    #   count(table: str) -> int
    # G3'te eklenir:
    #   fetch_events(frm, to) -> list[dict]
    #   fetch_production() -> list[dict]
