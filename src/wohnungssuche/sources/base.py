from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Config
from ..http import HttpClient
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
