"""WG-Gesucht.de – 1-Zimmer-Wohnungen and Wohnungen (optionally WG-Zimmer) in Regensburg."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import BlockedError
from ..models import Listing, ListingStub
from ..parsing import clean, parse_date, parse_number, parse_zip
from .base import Source

BASE_URL = "https://www.wg-gesucht.de"
CITY_ID = 111  # Regensburg
CARDS_PER_PAGE = 20
MAX_PAGES = 3

_IMAGE = re.compile(r"https://img\.wg-gesucht\.de/media/up/[^\"' ]+?\.large\.\w+")
_LAT = re.compile(r'"lat"\s*:\s*"?(-?\d+\.\d+)')
_LNG = re.compile(r'"lng"\s*:\s*"?(-?\d+\.\d+)')
_DISTRICT = re.compile(r"\d{5} Regensburg ([^\d].*)$")
_ROOMS = re.compile(r"(\d+(?:,\d)?)-Zimmer")


class WgGesucht(Source):
    name = "wg-gesucht"

    def search(self) -> list[ListingStub]:
        stubs: list[ListingStub] = []
        for page in range(MAX_PAGES):
            html = self.http.get_html(self._search_url(page))
            page_stubs = parse_search_page(html)
            stubs.extend(page_stubs)
            if len(page_stubs) < CARDS_PER_PAGE:
                break
        return stubs

    def fetch(self, stub: ListingStub) -> Listing:
        return parse_detail_page(self.http.get_html(stub.url), stub)

    def _search_url(self, page: int) -> str:
        if self.config.search.include_wg_rooms:
            slug, categories = "wg-zimmer-und-1-zimmer-wohnungen-und-wohnungen", "0+1+2"
        else:
            slug, categories = "1-zimmer-wohnungen-und-wohnungen", "1+2"
        max_rent = int(self.config.search.max_warm_rent)
        return f"{BASE_URL}/{slug}-in-Regensburg.{CITY_ID}.{categories}.1.{page}.html?rMax={max_rent}"


def parse_search_page(html: str) -> list[ListingStub]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(".wgg_card.offer_list_item[data-id]")
    title = soup.title.get_text() if soup.title else ""
    if not cards and "Regensburg" not in title:
        raise BlockedError("WG-Gesucht returned an unexpected page (captcha?)")

    stubs = []
    for card in cards:
        link = card.select_one("h2 a[href]")
        if not link:
            continue
        info = card.select_one(".col-xs-11 span")
        parts = [clean(p) for p in (info.get_text() if info else "").split("|")]
        kind_text = parts[0] if parts else ""
        district = clean(parts[1].replace("Regensburg", "").rstrip(".")) if len(parts) > 1 else None

        middle = card.select(".middle b")
        price = parse_number(middle[0].get_text()) if middle else None
        area = parse_number(middle[-1].get_text()) if len(middle) > 1 else None

        image = card.select_one(".card_image img")
        image_url = image.get("src") if image else None
        if image_url and "placeholder" in image_url:
            image_url = None

        stubs.append(
            ListingStub(
                id=f"wg:{card['data-id']}",
                url=urljoin(BASE_URL, link["href"]),
                title=clean(link.get_text()),
                price=price,
                area_m2=area,
                kind=_normalize_kind(kind_text),
                rooms=_rooms(kind_text),
                district=district or None,
                image=image_url,
            )
        )
    return stubs


def parse_detail_page(html: str, stub: ListingStub) -> Listing:
    soup = BeautifulSoup(html, "lxml")
    for script in soup.select("script, style"):
        script.decompose()

    panel = _panel_values(soup)
    key_facts = {
        clean(label.get_text()): clean(value.get_text())
        for label, value in zip(soup.select(".key_fact_detail"), soup.select(".key_fact_value"), strict=False)
    }

    if not key_facts and not panel:
        raise ValueError("unknown WG-Gesucht detail page layout")

    rent_warm = parse_number(key_facts.get("Gesamtmiete")) or stub.price
    rent_cold = parse_number(panel.get("Miete"))
    utilities = sum(
        v for v in (parse_number(panel.get("Nebenkosten")), parse_number(panel.get("Sonstige Kosten"))) if v
    ) or None

    address_el = next(
        (el for el in soup.select(".section_panel_detail") if parse_zip(el.get_text())), None
    )
    address = _dedupe_locality(clean(address_el.get_text(" "))) if address_el else None

    description = "\n\n".join(
        el.get_text("\n", strip=True) for el in soup.select("#ad_description_text [id^=freitext_]")
    )
    features = [clean(el.get_text(" ")) for el in soup.select(".utility_icons .text-center")]
    images = list(dict.fromkeys(m for m in _IMAGE.findall(html) if "user_photo" not in m))
    if not images and stub.image:
        images = [stub.image]

    lat = _LAT.search(html)
    lng = _LNG.search(html)
    available_from = parse_date(panel.get("frei ab"))
    available_until = parse_date(panel.get("frei bis"))

    return Listing(
        id=stub.id,
        source="wg-gesucht",
        url=stub.url,
        title=stub.title,
        kind=stub.kind,
        rent_warm=rent_warm,
        rent_cold=rent_cold,
        utilities=utilities,
        deposit=parse_number(panel.get("Kaution")),
        area_m2=parse_number(key_facts.get("Größe")) or stub.area_m2,
        rooms=stub.rooms,
        address=address,
        zip_code=parse_zip(address),
        district=_district(address) or stub.district,
        lat=float(lat.group(1)) if lat else None,
        lon=float(lng.group(1)) if lng else None,
        available_from=available_from.isoformat() if available_from else None,
        available_until=available_until.isoformat() if available_until else None,
        description=description,
        features=[f for f in features if f],
        images=images,
    )


def _panel_values(soup: BeautifulSoup) -> dict[str, str]:
    """Maps 'Miete:' -> '550€' style label/value rows of the detail page."""
    values: dict[str, str] = {}
    for label in soup.select(".section_panel_detail"):
        column = label.find_parent("div")
        sibling = column.find_next_sibling("div") if column else None
        value = sibling.select_one(".section_panel_value") if sibling else None
        if value:
            values[clean(label.get_text()).rstrip(":")] = clean(value.get_text())
    return values


def _dedupe_locality(address: str) -> str:
    """'Neupfarrplatz 6a 93047 Regensburg 93047 Regensburg' -> 'Neupfarrplatz 6a 93047 Regensburg'"""
    match = re.search(r"\d{5}", address)
    if not match:
        return address
    tail = address[match.start():]
    half = tail[: (len(tail) - 1) // 2]
    return address[: match.start()] + half if tail == f"{half} {half}" else address


def _district(address: str | None) -> str | None:
    """'Neuprüll 1 93051 Regensburg Kumpfmühl-Ziegetsdorf-Neuprüll' -> 'Kumpfmühl-Ziegetsdorf-Neuprüll'"""
    match = _DISTRICT.search(address or "")
    return match.group(1) if match else None


def _normalize_kind(text: str) -> str:
    if "WG" in text:
        return "WG-Zimmer"
    if text.startswith("1-Zimmer"):
        return "1-Zimmer-Wohnung"
    return "Wohnung"


def _rooms(text: str) -> float | None:
    match = _ROOMS.search(text)
    return parse_number(match.group(1)) if match else None
