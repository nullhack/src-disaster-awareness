"""Date parsing via a Strategy registry (open/closed).

Date strings arrive in several formats across the source adapters and the
resolver/pipeline:

* ISO-8601 (WHO, DDG, resolver incident ids, most feeds) — sometimes a
  trailing ``Z``, sometimes date-only.
* RFC-2822 HTTP-date (GDACS ``fromdate``).
* Unix epoch, seconds or milliseconds (USGS ``time``).

Rather than scatter one parser per format across the codebase, this module
exposes a :class:`DateParser` that tries registered format strategies in
order and returns the first that parses. Adding a new format is a matter of
registering one more callable — no existing strategy is edited (Strategy
pattern, open/closed).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable

DateStrategy = Callable[[str], "date | None"]


class DateParser:
    """Pluggable date parser built on a registry of format strategies.

    Each strategy is a ``callable(text) -> date | None`` that returns
    ``None`` (or raises) when it cannot handle the input. Strategies are
    tried in registration order; the first non-``None`` result wins.
    """

    def __init__(self) -> None:
        self._strategies: list[DateStrategy] = []

    def register(self, strategy: DateStrategy) -> DateStrategy:
        """Register a strategy (also usable as a decorator). Returns it."""
        self._strategies.append(strategy)
        return strategy

    def parse_date(self, value: str | None) -> date | None:
        text = (value or "").strip()
        if not text:
            return None
        for strategy in self._strategies:
            try:
                parsed = strategy(text)
            except (ValueError, TypeError, OverflowError, OSError):
                continue
            if parsed is not None:
                return parsed
        return None


def _parse_iso(text: str) -> date | None:
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.fromisoformat(text[:10])
        except ValueError:
            return None
    return dt.date()


# Non-ISO strptime formats served by upstream feeds. HealthMap ships
# ``"%d %b %Y"`` (e.g. "27 Jun 2026"). New formats plug in here.
_STRPTIME_FORMATS: tuple[str, ...] = ("%d %b %Y",)


def _parse_strptime(text: str) -> date | None:
    for fmt in _STRPTIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_rfc2822(text: str) -> date | None:
    dt = parsedate_to_datetime(text)
    if dt is None:
        return None
    return dt.date()


def _parse_epoch(text: str) -> date | None:
    # USGS serves milliseconds; tolerate seconds-scale digits (and float
    # notation) too.
    try:
        epoch = float(text)
    except ValueError:
        return None
    if epoch > 1_000_000_000_000:  # 10^12 -> millisecond territory
        epoch /= 1000
    return datetime.fromtimestamp(epoch, tz=timezone.utc).date()


# Module-default parser: ISO first (the common case), then explicit strptime
# formats, then lenient RFC-2822, then numeric epoch. Each strategy only
# matches its own input shape, so ordering is tolerant.
default_parser = DateParser()
default_parser.register(_parse_iso)
default_parser.register(_parse_strptime)
default_parser.register(_parse_rfc2822)
default_parser.register(_parse_epoch)


def parse_date(value: str | None) -> date | None:
    """Parse a date string with the default :data:`default_parser`."""
    return default_parser.parse_date(value)
