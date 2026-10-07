"""CLI used by the GitHub Actions workflow.

    python -m wohnungssuche collect     # portals durchsuchen, bewerten, speichern
    python -m wohnungssuche ai-queue    # Liste für die optionale KI-Bewertung schreiben
    python -m wohnungssuche notify      # Pushes verschicken (8:00-Digest / Sofort-Push)
    python -m wohnungssuche export      # Daten für die Web-App schreiben
    python -m wohnungssuche test-push   # Testnachricht aufs Handy
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from . import ai
from .collect import collect
from .config import ROOT, load_config
from .export import export_web_data
from .http import HttpClient
from .notify import notify
from .scoring import score_listing
from .ntfy import DEFAULT_SERVER, NtfyClient, PushMessage
from .sources import enabled_sources
from .store import Store

log = logging.getLogger("wohnungssuche")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="wohnungssuche")
    parser.add_argument(
        "command", choices=["collect", "ai-queue", "notify", "export", "test-push"]
    )
    parser.add_argument("--out", type=Path, default=ROOT / "web" / "public" / "data.json")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = load_config()
    store = Store().load()
    now = datetime.now(timezone.utc)
    client = NtfyClient(
        topic=os.environ.get("NTFY_TOPIC") or None,
        server=os.environ.get("NTFY_SERVER") or DEFAULT_SERVER,
        token=os.environ.get("NTFY_TOKEN") or None,
    )

    if args.command == "collect":
        new = collect(store, enabled_sources(HttpClient(), config), config, now)
        log.info("%d new listings", len(new))
        store.save()
    elif args.command == "ai-queue":
        log.info("%d listings queued for AI review", ai.write_queue(store))
    elif args.command == "notify":
        merged = ai.merge_reviews(store)
        if merged:
            log.info("merged %d AI reviews", merged)
            for listing in store.listings.values():
                score_listing(listing, config)
        notify(store, client, config, now, dashboard_url())
        store.save()
    elif args.command == "export":
        log.info("exported %d listings to %s", export_web_data(store, config, now, args.out), args.out)
    elif args.command == "test-push":
        client.send(
            PushMessage(
                title="✅ Wohnungssuche ist verbunden",
                message="Ab jetzt bekommst du jeden Morgen um 8:00 die neuen Wohnungen in Regensburg.",
                tags=["tada"],
                click=dashboard_url(),
            )
        )


def dashboard_url() -> str:
    explicit = os.environ.get("DASHBOARD_URL")
    if explicit:
        return explicit
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/"
    return "https://github.com/"


if __name__ == "__main__":
    main()
