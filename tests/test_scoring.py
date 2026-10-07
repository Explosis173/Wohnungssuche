from dataclasses import replace
from datetime import date

import pytest

from wohnungssuche.scoring import (
    PARKING_NONE,
    PARKING_OWN,
    PARKING_OWN_EXTRA,
    PARKING_PUBLIC,
    PARKING_UNKNOWN,
    classify_parking,
    ensure_warm_rent,
    exclusion_reason,
    score_listing,
)

TODAY = date(2026, 10, 7)


def test_central_spacious_cheap_flat_scores_top(config, make_listing):
    listing = make_listing(rent_warm=420, area_m2=42, rooms=2, features=["Tiefgaragenstellplatz"])
    score_listing(listing, config)
    assert listing.score >= 80
    assert listing.rating == "Top"
    assert "Sehr zentral" in listing.pros
    assert "Separates Schlafzimmer" in listing.pros


def test_far_and_small_flat_scores_low(config, make_listing):
    listing = make_listing(lat=48.97, lon=12.16, zip_code="93055", area_m2=21, rent_warm=595, description="")
    score_listing(listing, config)
    assert listing.score < 50
    assert "Eng – deine Möbel passen nur knapp" in listing.cons


def test_more_space_never_lowers_score(config, make_listing):
    scores = []
    for area in (22, 26, 30, 40, 60):
        listing = make_listing(area_m2=area)
        score_listing(listing, config)
        scores.append(listing.score)
    assert scores == sorted(scores)


def test_closer_to_centre_scores_higher(config, make_listing):
    near, far = make_listing(), make_listing(lat=49.045, lon=12.13)
    score_listing(near, config)
    score_listing(far, config)
    assert near.score > far.score
    assert far.distance_km > 3


def test_furnished_is_penalized_but_unfurnished_is_not(config, make_listing):
    furnished = make_listing(description="Vollmöbliert, sofort frei")
    unfurnished = make_listing(description="Unmöbliert, sofort frei")
    score_listing(furnished, config)
    score_listing(unfurnished, config)
    assert furnished.breakdown["penalty"] < 0
    assert unfurnished.breakdown["penalty"] == 0


def test_estimates_warm_rent_from_cold_rent(config, make_listing):
    listing = make_listing(rent_warm=None, rent_cold=400, area_m2=30)
    ensure_warm_rent(listing, config)
    assert listing.rent_warm == 490
    assert listing.rent_estimated


def test_uses_stated_utilities_before_estimating(config, make_listing):
    listing = make_listing(rent_warm=None, rent_cold=400, utilities=80)
    ensure_warm_rent(listing, config)
    assert listing.rent_warm == 480
    assert not listing.rent_estimated


def test_exclusions(config, make_listing):
    assert exclusion_reason(make_listing(), config, TODAY) is None
    assert "Warmmiete" in exclusion_reason(make_listing(rent_warm=640), config, TODAY)
    assert "m²" in exclusion_reason(make_listing(area_m2=15), config, TODAY)
    assert exclusion_reason(make_listing(title="Tauschwohnung Altstadt"), config, TODAY) == "Tauschwohnung"
    assert exclusion_reason(make_listing(kind="WG-Zimmer"), config, TODAY) == "WG-Zimmer"


def test_short_sublet_is_excluded_long_one_is_kept_with_penalty(config, make_listing):
    short = make_listing(available_from="2026-11-01", available_until="2027-02-01")
    long = make_listing(available_from="2026-11-01", available_until="2027-10-01")
    assert "Zwischenmiete" in exclusion_reason(short, config, TODAY)
    assert exclusion_reason(long, config, TODAY) is None
    score_listing(long, config)
    assert any(con.startswith("Befristet") for con in long.cons)


def test_ai_adjustment_is_capped(config, make_listing):
    base, boosted = make_listing(), make_listing(ai_review={"score_adjustment": 50})
    score_listing(base, config)
    score_listing(boosted, config)
    assert boosted.score - base.score <= 10


def test_comfortable_area_covers_furniture(config):
    # Bed, wardrobe, desk, couch, TV board and shelf plus kitchen/bath.
    assert 22 <= config.comfortable_area_m2 <= 28


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Ein Tiefgaragenstellplatz ist inklusive.", PARKING_OWN),
        ("Garage vorhanden", PARKING_OWN),
        ("Ein Stellplatz kann für 40 € dazugemietet werden.", PARKING_OWN_EXTRA),
        ("Separat kann zusätzlich ein Parkplatz in der Tiefgarage angemietet werden.", PARKING_OWN_EXTRA),
        ("Bewohnerparken möglich", PARKING_PUBLIC),
        ("Kein Stellplatz vorhanden, aber Bewohnerparken möglich.", PARKING_PUBLIC),
        ("Leider kein Parkplatz.", PARKING_NONE),
        ("Fahrradstellplatz im Hof, schöner Parkettboden", PARKING_UNKNOWN),
    ],
)
def test_parking_classification(make_listing, text, expected):
    assert classify_parking(make_listing(description=text)) == expected


def test_parking_weighs_heavily(config, make_listing):
    with_parking = make_listing(description="Mit Tiefgaragenstellplatz")
    without = make_listing(description="Helle Wohnung")
    score_listing(with_parking, config)
    score_listing(without, config)
    assert with_parking.score - without.score >= config.weights.parking - 1
    assert "Kein Parkplatz erwähnt" in without.cons


def test_require_parking_excludes(config, make_listing):
    strict = replace(config, search=replace(config.search, require_parking=True))
    assert exclusion_reason(make_listing(description="Kein Parkplatz"), strict, TODAY) == "Kein Parkplatz"
    assert exclusion_reason(make_listing(description="Mit Garage"), strict, TODAY) is None
