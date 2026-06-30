"""H7 — hat-tanımı (line YAML) doğrulayıcı.

Yeni bir hattın hatasız/hızlı modellenmesi için kurallı doğrulama: eyleme dönük hata
listesi üretir (boş = geçerli). Kurallar simülatör/platform varsayımlarıyla hizalı
(özellikle "tam 1 bottleneck" — bkz. simülatör line.py bottleneck guard).
"""
from __future__ import annotations


class LineValidationError(ValueError):
    """Geçersiz hat tanımı (hata listesiyle)."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def _is_positive_int(v) -> bool:
    try:
        return int(v) > 0
    except (TypeError, ValueError):
        return False


def validate_line_dict(raw: dict) -> list[str]:
    """Ham line dict'ini doğrular; eyleme dönük hata mesajları listesi döner (boş = geçerli)."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        return ["kök yapı bir nesne olmalı (line/tanks/orders)"]

    line = raw.get("line")
    if not isinstance(line, dict) or not line.get("id"):
        errors.append("line.id zorunlu")

    tanks = raw.get("tanks")
    if not isinstance(tanks, list) or not tanks:
        errors.append("tanks boş olamaz (en az bir tank gerekli)")
        tanks = []

    bottlenecks = 0
    for i, t in enumerate(tanks):
        if not isinstance(t, dict):
            errors.append(f"tanks[{i}] bir nesne olmalı")
            continue
        tid = t.get("id") or "?"
        if not t.get("id"):
            errors.append(f"tanks[{i}].id zorunlu")
        tmin, tmax = t.get("time_min"), t.get("time_max")
        if tmin is None:
            errors.append(f"tanks[{i}] ({tid}): time_min zorunlu")
        if tmax is None:
            errors.append(f"tanks[{i}] ({tid}): time_max zorunlu")
        if tmin is not None and tmax is not None:
            try:
                if float(tmin) > float(tmax):
                    errors.append(f"tanks[{i}] ({tid}): time_min ({tmin}) > time_max ({tmax})")
            except (TypeError, ValueError):
                errors.append(f"tanks[{i}] ({tid}): time_min/time_max sayısal olmalı")
        if not _is_positive_int(t.get("capacity", 1)):
            errors.append(f"tanks[{i}] ({tid}): capacity > 0 (tamsayı) olmalı")
        if t.get("bottleneck"):
            bottlenecks += 1

    if tanks and bottlenecks != 1:
        errors.append(f"tam 1 bottleneck tank gerekli ({bottlenecks} bulundu)")

    orders = raw.get("orders") or []
    for i, o in enumerate(orders):
        if not isinstance(o, dict):
            errors.append(f"orders[{i}] bir nesne olmalı")
            continue
        oid = o.get("order_id") or "?"
        if o.get("carrier_qty") is None:
            errors.append(f"orders[{i}] ({oid}): carrier_qty zorunlu (Quality paydası)")
        elif not _is_positive_int(o.get("carrier_qty")):
            errors.append(f"orders[{i}] ({oid}): carrier_qty > 0 (tamsayı) olmalı")

    return errors
