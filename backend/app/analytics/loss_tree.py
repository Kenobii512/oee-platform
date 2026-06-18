"""Kayıp ağacı çıkarımı — yalnız genel veriden (events + production + hat tanımı).

Referans mantık: simulator/src/accuracy.py::extract_loss_tree. 5 kategori (no-scrap);
görünür kanallar doğrudan, gizli kanallar (FILL/SPEED) çıkarımla kestirilir.

FIREWALL: bu fonksiyon `ground_truth` ALMAZ (imza düzeyinde). Gerçek yalnız doğrulama
testine girer (accuracy.py `compare`/`truth_loss_tree` deseni).

Dönem kapsamı (G4 MVP): from/to yalnız events'e uygulanır (çağıran `fetch_events(frm,to)`
ile filtreler); production tüm veri üzerinden alınır. Dönem-doğru production filtrelemesi
ayrı bir küçük görev (G4.1).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.analytics.nominal import inferred_nominal_per_order, nominal_full_pass
from app.models.contract import LineDefinition

# No-scrap modeli (G12): hurda kanalı yok → 5 kategori. Spec-dışı parça redo'ya gider.
VISIBLE = ("DOWNTIME", "MICROSTOP", "QUALITY_REDO")
INFERRED = ("FILL_LOSS", "SPEED_LOSS")
CATEGORIES = VISIBLE + INFERRED
# Her kategorinin doğal ekseni (dakika vs parça).
_MINUTES = {"DOWNTIME", "MICROSTOP", "SPEED_LOSS"}


@dataclass(frozen=True)
class LossEntry:
    minutes: float = 0.0  # zaman kaybı (DOWNTIME/MICROSTOP/SPEED_LOSS)
    parts: float = 0.0    # malzeme kaybı (FILL_LOSS/QUALITY_REDO)


@dataclass(frozen=True)
class LossTree:
    """Kategori -> LossEntry. Tüm CATEGORIES anahtarları daima bulunur."""

    entries: dict[str, LossEntry]

    def value(self, category: str) -> float:
        """Kategorinin doğal eksenindeki büyüklüğü (minutes ya da parts)."""
        e = self.entries.get(category, LossEntry())
        return e.minutes if category in _MINUTES else e.parts


def axis_of(category: str) -> str:
    return "minutes" if category in _MINUTES else "parts"


def kind_of(category: str) -> str:
    return "visible" if category in VISIBLE else "inferred"


def extract_loss_tree(
    events: list[dict], production: list[dict], line: LineDefinition
) -> LossTree:
    """Genel veriden kategori bazında kayıp ağacı. `ground_truth` ALMAZ (firewall)."""
    minutes = {c: 0.0 for c in CATEGORIES}
    parts = {c: 0.0 for c in CATEGORIES}

    # Görünür zaman kayıpları: süre events'te birebir.
    for e in events:
        et = e["event_type"]
        if et in ("DOWNTIME", "MICROSTOP"):
            minutes[et] += e["duration"]

    # Görünür malzeme kayıpları: production sayımları (no-scrap: yalnız redo'dan geçen
    # ayrık parça; hurda kanalı yok).
    parts["QUALITY_REDO"] = float(sum(p["redo_count"] for p in production))

    # Gizli kanal — doluluk: carrier_qty public değil. İş emri başına gözlenen en
    # büyük loaded_qty nominal kabul edilip eksiklikler toplanır (çıkarım).
    nominal = inferred_nominal_per_order(production)
    parts["FILL_LOSS"] = float(
        sum(max(0, nominal[p["order_id"]] - p["loaded_qty"]) for p in production)
    )

    # Gizli kanal — hız: fiili PROCESS toplamının nominal beklentiyi aşan kısmı.
    # Geçiş sayısı PROCESS olay sayısından türetilir (redo ek geçişleri dahil);
    # nominal hat tanımından gelir → yalnız hız sapması izole edilir.
    proc = [e for e in events if e["event_type"] == "PROCESS"]
    if line.tanks and proc:
        passes = len(proc) / len(line.tanks)
        nominal_total = passes * nominal_full_pass(line)
        actual_total = sum(e["duration"] for e in proc)
        minutes["SPEED_LOSS"] = max(0.0, actual_total - nominal_total)

    return LossTree({c: LossEntry(minutes[c], parts[c]) for c in CATEGORIES})
