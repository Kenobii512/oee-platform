"""H8 — takvim-dakikası: hat takviminden gerçek çalışılabilir süre.

Utilization = çalışılan / takvim-zamanı. Takvim-zamanı = bir pencerede çalışma-günü
∩ vardiya − mola − planlı bakım. Vardiya-dışı (gece/hafta sonu) dışlanır; mola ve
bakım örtüşse bile bir kez düşülür (union). FIREWALL: `ground_truth` ALMAZ.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.analytics.oee import union_length
from app.config import CalendarDef


def _to_dt(v) -> datetime:
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v))


def calendar_minutes(frm, to, cal: CalendarDef) -> float:
    """[frm, to) içinde takvim (çalışılabilir) dakikalarının toplamı.

    Gün gün yürür; her çalışma günü her vardiyanın pencere ile kesişimini alır,
    o kesişime düşen mola + bakım aralıklarının BİRLEŞİMİNİ (çift sayım yok) çıkarır.
    """
    frm, to = _to_dt(frm), _to_dt(to)
    if to <= frm or not cal.shifts or not cal.workdays:
        return 0.0

    total = 0.0
    day = datetime(frm.year, frm.month, frm.day)
    while day <= to:
        if day.weekday() in cal.workdays:
            for sh in cal.shifts:
                seg_s = max(day + timedelta(minutes=sh.start_min), frm)
                seg_e = min(day + timedelta(minutes=sh.end_min), to)
                if seg_e <= seg_s:
                    continue
                seg_min = (seg_e - seg_s).total_seconds() / 60.0
                # Çalışılmayan aralıklar (mola + bakım) segmente kırpılır, union ile düşülür.
                nonwork: list[tuple[float, float]] = []
                for br in cal.breaks:
                    bs = day + timedelta(minutes=br.start_min)
                    be = bs + timedelta(minutes=br.duration_min)
                    nonwork.append((bs, be))
                for mw in cal.maintenance:
                    nonwork.append((mw.start, mw.start + timedelta(minutes=mw.duration_min)))
                clipped: list[tuple[float, float]] = []
                for ns, ne in nonwork:
                    cs, ce = max(ns, seg_s), min(ne, seg_e)
                    if ce > cs:
                        clipped.append((
                            (cs - seg_s).total_seconds() / 60.0,
                            (ce - seg_s).total_seconds() / 60.0,
                        ))
                total += seg_min - union_length(clipped)
        day += timedelta(days=1)
    return total
