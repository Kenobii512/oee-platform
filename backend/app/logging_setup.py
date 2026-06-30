"""H9 — yapılandırılmış loglama kurulumu (stdlib; yeni bağımlılık yok).

Seviye `OEE_LOG_LEVEL` env'inden (varsayılan INFO). Uygulama logger'ı `oee` kökü altında;
alt logger'lar (`oee.request`, `oee.ingest`) seviyeyi miras alır. Root'u zorla yeniden
yapılandırmaz (test caplog handler'ını korur).
"""
from __future__ import annotations

import logging
import os

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def setup_logging() -> None:
    level_name = os.environ.get("OEE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.getLogger("oee").setLevel(level)
    # Yalnız hiç handler yoksa root'a bir tane ekle (mevcut handler'ları/caplog'u bozma).
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format=_FORMAT)
