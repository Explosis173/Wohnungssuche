from __future__ import annotations

from ..config import Config
from ..http import HttpClient
from .base import Source
from .kleinanzeigen import Kleinanzeigen
from .wg_gesucht import WgGesucht


def enabled_sources(http: HttpClient, config: Config) -> list[Source]:
    sources: list[Source] = []
    if config.sources.wg_gesucht_enabled:
        sources.append(WgGesucht(http, config))
    if config.sources.kleinanzeigen_enabled:
        sources.append(Kleinanzeigen(http, config))
    return sources


__all__ = ["Source", "WgGesucht", "Kleinanzeigen", "enabled_sources"]
