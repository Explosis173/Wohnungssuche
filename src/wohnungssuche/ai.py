"""Optional AI review via Claude Code in GitHub Actions (runs on your Claude subscription).

`write_queue` exports listings that have no review yet, the workflow lets Claude
write data/ai_reviews.json, and `merge_reviews` folds that back into the listings.
Without the CLAUDE_CODE_OAUTH_TOKEN secret this simply never runs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .store import Store

log = logging.getLogger(__name__)

MAX_QUEUE = 15
REVIEW_FIELDS = ("summary", "furniture_fit", "red_flags", "score_adjustment")


def queue_path(store: Store) -> Path:
    return store.data_dir / "ai_queue.json"


def reviews_path(store: Store) -> Path:
    return store.data_dir / "ai_reviews.json"


def write_queue(store: Store) -> int:
    todo = [
        l for l in sorted(store.listings.values(), key=lambda l: -l.score)
        if l.active and not l.ai_review and not l.duplicate_of
    ][:MAX_QUEUE]
    payload = [
        {
            "id": l.id,
            "title": l.title,
            "rent_warm": l.rent_warm,
            "rent_estimated": l.rent_estimated,
            "area_m2": l.area_m2,
            "rooms": l.rooms,
            "district": l.district,
            "distance_km": l.distance_km,
            "available_from": l.available_from,
            "available_until": l.available_until,
            "features": l.features,
            "description": l.description[:3000],
        }
        for l in todo
    ]
    path = queue_path(store)
    if payload:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    elif path.exists():
        path.unlink()
    return len(payload)


def merge_reviews(store: Store) -> int:
    path = reviews_path(store)
    merged = 0
    if path.exists():
        try:
            reviews = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            log.warning("ignoring unreadable AI reviews: %s", exc)
            reviews = {}
        for listing_id, review in reviews.items():
            listing = store.listings.get(listing_id)
            if listing and isinstance(review, dict):
                listing.ai_review = {k: review[k] for k in REVIEW_FIELDS if k in review}
                merged += 1
        path.unlink()
    queue = queue_path(store)
    if queue.exists():
        queue.unlink()
    return merged
