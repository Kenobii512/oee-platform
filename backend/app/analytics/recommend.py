"""Kural tabanlı öneri motoru (G9) — TL'li kayıp ağacı üstüne.

Tasarım: MVP kural tabanlı. Tahmini kazanç MODÜLER bir GainEstimator Protokolü
arkasındadır; varsayılan oran-tabanlıdır (TL × config geri-kazanım oranı). İleride
simülatör destekli what-if aynı arayüze takılır. Abartılı kesinlik/garanti dili YOK;
her öneride varsayım açıkça yazılır.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from app.config import RecommendConfig


class GainEstimator(Protocol):
    """Bir kategori için tahmini TL kazancı. Modüler: sim what-if ileride buraya takılır."""

    def estimate(self, category: str, tl: float) -> float: ...


class RatioGainEstimator:
    """Varsayılan tahminci: kazanç = TL × kategori geri-kazanım oranı (config'ten)."""

    def __init__(self, config: RecommendConfig) -> None:
        self._config = config

    def _ratio(self, category: str) -> float:
        rule = self._config.rules.get(category)
        return rule.recovery_ratio if rule else self._config.default_recovery_ratio

    def estimate(self, category: str, tl: float) -> float:
        return tl * self._ratio(category)


def _top_reason_detail(events: list[dict], category: str) -> str:
    """DOWNTIME/MICROSTOP için en çok süreyi tüketen neden/istasyonu metne çevirir."""
    by_reason: dict[str, float] = defaultdict(float)
    by_station: dict[str, float] = defaultdict(float)
    for e in events:
        if e.get("event_type") != category:
            continue
        dur = float(e.get("duration") or 0.0)
        reason = e.get("reason_code")
        if reason:
            by_reason[reason] += dur
        station = e.get("station_id")
        if station:
            by_station[station] += dur
    # Dönen metin TAM yüklem öbeğidir; şablonlar "{detail}" sonrası ek yüklem KOYMAZ
    # (eski "{detail} yoğun" kalıbı "istasyonunda yoğun yoğun" üretiyordu).
    if by_reason:
        top = max(by_reason, key=by_reason.get)
        return f"`{top}` nedeninde yoğunlaşıyor (en yüksek süre payı)"
    if by_station:
        top = max(by_station, key=by_station.get)
        return f"`{top}` istasyonunda yoğunlaşıyor"
    return "için neden kaydı yetersiz (operatör giriş kapsamı düşük)"


def generate_recommendations(
    cost_tree: dict,
    events: list[dict],
    config: RecommendConfig,
    estimator: GainEstimator,
) -> list[dict]:
    """cost_tree'yi (TL azalan) alır, her kategori için config şablonunu doldurur.

    Dönen her öğe: {category, tl, estimated_gain_tl, estimated_gain_tl_low,
    estimated_gain_tl_high, recovery_ratio, title, action, assumption, axis, value, kind}.
    `estimated_gain_tl` nokta tahmin (üst/iyimser sınır); low/high config bant faktörleriyle
    bir ARALIK verir (abartılı kesinlik yerine). Liste TL azalan (cost_tree sırasını korur).
    """
    recs: list[dict] = []
    for entry in cost_tree["categories"]:
        cat = entry["category"]
        rule = config.rules.get(cat)
        if rule is None or entry["tl"] <= 0:
            continue
        ratio = rule.recovery_ratio
        detail = (
            _top_reason_detail(events, cat)
            if cat in ("DOWNTIME", "MICROSTOP")
            else ""
        )
        pct = f"{round(ratio * 100)}"
        gain = estimator.estimate(cat, entry["tl"])
        recs.append(
            {
                "category": cat,
                "axis": entry["axis"],
                "value": entry["value"],
                "kind": entry["kind"],
                "tl": entry["tl"],
                "estimated_gain_tl": gain,
                "estimated_gain_tl_low": gain * config.recovery_low_factor,
                "estimated_gain_tl_high": gain * config.recovery_high_factor,
                # H3: kayıp kaleminin veri-güveni (düşük ise öneride uyarı gösterilir).
                "low_confidence": bool(entry.get("low_confidence", False)),
                "recovery_ratio": ratio,
                "title": rule.title,
                "action": rule.action.format(detail=detail, pct=pct),
                "assumption": rule.assumption.format(detail=detail, pct=pct),
            }
        )
    return recs
