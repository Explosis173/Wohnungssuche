"""Exports the data the web app shows (web/public/data.json)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from .config import Config
from .store import Store

# Recently vanished listings stay visible (greyed out) for a while.
SHOW_INACTIVE_FOR = timedelta(days=7)


def export_web_data(store: Store, config: Config, now: datetime, out: Path) -> int:
    listings = [
        l for l in store.listings.values()
        if not l.duplicate_of
        and (l.active or (l.last_seen and now - datetime.fromisoformat(l.last_seen) <= SHOW_INACTIVE_FOR))
    ]
    listings.sort(key=lambda l: (not l.active, -l.score))
    data = {
        "generated_at": now.isoformat(timespec="seconds"),
        "criteria": {
            "max_warm_rent": config.search.max_warm_rent,
            "min_area_m2": config.search.min_area_m2,
            "comfortable_area_m2": config.comfortable_area_m2,
            "center_name": config.location.center_name,
            "center": [config.location.center_lat, config.location.center_lon],
            "furniture": [item.name for item in config.furniture],
            "weights": vars(config.weights),
        },
        "sources": {name: vars(h) for name, h in store.state.health.items()},
        "listings": [l.to_dict() for l in listings],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return len(listings)
