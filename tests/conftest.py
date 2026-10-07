from __future__ import annotations

from pathlib import Path

import pytest

from wohnungssuche.config import DEFAULT_CONFIG_PATH, Config, load_config
from wohnungssuche.models import Listing


@pytest.fixture
def config() -> Config:
    return load_config(DEFAULT_CONFIG_PATH)


@pytest.fixture
def make_listing():
    def factory(**overrides) -> Listing:
        defaults = dict(
            id="ka:1",
            source="kleinanzeigen",
            url="https://example.com/1",
            title="Schöne 1-Zimmer-Wohnung",
            kind="1-Zimmer-Wohnung",
            rent_warm=520.0,
            area_m2=32.0,
            rooms=1.0,
            zip_code="93047",
            lat=49.0190,
            lon=12.0970,
            description="Helle Wohnung mit Einbauküche und Balkon.",
            images=["https://example.com/1.jpg"],
        )
        defaults.update(overrides)
        return Listing(**defaults)

    return factory


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"
