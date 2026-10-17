from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Config
from ..http import HttpClient, Page
from ..models import Listing, ListingStub


class Source(ABC):
    """A listing portal. `search` reads result pages, `fetch` one detail page."""

    name: str

    def __init__(self, http: HttpClient, config: Config) -> None:
        self.http = http
        self.config = config

    @abstractmethod
    def search(self) -> list[ListingStub]: ...

    @abstractmethod
    def fetch(self, stub: ListingStub) -> Listing: ...

    def is_gone(self, listing: Listing) -> bool:
        """True if the ad was deleted or deactivated on the portal."""
        page = self.http.get_page(listing.url)
        return page.gone or self.shows_removed_ad(page)

    def shows_removed_ad(self, page: Page) -> bool:
        return False
