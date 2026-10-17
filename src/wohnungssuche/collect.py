"""Collect step: search all portals, fetch new listings, filter, score, store."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from .config import Config
from .geo import haversine_km
from .models import Listing, ListingStub
from .scoring import exclusion_reason, score_listing
from .sources import Source
from .store import Store

log = logging.getLogger(__name__)

# Listings missing from the search results are checked on the portal and deleted
# once the ad is gone. Without a clear answer they are deleted after this long.
DELETE_UNSEEN_AFTER = timedelta(days=7)
MAX_GONE_CHECKS_PER_SOURCE = 25
GONE_REASON = "Nicht mehr online"
FORGET_REJECTED_AFTER = timedelta(days=21)
# Two listings this close with the same rent/size are the same flat on two portals.
DUPLICATE_DISTANCE_KM = 0.2
MIN_FETCHES_FOR_HEALTH = 3


def collect(store: Store, sources: list[Source], config: Config, now: datetime) -> list[Listing]:
    """Returns the listings that are new in this run."""
    new_listings: list[Listing] = []
    for source in sources:
        new_listings.extend(_collect_source(store, source, config, now))

    # Re-check everything so rule and config changes also apply to stored listings.
    stamp = now.isoformat(timespec="seconds")
    for listing_id, listing in list(store.listings.items()):
        score_listing(listing, config)
        reason = exclusion_reason(listing, config, now.date())
        if reason:
            del store.listings[listing_id]
            new_listings = [l for l in new_listings if l.id != listing_id]
            _reject(store, listing_id, reason, stamp)
    _mark_duplicates(store, new_listings)
    _forget_old(store, now)
    return new_listings


def _collect_source(store: Store, source: Source, config: Config, now: datetime) -> list[Listing]:
    health = store.health(source.name)
    stamp = now.isoformat(timespec="seconds")
    try:
        stubs = source.search()
    except Exception as exc:  # noqa: BLE001 – one broken portal must not stop the others
        log.error("%s: search failed: %s", source.name, exc)
        health.consecutive_failures += 1
        health.last_error = f"{stamp}: {exc}"[:300]
        return []

    health.last_success = stamp
    health.last_count = len(stubs)
    log.info("%s: %d results", source.name, len(stubs))

    seen_ids = {stub.id for stub in stubs}
    missing = []
    for listing in store.listings.values():
        if listing.source != source.name:
            continue
        if listing.id in seen_ids:
            listing.last_seen = stamp
            listing.active = True
        else:
            missing.append(listing)
    _delete_gone(store, source, missing, now)

    new_listings: list[Listing] = []
    fetched = failed = 0
    for stub in stubs:
        if stub.id in store.listings or stub.id in store.state.rejected:
            continue
        reason = _prefilter(stub, config)
        if reason:
            _reject(store, stub.id, reason, stamp)
            continue
        if fetched >= config.sources.max_detail_fetches_per_source:
            log.info("%s: detail limit reached, rest follows next run", source.name)
            break
        fetched += 1
        try:
            listing = source.fetch(stub)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: could not load %s: %s", source.name, stub.url, exc)
            failed += 1
            health.last_error = f"{stamp}: {exc}"[:300]
            continue

        score_listing(listing, config)
        reason = exclusion_reason(listing, config, now.date())
        if reason:
            _reject(store, stub.id, reason, stamp)
            continue
        listing.first_seen = listing.last_seen = stamp
        store.listings[listing.id] = listing
        new_listings.append(listing)
        log.info("NEW %s %s – %d/100", listing.id, listing.title, listing.score)

    if fetched >= MIN_FETCHES_FOR_HEALTH and failed == fetched:
        # Search works but no detail page can be read: the layout probably changed.
        health.consecutive_failures += 1
    else:
        health.consecutive_failures = 0
    return new_listings


def _delete_gone(store: Store, source: Source, missing: list[Listing], now: datetime) -> None:
    """Deletes listings whose ad no longer exists on the portal.

    Not being in the search results is not enough (the ad may just have dropped
    off the result pages), so each one is checked on the portal itself.
    """
    stamp = now.isoformat(timespec="seconds")
    missing.sort(key=lambda l: l.last_seen)
    for i, listing in enumerate(missing):
        gone: bool | None = None
        if i < MAX_GONE_CHECKS_PER_SOURCE:
            try:
                gone = source.is_gone(listing)
            except Exception as exc:  # noqa: BLE001 – unknown, try again next run
                log.warning("%s: could not check %s: %s", source.name, listing.url, exc)
        unseen_for = now - datetime.fromisoformat(listing.last_seen)
        if gone or unseen_for > DELETE_UNSEEN_AFTER:
            del store.listings[listing.id]
            _reject(store, listing.id, GONE_REASON, stamp)
            log.info("DELETED %s %s (nicht mehr online)", listing.id, listing.title)
        elif gone is False:
            listing.active = True  # still online, only dropped off the result pages


def _prefilter(stub: ListingStub, config: Config) -> str | None:
    """Cheap checks on search-result data to avoid loading detail pages for nothing."""
    if stub.price is not None and stub.price > config.search.max_warm_rent:
        return f"Preis {stub.price:.0f} €"
    if stub.area_m2 is not None and stub.area_m2 < config.search.min_area_m2:
        return f"{stub.area_m2:g} m²"
    if stub.kind == "WG-Zimmer" and not config.search.include_wg_rooms:
        return "WG-Zimmer"
    return None


def _reject(store: Store, listing_id: str, reason: str, stamp: str) -> None:
    store.state.rejected[listing_id] = {"reason": reason, "seen": stamp}


def _mark_duplicates(store: Store, new_listings: list[Listing]) -> None:
    for listing in store.listings.values():
        if listing.duplicate_of and listing.duplicate_of not in store.listings:
            listing.duplicate_of = None  # the other copy was deleted, show this one
    for new in new_listings:
        for other in store.listings.values():
            if other.id == new.id or other.source == new.source or other.duplicate_of or not other.active:
                continue
            if _same_flat(new, other):
                new.duplicate_of = other.id
                break


def _same_flat(a: Listing, b: Listing) -> bool:
    if None in (a.lat, a.lon, b.lat, b.lon, a.rent_warm, b.rent_warm, a.area_m2, b.area_m2):
        return False
    return (
        abs(a.rent_warm - b.rent_warm) <= 30
        and abs(a.area_m2 - b.area_m2) <= 2
        and haversine_km(a.lat, a.lon, b.lat, b.lon) <= DUPLICATE_DISTANCE_KM
    )


def _forget_old(store: Store, now: datetime) -> None:
    for listing_id, entry in list(store.state.rejected.items()):
        if now - datetime.fromisoformat(entry["seen"]) > FORGET_REJECTED_AFTER:
            del store.state.rejected[listing_id]
