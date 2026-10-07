"""Rule-based rating (0–100) of a listing against the search criteria.

Runs without any AI or API costs. If an optional AI review exists, its
score adjustment is added on top.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .config import Config
from .geo import bike_minutes, district_for_zip, haversine_km, resolve_position
from .models import Listing
from .parsing import months_between

UNKNOWN_LOCATION_FACTOR = 0.4
UNKNOWN_SIZE_FACTOR = 0.4
FALLBACK_UTILITIES = 100.0
# Warm rent at or below this share of the maximum gets full price points.
CHEAP_SHARE = 0.7
# Price points left when the rent is exactly at the maximum.
PRICE_FACTOR_AT_MAX = 0.25
# m² above the comfortable minimum after which more space adds nothing.
SIZE_HEADROOM_M2 = 20.0
AI_ADJUSTMENT_LIMIT = 10

RATINGS = ((80, "Top"), (65, "Gut"), (50, "Okay"), (0, "Mäßig"))


@dataclass(frozen=True)
class Keyword:
    pattern: re.Pattern[str]
    points: float
    label: str


def _kw(pattern: str, points: float, label: str) -> Keyword:
    return Keyword(re.compile(pattern, re.IGNORECASE), points, label)


BONUS_KEYWORDS = (
    _kw(r"einbauküche|\bebk\b|küchenzeile|pantryküche|eigene küche|küche vorhanden", 3, "Einbauküche"),
    _kw(r"balkon|terrasse|loggia", 3, "Balkon/Terrasse"),
    _kw(r"keller(?!wohnung)|abstellraum", 1, "Keller/Abstellraum"),
    _kw(r"waschmaschine|waschküche", 1, "Waschmaschine möglich"),
    _kw(r"fahrradkeller|fahrradstellplatz|fahrradabstell", 1, "Fahrradstellplatz"),
    _kw(r"unbefristet", 1, "Unbefristet"),
)

# These are subtracted from the total, not only from the extras bucket.
PENALTY_KEYWORDS = (
    _kw(r"(?<!un)(?<!teil)(?<!nicht )möbliert", -3, "Möbliert – deine eigenen Möbel müssten woanders hin"),
    _kw(r"untermiete", -2, "Nur Untermiete"),
    _kw(r"wochenendheimfahrer|wochenendpendler", -8, "Nur für Wochenendheimfahrer"),
    _kw(r"nur (?:für |an )?(?:studentinnen|frauen|weibliche)", -6, "Mieterkreis eingeschränkt (Text prüfen)"),
    _kw(r"nur (?:für |an )?(?:studenten|studierende|azubis)", -3, "Nur für Studierende/Azubis"),
    _kw(r"ablöse", -1, "Ablöse verlangt"),
)

# Parking, checked in this order on the text with negations removed.
NO_PARKING = re.compile(
    r"kein(?:e[nr]?)? (?:eigene[nr]? )?(?:auto|pkw)?(?:stellpl(?:atz|ätze)|parkpl(?:atz|ätze)|parkmöglichkeit(?:en)?|garage)"
    r"|ohne (?:stellplatz|parkplatz|garage)|schlechte parkmöglichkeit(?:en)?|parken (?:ist )?(?:schwierig|schlecht|kaum)",
    re.IGNORECASE,
)
OWN_PARKING = re.compile(
    r"tiefgarage|\bgarage|carport|\bstellpl(?:atz|ätze)|(?:auto|pkw|kfz|außen)stellplatz"
    r"|eigene[rn]? parkplatz|parkplatz (?:inkl|inklusive|vorhanden|am haus|vor dem haus|im hof|gehört)",
    re.IGNORECASE,
)
PARKING_COSTS_EXTRA = re.compile(
    r"(?:stellplatz|parkplatz|garage|carport)[^.\n]{0,80}?"
    r"(?:\d+\s*(?:€|euro)|aufpreis|zusätzlich|extra|zzgl|separat|angemietet|anmiet|dazu ?(?:ge)?miet)"
    r"|(?:aufpreis|zusätzlich|separat|zzgl)[^.\n]{0,80}?(?:stellplatz|parkplatz|garage|carport)",
    re.IGNORECASE,
)
PUBLIC_PARKING = re.compile(
    r"bewohnerpark|anwohnerpark|gute parkmöglichkeit|parkmöglichkeit(?:en)? (?:vorhanden|in der nähe|vor dem haus|direkt|ausreichend)"
    r"|parkpl(?:atz|ätze) (?:in der|auf der|an der) straße|kostenlose[sn]? park|öffentliche parkpl|parkhaus",
    re.IGNORECASE,
)
PARKING_OWN = "Eigener Stellplatz"
PARKING_OWN_EXTRA = "Stellplatz (gegen Aufpreis)"
PARKING_PUBLIC = "Parken auf der Straße / Bewohnerparken"
PARKING_NONE = "Kein Parkplatz"
PARKING_UNKNOWN = "Kein Parkplatz erwähnt"
PARKING_FACTORS = {
    PARKING_OWN: 1.0,
    PARKING_OWN_EXTRA: 0.85,
    PARKING_PUBLIC: 0.45,
    PARKING_NONE: 0.0,
    PARKING_UNKNOWN: 0.0,
}

SWAP_PATTERN = re.compile(r"tausch|swap", re.IGNORECASE)  # checked on the title only


def ensure_warm_rent(listing: Listing, config: Config) -> None:
    """Fills rent_warm from the cold rent if the listing only states that."""
    if listing.rent_warm is not None or listing.rent_cold is None:
        return
    if listing.utilities is not None:
        listing.rent_warm = listing.rent_cold + listing.utilities
        return
    estimate = (
        listing.area_m2 * config.search.utilities_per_m2_estimate
        if listing.area_m2
        else FALLBACK_UTILITIES
    )
    listing.utilities = round(estimate)
    listing.rent_warm = round(listing.rent_cold + estimate)
    listing.rent_estimated = True


def exclusion_reason(listing: Listing, config: Config, today: date) -> str | None:
    """Hard filters. A listing with a reason is never shown or pushed."""
    search = config.search
    if listing.rent_warm is not None and listing.rent_warm > search.max_warm_rent:
        return f"Warmmiete {listing.rent_warm:.0f} € > {search.max_warm_rent:.0f} €"
    if listing.area_m2 is not None and listing.area_m2 < search.min_area_m2:
        return f"{listing.area_m2:g} m² < {search.min_area_m2:g} m²"
    if listing.is_swap or SWAP_PATTERN.search(listing.title):
        return "Tauschwohnung"
    if listing.kind == "WG-Zimmer" and not search.include_wg_rooms:
        return "WG-Zimmer"
    if search.require_parking and PARKING_FACTORS[classify_parking(listing)] == 0:
        return "Kein Parkplatz"
    if listing.available_until:
        start = max(today, date.fromisoformat(listing.available_from)) if _is_iso(listing.available_from) else today
        end = date.fromisoformat(listing.available_until)
        if months_between(start, end) < search.min_rental_months:
            return f"Zwischenmiete bis {end:%d.%m.%Y}"
    return None


def score_listing(listing: Listing, config: Config) -> None:
    """Computes score, rating, breakdown, pros and cons in place."""
    ensure_warm_rent(listing, config)
    pros: list[str] = []
    cons: list[str] = []
    w = config.weights

    location = _location_factor(listing, config, pros, cons)
    size = _size_factor(listing, config, pros, cons)
    price = _price_factor(listing, config, pros, cons)
    parking = _parking_factor(listing, pros, cons)
    extras, penalty = _keyword_points(listing, pros, cons)

    breakdown = {
        "location": round(location * w.location, 1),
        "size": round(size * w.size, 1),
        "price": round(price * w.price, 1),
        "parking": round(parking * w.parking, 1),
        "extras": round(extras * w.extras, 1),
        "penalty": penalty,
    }
    if listing.ai_review:
        adjustment = _clamp(float(listing.ai_review.get("score_adjustment", 0)), -AI_ADJUSTMENT_LIMIT, AI_ADJUSTMENT_LIMIT)
        breakdown["ai"] = adjustment

    listing.score = int(round(_clamp(sum(breakdown.values()), 0, 100)))
    listing.rating = next(label for threshold, label in RATINGS if listing.score >= threshold)
    listing.breakdown = breakdown
    listing.pros = pros
    listing.cons = cons
    if not listing.district:
        listing.district = district_for_zip(listing.zip_code)


def _location_factor(listing: Listing, config: Config, pros: list[str], cons: list[str]) -> float:
    loc = config.location
    position = resolve_position(listing.lat, listing.lon, listing.zip_code, (loc.center_lat, loc.center_lon))
    if position is None:
        cons.append("Lage unbekannt")
        listing.distance_km = listing.bike_minutes = None
        return UNKNOWN_LOCATION_FACTOR

    distance = haversine_km(*position, loc.center_lat, loc.center_lon)
    listing.distance_km = round(distance, 1)
    listing.bike_minutes = bike_minutes(distance)
    if distance <= 1.5:
        pros.append("Sehr zentral")
    elif distance > 3.5:
        cons.append(f"{distance:.1f} km bis zur Altstadt")
    if distance <= loc.ideal_km:
        return 1.0
    if distance >= loc.max_km:
        return 0.0
    return 1 - (distance - loc.ideal_km) / (loc.max_km - loc.ideal_km)


def _size_factor(listing: Listing, config: Config, pros: list[str], cons: list[str]) -> float:
    area = listing.area_m2
    if area is None:
        cons.append("Größe unbekannt")
        return UNKNOWN_SIZE_FACTOR

    minimum = config.search.min_area_m2
    comfortable = config.comfortable_area_m2
    if area < comfortable:
        cons.append("Eng – deine Möbel passen nur knapp")
        factor = 0.5 * max(0.0, area - minimum) / max(1.0, comfortable - minimum)
    else:
        factor = 0.5 + 0.5 * min(1.0, (area - comfortable) / SIZE_HEADROOM_M2)
        if area >= comfortable + 6:
            pros.append("Genug Platz für alle Möbel")

    if listing.rooms and listing.rooms >= 2:
        pros.append("Separates Schlafzimmer")
        factor = min(1.0, factor + 0.1)
    return factor


def _price_factor(listing: Listing, config: Config, pros: list[str], cons: list[str]) -> float:
    warm = listing.rent_warm
    maximum = config.search.max_warm_rent
    if warm is None:
        cons.append("Miete unklar")
        return 0.3
    if listing.rent_estimated:
        cons.append("Warmmiete geschätzt (nur Kaltmiete angegeben)")

    cheap = maximum * CHEAP_SHARE
    if warm <= cheap:
        pros.append("Günstig")
        return 1.0
    return 1 - (1 - PRICE_FACTOR_AT_MAX) * (warm - cheap) / (maximum - cheap)


def classify_parking(listing: Listing) -> str:
    text = _text(listing)
    without_negations = NO_PARKING.sub(" ", text)
    if OWN_PARKING.search(without_negations):
        return PARKING_OWN_EXTRA if PARKING_COSTS_EXTRA.search(without_negations) else PARKING_OWN
    if PUBLIC_PARKING.search(without_negations):
        return PARKING_PUBLIC
    return PARKING_NONE if NO_PARKING.search(text) else PARKING_UNKNOWN


def _parking_factor(listing: Listing, pros: list[str], cons: list[str]) -> float:
    listing.parking = classify_parking(listing)
    factor = PARKING_FACTORS[listing.parking]
    (pros if factor >= 0.85 else cons).append(listing.parking)
    return factor


def _text(listing: Listing) -> str:
    return " ".join([listing.title, listing.description, " ".join(listing.features)])


def _keyword_points(listing: Listing, pros: list[str], cons: list[str]) -> tuple[float, float]:
    text = _text(listing)
    bonus = 0.0
    for keyword in BONUS_KEYWORDS:
        if keyword.pattern.search(text):
            bonus += keyword.points
            pros.append(keyword.label)

    penalty = 0.0
    for keyword in PENALTY_KEYWORDS:
        if keyword.pattern.search(text):
            penalty += keyword.points
            cons.append(keyword.label)
    if listing.available_until:
        penalty -= 6
        cons.append(f"Befristet bis {date.fromisoformat(listing.available_until):%d.%m.%Y}")
    if not listing.images:
        penalty -= 1
        cons.append("Keine Fotos")

    # Extras bucket: neutral listing = half the points.
    extras = _clamp(0.5 + bonus / 10, 0, 1)
    return extras, penalty


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _is_iso(value: str | None) -> bool:
    return bool(value) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
