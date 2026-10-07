"""Polite HTTP client: browser-like headers, retries and a delay between requests."""

from __future__ import annotations

import logging
import random
import time

import requests

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)


class BlockedError(RuntimeError):
    """The site answered with a captcha / bot wall instead of content."""


class HttpClient:
    def __init__(self, min_delay: float = 1.5, max_delay: float = 3.5, retries: int = 3) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.6",
            }
        )
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._retries = retries
        self._last_request = 0.0

    def get_html(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self._retries + 1):
            self._wait()
            try:
                response = self._session.get(url, timeout=30)
            except requests.RequestException as exc:
                last_error = exc
                log.warning("GET %s failed (attempt %d): %s", url, attempt, exc)
                continue
            if response.status_code in (403, 429):
                raise BlockedError(f"{response.status_code} for {url}")
            if response.status_code >= 500:
                last_error = RuntimeError(f"{response.status_code} for {url}")
                log.warning("GET %s -> %d (attempt %d)", url, response.status_code, attempt)
                continue
            response.raise_for_status()
            return response.text
        raise RuntimeError(f"giving up on {url}: {last_error}")

    def _wait(self) -> None:
        delay = random.uniform(self._min_delay, self._max_delay)
        elapsed = time.monotonic() - self._last_request
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request = time.monotonic()
