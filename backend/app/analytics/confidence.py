"""H3 — belirsizlik/güven + öz-teşhis.

Gizli kayıp çıkarımına (FILL_LOSS/SPEED_LOSS) sahada ground-truth OLMADAN güven
kazandırır: nokta değer yerine güven aralığı (low/high) + veri-yeterlilik skoru.
"Sessizce yanlış sayı" yerine "ne kadar emin" diyen şeffaf, varsayım-tabanlı katman
(aşırı mühendislik yok). FIREWALL: bu modül `ground_truth` ALMAZ.

Bant modeli (recommend.py `_low/_high` + config-faktör desenini aynalar):
- Tam yeterlilikte (sufficiency=1): [value×low_factor, value×high_factor].
- Yeterlilik düştükçe bant simetrik genişler: alt 0'a iner, üst büyür.
Çıkarım sistematik olarak eksik sayar → bant yukarı asimetrik (high_factor > 1).
"""
from __future__ import annotations

from typing import Protocol

from app.analytics.oee import availability_from_events
from app.config import ConfidenceConfig
from app.models.contract import LineDefinition

# Yeterlilik skoru doygunluk eşikleri (şeffaf sabit; gözlemlenebilir sinyaller).
_DENSITY_FULL = 200.0  # bu kadar olayda olay-yoğunluğu sinyali doygun
_SPAN_FULL_MIN = 240.0  # bu kadar dakika kapsamda süre sinyali doygun (~4 saat)
_PROD_FULL = 20.0  # bu kadar üretim satırında üretim-kapsamı sinyali doygun


def data_sufficiency(
    events: list[dict], production: list[dict], line: LineDefinition
) -> float:
    """0..1 veri-yeterlilik skoru: olay yoğunluğu + kapsanan süre + üretim kapsamı.

    Düşük skor → çıkarım/OEE güvenilmez ("düşük güven"). Gözlemlenebilir sinyallerden;
    `ground_truth` KULLANMAZ.
    """
    if not events or not production:
        return 0.0
    density = min(1.0, len(events) / _DENSITY_FULL)
    span_min = availability_from_events(events)[1]
    span_score = min(1.0, span_min / _SPAN_FULL_MIN)
    prod_score = min(1.0, len(production) / _PROD_FULL)
    return round((density + span_score + prod_score) / 3.0, 4)


def band(value: float, sufficiency: float, cfg: ConfidenceConfig) -> tuple[float, float]:
    """Nokta `value` etrafında güven aralığı (low ≤ value ≤ high).

    Tam yeterlilikte taban faktörler; yeterlilik düştükçe bant genişler (alt 0'a iner,
    üst büyür). low_factor ≤ 1 ≤ high_factor olduğundan value daima banttadır.
    """
    s = max(0.0, min(1.0, sufficiency))
    low = value * cfg.low_factor * s
    high = value * cfg.high_factor * (2.0 - s)
    return max(0.0, low), high


class BandEstimator(Protocol):
    """Bir çıkarım kanalı için güven aralığı. Modüler: ileride istatistiksel model takılır."""

    def band(self, value: float, sufficiency: float) -> tuple[float, float]: ...


class FactorBandEstimator:
    """Varsayılan tahminci: config faktörleri + yeterlilik genişlemesi (`band`)."""

    def __init__(self, cfg: ConfidenceConfig) -> None:
        self._cfg = cfg

    def band(self, value: float, sufficiency: float) -> tuple[float, float]:
        return band(value, sufficiency, self._cfg)
