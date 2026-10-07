"""Domain model for a rental listing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any


@dataclass
class Listing:
    id: str                         # "<source>:<source id>", e.g. "wg:14215224"
    source: str                     # "wg-gesucht" | "kleinanzeigen"
    url: str
    title: str
    kind: str = "Wohnung"           # "1-Zimmer-Wohnung", "Wohnung", "WG-Zimmer"

    rent_warm: float | None = None
    rent_cold: float | None = None
    utilities: float | None = None
    rent_estimated: bool = False    # True if warm rent was estimated from cold rent
    deposit: float | None = None

    area_m2: float | None = None
    rooms: float | None = None

    address: str | None = None
    zip_code: str | None = None
    district: str | None = None
    lat: float | None = None
    lon: float | None = None

    available_from: str | None = None   # ISO date or free text
    available_until: str | None = None  # ISO date if the lease is temporary
    is_swap: bool = False               # "Tauschwohnung"

    description: str = ""
    features: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)

    # Filled by scoring
    score: int = 0
    rating: str = ""
    breakdown: dict[str, float] = field(default_factory=dict)
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    distance_km: float | None = None
    bike_minutes: int | None = None

    # Optional AI review (via Claude subscription)
    ai_review: dict[str, Any] | None = None

    # Lifecycle, filled by the store
    first_seen: str = ""
    last_seen: str = ""
    notified_at: str | None = None
    active: bool = True
    duplicate_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Listing":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass(frozen=True)
class ListingStub:
    """What a search results page tells us before fetching the detail page."""

    id: str
    url: str
    title: str
    price: float | None = None      # as shown in the list (warm on WG-Gesucht, cold on Kleinanzeigen)
    area_m2: float | None = None
    kind: str = "Wohnung"
    rooms: float | None = None
    district: str | None = None
    zip_code: str | None = None
    image: str | None = None
