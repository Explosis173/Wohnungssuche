"""Small helpers to turn German listing text into numbers and dates."""

from __future__ import annotations

import re
from datetime import date

_NUMBER = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")
_DATE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
_ZIP = re.compile(r"\b(9\d{4})\b")
_WHITESPACE = re.compile(r"\s+")


def parse_number(text: str | None) -> float | None:
    """'1.050 €' -> 1050.0, '21,09 m²' -> 21.09, '2,5 Zi.' -> 2.5"""
    if not text:
        return None
    match = _NUMBER.search(text.replace("\xa0", " "))
    if not match:
        return None
    return float(match.group(0).replace(".", "").replace(",", "."))


def parse_date(text: str | None) -> date | None:
    if not text:
        return None
    match = _DATE.search(text)
    if not match:
        return None
    day, month, year = (int(g) for g in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_zip(text: str | None) -> str | None:
    if not text:
        return None
    match = _ZIP.search(text)
    return match.group(1) if match else None


def clean(text: str | None) -> str:
    return _WHITESPACE.sub(" ", text or "").strip()


def months_between(start: date, end: date) -> float:
    return (end - start).days / 30.44
