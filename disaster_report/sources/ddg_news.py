
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException

from disaster_report.models import NewsItem

logger = logging.getLogger(__name__)

_REGION = "wt-wt"
_SAFESEARCH = "on"
_MAX_RESULTS = 25

_MIN_DELAY_SECONDS = 3.0
_MAX_RETRIES = 3
_INITIAL_BACKOFF = 10.0

_CRAWL_WINDOW_SECONDS = 120

_URL_DATE_RE_1 = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")
_URL_DATE_RE_2 = re.compile(r"/(\d{8})/")

_RELATIVE_RE = re.compile(
    r"(\d+)\s*(minute|hour|day|week|month|year)s?\s*ago", re.IGNORECASE
)

_UNIT_TO_DELTA = {
    "minute": "minutes",
    "hour": "hours",
    "day": "days",
    "week": "weeks",
    "month": "days",
    "year": "days",
}
_MONTH_DAYS = 30
_YEAR_DAYS = 365


class DuckDuckGoNewsAdapter:

    def __init__(self) -> None:
        self._last_call_time: float = 0.0

    def search(self, query: str, timelimit: str | None = None) -> list[NewsItem]:

        elapsed = time.monotonic() - self._last_call_time
        if elapsed < _MIN_DELAY_SECONDS:
            time.sleep(_MIN_DELAY_SECONDS - elapsed)

        backoff = _INITIAL_BACKOFF
        for attempt in range(_MAX_RETRIES + 1):
            try:
                self._last_call_time = time.monotonic()
                results = DDGS().news(
                    query=query,
                    region=_REGION,
                    safesearch=_SAFESEARCH,
                    timelimit=timelimit,
                    max_results=_MAX_RESULTS,
                )
                return [
                    item
                    for result in results
                    if (item := _to_news_item(result, timelimit)) is not None
                ]
            except (RatelimitException, TimeoutException) as exc:
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "ddg rate-limited (attempt %d/%d), backing off %.1fs: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        backoff,
                        exc,
                    )
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.warning(
                        "ddg rate-limited after %d retries, giving up: %s",
                        _MAX_RETRIES,
                        exc,
                    )
                    return []
            except DDGSException:
                return []
            except Exception as exc:
                logger.warning(
                    "ddg unexpected error (query=%s): %r", query[:60], exc
                )
                return []
        return []


def _normalize_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw)
        return dt.replace(microsecond=0).isoformat()
    except ValueError:
        pass
    m = _RELATIVE_RE.search(raw)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        if unit == "month":
            delta = timedelta(days=n * _MONTH_DAYS)
        elif unit == "year":
            delta = timedelta(days=n * _YEAR_DAYS)
        else:
            delta = timedelta(**{_UNIT_TO_DELTA[unit]: n})
        return (datetime.now(timezone.utc) - delta).replace(microsecond=0).isoformat()
    return ""


def _extract_url_date(url: str) -> str:
    m = _URL_DATE_RE_1.search(url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _URL_DATE_RE_2.search(url)
    if m:
        d = m.group(1)
        if d.startswith("20"):
            return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    return ""


def _is_crawl_timestamp(date_str: str) -> bool:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (
        abs((datetime.now(timezone.utc) - dt).total_seconds()) < _CRAWL_WINDOW_SECONDS
    )


_TIMELIMIT_DAYS: dict[str, int] = {
    "d": 1,
    "w": 7,
    "m": 30,
}


def _resolve_date(raw_date: str, url: str, timelimit: str | None = None) -> str:
    normalized = _normalize_date(raw_date)
    if normalized and not _is_crawl_timestamp(normalized) and _date_in_range(
        normalized, timelimit
    ):
        return normalized
    if normalized:
        logger.debug(
            "ddg date rejected (crawl ts or out of range): %s for %s",
            normalized,
            url[:60],
        )
    url_date = _extract_url_date(url)
    if url_date and _date_in_range(f"{url_date}T00:00:00+00:00", timelimit):
        return f"{url_date}T00:00:00+00:00"
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _date_in_range(date_str: str, timelimit: str | None) -> bool:
    if not date_str:
        return False
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if dt > now:
        return False
    if timelimit and timelimit in _TIMELIMIT_DAYS:
        max_age = timedelta(days=_TIMELIMIT_DAYS[timelimit])
        if (now - dt) > max_age:
            return False
    return True


def _to_news_item(result: Any, timelimit: str | None = None) -> NewsItem | None:
    record = result if isinstance(result, dict) else {}
    url = str(record.get("url") or "")
    if not url:
        return None
    published = _resolve_date(str(record.get("date") or ""), url, timelimit)
    return NewsItem(
        url=url,
        title=str(record.get("title") or ""),
        body=str(record.get("body") or ""),
        published_date=published,
        source=str(record.get("source") or ""),
        domain=_domain_of(url),
        image=str(record.get("image") or ""),
    )


def _domain_of(url: str) -> str:
    hostname = urlparse(url).hostname
    return hostname or ""
