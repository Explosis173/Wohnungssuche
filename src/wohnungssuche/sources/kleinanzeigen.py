"""Kleinanzeigen.de – Mietwohnungen in Regensburg (Angebote, keine Gesuche)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import BlockedError
from ..models import Listing, ListingStub
from ..parsing import clean, parse_number, parse_zip
from .base import Source

BASE_URL = "https://www.kleinanzeigen.de"
LOCATION_ID = 7636  # Regensburg
CATEGORY_ID = 203   # Mietwohnungen

_PRICE = re.compile(r"^\d[\d.]*\s*€")
_FACTS = re.compile(r"^\d[\d.,]*\s*(?:m²|Zi\.)")
_WG = re.compile(r"\bWG\b|WG-Zimmer|\d+er[- ]WG|Mitbewohner", re.IGNORECASE)
_IMAGE_RULE = re.compile(r"\?rule=\$_\d+\.\w+$")


class Kleinanzeigen(Source):
    name = "kleinanzeigen"

    def search(self) -> list[ListingStub]:
        stubs: list[ListingStub] = []
        for page in range(1, self.config.sources.kleinanzeigen_pages + 1):
            page_stubs = parse_search_page(self.http.get_html(self._search_url(page)))
            stubs.extend(page_stubs)
            if not page_stubs:
                break
        return stubs

    def fetch(self, stub: ListingStub) -> Listing:
        return parse_detail_page(self.http.get_html(stub.url), stub)

    def _search_url(self, page: int) -> str:
        # The list price on Kleinanzeigen is the cold rent, so this is a superset of
        # what we want; the warm rent is checked after loading the detail page.
        max_rent = int(self.config.search.max_warm_rent)
        page_part = f"seite:{page}/" if page > 1 else ""
        return (
            f"{BASE_URL}/s-wohnung-mieten/regensburg/anzeige:angebote/preis::{max_rent}/"
            f"{page_part}c{CATEGORY_ID}l{LOCATION_ID}"
        )


def parse_search_page(html: str) -> list[ListingStub]:
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select("article[data-adid][data-href]")
    if not articles and "kleinanzeigen" not in (soup.title.get_text().lower() if soup.title else ""):
        raise BlockedError("Kleinanzeigen returned an unexpected page (bot protection?)")

    stubs = []
    for article in articles:
        for svg in article.select("svg, script"):
            svg.decompose()
        strings = [clean(s) for s in article.stripped_strings]
        heading = article.select_one("h2, h3")
        title = clean(heading.get_text()) if heading else ""
        facts = next((s for s in strings if _FACTS.match(s)), "")
        price_text = next((s for s in strings if _PRICE.match(s)), None)
        location = next((s for s in strings if parse_zip(s)), None)
        image = article.select_one("img[src]")

        area, rooms = _parse_facts(facts)
        stubs.append(
            ListingStub(
                id=f"ka:{article['data-adid']}",
                url=urljoin(BASE_URL, article["data-href"]),
                title=title,
                price=parse_number(price_text),
                area_m2=area,
                rooms=rooms,
                kind=_kind(title, rooms),
                zip_code=parse_zip(location),
                image=_full_size_image(image["src"]) if image else None,
            )
        )
    return stubs


@dataclass
class _Detail:
    """Layout-independent content of a detail page."""

    attributes: dict[str, str] = field(default_factory=dict)  # "Warmmiete" -> "470 €"
    price: float | None = None
    title: str = ""
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    description: str = ""
    features: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)


def parse_detail_page(html: str, stub: ListingStub) -> Listing:
    soup = BeautifulSoup(html, "lxml")
    # Kleinanzeigen A/B-tests a new (Astro) detail page next to the classic one.
    detail = _parse_astro(soup) or _parse_classic(soup)
    attrs = detail.attributes
    if not attrs and not detail.description:
        raise ValueError("unknown Kleinanzeigen detail page layout")

    rent_cold = detail.price or stub.price
    utilities = parse_number(attrs.get("Nebenkosten"))
    rent_warm = parse_number(attrs.get("Warmmiete"))
    if rent_warm is None and rent_cold is not None and utilities is not None:
        rent_warm = rent_cold + utilities
    area = parse_number(attrs.get("Wohnfläche")) or stub.area_m2
    rooms = parse_number(attrs.get("Zimmer")) or stub.rooms
    title = stub.title or detail.title
    images = list(dict.fromkeys(detail.images)) or ([stub.image] if stub.image else [])

    return Listing(
        id=stub.id,
        source="kleinanzeigen",
        url=stub.url,
        title=title,
        kind=_kind(title, rooms),
        rent_warm=rent_warm,
        rent_cold=rent_cold,
        utilities=utilities,
        deposit=parse_number(attrs.get("Kaution / Genoss.-Anteile") or attrs.get("Kaution")),
        area_m2=area,
        rooms=rooms,
        address=detail.address,
        zip_code=parse_zip(detail.address) or stub.zip_code,
        lat=detail.lat,
        lon=detail.lon,
        available_from=attrs.get("Verfügbar ab"),
        is_swap=attrs.get("Tauschangebot", "").lower() == "tausch",
        description=detail.description,
        features=detail.features,
        images=images,
    )


def _parse_classic(soup: BeautifulSoup) -> _Detail:
    detail = _Detail()
    for item in soup.select(".addetailslist--detail"):
        value = item.select_one(".addetailslist--detail--value")
        if not value:
            continue
        value_text = clean(value.get_text())
        value.extract()
        detail.attributes[clean(item.get_text())] = value_text

    price_el = soup.select_one("#viewad-price")
    detail.price = parse_number(price_el.get_text()) if price_el else None
    title_el = soup.select_one("#viewad-title")
    detail.title = clean(title_el.get_text()) if title_el else ""
    street = soup.select_one("#street-address")
    locality = soup.select_one("#viewad-locality")
    detail.address = _clean_address(" ".join(el.get_text() for el in (street, locality) if el))
    detail.lat = _meta_float(soup, "og:latitude")
    detail.lon = _meta_float(soup, "og:longitude")
    description_el = soup.select_one("#viewad-description-text")
    detail.description = description_el.get_text("\n", strip=True) if description_el else ""
    detail.features = [clean(tag.get_text()) for tag in soup.select(".checktaglist .checktag")]
    for img in soup.select(".galleryimage-element img"):
        src = img.get("src") or img.get("data-imgsrc")
        if src:
            detail.images.append(_full_size_image(src))
    return detail


def _parse_astro(soup: BeautifulSoup) -> _Detail | None:
    ad = _astro_ad_data(soup)
    if ad is None:
        return None
    detail = _Detail()
    for group in ("localizedAttributes", "groupedLocalizedAttributesForRightColumn"):
        for attr in ad.get(group) or []:
            if isinstance(attr, dict) and attr.get("localizedName"):
                detail.attributes[clean(attr["localizedName"])] = clean(str(attr.get("localizedValue", "")))
    price = ad.get("price") or {}
    detail.price = float(price["amount"]) if isinstance(price, dict) and price.get("amount") is not None else None
    detail.title = clean(ad.get("title"))
    location = ad.get("locationSearchParameters") or {}
    detail.address = _clean_address(
        f"{location.get('streetAndHouseNumber') or ''}, {location.get('location') or ''}".strip(", ")
    )
    detail.lat = location.get("latitude")
    detail.lon = location.get("longitude")
    detail.description = _html_to_text(ad.get("description") or "")
    detail.features = [clean(tag) for tag in ad.get("tags") or [] if isinstance(tag, str)]
    for image in (ad.get("imageDetails") or {}).get("imageList") or []:
        url = image.get("largeUrl") or image.get("teaserUrl") or image.get("thumbnailUrl")
        if url:
            detail.images.append(_full_size_image(url))
    return detail


def _astro_ad_data(soup: BeautifulSoup) -> dict[str, Any] | None:
    """Finds the ad object in the serialized props of the page's Astro islands."""
    for island in soup.select("astro-island[props]"):
        if "localizedAttributes" not in island["props"]:
            continue
        try:
            props = _revive(json.loads(island["props"]))
        except (json.JSONDecodeError, TypeError):
            continue
        for candidate in (props.get("adData"), props.get("data")):
            if isinstance(candidate, dict) and "localizedAttributes" in candidate and "title" in candidate:
                return candidate
    return None


def _revive(value: Any) -> Any:
    """Astro serializes props as [type, value] pairs (0 = plain value, 1 = array)."""
    if isinstance(value, dict):
        return {k: _revive(v) for k, v in value.items()}
    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int):
        kind, inner = value
        if kind == 0:
            return _revive(inner) if isinstance(inner, dict) else inner
        if kind == 1:
            return [_revive(v) for v in inner]
        return inner
    return value


def _html_to_text(text: str) -> str:
    """The Astro page keeps the description as HTML ('Zeile<br />Zeile')."""
    with_breaks = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    plain = BeautifulSoup(with_breaks, "lxml").get_text()
    return "\n".join(line.strip() for line in plain.splitlines()).strip()


def _kind(title: str, rooms: float | None) -> str:
    if _WG.search(title):
        return "WG-Zimmer"
    return "1-Zimmer-Wohnung" if rooms == 1 else "Wohnung"


def _clean_address(text: str) -> str | None:
    return clean(text.replace("Bayern - ", "")) or None


def _parse_facts(text: str) -> tuple[float | None, float | None]:
    """'21,09 m² · 1 Zi.' -> (21.09, 1.0)"""
    area = rooms = None
    for part in text.split("·"):
        if "m²" in part:
            area = parse_number(part)
        elif "Zi" in part:
            rooms = parse_number(part)
    return area, rooms


def _full_size_image(url: str) -> str:
    return _IMAGE_RULE.sub("?rule=$_59.JPG", url)


def _meta_float(soup: BeautifulSoup, prop: str) -> float | None:
    meta = soup.select_one(f'meta[property="{prop}"]')
    try:
        return float(meta["content"]) if meta else None
    except (KeyError, ValueError):
        return None
