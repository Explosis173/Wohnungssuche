"""JSON files in data/ are the database – committed to git by the workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import ROOT
from .models import Listing

DATA_DIR = ROOT / "data"


@dataclass
class SourceHealth:
    last_success: str | None = None
    last_error: str | None = None
    consecutive_failures: int = 0
    last_count: int = 0


@dataclass
class State:
    last_digest_date: str | None = None
    rejected: dict[str, dict[str, str]] = field(default_factory=dict)  # id -> {reason, seen}
    health: dict[str, SourceHealth] = field(default_factory=dict)
    alerted_on: str | None = None  # date of the last "something is broken" push


class Store:
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.listings: dict[str, Listing] = {}
        self.state = State()

    @property
    def listings_path(self) -> Path:
        return self.data_dir / "listings.json"

    @property
    def state_path(self) -> Path:
        return self.data_dir / "state.json"

    def load(self) -> "Store":
        if self.listings_path.exists():
            raw = json.loads(self.listings_path.read_text(encoding="utf-8"))
            self.listings = {item["id"]: Listing.from_dict(item) for item in raw}
        if self.state_path.exists():
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.state = State(
                last_digest_date=raw.get("last_digest_date"),
                rejected=raw.get("rejected", {}),
                health={k: SourceHealth(**v) for k, v in raw.get("health", {}).items()},
                alerted_on=raw.get("alerted_on"),
            )
        return self

    def save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        ordered = sorted(self.listings.values(), key=lambda l: (not l.active, -l.score, l.id))
        _write_json(self.listings_path, [l.to_dict() for l in ordered])
        _write_json(
            self.state_path,
            {
                "last_digest_date": self.state.last_digest_date,
                "alerted_on": self.state.alerted_on,
                "health": {k: vars(v) for k, v in sorted(self.state.health.items())},
                "rejected": dict(sorted(self.state.rejected.items())),
            },
        )

    def health(self, source: str) -> SourceHealth:
        return self.state.health.setdefault(source, SourceHealth())


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
