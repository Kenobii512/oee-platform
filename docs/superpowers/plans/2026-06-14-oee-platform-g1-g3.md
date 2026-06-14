# OEE Platform G1–G3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `oee-platform/` repo through its first three tasks — a working FastAPI+DuckDB skeleton with a frozen data contract (G1), a validating idempotent CSV ingest layer (G2), and an OEE engine that computes A/P/Q/OEE from public data only, matching the simulator's `metrics.py` (G3).

**Architecture:** Single FastAPI service over DuckDB. One-way layer dependency: `api → analytics/ingest → store(Repository) → duckdb`. Business logic never imports concrete DuckDB; it goes through a `Repository` Protocol so a future swap to Postgres touches one file. OEE is computed purely from public CSV (`events`, `production`, `orders`) plus the line definition; the simulator is reference/regression only and the firewall (`ground_truth.csv` never ingested) is enforced in code.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, DuckDB, pydantic v2, PyYAML, pytest, httpx. Docker single container.

**Spec:** `docs/superpowers/specs/2026-06-14-oee-platform-g1-g3-design.md`

**Key decisions (from brainstorming):**
- **Quality denominator** = config carrier capacity (`LineDefinition.carrier_capacity[order_id]`); if absent, fall back to per-order `max(loaded_qty)` inference (`accuracy.py` pattern).
- **Idempotency** = production/orders keyed on natural PK with `ON CONFLICT DO UPDATE`; events keyed on `(source_file, row_ordinal)` with `ON CONFLICT DO NOTHING`.
- **Firewall** = any file named `ground_truth*` is skipped without opening it.
- **Golden fixtures** = generated once by running the simulator at seed 42 (lossless + baseline), committed as static CSVs + a `baseline_golden.json`; tests have no runtime simulator dependency.

**Paths:** All work happens under repo root `C:\Cowork_Playground\oee`. The new platform lives in `oee-platform/`. The simulator at `simulator/` is read-only reference. Commands below assume CWD = `oee-platform/` unless stated. `oee-platform/` is its own git repo (`git init` in Task 1).

---

## G1 — Repo skeleton + Data contract + ADR

### Task 1: Scaffold repo, dependencies, Docker

**Files:**
- Create: `oee-platform/.gitignore`, `oee-platform/README.md`, `oee-platform/backend/requirements.txt`, `oee-platform/backend/Dockerfile`, `oee-platform/docker-compose.yml`
- Create empty packages: `oee-platform/backend/app/__init__.py`, `app/api/__init__.py`, `app/models/__init__.py`, `app/store/__init__.py`, `app/ingest/__init__.py`, `app/analytics/__init__.py`, `backend/tests/__init__.py`

- [ ] **Step 1: Create directories and empty `__init__.py` files**

```bash
mkdir -p oee-platform/backend/app/{api,models,store,ingest,analytics} oee-platform/backend/tests/fixtures oee-platform/config oee-platform/docs/adr
touch oee-platform/backend/app/__init__.py oee-platform/backend/app/api/__init__.py oee-platform/backend/app/models/__init__.py oee-platform/backend/app/store/__init__.py oee-platform/backend/app/ingest/__init__.py oee-platform/backend/app/analytics/__init__.py oee-platform/backend/tests/__init__.py
```

- [ ] **Step 2: Write `backend/requirements.txt`**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
duckdb==1.1.3
pydantic==2.10.4
pyyaml==6.0.2
pandas==2.2.3
pytest==8.3.4
httpx==0.28.1
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
*.duckdb
*.duckdb.wal
.pytest_cache/
```

- [ ] **Step 4: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 5: Write `docker-compose.yml`**

```yaml
services:
  oee-platform:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OEE_DUCKDB_PATH=/data/oee.duckdb
      - OEE_LINE_CONFIG=/app/config/line_default.yaml
    volumes:
      - ./config:/app/config:ro
      - oee-data:/data
volumes:
  oee-data:
```

- [ ] **Step 6: Write `README.md`**

```markdown
# OEE Platform

Kaplama hattı için OEE/verimlilik platformu. Genel CSV'leri (events/production/orders)
DuckDB'ye yükler ve OEE'yi yalnızca genel veriden hesaplar.

## Çalıştırma

    docker-compose up --build
    # GET http://localhost:8000/health -> {"status":"ok"}

## Test

    cd backend
    pip install -r requirements.txt
    pytest -v

## İlkeler

- Şema kutsaldır; platform verinin kaynağını bilmez.
- `ground_truth.csv` ASLA yüklenmez (firewall).
- OEE mantığı tek serviste (`app/analytics/oee.py`).
```

- [ ] **Step 7: Init git and commit**

```bash
cd oee-platform && git init && git add -A && git commit -m "chore: scaffold oee-platform repo skeleton"
```

---

### Task 2: Data contract models (pydantic)

**Files:**
- Create: `backend/app/models/contract.py`
- Test: `backend/tests/test_contract.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_contract.py`**

```python
import pytest
from pydantic import ValidationError

from app.models.contract import EventRow, ProductionRow, OrderRow, EventType


def test_valid_event_row():
    row = EventRow(
        timestamp="2026-01-05 06:00:30.000",
        line_id="LINE-01",
        station_id="yagsizlandirma",
        event_type="PROCESS",
        duration=3.91,
        reason_code=None,
        operator_entered_reason=None,
        operator_entry_ts=None,
    )
    assert row.event_type is EventType.PROCESS
    assert row.station_id == "yagsizlandirma"


def test_event_type_enum_has_nine_values():
    assert {e.value for e in EventType} == {
        "LOAD", "PROCESS", "MOVE", "UNLOAD", "QC",
        "OVER_RESIDENCE", "DOWNTIME", "MICROSTOP", "STRIP",
    }


def test_bad_event_type_rejected():
    with pytest.raises(ValidationError):
        EventRow(timestamp="2026-01-05 06:00:30.000", line_id="L", event_type="BOGUS", duration=1.0)


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError):
        EventRow(line_id="L", event_type="LOAD", duration=1.0)  # no timestamp


def test_valid_production_row():
    row = ProductionRow(carrier_id="CAR-0001", order_id="ORD-0001",
                        loaded_qty=92, good_count=92, redo_count=0, scrap_count=0)
    assert row.good_count == 92


def test_production_count_invariant_violation_rejected():
    with pytest.raises(ValidationError):
        ProductionRow(carrier_id="C", order_id="O",
                      loaded_qty=100, good_count=90, redo_count=0, scrap_count=5)  # 90+5 != 100


def test_production_redo_not_in_invariant():
    # redo_count is a separate rework volume, NOT part of good+scrap==loaded
    row = ProductionRow(carrier_id="C", order_id="O",
                        loaded_qty=100, good_count=98, redo_count=7, scrap_count=2)
    assert row.redo_count == 7


def test_valid_order_row():
    row = OrderRow(order_id="ORD-0001", product_id="PRD-A", target_cycle=40.0, planned_qty=4000)
    assert row.planned_qty == 4000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd oee-platform/backend && python -m pytest tests/test_contract.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.contract'`

- [ ] **Step 3: Write `backend/app/models/contract.py`**

```python
"""Veri sözleşmesi — platformun sahadan beklediği genel CSV şemaları.

Şema simülatörün çıktı şemasıyla birebir aynıdır ama burada BAĞIMSIZ sözleşme
olarak tanımlanır; platform verinin kaynağını bilmez.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, model_validator


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
    station_id: Optional[str] = None
    event_type: EventType
    duration: float
    reason_code: Optional[str] = None
    operator_entered_reason: Optional[str] = None
    operator_entry_ts: Optional[datetime] = None


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd oee-platform/backend && python -m pytest tests/test_contract.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g1): data contract pydantic models + tests"
```

---

### Task 3: Config loading + copy line definition

**Files:**
- Create: `oee-platform/config/line_default.yaml` (copy from simulator)
- Create: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Copy the simulator line definition**

```bash
cp simulator/config/line_default.yaml oee-platform/config/line_default.yaml
```

- [ ] **Step 2: Write the failing test `backend/tests/test_config.py`**

```python
from pathlib import Path

from app.config import load_line_definition

CONFIG = Path(__file__).resolve().parents[2] / "config" / "line_default.yaml"


def test_loads_tanks_in_order():
    line = load_line_definition(CONFIG)
    assert line.id == "LINE-01"
    assert [t.id for t in line.tanks][0] == "yagsizlandirma"
    assert any(t.bottleneck for t in line.tanks)


def test_nominal_full_pass_minutes():
    line = load_line_definition(CONFIG)
    nominal = sum((t.time_min + t.time_max) / 2.0 for t in line.tanks)
    assert nominal == 36.75  # (3.5+1.25+2.5+1.25+22.5+1.25+4.5)


def test_carrier_capacity_from_orders():
    line = load_line_definition(CONFIG)
    assert line.carrier_capacity["ORD-0001"] == 100
    assert line.carrier_capacity["ORD-0002"] == 100
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd oee-platform/backend && python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 4: Write `backend/app/config.py`**

```python
"""Konfigürasyon yükleme: env + hat tanımı YAML.

Hat tanımı simülatörün `line_default.yaml` formatını esas alır; platform onu
config olarak okur (ground-truth değil, mühendislik master-data'sı).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
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


def load_app_config() -> AppConfig:
    """Env'den uygulama ayarlarını okur (varsayılanlarla)."""
    return AppConfig(
        duckdb_path=os.environ.get("OEE_DUCKDB_PATH", "oee.duckdb"),
        line_config_path=os.environ.get(
            "OEE_LINE_CONFIG", str(Path(__file__).resolve().parents[2] / "config" / "line_default.yaml")
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd oee-platform/backend && python -m pytest tests/test_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g1): config loading + line definition with carrier capacity"
```

---

### Task 4: Repository interface + DuckDB connection shell

**Files:**
- Create: `backend/app/store/repository.py`
- Create: `backend/app/store/duckdb_repo.py`
- Test: `backend/tests/test_repo_connection.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_repo_connection.py`**

```python
from app.store.duckdb_repo import DuckDBRepository


def test_connect_and_close(tmp_path):
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect()
    assert repo.con is not None
    # connection usable
    assert repo.con.execute("SELECT 1").fetchone()[0] == 1
    repo.close()
    assert repo.con is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd oee-platform/backend && python -m pytest tests/test_repo_connection.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.store.duckdb_repo'`

- [ ] **Step 3: Write `backend/app/store/repository.py`**

```python
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
```

- [ ] **Step 4: Write `backend/app/store/duckdb_repo.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd oee-platform/backend && python -m pytest tests/test_repo_connection.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g1): repository protocol + duckdb connection shell"
```

---

### Task 5: FastAPI app + /health

**Files:**
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_health.py`**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd oee-platform/backend && python -m pytest tests/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Write `backend/app/main.py`**

```python
"""FastAPI uygulama girişi."""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="OEE Platform")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd oee-platform/backend && python -m pytest tests/test_health.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g1): FastAPI app with /health"
```

---

### Task 6: Docs — data contract + ADR

**Files:**
- Create: `oee-platform/docs/data-contract.md`
- Create: `oee-platform/docs/adr/0001-mimari.md`

- [ ] **Step 1: Write `docs/data-contract.md`**

```markdown
# Veri Sözleşmesi

Kaynak: sahadan/simülatörden gelen `*.csv`. Üç genel dosya platforma girer.
**Firewall:** `ground_truth.csv` ASLA ingest edilmez; yalnız ayrı doğrulama yolundan
okunur (G6). Platform verinin simülatörden mi sahadan mı geldiğini bilmez.

## events.csv
| alan | tip | not |
|------|-----|-----|
| timestamp | ISO datetime | olay başlangıcı |
| line_id | str | hat kimliği |
| station_id | str/boş | tank id / `HOIST` / hat seviyesinde boş |
| event_type | enum | LOAD, PROCESS, MOVE, UNLOAD, QC, OVER_RESIDENCE, DOWNTIME, MICROSTOP, STRIP |
| duration | float (dk) | olay süresi |
| reason_code | str/boş | DOWNTIME→otomatik kod; MICROSTOP→boş |
| operator_entered_reason | str/boş | operatör etiketi |
| operator_entry_ts | datetime/boş | operatör giriş zamanı |

## production.csv
| alan | tip | not |
|------|-----|-----|
| carrier_id | str | askı |
| order_id | str | iş emri |
| loaded_qty | int | yüklenen parça |
| good_count | int | sağlam |
| redo_count | int | yeniden işlenen (rework hacmi) |
| scrap_count | int | hurda |

Değişmez: `good_count + scrap_count == loaded_qty`. `redo_count` ayrı rework hacmidir.

## orders.csv
order_id, product_id, target_cycle, planned_qty.

## Hat tanımı (line definition)
`config/line_default.yaml` formatında: nominal tank süreleri, darboğaz, askı kapasitesi.
Quality/Performance kırılımı için gereklidir. Askı kapasitesi master-data'dır (firewall
arkasında değil).
```

- [ ] **Step 2: Write `docs/adr/0001-mimari.md`**

```markdown
# ADR 0001 — Mimari Kararı

## Bağlam
Kaplama hattı için OEE platformu. Veri sahadan veya simülatörden gelir; platform farkı
bilmemeli.

## Karar
- **Yığın:** Python 3.11 + FastAPI (backend) + DuckDB (depo) + Docker (tek konteyner).
- **Katmanlar:** `api → analytics/ingest → store(Repository) → duckdb`, tek yönlü bağımlılık.
  İş mantığı somut DuckDB'yi tanımaz; `Repository` Protocol'üne bağlıdır.
- **Dağıtım:** Tek konteyner (laptop + VM). Veri DuckDB dosyasında.
- **DuckDB→Postgres:** Gömülü DuckDB ile başlanır (sıfır kurulum, hızlı analitik). Ölçek/
  çok-kullanıcı gerekince `duckdb_repo.py` Postgres uygulamasıyla değiştirilir; arayüz sabit.
- **OEE tek doğruluk kaynağı:** Hesap `analytics/oee.py`'de toplanır; simülatör `metrics.py`
  yalnız referans/regresyon.

## Kapsam dışı
Kubernetes, çok-kiracılık, what-if motoru, gerçek-zamanlı akış. Sonraki sürümlerde.

## Sonuç
Hızlı, tek-konteyner, test edilebilir iskelet; veri katmanı geleceğe karşı yalıtılmış.
```

- [ ] **Step 3: Commit**

```bash
cd oee-platform && git add -A && git commit -m "docs(g1): data contract + architecture ADR"
```

---

### Task 7: G1 verification gate

- [ ] **Step 1: Run full test suite**

Run: `cd oee-platform/backend && python -m pytest -v`
Expected: PASS (all G1 tests green: contract, config, repo_connection, health)

- [ ] **Step 2: Verify Docker brings the service up**

Run: `cd oee-platform && docker-compose up --build -d && sleep 5 && curl -s http://localhost:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 3: Tear down**

Run: `cd oee-platform && docker-compose down`

> **CHECKPOINT:** G1 done. Skeleton runs, /health 200, pytest green. Do not start G2 until this gate passes.

---

## G2 — Ingest + Storage layer

### Task 8: DuckDB schemas + idempotent write/query methods

**Files:**
- Modify: `backend/app/store/repository.py` (extend Protocol)
- Modify: `backend/app/store/duckdb_repo.py` (schemas + methods)
- Test: `backend/tests/test_repo_idempotent.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_repo_idempotent.py`**

```python
from app.store.duckdb_repo import DuckDBRepository


def _repo(tmp_path):
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect()
    repo.init_schema()
    return repo


def test_events_insert_idempotent_on_source_and_ordinal(tmp_path):
    repo = _repo(tmp_path)
    rows = [
        {"row_ordinal": 0, "timestamp": "2026-01-05 06:00:00", "line_id": "L",
         "station_id": None, "event_type": "LOAD", "duration": 0.0,
         "reason_code": None, "operator_entered_reason": None, "operator_entry_ts": None},
        {"row_ordinal": 1, "timestamp": "2026-01-05 06:00:00", "line_id": "L",
         "station_id": "HOIST", "event_type": "MOVE", "duration": 0.5,
         "reason_code": None, "operator_entered_reason": None, "operator_entry_ts": None},
    ]
    repo.insert_events(rows, source_file="events.csv")
    repo.insert_events(rows, source_file="events.csv")  # second load
    assert repo.count("events") == 2  # no duplicates
    repo.close()


def test_identical_events_both_kept(tmp_path):
    # Two byte-identical events at different ordinals are both preserved.
    repo = _repo(tmp_path)
    rows = [
        {"row_ordinal": 0, "timestamp": "2026-01-05 06:00:00", "line_id": "L",
         "station_id": None, "event_type": "LOAD", "duration": 0.0,
         "reason_code": None, "operator_entered_reason": None, "operator_entry_ts": None},
        {"row_ordinal": 1, "timestamp": "2026-01-05 06:00:00", "line_id": "L",
         "station_id": None, "event_type": "LOAD", "duration": 0.0,
         "reason_code": None, "operator_entered_reason": None, "operator_entry_ts": None},
    ]
    repo.insert_events(rows, source_file="events.csv")
    assert repo.count("events") == 2
    repo.close()


def test_production_upsert_updates(tmp_path):
    repo = _repo(tmp_path)
    repo.upsert_production([{"carrier_id": "C1", "order_id": "O1",
                            "loaded_qty": 100, "good_count": 90, "redo_count": 0, "scrap_count": 10}])
    # corrected re-load: good 95 / scrap 5
    repo.upsert_production([{"carrier_id": "C1", "order_id": "O1",
                            "loaded_qty": 100, "good_count": 95, "redo_count": 0, "scrap_count": 5}])
    assert repo.count("production") == 1
    rows = repo.fetch_production()
    assert rows[0]["good_count"] == 95
    repo.close()


def test_orders_upsert_idempotent(tmp_path):
    repo = _repo(tmp_path)
    o = [{"order_id": "O1", "product_id": "P", "target_cycle": 40.0, "planned_qty": 4000}]
    repo.upsert_orders(o)
    repo.upsert_orders(o)
    assert repo.count("orders") == 1
    repo.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd oee-platform/backend && python -m pytest tests/test_repo_idempotent.py -v`
Expected: FAIL with `AttributeError: 'DuckDBRepository' object has no attribute 'init_schema'` raising NotImplementedError / missing methods

- [ ] **Step 3: Extend `backend/app/store/repository.py` Protocol**

Replace the comment block at the end with real signatures:

```python
    def init_schema(self) -> None: ...
    def insert_events(self, rows: list[dict], source_file: str) -> int: ...
    def upsert_production(self, rows: list[dict]) -> int: ...
    def upsert_orders(self, rows: list[dict]) -> int: ...
    def count(self, table: str) -> int: ...
    def fetch_events(self, frm: str | None = None, to: str | None = None) -> list[dict]: ...
    def fetch_production(self) -> list[dict]: ...
```

- [ ] **Step 4: Replace `init_schema` and add methods in `backend/app/store/duckdb_repo.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd oee-platform/backend && python -m pytest tests/test_repo_idempotent.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g2): duckdb schemas + idempotent upsert/query methods"
```

---

### Task 9: LoadReport

**Files:**
- Create: `backend/app/ingest/report.py`
- Test: `backend/tests/test_load_report.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_load_report.py`**

```python
from app.ingest.report import LoadReport


def test_report_accumulates_counts():
    rep = LoadReport()
    rep.accepted["events"] = 10
    rep.rejected.append({"file": "production.csv", "row": 3, "error": "bad"})
    rep.skipped.append("ground_truth.csv")
    d = rep.to_dict()
    assert d["accepted"]["events"] == 10
    assert d["rejected_count"] == 1
    assert d["skipped"] == ["ground_truth.csv"]
    assert d["errors"][0]["row"] == 3


def test_report_caps_error_list():
    rep = LoadReport(max_errors=2)
    for i in range(5):
        rep.add_rejection("f.csv", i, "e")
    assert rep.to_dict()["rejected_count"] == 5  # full count kept
    assert len(rep.to_dict()["errors"]) == 2     # but only first 2 surfaced
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd oee-platform/backend && python -m pytest tests/test_load_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.ingest.report'`

- [ ] **Step 3: Write `backend/app/ingest/report.py`**

```python
"""Yükleme raporu: kabul/ret/atlanan sayıları + ilk N hata."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoadReport:
    max_errors: int = 50
    accepted: dict[str, int] = field(default_factory=dict)
    rejected: list[dict] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def add_rejection(self, file: str, row: int, error: str) -> None:
        self.rejected.append({"file": file, "row": row, "error": error})

    def to_dict(self) -> dict:
        return {
            "accepted": dict(self.accepted),
            "rejected_count": len(self.rejected),
            "skipped": list(self.skipped),
            "errors": self.rejected[: self.max_errors],
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd oee-platform/backend && python -m pytest tests/test_load_report.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g2): LoadReport"
```

---

### Task 10: Fixture generation (run simulator once)

**Files:**
- Create: `oee-platform/backend/tests/fixtures/_generate.py`
- Create (generated, committed): `backend/tests/fixtures/lossless/{events,production,orders}.csv`, `backend/tests/fixtures/baseline/{events,production,orders,ground_truth}.csv`, `backend/tests/fixtures/baseline_golden.json`

> This task is run once with the simulator's interpreter to materialize static fixtures. Tests never import the simulator.

- [ ] **Step 1: Write `backend/tests/fixtures/_generate.py`**

```python
"""Tek seferlik golden fixture üreteci. Simülatör .venv'iyle çalıştırılır:

    cd simulator
    .venv/Scripts/python ../oee-platform/backend/tests/fixtures/_generate.py

Çıktı: oee-platform/backend/tests/fixtures/{lossless,baseline}/*.csv + baseline_golden.json
Tests bu statik dosyaları okur; simülatöre çalışma-zamanı bağımlılığı yoktur.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parents[4] / "simulator"
sys.path.insert(0, str(SIM))

from src.config import load_config            # noqa: E402
from src.line import run_simulation           # noqa: E402
from src.losses import load_scenario          # noqa: E402
from src.metrics import compute_oee           # noqa: E402

OUT = Path(__file__).resolve().parent
CONFIG = SIM / "config" / "line_default.yaml"
SCENARIO = SIM / "config" / "scenario_baseline.yaml"
SEED = 42


def main() -> None:
    cfg = load_config(CONFIG)

    # Lossless set (no scenario)
    res = run_simulation(cfg, seed=SEED)
    res.recorder.write_csvs(OUT / "lossless", res.carriers, cfg.orders)
    (OUT / "lossless" / "ground_truth.csv").unlink(missing_ok=True)

    # Baseline set (with loss scenario)
    scn = load_scenario(SCENARIO)
    res_b = run_simulation(cfg, seed=SEED, scenario=scn)
    res_b.recorder.write_csvs(OUT / "baseline", res_b.carriers, cfg.orders)
    oee = compute_oee(res_b, cfg)
    (OUT / "baseline_golden.json").write_text(json.dumps({
        "seed": SEED,
        "availability": oee.availability,
        "performance": oee.performance,
        "quality": oee.quality,
        "oee": oee.oee,
    }, indent=2))
    print("fixtures yazıldı:", OUT)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate the fixtures**

Run (from repo root):
```bash
cd simulator && .venv/Scripts/python.exe ../oee-platform/backend/tests/fixtures/_generate.py
```
Expected: prints `fixtures yazıldı: ...`; creates `lossless/*.csv` (no ground_truth), `baseline/*.csv` (incl ground_truth.csv), `baseline_golden.json`.

- [ ] **Step 3: Sanity-check the golden file**

Run: `cat oee-platform/backend/tests/fixtures/baseline_golden.json`
Expected: a JSON object with `oee` between 0.55 and 0.70 (baseline band).

- [ ] **Step 4: Commit fixtures**

```bash
cd oee-platform && git add -A && git commit -m "test(g2): generate seed-42 lossless + baseline fixtures and golden"
```

---

### Task 11: CSV loader with validation + firewall

**Files:**
- Create: `backend/app/ingest/loader.py`
- Test: `backend/tests/test_ingest_ok.py`, `backend/tests/test_ingest_reject.py`, `backend/tests/test_idempotent.py`, `backend/tests/test_no_ground_truth.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_ingest_ok.py`**

```python
import csv
from pathlib import Path

from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def _count_csv_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # minus header


def test_baseline_loads_and_row_counts_match(tmp_path):
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect(); repo.init_schema()
    report = load_csv_dir(FIX, repo)
    assert repo.count("events") == _count_csv_rows(FIX / "events.csv")
    assert repo.count("production") == _count_csv_rows(FIX / "production.csv")
    assert repo.count("orders") == _count_csv_rows(FIX / "orders.csv")
    assert report.to_dict()["rejected_count"] == 0
    repo.close()
```

- [ ] **Step 2: Write `backend/tests/test_ingest_reject.py`**

```python
from pathlib import Path

from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository


def test_bad_rows_rejected_good_rows_loaded(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    # one good event, one bad event_type
    (d / "events.csv").write_text(
        "timestamp,line_id,station_id,event_type,duration,reason_code,operator_entered_reason,operator_entry_ts\n"
        "2026-01-05 06:00:00.000,LINE-01,,LOAD,0.0,,,\n"
        "2026-01-05 06:00:01.000,LINE-01,,BOGUS,1.0,,,\n"
    )
    # one good production, one violating good+scrap==loaded
    (d / "production.csv").write_text(
        "carrier_id,order_id,loaded_qty,good_count,redo_count,scrap_count\n"
        "CAR-1,ORD-1,100,100,0,0\n"
        "CAR-2,ORD-1,100,90,0,5\n"
    )
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect(); repo.init_schema()
    report = load_csv_dir(d, repo)
    assert repo.count("events") == 1
    assert repo.count("production") == 1
    rd = report.to_dict()
    assert rd["rejected_count"] == 2
    assert any(e["file"] == "events.csv" for e in rd["errors"])
    assert any(e["file"] == "production.csv" for e in rd["errors"])
    repo.close()
```

- [ ] **Step 3: Write `backend/tests/test_idempotent.py`**

```python
from pathlib import Path

from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_second_load_no_duplicates(tmp_path):
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect(); repo.init_schema()
    load_csv_dir(FIX, repo)
    e1, p1, o1 = repo.count("events"), repo.count("production"), repo.count("orders")
    load_csv_dir(FIX, repo)  # load again
    assert (repo.count("events"), repo.count("production"), repo.count("orders")) == (e1, p1, o1)
    repo.close()
```

- [ ] **Step 4: Write `backend/tests/test_no_ground_truth.py`**

```python
from pathlib import Path

from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"  # contains ground_truth.csv


def test_ground_truth_never_loaded(tmp_path):
    assert (FIX / "ground_truth.csv").exists()  # fixture has it
    repo = DuckDBRepository(str(tmp_path / "t.duckdb"))
    repo.connect(); repo.init_schema()
    report = load_csv_dir(FIX, repo)
    # no table receives ground_truth rows; report marks it skipped
    assert "ground_truth.csv" in report.to_dict()["skipped"]
    # events table only has real events, not the 7-col ground_truth schema
    assert repo.con.execute(
        "SELECT COUNT(*) FROM events WHERE event_type IN ('FILL_LOSS','SPEED_LOSS')"
    ).fetchone()[0] == 0
    repo.close()
```

- [ ] **Step 5: Run the four tests to verify they fail**

Run: `cd oee-platform/backend && python -m pytest tests/test_ingest_ok.py tests/test_ingest_reject.py tests/test_idempotent.py tests/test_no_ground_truth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.ingest.loader'`

- [ ] **Step 6: Write `backend/app/ingest/loader.py`**

```python
"""Genel CSV'leri doğrulayıp DuckDB'ye yükler.

Firewall: adı `ground_truth` ile başlayan dosya AÇILMADAN atlanır. events doğal
anahtarsız olduğu için (source_file, row_ordinal) ile idempotent; production/orders
doğal anahtarla upsert (bkz. repository).
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

from pydantic import ValidationError

from app.ingest.report import LoadReport
from app.models.contract import EventRow, OrderRow, ProductionRow
from app.store.repository import Repository

_OPTIONAL_BLANK = {None, ""}


def _clean(value):
    """CSV boş hücresi / NaN -> None."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_ground_truth(name: str) -> bool:
    return name.lower().startswith("ground_truth")


def load_csv_dir(path: str | Path, repo: Repository) -> LoadReport:
    d = Path(path)
    report = LoadReport()

    # Firewall: ground_truth dosyalarını açmadan atla.
    for f in sorted(d.glob("*.csv")):
        if _is_ground_truth(f.name):
            report.skipped.append(f.name)

    _load_events(d / "events.csv", repo, report)
    _load_production(d / "production.csv", repo, report)
    _load_orders(d / "orders.csv", repo, report)
    return report


def _load_events(path: Path, repo: Repository, report: LoadReport) -> None:
    if not path.exists():
        return
    valid: list[dict] = []
    for i, raw in enumerate(_read_csv(path)):
        try:
            row = EventRow(
                timestamp=raw["timestamp"],
                line_id=raw["line_id"],
                station_id=_clean(raw.get("station_id")),
                event_type=raw["event_type"],
                duration=raw["duration"],
                reason_code=_clean(raw.get("reason_code")),
                operator_entered_reason=_clean(raw.get("operator_entered_reason")),
                operator_entry_ts=_clean(raw.get("operator_entry_ts")),
            )
        except (ValidationError, KeyError, ValueError) as exc:
            report.add_rejection(path.name, i, str(exc))
            continue
        valid.append({
            "row_ordinal": i,
            "timestamp": row.timestamp,
            "line_id": row.line_id,
            "station_id": row.station_id,
            "event_type": row.event_type.value,
            "duration": row.duration,
            "reason_code": row.reason_code,
            "operator_entered_reason": row.operator_entered_reason,
            "operator_entry_ts": row.operator_entry_ts,
        })
    if valid:
        repo.insert_events(valid, source_file=path.name)
    report.accepted["events"] = len(valid)


def _load_production(path: Path, repo: Repository, report: LoadReport) -> None:
    if not path.exists():
        return
    valid: list[dict] = []
    for i, raw in enumerate(_read_csv(path)):
        try:
            row = ProductionRow(
                carrier_id=raw["carrier_id"],
                order_id=raw["order_id"],
                loaded_qty=raw["loaded_qty"],
                good_count=raw["good_count"],
                redo_count=raw["redo_count"],
                scrap_count=raw["scrap_count"],
            )
        except (ValidationError, KeyError, ValueError) as exc:
            report.add_rejection(path.name, i, str(exc))
            continue
        valid.append(row.model_dump())
    if valid:
        repo.upsert_production(valid)
    report.accepted["production"] = len(valid)


def _load_orders(path: Path, repo: Repository, report: LoadReport) -> None:
    if not path.exists():
        return
    valid: list[dict] = []
    for i, raw in enumerate(_read_csv(path)):
        try:
            row = OrderRow(
                order_id=raw["order_id"],
                product_id=raw["product_id"],
                target_cycle=raw["target_cycle"],
                planned_qty=raw["planned_qty"],
            )
        except (ValidationError, KeyError, ValueError) as exc:
            report.add_rejection(path.name, i, str(exc))
            continue
        valid.append(row.model_dump())
    if valid:
        repo.upsert_orders(valid)
    report.accepted["orders"] = len(valid)
```

- [ ] **Step 7: Run the four tests to verify they pass**

Run: `cd oee-platform/backend && python -m pytest tests/test_ingest_ok.py tests/test_ingest_reject.py tests/test_idempotent.py tests/test_no_ground_truth.py -v`
Expected: PASS (4 files, all green)

- [ ] **Step 8: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g2): CSV loader with validation, firewall, idempotency"
```

---

### Task 12: POST /ingest endpoint

**Files:**
- Create: `backend/app/api/ingest_routes.py`
- Modify: `backend/app/main.py` (wire router + repo lifecycle)
- Test: `backend/tests/test_ingest_endpoint.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_ingest_endpoint.py`**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_ingest_endpoint_returns_report(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        r = client.post("/ingest", json={"path": str(FIX)})
        assert r.status_code == 200
        body = r.json()
        assert body["accepted"]["production"] > 0
        assert "ground_truth.csv" in body["skipped"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd oee-platform/backend && python -m pytest tests/test_ingest_endpoint.py -v`
Expected: FAIL (404 on /ingest or import error)

- [ ] **Step 3: Write `backend/app/api/ingest_routes.py`**

```python
"""POST /ingest -> LoadReport."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.ingest.loader import load_csv_dir

router = APIRouter()


class IngestRequest(BaseModel):
    path: str


@router.post("/ingest")
def ingest(req: IngestRequest, request: Request) -> dict:
    repo = request.app.state.repo
    report = load_csv_dir(req.path, repo)
    return report.to_dict()
```

- [ ] **Step 4: Rewrite `backend/app/main.py` to wire repo lifecycle + router**

```python
"""FastAPI uygulama girişi + repo yaşam döngüsü."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.ingest_routes import router as ingest_router
from app.config import load_app_config
from app.store.duckdb_repo import DuckDBRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = load_app_config()
    repo = DuckDBRepository(cfg.duckdb_path)
    repo.connect()
    repo.init_schema()
    app.state.repo = repo
    app.state.config = cfg
    try:
        yield
    finally:
        repo.close()


app = FastAPI(title="OEE Platform", lifespan=lifespan)
app.include_router(ingest_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Run test to verify it passes (and re-run health)**

Run: `cd oee-platform/backend && python -m pytest tests/test_ingest_endpoint.py tests/test_health.py -v`
Expected: PASS (2 passed). Note: `TestClient(app)` as a context manager triggers lifespan.

- [ ] **Step 6: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g2): POST /ingest endpoint + repo lifecycle"
```

---

### Task 13: G2 verification gate

- [ ] **Step 1: Run full suite**

Run: `cd oee-platform/backend && python -m pytest -v`
Expected: PASS (all G1+G2 tests green)

> **CHECKPOINT:** G2 done. Ingest validates, is idempotent, enforces firewall. Do not start G3 until green.

---

## G3 — OEE engine

### Task 14: OEE definitions unit tests + engine core

**Files:**
- Create: `backend/app/analytics/oee.py`
- Test: `backend/tests/test_oee_defs.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_oee_defs.py`**

```python
from app.analytics.oee import union_length, availability_from_events


def test_union_length_disjoint():
    assert union_length([(0.0, 2.0), (5.0, 7.0)]) == 4.0


def test_union_length_overlapping_counted_once():
    # overlapping/nested downtimes counted once
    assert union_length([(0.0, 5.0), (2.0, 7.0)]) == 7.0
    assert union_length([(0.0, 10.0), (3.0, 4.0)]) == 10.0


def test_union_length_empty():
    assert union_length([]) == 0.0


def test_availability_subtracts_downtime_union_once():
    # span 0..100; two overlapping DOWNTIME (10..30) and (20..40) -> union 30 min
    events = [
        {"timestamp": 0.0, "duration": 0.0, "event_type": "LOAD", "station_id": None},
        {"timestamp": 10.0, "duration": 20.0, "event_type": "DOWNTIME", "station_id": None},
        {"timestamp": 20.0, "duration": 20.0, "event_type": "DOWNTIME", "station_id": None},
        {"timestamp": 100.0, "duration": 0.0, "event_type": "QC", "station_id": None},
    ]
    # availability_from_events works in minutes-floats for the unit test
    a, span, dt = availability_from_events(events)
    assert span == 100.0
    assert dt == 30.0  # not 40
    assert a == 0.70
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd oee-platform/backend && python -m pytest tests/test_oee_defs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.analytics.oee'`

- [ ] **Step 3: Write `backend/app/analytics/oee.py`**

```python
"""OEE motoru — tek doğruluk kaynağı. Yalnız genel veriden (events, production +
hat tanımı) Availability/Performance/Quality/OEE hesaplar.

Tanımlar simülatör `src/metrics.py` ile BİREBİR:
- Availability = (span − union(DOWNTIME∪MICROSTOP)) / span. Örtüşen duruşlar bir kez.
- Performance  = (askı × Σ nominal tam-geçiş) / Σ PROCESS süresi.
- Quality      = Σ good / Σ intended. intended = hat tanımı askı kapasitesi (master-data);
                 yoksa iş emri başına max(loaded_qty) çıkarımı (accuracy.py deseni).
- OEE = A × P × Q.

Ayrıca utilization (planlı bakım) ayrı raporlanır; OEE'yi etkilemez.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.models.contract import LineDefinition

_DOWNTIME_TYPES = {"DOWNTIME", "MICROSTOP"}


@dataclass(frozen=True)
class OeeResult:
    availability: float
    performance: float
    quality: float
    oee: float
    utilization: float
    planned_downtime_min: float


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def union_length(intervals: list[tuple[float, float]]) -> float:
    """Aralık birleşiminin toplam uzunluğu (örtüşenler bir kez). metrics.py ile aynı."""
    if not intervals:
        return 0.0
    intervals = sorted(intervals)
    total = 0.0
    cur_start, cur_end = intervals[0]
    for start, end in intervals[1:]:
        if start > cur_end:
            total += cur_end - cur_start
            cur_start, cur_end = start, end
        else:
            cur_end = max(cur_end, end)
    total += cur_end - cur_start
    return total


def _to_minutes(ts) -> float:
    """timestamp (datetime veya ISO str veya float dakika) -> dakika ekseni.

    Birim testler float dakika geçer; gerçek veride datetime gelir ve en erken
    olaya göre göreli dakikaya çevrilir (çağıran tarafta normalize edilir)."""
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    return ts.timestamp() / 60.0


def availability_from_events(events: list[dict]) -> tuple[float, float, float]:
    """(availability, span_min, downtime_union_min). events: timestamp(min/datetime),
    duration(dk), event_type."""
    if not events:
        return 0.0, 0.0, 0.0
    starts = [_to_minutes(e["timestamp"]) for e in events]
    ends = [s + e["duration"] for s, e in zip(starts, events)]
    base = min(starts)
    span = max(ends) - base
    downtime = union_length([
        (_to_minutes(e["timestamp"]) - base, _to_minutes(e["timestamp"]) - base + e["duration"])
        for e in events
        if e["event_type"] in _DOWNTIME_TYPES
    ])
    avail = _clamp01((span - downtime) / span) if span > 0 else 0.0
    return avail, span, downtime


def _performance(events: list[dict], num_carriers: int, line: LineDefinition) -> float:
    nominal_full_pass = sum((t.time_min + t.time_max) / 2.0 for t in line.tanks)
    ideal = num_carriers * nominal_full_pass
    actual = sum(e["duration"] for e in events if e["event_type"] == "PROCESS")
    return _clamp01(ideal / actual) if actual > 0 else 0.0


def _quality(production: list[dict], line: LineDefinition) -> float:
    good = sum(p["good_count"] for p in production)
    if line.carrier_capacity:
        intended = sum(line.carrier_capacity.get(p["order_id"], 0) for p in production)
        if intended == 0:  # order_id'ler config'te yoksa çıkarıma düş
            intended = _inferred_intended(production)
    else:
        intended = _inferred_intended(production)
    return _clamp01(good / intended) if intended > 0 else 0.0


def _inferred_intended(production: list[dict]) -> int:
    """Fallback (accuracy.py deseni): iş emri başına gözlenen en büyük loaded_qty
    nominal kabul edilir; intended = Σ nominal."""
    nominal: dict[str, int] = {}
    for p in production:
        nominal[p["order_id"]] = max(nominal.get(p["order_id"], 0), p["loaded_qty"])
    return sum(nominal[p["order_id"]] for p in production)


def compute_oee(
    events: list[dict],
    production: list[dict],
    line: LineDefinition,
    planned_downtime_min: float = 0.0,
) -> OeeResult:
    if not events or not production:
        return OeeResult(0.0, 0.0, 0.0, 0.0, 0.0, planned_downtime_min)
    avail, span, _dt = availability_from_events(events)
    perf = _performance(events, len(production), line)
    qual = _quality(production, line)
    oee = avail * perf * qual
    operating = span * avail
    calendar = span + planned_downtime_min
    utilization = _clamp01(operating / calendar) if calendar > 0 else 0.0
    return OeeResult(avail, perf, qual, oee, utilization, planned_downtime_min)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd oee-platform/backend && python -m pytest tests/test_oee_defs.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g3): OEE engine core + definition unit tests"
```

---

### Task 15: Lossless + baseline parity tests (from fixtures)

**Files:**
- Create: `backend/tests/test_oee_lossless.py`
- Create: `backend/tests/test_oee_baseline.py`
- Create: `backend/tests/conftest.py` (fixture loader helper)

- [ ] **Step 1: Write `backend/tests/conftest.py`**

```python
"""Test yardımcıları: fixture CSV'lerini repo'ya yükleyip OEE girdisi hazırlar."""
import csv
from pathlib import Path

import pytest

from app.config import load_line_definition
from app.ingest.loader import load_csv_dir
from app.store.duckdb_repo import DuckDBRepository

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LINE_CONFIG = Path(__file__).resolve().parents[2] / "config" / "line_default.yaml"


def load_fixture_into_repo(fixture_dir: Path, db_path: str):
    repo = DuckDBRepository(db_path)
    repo.connect()
    repo.init_schema()
    load_csv_dir(fixture_dir, repo)
    return repo


@pytest.fixture
def line_def():
    return load_line_definition(LINE_CONFIG)
```

- [ ] **Step 2: Write `backend/tests/test_oee_lossless.py`**

```python
from pathlib import Path

from app.analytics.oee import compute_oee
from tests.conftest import FIXTURES, load_fixture_into_repo


def test_lossless_oee_at_least_95(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "lossless", str(tmp_path / "l.duckdb"))
    events = repo.fetch_events()
    production = repo.fetch_production()
    result = compute_oee(events, production, line_def)
    assert result.oee >= 0.95, result
    repo.close()
```

- [ ] **Step 3: Write `backend/tests/test_oee_baseline.py`**

```python
import json
from pathlib import Path

from app.analytics.oee import compute_oee
from tests.conftest import FIXTURES, load_fixture_into_repo

GOLDEN = json.loads((FIXTURES / "baseline_golden.json").read_text())


def test_baseline_matches_simulator_within_1pct(tmp_path, line_def):
    repo = load_fixture_into_repo(FIXTURES / "baseline", str(tmp_path / "b.duckdb"))
    events = repo.fetch_events()
    production = repo.fetch_production()
    result = compute_oee(events, production, line_def)
    for field in ("availability", "performance", "quality", "oee"):
        platform = getattr(result, field)
        golden = GOLDEN[field]
        assert abs(platform - golden) <= 0.01, (field, platform, golden)
    repo.close()
```

- [ ] **Step 4: Run the two tests**

Run: `cd oee-platform/backend && python -m pytest tests/test_oee_lossless.py tests/test_oee_baseline.py -v`
Expected: PASS. If baseline fails on `quality` beyond 0.01, the carrier_capacity map is not matching the fixture's order_ids — verify `line_def.carrier_capacity` covers ORD-0001/ORD-0002 and the fixtures used those orders (they do; fixtures use the config order book, no `--weeks`).

> **Note on parity:** Availability/Performance use only public columns and are algorithmically identical to `metrics.py`. Quality matches exactly because `carrier_capacity[order]=100` equals the simulator's `loaded+fill_lost` per carrier. The `span` definition (`max(end)-min(start)`) equals `metrics.py`'s `max(sim_minutes+duration)` because the earliest event is at sim minute 0.

- [ ] **Step 5: Commit**

```bash
cd oee-platform && git add -A && git commit -m "test(g3): lossless threshold + baseline parity vs simulator"
```

---

### Task 16: GET /oee endpoint

**Files:**
- Create: `backend/app/api/oee_routes.py`
- Modify: `backend/app/main.py` (include oee router)
- Test: `backend/tests/test_oee_endpoint.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_oee_endpoint.py`**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_oee_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIX)})
        r = client.get("/oee")
        assert r.status_code == 200
        body = r.json()
        assert set(body) >= {"availability", "performance", "quality", "oee",
                             "utilization", "planned_downtime_min"}
        assert 0.0 <= body["oee"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd oee-platform/backend && python -m pytest tests/test_oee_endpoint.py -v`
Expected: FAIL (404 on /oee)

- [ ] **Step 3: Write `backend/app/api/oee_routes.py`**

```python
"""GET /oee?from=&to= -> OeeResult (yalnız genel veriden)."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query, Request

from app.analytics.oee import compute_oee
from app.config import load_line_definition, load_planned_maintenance

router = APIRouter()


def _planned_downtime(path: str, frm: str | None, to: str | None) -> float:
    """Planlı bakım pencerelerinin [frm,to] ile kesişimi (dakika)."""
    from datetime import datetime, timedelta

    windows = load_planned_maintenance(path)
    total = 0.0
    f = datetime.fromisoformat(frm) if frm else None
    t = datetime.fromisoformat(to) if to else None
    for w in windows:
        start = w.start
        end = w.start + timedelta(minutes=w.duration_min)
        lo = max(start, f) if f else start
        hi = min(end, t) if t else end
        if hi > lo:
            total += (hi - lo).total_seconds() / 60.0
    return total


@router.get("/oee")
def get_oee(
    request: Request,
    frm: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> dict:
    repo = request.app.state.repo
    cfg = request.app.state.config
    line = load_line_definition(cfg.line_config_path)
    events = repo.fetch_events(frm, to)
    production = repo.fetch_production()
    planned = _planned_downtime(cfg.line_config_path, frm, to)
    result = compute_oee(events, production, line, planned_downtime_min=planned)
    return asdict(result)
```

- [ ] **Step 4: Add the oee router to `backend/app/main.py`**

Add import near the other router import:
```python
from app.api.oee_routes import router as oee_router
```
And after `app.include_router(ingest_router)`:
```python
app.include_router(oee_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd oee-platform/backend && python -m pytest tests/test_oee_endpoint.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
cd oee-platform && git add -A && git commit -m "feat(g3): GET /oee endpoint with utilization"
```

---

### Task 17: G3 verification gate + README update

- [ ] **Step 1: Run the full suite**

Run: `cd oee-platform/backend && python -m pytest -v`
Expected: PASS (all G1+G2+G3 tests green)

- [ ] **Step 2: Manual smoke via Docker**

Run:
```bash
cd oee-platform && docker-compose up --build -d && sleep 5
curl -s -X POST http://localhost:8000/ingest -H "Content-Type: application/json" -d "{\"path\": \"/app/tests/fixtures/baseline\"}" || true
curl -s http://localhost:8000/health
docker-compose down
```
Expected: `/health` returns `{"status":"ok"}`. (Ingest via Docker needs fixtures mounted; the authoritative verification is the pytest suite. Optional.)

- [ ] **Step 3: Append OEE usage to `README.md`**

Add:
```markdown

## OEE

    POST /ingest   {"path": "/abs/path/to/csv_dir"}   -> LoadReport
    GET  /oee?from=...&to=...                          -> {availability, performance, quality, oee, utilization, planned_downtime_min}

OEE yalnız genel veriden (events/production + hat tanımı) hesaplanır; tanımlar
simülatör `metrics.py` ile birebir. `ground_truth.csv` asla kullanılmaz.
```

- [ ] **Step 4: Commit**

```bash
cd oee-platform && git add -A && git commit -m "docs(g3): README OEE usage; G1-G3 complete"
```

> **CHECKPOINT:** G1–G3 complete. Skeleton runs, ingest is idempotent + firewalled, OEE matches the simulator within ±1% on baseline and ≥95% on lossless.

---

## Self-review notes (addressed in plan)

- **Spec coverage:** G1 (Tasks 1–7), G2 (8–13), G3 (14–17) cover every spec section: contract models, config+carrier_capacity, repository protocol, /health, docs/ADR, schemas+idempotency hybrid, LoadReport, firewall, /ingest, OEE engine (A/P/Q + Option B + inference fallback + union), utilization, /oee, golden fixtures, all named tests.
- **Type consistency:** `compute_oee(events, production, line, planned_downtime_min)` and `OeeResult` fields used identically across Tasks 14–16. `Repository` methods declared in Task 8 match `duckdb_repo.py` and call sites in loader/routes.
- **Known residual risk:** baseline `quality` parity depends on fixtures using the config order book (ORD-0001/0002, carrier_qty=100). Fixture generation (Task 10) uses `cfg.orders` with no `--weeks`, guaranteeing this. If a future fixture uses synthesized multi-week orders, `carrier_capacity` won't cover them and Quality falls back to inference (documented, ±1% may not hold — out of scope here).
- **Utilization scope:** computed from `planned_maintenance` windows only (off-shift/breaks deferred); non-parity-tested, does not affect OEE — consistent with spec's "lightweight" framing.
