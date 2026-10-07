"""Loads config.yaml into typed settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "config.yaml"

# Kitchen, bath and hallway of a typical small flat, on top of the living room.
BASE_AREA_M2 = 8.0
# Free floor space needed around furniture (walking, opening doors/drawers).
CIRCULATION_FACTOR = 2.3


@dataclass(frozen=True)
class FurnitureItem:
    name: str
    width: float
    depth: float

    @property
    def footprint(self) -> float:
        return self.width * self.depth


@dataclass(frozen=True)
class SearchSettings:
    max_warm_rent: float = 600
    min_area_m2: float = 20
    min_rental_months: int = 6
    include_wg_rooms: bool = False
    require_parking: bool = False
    utilities_per_m2_estimate: float = 3.0


@dataclass(frozen=True)
class LocationSettings:
    center_name: str = "Altstadt"
    center_lat: float = 49.0187
    center_lon: float = 12.0966
    ideal_km: float = 1.0
    max_km: float = 6.0


@dataclass(frozen=True)
class Weights:
    location: float = 30
    size: float = 25
    price: float = 15
    parking: float = 20
    extras: float = 10


@dataclass(frozen=True)
class NotificationSettings:
    timezone: str = "Europe/Berlin"
    digest_hour: int = 8
    max_listings_per_digest: int = 10
    instant_push_min_score: int = 80
    send_empty_digest: bool = True


@dataclass(frozen=True)
class SourceSettings:
    wg_gesucht_enabled: bool = True
    kleinanzeigen_enabled: bool = True
    kleinanzeigen_pages: int = 2
    max_detail_fetches_per_source: int = 30


@dataclass(frozen=True)
class Config:
    search: SearchSettings = field(default_factory=SearchSettings)
    location: LocationSettings = field(default_factory=LocationSettings)
    furniture: tuple[FurnitureItem, ...] = ()
    weights: Weights = field(default_factory=Weights)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    sources: SourceSettings = field(default_factory=SourceSettings)

    @property
    def comfortable_area_m2(self) -> int:
        """Living space at which all furniture fits comfortably (incl. kitchen/bath)."""
        furniture = sum(item.footprint for item in self.furniture)
        return round(furniture * CIRCULATION_FACTOR + BASE_AREA_M2)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = raw.get("sources", {})
    return Config(
        search=SearchSettings(**raw.get("search", {})),
        location=LocationSettings(**raw.get("location", {})),
        furniture=tuple(FurnitureItem(**item) for item in raw.get("furniture", [])),
        weights=Weights(**raw.get("weights", {})),
        notifications=NotificationSettings(**raw.get("notifications", {})),
        sources=SourceSettings(
            wg_gesucht_enabled=sources.get("wg_gesucht", {}).get("enabled", True),
            kleinanzeigen_enabled=sources.get("kleinanzeigen", {}).get("enabled", True),
            kleinanzeigen_pages=sources.get("kleinanzeigen", {}).get("pages", 2),
            max_detail_fetches_per_source=sources.get("max_detail_fetches_per_source", 30),
        ),
    )
