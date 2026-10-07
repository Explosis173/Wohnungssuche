"""Notify step: morning digest at 8:00 plus instant pushes for top listings."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import Config
from .models import Listing
from .ntfy import NtfyClient, PushMessage
from .store import Store

log = logging.getLogger(__name__)

# Runs before this hour never send the digest (protects against odd manual runs at night).
EARLIEST_DIGEST_HOUR = 5
DESCRIPTION_PREVIEW_CHARS = 280
# ntfy rejects scheduled deliveries less than 10 s ahead.
MIN_SCHEDULE_AHEAD = timedelta(minutes=1)
# After this many failed runs in a row a portal counts as broken and you get told.
BROKEN_AFTER_FAILURES = 3

RATING_EMOJI = {"Top": "🔥", "Gut": "✅", "Okay": "🙂", "Mäßig": "😐"}
SOURCE_LABEL = {"wg-gesucht": "WG-Gesucht", "kleinanzeigen": "Kleinanzeigen"}


def notify(store: Store, client: NtfyClient, config: Config, now: datetime, dashboard_url: str) -> int:
    """Sends due notifications. Returns the number of pushes sent."""
    settings = config.notifications
    local_now = now.astimezone(ZoneInfo(settings.timezone))
    today = local_now.date().isoformat()
    pending = sorted(
        (l for l in store.listings.values() if l.active and not l.notified_at and not l.duplicate_of),
        key=lambda l: -l.score,
    )

    digest_due = store.state.last_digest_date != today and local_now.hour >= EARLIEST_DIGEST_HOUR
    if digest_due:
        digest_at = local_now.replace(hour=settings.digest_hour, minute=0, second=0, microsecond=0)
        # ntfy holds scheduled messages until then; if 8:00 already passed, send right away.
        deliver_at = digest_at if digest_at - local_now >= MIN_SCHEDULE_AHEAD else None
        messages = _digest(store, pending, config, dashboard_url, deliver_at)
        to_mark = pending
    else:
        top = [l for l in pending if settings.instant_push_min_score and l.score >= settings.instant_push_min_score]
        messages = [_listing_message(l, None, dashboard_url, instant=True) for l in top]
        to_mark = top

    alerts = _health_alerts(store, today, dashboard_url)
    messages += alerts
    for message in messages:
        client.send(message)

    if client.enabled:  # a dry run must not change what counts as "already sent"
        stamp = now.isoformat(timespec="seconds")
        for listing in to_mark:
            listing.notified_at = stamp
        if digest_due:
            store.state.last_digest_date = today
        if alerts:
            store.state.alerted_on = today
    log.info("sent %d push notifications", len(messages))
    return len(messages)


def _digest(
    store: Store, pending: list[Listing], config: Config, dashboard_url: str, deliver_at: datetime | None
) -> list[PushMessage]:
    settings = config.notifications
    shown = pending[: settings.max_listings_per_digest]
    active = sorted((l for l in store.listings.values() if l.active and not l.duplicate_of), key=lambda l: -l.score)

    if not shown:
        if not settings.send_empty_digest:
            return []
        best = f"\nBeste aktive: {active[0].score}/100 – {_short(active[0])}" if active else ""
        return [
            PushMessage(
                title="Heute keine neuen Wohnungen",
                message=f"{len(active)} Angebote aktuell im Ranking.{best}",
                priority=2,
                tags=["house"],
                click=dashboard_url,
                deliver_at=deliver_at,
            )
        ]

    # Notification centers show the newest first: deliver worst → best → summary,
    # so the summary ends up on top followed by #1, #2, …
    def at(offset: int) -> datetime | None:
        return deliver_at + timedelta(seconds=offset) if deliver_at else None

    messages = []
    for offset, (rank, listing) in enumerate(reversed(list(enumerate(shown, start=1)))):
        messages.append(_listing_message(listing, rank, dashboard_url, deliver_at=at(offset)))

    lines = [f"#{i} {RATING_EMOJI[l.rating]} {l.score}/100 – {_short(l)}" for i, l in enumerate(shown, start=1)]
    if len(pending) > len(shown):
        lines.append(f"+ {len(pending) - len(shown)} weitere in der App")
    count = len(pending)
    messages.append(
        PushMessage(
            title=f"🏠 {count} neue Wohnung{'en' if count != 1 else ''} in Regensburg",
            message="\n".join(lines),
            priority=4 if shown[0].rating == "Top" else 3,
            tags=["house"],
            click=dashboard_url,
            actions=[("Ranking öffnen", dashboard_url)],
            deliver_at=at(len(shown)),
        )
    )
    return messages


def _listing_message(
    listing: Listing, rank: int | None, dashboard_url: str, deliver_at: datetime | None = None, instant: bool = False
) -> PushMessage:
    emoji = RATING_EMOJI[listing.rating]
    prefix = "Neue Top-Wohnung · " if instant else (f"#{rank} · " if rank else "")
    warm = f"{listing.rent_warm:.0f} €{'*' if listing.rent_estimated else ''} warm" if listing.rent_warm else "Miete ?"
    area = _area(listing)
    title = f"{prefix}{emoji} {listing.score}/100 · {warm} · {area}"

    lines = [listing.title]
    where = listing.district or listing.address or "Regensburg"
    if listing.distance_km is not None:
        where += f" · {listing.distance_km:g} km zur Altstadt (~{listing.bike_minutes} min Rad)"
    lines.append(f"📍 {where}")
    facts = []
    if listing.rooms:
        facts.append(f"{listing.rooms:g} Zi.")
    if listing.available_from:
        facts.append(f"frei ab {_format_date(listing.available_from)}")
    facts.append(SOURCE_LABEL.get(listing.source, listing.source))
    lines.append("🗓 " + " · ".join(facts))
    if listing.parking:
        lines.append(f"🚗 {listing.parking}")
    pros = [p for p in listing.pros if p != listing.parking]
    cons = [c for c in listing.cons if c != listing.parking]
    if pros:
        lines.append("👍 " + ", ".join(pros[:4]))
    if cons:
        lines.append("⚠️ " + ", ".join(cons[:3]))
    if listing.ai_review and listing.ai_review.get("summary"):
        lines.append("🤖 " + str(listing.ai_review["summary"]))
    if listing.description:
        preview = " ".join(listing.description.split())
        if len(preview) > DESCRIPTION_PREVIEW_CHARS:
            preview = preview[:DESCRIPTION_PREVIEW_CHARS].rsplit(" ", 1)[0] + " …"
        lines.append("\n" + preview)

    return PushMessage(
        title=title,
        message="\n".join(lines),
        priority=5 if instant else (4 if listing.rating == "Top" else 3),
        tags=["fire"] if listing.rating == "Top" else ["house"],
        click=listing.url,
        attach=listing.images[0] if listing.images else None,
        actions=[("Anzeige öffnen", listing.url), ("Im Ranking", f"{dashboard_url}#/l/{listing.id}")],
        deliver_at=deliver_at,
    )


def _health_alerts(store: Store, today: str, dashboard_url: str) -> list[PushMessage]:
    broken = {
        name: health
        for name, health in store.state.health.items()
        if health.consecutive_failures >= BROKEN_AFTER_FAILURES
    }
    if not broken or store.state.alerted_on == today:
        return []
    details = "\n".join(
        f"• {SOURCE_LABEL.get(name, name)}: seit {h.consecutive_failures} Läufen keine Daten ({h.last_error})"
        for name, h in broken.items()
    )
    return [
        PushMessage(
            title="⚠️ Wohnungssuche: Aktion nötig",
            message=(
                f"{details}\n\nWahrscheinlich hat das Portal seine Seite geändert oder blockiert den Abruf. "
                "Gib Astra Bescheid: „Bitte Claude im Repo Wohnungssuche den Scraper reparieren lassen.“"
            ),
            priority=4,
            tags=["warning"],
            click=dashboard_url,
        )
    ]


def _short(listing: Listing) -> str:
    warm = f"{listing.rent_warm:.0f} €" if listing.rent_warm else "? €"
    return f"{warm}, {_area(listing)}, {listing.district or 'Regensburg'}"


def _area(listing: Listing) -> str:
    return f"{round(listing.area_m2)} m²" if listing.area_m2 else "? m²"


def _format_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d.%m.%Y")
    except ValueError:
        return value
