"""DuckDB tabanlı Repository. G1'de yalnız bağlantı kabuğu."""
from __future__ import annotations

import duckdb


class DuckDBRepository:
    def __init__(self, path: str) -> None:
        self.path = path
        self.con: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> None:
        if self.con is None:
            self.con = duckdb.connect(self.path)

    def close(self) -> None:
        if self.con is not None:
            self.con.close()
            self.con = None

    def init_schema(self) -> None:
        """G2'de tablo şemaları burada oluşturulur."""
        raise NotImplementedError
