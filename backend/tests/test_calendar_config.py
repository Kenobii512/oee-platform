"""H8 — takvim ayrıştırma: line_default.yaml calendar bloğu -> CalendarDef."""
from app.config import _hhmm_to_min, load_calendar
from tests.conftest import LINE_CONFIG


def test_hhmm_to_min():
    assert _hhmm_to_min("06:00") == 360
    assert _hhmm_to_min("14:00") == 840
    assert _hhmm_to_min("00:00") == 0
    assert _hhmm_to_min("23:30") == 1410


def test_load_calendar_default():
    cal = load_calendar(LINE_CONFIG)
    assert cal.workdays == (0, 1, 2, 3, 4)  # Pzt–Cum, 0=Pazartesi
    assert len(cal.shifts) == 2
    assert (cal.shifts[0].start_min, cal.shifts[0].end_min) == (360, 840)  # 06:00–14:00
    assert (cal.shifts[1].start_min, cal.shifts[1].end_min) == (840, 1320)  # 14:00–22:00
    assert len(cal.breaks) == 2
    assert cal.breaks[0].start_min == 600 and cal.breaks[0].duration_min == 15  # 10:00 +15
    assert len(cal.maintenance) == 1
    assert cal.maintenance[0].duration_min == 120


def test_load_calendar_missing_blocks_empty(tmp_path):
    # calendar bloğu olmayan minimal line -> boş tuple'lar (geriye uyumlu)
    p = tmp_path / "line.yaml"
    p.write_text(
        "line: {id: L1}\ntanks: [{id: t, time_min: 1, time_max: 2, bottleneck: true}]\n",
        encoding="utf-8",
    )
    cal = load_calendar(p)
    assert cal.workdays == () and cal.shifts == () and cal.breaks == () and cal.maintenance == ()
