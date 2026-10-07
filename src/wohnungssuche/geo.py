"""Distances and fallback coordinates for Regensburg."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

# Rough centroids of Regensburg postcodes, used when a listing has no coordinates.
ZIP_CENTROIDS: dict[str, tuple[float, float, str]] = {
    "93047": (49.0175, 12.0960, "Innenstadt / Altstadt"),
    "93049": (49.0150, 12.0620, "Westenviertel / Prüfening / Königswiesen"),
    "93051": (49.0035, 12.0820, "Kumpfmühl / Ziegetsdorf / Neuprüll"),
    "93053": (49.0010, 12.1060, "Galgenberg / Kasernenviertel / Uni"),
    "93055": (49.0120, 12.1330, "Ostenviertel / Burgweinting / Schwabelweis"),
    "93057": (49.0400, 12.1060, "Regensburg-Nord / Reinhausen / Sallern"),
    "93059": (49.0300, 12.0920, "Stadtamhof / Steinweg / Weichs"),
}

# Detour factor road vs. straight line, and average city cycling speed.
_ROUTE_FACTOR = 1.3
_BIKE_KMH = 15.0
# Coordinates farther than this from the centre are treated as geocoding errors.
_MAX_PLAUSIBLE_KM = 15.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def bike_minutes(distance_km: float) -> int:
    return max(1, round(distance_km * _ROUTE_FACTOR / _BIKE_KMH * 60))


def resolve_position(
    lat: float | None, lon: float | None, zip_code: str | None, center: tuple[float, float]
) -> tuple[float, float] | None:
    """Best known coordinates for a listing: its own, else its postcode centroid."""
    if lat is not None and lon is not None and haversine_km(lat, lon, *center) <= _MAX_PLAUSIBLE_KM:
        return lat, lon
    if zip_code in ZIP_CENTROIDS:
        zlat, zlon, _ = ZIP_CENTROIDS[zip_code]
        return zlat, zlon
    return None


def district_for_zip(zip_code: str | None) -> str | None:
    entry = ZIP_CENTROIDS.get(zip_code or "")
    return entry[2] if entry else None
