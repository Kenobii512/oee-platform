"""H8 — takvim-dakikası: workday ∩ vardiya − mola − bakım (örtüşme bir kez)."""
from datetime import datetime

from app.analytics.calendar import calendar_minutes
from app.config import (
    BreakDef,
    CalendarDef,
    MaintenanceWindow,
    ShiftDef,
    load_calendar,
)
from tests.conftest import LINE_CONFIG

CAL = load_calendar(LINE_CONFIG)  # 2 vardiya 06-14/14-22, 2 mola 15dk, Pzt-Cum


def dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def test_one_full_workday():
    # Pzt 06:00 -> Salı 06:00: 2×8s = 960 dk − 2×15 dk mola = 930
    assert calendar_minutes(dt("2026-01-05 06:00"), dt("2026-01-06 06:00"), CAL) == 930


def test_weekend_is_zero():
    # Cmt 06:00 -> Pzt 06:00: hafta sonu çalışma günü değil
    assert calendar_minutes(dt("2026-01-10 06:00"), dt("2026-01-12 06:00"), CAL) == 0


def test_offshift_window_excluded():
    # Pzt 22:00 -> Salı 05:00: tamamı vardiya dışı (gece)
    assert calendar_minutes(dt("2026-01-05 22:00"), dt("2026-01-06 05:00"), CAL) == 0


def test_partial_shift_window():
    # Pzt 08:00 -> 12:00: shift1 içinde 4 saat − 10:00 molası (15dk) = 225
    assert calendar_minutes(dt("2026-01-05 08:00"), dt("2026-01-05 12:00"), CAL) == 225


def test_maintenance_within_shift_subtracted_once():
    # Tek vardiya 06-14, mola yok; iki ÖRTÜŞEN bakım penceresi -> bir kez düşülür.
    cal = CalendarDef(
        workdays=(0, 1, 2, 3, 4),
        shifts=(ShiftDef(360, 840),),  # 06:00-14:00 = 480 dk
        breaks=(),
        maintenance=(
            MaintenanceWindow(dt("2026-01-05 08:00"), 60),  # 08:00-09:00
            MaintenanceWindow(dt("2026-01-05 08:30"), 60),  # 08:30-09:30 (örtüşür)
        ),
    )
    # birleşik bakım 08:00-09:30 = 90 dk; 480 − 90 = 390
    assert calendar_minutes(dt("2026-01-05 06:00"), dt("2026-01-05 14:00"), cal) == 390


def test_break_and_maintenance_no_double_subtract():
    # mola 10:00+15 ve bakım 10:00+30 örtüşür -> union 30 dk düşülür (45 değil)
    cal = CalendarDef(
        workdays=(0,),
        shifts=(ShiftDef(360, 840),),  # 480 dk
        breaks=(BreakDef(600, 15),),   # 10:00-10:15
        maintenance=(MaintenanceWindow(dt("2026-01-05 10:00"), 30),),  # 10:00-10:30
    )
    assert calendar_minutes(dt("2026-01-05 06:00"), dt("2026-01-05 14:00"), cal) == 450


def test_empty_calendar_is_zero():
    cal = CalendarDef((), (), (), ())
    assert calendar_minutes(dt("2026-01-05 06:00"), dt("2026-01-06 06:00"), cal) == 0.0
