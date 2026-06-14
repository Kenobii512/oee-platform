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
        assert self.con is not None
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS events (
                source_file VARCHAR,
                row_ordinal INTEGER,
                timestamp TIMESTAMP,
                line_id VARCHAR,
                station_id VARCHAR,
                event_type VARCHAR,
                duration DOUBLE,
                reason_code VARCHAR,
                operator_entered_reason VARCHAR,
                operator_entry_ts TIMESTAMP,
                PRIMARY KEY (source_file, row_ordinal)
            );
        """)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS production (
                carrier_id VARCHAR PRIMARY KEY,
                order_id VARCHAR,
                loaded_qty INTEGER,
                good_count INTEGER,
                redo_count INTEGER,
                scrap_count INTEGER
            );
        """)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR PRIMARY KEY,
                product_id VARCHAR,
                target_cycle DOUBLE,
                planned_qty INTEGER
            );
        """)

    def insert_events(self, rows: list[dict], source_file: str) -> int:
        assert self.con is not None
        params = [
            (
                source_file, r["row_ordinal"], r["timestamp"], r["line_id"],
                r.get("station_id"), r["event_type"], r["duration"],
                r.get("reason_code"), r.get("operator_entered_reason"),
                r.get("operator_entry_ts"),
            )
            for r in rows
        ]
        self.con.executemany(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
            params,
        )
        return len(params)

    def upsert_production(self, rows: list[dict]) -> int:
        assert self.con is not None
        params = [
            (r["carrier_id"], r["order_id"], r["loaded_qty"],
             r["good_count"], r["redo_count"], r["scrap_count"])
            for r in rows
        ]
        self.con.executemany(
            """INSERT INTO production VALUES (?,?,?,?,?,?)
               ON CONFLICT (carrier_id) DO UPDATE SET
                 order_id=excluded.order_id, loaded_qty=excluded.loaded_qty,
                 good_count=excluded.good_count, redo_count=excluded.redo_count,
                 scrap_count=excluded.scrap_count""",
            params,
        )
        return len(params)

    def upsert_orders(self, rows: list[dict]) -> int:
        assert self.con is not None
        params = [
            (r["order_id"], r["product_id"], r["target_cycle"], r["planned_qty"])
            for r in rows
        ]
        self.con.executemany(
            """INSERT INTO orders VALUES (?,?,?,?)
               ON CONFLICT (order_id) DO UPDATE SET
                 product_id=excluded.product_id, target_cycle=excluded.target_cycle,
                 planned_qty=excluded.planned_qty""",
            params,
        )
        return len(params)

    def count(self, table: str) -> int:
        assert self.con is not None
        if table not in ("events", "production", "orders"):
            raise ValueError(f"bilinmeyen tablo: {table}")
        return self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def fetch_events(self, frm: str | None = None, to: str | None = None) -> list[dict]:
        assert self.con is not None
        sql = ("SELECT timestamp, station_id, event_type, duration "
               "FROM events WHERE 1=1")
        args: list = []
        if frm is not None:
            sql += " AND timestamp >= ?"
            args.append(frm)
        if to is not None:
            sql += " AND timestamp <= ?"
            args.append(to)
        cur = self.con.execute(sql, args)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def fetch_production(self) -> list[dict]:
        assert self.con is not None
        cur = self.con.execute(
            "SELECT carrier_id, order_id, loaded_qty, good_count, redo_count, scrap_count "
            "FROM production"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
