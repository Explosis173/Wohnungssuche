"""Parser tests on trimmed-down copies of the real page markup (no personal data)."""

import json

import pytest

from wohnungssuche.http import BlockedError
from wohnungssuche.models import ListingStub
from wohnungssuche.sources import kleinanzeigen, wg_gesucht

WG_SEARCH = """
<html><head><title>1-Zimmer-Wohnung mieten in Regensburg</title></head><body>
<div class="wgg_card offer_list_item" data-id="14132785">
  <div class="card_image"><a href="/x"><img src="https://img.wg-gesucht.de/media/up/a.small.jpg"></a></div>
  <h2 class="truncate_title"><a href="/1-zimmer-wohnungen-in-Regensburg-Steinweg.14132785.html"> Schöne 1,5 Zimmer Wohnung </a></h2>
  <div class="col-xs-11"><span>1-Zimmer-Wohnung | Regensburg Steinweg | Am Pfaffensteiner Hang</span></div>
  <div class="row middle">
    <div class="col-xs-3"><b>550 €</b></div>
    <div class="col-xs-5">01.11.2026 - 01.07.2027</div>
    <div class="col-xs-3"><b>35 m²</b></div>
  </div>
</div>
<div class="wgg_card offer_list_item" data-id="2">
  <div class="card_image"><img src="https://www.wg-gesucht.de/img/placeholder/dummy_small.png"></div>
  <h2><a href="/2.html">2-Zimmer</a></h2>
  <div class="col-xs-11"><span>2-Zimmer-Wohnung | Regensburg Kumpfmühl-Ziegetsdorf-Neu... | X</span></div>
  <div class="row middle"><div><b>590 €</b></div><div><b>48 m²</b></div></div>
</div>
</body></html>
"""

WG_DETAIL = """
<html><body>
<script>var map = {"lat":49.030399,"lng":12.083213};</script>
<div class="key_fact_value">35m²</div><div class="key_fact_detail">Größe</div>
<div class="key_fact_value">550€</div><div class="key_fact_detail">Gesamtmiete</div>
<div class="row"><div class="col-xs-6"><span class="section_panel_detail">Miete:</span></div>
  <div class="col-xs-6"><span class="section_panel_value">450€</span></div></div>
<div class="row"><div class="col-xs-6"><span class="section_panel_detail">Nebenkosten:</span></div>
  <div class="col-xs-6"><span class="section_panel_value">100€</span></div></div>
<div class="row"><div class="col-xs-6"><span class="section_panel_detail">Kaution:</span></div>
  <div class="col-xs-6"><span class="section_panel_value">1350€</span></div></div>
<a><span class="section_panel_detail">Am Pfaffensteiner Hang<br>93059 Regensburg Steinweg 93059 Regensburg Steinweg</span></a>
<div class="row"><div class="col-xs-6"><span class="section_panel_detail">frei ab:</span></div>
  <div class="col-xs-6"><span class="section_panel_value">01.11.2026</span></div></div>
<div class="row"><div class="col-xs-6"><span class="section_panel_detail">frei bis:</span></div>
  <div class="col-xs-6"><span class="section_panel_value">01.07.2027</span></div></div>
<div class="utility_icons"><div class="text-center">Balkon</div><div class="text-center">Keller</div></div>
<div id="ad_description_text"><div id="freitext_0"><script>ad()</script><p>Helle Wohnung.<br>Mit Blick.</p></div></div>
<img src="https://img.wg-gesucht.de/media/up/2026/40/abc_room.large.jpg">
<img src="https://img.wg-gesucht.de/media/up/2026/40/abc_room.large.jpg">
<img src="https://img.wg-gesucht.de/media/up/2022/11/xyz_user_photo_1.large.jpeg">
</body></html>
"""

KA_SEARCH = """
<html><head><title>Mietwohnung in Regensburg - Bayern | kleinanzeigen.de</title></head><body>
<article data-adid="3533365123" data-href="/s-anzeige/zentral/3533365123-203-7656">
  <img src="https://img.kleinanzeigen.de/api/v1/prod-ads/images/50/abc?rule=$_2.AUTO">
  <span>93053 Regensburg</span>
  <h3><a href="/s-anzeige/zentral/3533365123-203-7656">Zentral gelegene Wohnung</a></h3>
  <p>Ruhige 57,5 m² Wohnung, 1-Zi. mit Blick …</p>
  <p>21,09 m² · 1 Zi.</p>
  <p>350 €</p>
</article>
<article data-adid="2" data-href="/s-anzeige/wg/2-203-7656">
  <span>93049 Regensburg</span><h3>Schönes WG-Zimmer (4er WG)</h3><p>14 m² · 1 Zi.</p><p>300 €</p>
</article>
</body></html>
"""

KA_DETAIL_CLASSIC = """
<html><head>
<meta property="og:latitude" content="49.0082863"><meta property="og:longitude" content="12.100566">
</head><body>
<h1 id="viewad-title">Zentral gelegene Wohnung</h1>
<h2 id="viewad-price">350 €</h2>
<span id="street-address">Galgenbergstraße 12,</span><span id="viewad-locality">93053 Bayern - Regensburg</span>
<ul>
<li class="addetailslist--detail">Wohnfläche<span class="addetailslist--detail--value">21,09 m²</span></li>
<li class="addetailslist--detail">Zimmer<span class="addetailslist--detail--value">1</span></li>
<li class="addetailslist--detail">Nebenkosten<span class="addetailslist--detail--value">120 €</span></li>
<li class="addetailslist--detail">Warmmiete<span class="addetailslist--detail--value">470 €</span></li>
<li class="addetailslist--detail">Tauschangebot<span class="addetailslist--detail--value">Kein Tausch</span></li>
</ul>
<ul class="checktaglist"><li class="checktag">Balkon</li><li class="checktag">Einbauküche</li></ul>
<p id="viewad-description-text">Zeile eins<br>Zeile zwei</p>
<div class="galleryimage-element"><img src="https://img.kleinanzeigen.de/api/v1/prod-ads/images/50/abc?rule=$_59.AUTO"></div>
</body></html>
"""


def _astro_detail() -> str:
    def plain(value):
        if isinstance(value, dict):
            return [0, {k: plain(v) for k, v in value.items()}]
        if isinstance(value, list):
            return [1, [plain(v) for v in value]]
        return [0, value]

    ad = {
        "id": "3533365123",
        "title": "Zentral gelegene Wohnung",
        "description": "Zeile eins<br />Zeile zwei",
        "price": {"amount": 350, "type": "FIXED"},
        "localizedAttributes": [
            {"localizedValue": "21,09 m²", "localizedName": "Wohnfläche"},
            {"localizedValue": "1", "localizedName": "Zimmer"},
        ],
        "groupedLocalizedAttributesForRightColumn": [
            {"localizedValue": "120 €", "localizedName": "Nebenkosten"},
            {"localizedValue": "470 €", "localizedName": "Warmmiete"},
        ],
        "tags": ["Balkon", "Einbauküche"],
        "locationSearchParameters": {
            "location": "93053 Bayern - Regensburg",
            "streetAndHouseNumber": "Galgenbergstraße 12",
            "latitude": 49.0082863,
            "longitude": 12.100566,
        },
        "imageDetails": {"imageList": [{"largeUrl": "https://img.kleinanzeigen.de/api/v1/prod-ads/images/50/abc?rule=$_57.AUTO"}]},
    }
    props = json.dumps({"adData": plain(ad)}).replace('"', "&quot;")
    return f'<html><body><astro-island component-url="/ContactButton.js" props="{props}"></astro-island></body></html>'


def test_wg_search_page():
    stubs = wg_gesucht.parse_search_page(WG_SEARCH)
    assert [s.id for s in stubs] == ["wg:14132785", "wg:2"]
    first, second = stubs
    assert first.price == 550 and first.area_m2 == 35
    assert first.kind == "1-Zimmer-Wohnung" and first.district == "Steinweg"
    assert first.url.startswith("https://www.wg-gesucht.de/")
    assert second.image is None
    assert second.rooms == 2 and second.kind == "Wohnung"


def test_wg_detail_page():
    stub = wg_gesucht.parse_search_page(WG_SEARCH)[0]
    listing = wg_gesucht.parse_detail_page(WG_DETAIL, stub)
    assert listing.rent_warm == 550 and listing.rent_cold == 450 and listing.utilities == 100
    assert listing.deposit == 1350
    assert listing.area_m2 == 35
    assert listing.zip_code == "93059"
    assert listing.address == "Am Pfaffensteiner Hang 93059 Regensburg Steinweg"
    assert listing.district == "Steinweg"
    assert (listing.lat, listing.lon) == (49.030399, 12.083213)
    assert listing.available_from == "2026-11-01" and listing.available_until == "2027-07-01"
    assert listing.features == ["Balkon", "Keller"]
    assert listing.images == ["https://img.wg-gesucht.de/media/up/2026/40/abc_room.large.jpg"]
    assert listing.description == "Helle Wohnung.\nMit Blick."


def test_wg_blocked_page_raises():
    with pytest.raises(BlockedError):
        wg_gesucht.parse_search_page("<html><head><title>Sicherheitsprüfung</title></head></html>")


def test_kleinanzeigen_search_page():
    stubs = kleinanzeigen.parse_search_page(KA_SEARCH)
    first, wg = stubs
    assert first.id == "ka:3533365123"
    assert first.area_m2 == 21.09 and first.rooms == 1 and first.price == 350
    assert first.zip_code == "93053"
    assert first.image.endswith("?rule=$_59.JPG")
    assert wg.kind == "WG-Zimmer"


@pytest.mark.parametrize("html", [KA_DETAIL_CLASSIC, _astro_detail()], ids=["classic", "astro"])
def test_kleinanzeigen_detail_layouts(html):
    stub = ListingStub(id="ka:3533365123", url="https://www.kleinanzeigen.de/s-anzeige/x", title="")
    listing = kleinanzeigen.parse_detail_page(html, stub)
    assert listing.title == "Zentral gelegene Wohnung"
    assert listing.rent_cold == 350 and listing.utilities == 120 and listing.rent_warm == 470
    assert listing.area_m2 == 21.09 and listing.rooms == 1
    assert listing.address == "Galgenbergstraße 12, 93053 Regensburg"
    assert listing.zip_code == "93053"
    assert listing.lat == pytest.approx(49.0082863)
    assert listing.features == ["Balkon", "Einbauküche"]
    assert listing.images == ["https://img.kleinanzeigen.de/api/v1/prod-ads/images/50/abc?rule=$_59.JPG"]
    assert listing.description == "Zeile eins\nZeile zwei"


def test_kleinanzeigen_unknown_layout_raises():
    stub = ListingStub(id="ka:1", url="x", title="t")
    with pytest.raises(ValueError):
        kleinanzeigen.parse_detail_page("<html><body>nichts</body></html>", stub)
