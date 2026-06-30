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


def _clean(value):
    """CSV boş hücresi / NaN -> None."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _read_csv(path: Path, report: LoadReport | None = None) -> list[dict]:
    """CSV'yi zarifçe oku: bozuk encoding karakterleri değiştirilir (utf-8-sig + replace),
    yapısal CSV hatası (csv.Error) dosya bazında reddedilir — tüm yüklemeyi düşürmez."""
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            return list(csv.DictReader(f))
    except (csv.Error, OSError) as exc:
        if report is not None:
            report.add_rejection(path.name, -1, f"CSV okunamadı: {exc}")
        return []


def _is_ground_truth(name: str) -> bool:
    return name.lower().startswith("ground_truth")


def load_csv_dir(path: str | Path, repo: Repository) -> LoadReport:
    d = Path(path)
    if not d.is_dir():
        raise NotADirectoryError(f"ingest yolu bir dizin değil ya da yok: {d}")
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
    for i, raw in enumerate(_read_csv(path, report)):
        try:
            row = EventRow(
                timestamp=raw["timestamp"],
                line_id=raw["line_id"],
                carrier_id=_clean(raw.get("carrier_id")),
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
            "carrier_id": row.carrier_id,
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
    for i, raw in enumerate(_read_csv(path, report)):
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
    for i, raw in enumerate(_read_csv(path, report)):
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
