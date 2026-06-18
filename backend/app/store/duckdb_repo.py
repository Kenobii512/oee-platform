"""DuckDB tabanlı Repository.

Tek bağlantı; tüm DB erişimi bir kilitle serileştirilir. FastAPI sync endpoint'leri
ayrı thread'lerde çalışır ve pano endpoint'leri paralel istek atar — tek DuckDB
bağlantısı eşzamanlı erişimde güvenli olmadığından (segfault), erişim kilitle korunur.
Bu ölçekte (gömülü, küçük veri) performans etkisi ihmal edilebilir.
"""
from __future__ import annotations

import threading

import duckdb


class DuckDBRepository:
    def __init__(self, path: str) -> None:
        self.path = path
        self.con: duckdb.DuckDBPyConnection | None = None
        self._lock = threading.RLock()

    def connect(self) -> None:
        if self.con is None:
            self.con = duckdb.connect(self.path)

    def close(self) -> None:
        if self.con is not None:
            self.con.close()
            self.con = None

    def init_schema(self) -> None:
        assert self.con is not None
        with self._lock:
            self._create_tables()

    def reset(self) -> None:
        """Tüm verileri siler (senaryo değişiminde temiz başlangıç için)."""
        assert self.con is not None
        with self._lock:
            for table in ("events", "production", "orders"):
                self.con.execute(f"DELETE FROM {table}")

    def _create_tables(self) -> None:
        assert self.con is not None
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS events (
                source_file VARCHAR,
                row_ordinal INTEGER,
                timestamp TIMESTAMP,
                line_id VARCHAR,
                carrier_id VARCHAR,
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
                r.get("carrier_id"), r.get("station_id"), r["event_type"],
                r["duration"], r.get("reason_code"), r.get("operator_entered_reason"),
                r.get("operator_entry_ts"),
            )
            for r in rows
        ]
        with self._lock:
            self.con.executemany(
                "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
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
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            return self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def fetch_events(self, frm: str | None = None, to: str | None = None) -> list[dict]:
        assert self.con is not None
        sql = ("SELECT timestamp, carrier_id, station_id, event_type, duration, "
               "reason_code, operator_entered_reason "
               "FROM events WHERE 1=1")
        args: list = []
        if frm is not None:
            sql += " AND timestamp >= ?"
            args.append(frm)
        if to is not None:
            sql += " AND timestamp <= ?"
            args.append(to)
        with self._lock:
            cur = self.con.execute(sql, args)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def fetch_production(
        self, frm: str | None = None, to: str | None = None
    ) -> list[dict]:
        """Üretim (askı) sayımları. frm/to verilirse dönem-doğru atıf (G4.1): bir askı,
        kendisine ait olayların EN GEÇ zaman damgası (hattı terk ettiği an) `[frm,to]`
        penceresine düşüyorsa dahil edilir. İkisi de None ise tüm üretim (geriye uyumlu).

        NOT: Pencereli sorgu (frm/to verili) events ile INNER JOIN yapar; HİÇ olayı olmayan
        (orphan) bir production carrier'ı pencere dışı kalır. Geçerli veride her askı olay
        üretir (LOAD/PROCESS) → orphan = veri-kalite hatasıdır, OEE'ye katılmamalıdır. Bu,
        final replay snapshot'ının (to=global max) None,None ile birebir kalmasının önkoşulu.
        """
        assert self.con is not None
        select = ("carrier_id, order_id, loaded_qty, good_count, "
                  "redo_count, scrap_count")
        if frm is None and to is None:
            sql = f"SELECT {select} FROM production"
            args: list = []
        else:
            sql = (
                f"SELECT p.{select.replace(', ', ', p.')} FROM production p "
                "JOIN (SELECT carrier_id, max(timestamp) AS ts FROM events "
                "      WHERE carrier_id IS NOT NULL AND carrier_id <> '' "
                "      GROUP BY carrier_id) e ON p.carrier_id = e.carrier_id "
                "WHERE 1=1"
            )
            args = []
            if frm is not None:
                sql += " AND e.ts >= CAST(? AS TIMESTAMP)"
                args.append(frm)
            if to is not None:
                sql += " AND e.ts <= CAST(? AS TIMESTAMP)"
                args.append(to)
        with self._lock:
            cur = self.con.execute(sql, args)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
