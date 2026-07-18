
from __future__ import annotations

import logging
from typing import Any

import httpx
import trafilatura

from disaster_report.models import FetchedArticle

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (compatible; DisasterReportBot/1.0; +https://github.com/nullhack/src-disaster-awareness)"
)
_TIMEOUT = 10.0


def fetch_article(url: str, timeout: float = _TIMEOUT) -> FetchedArticle | None:
    try:
        resp = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("fetch: %s — http error: %s", url, exc)
        return None
    html = resp.text
    if not html:
        logger.warning("fetch: %s — empty body", url)
        return None
    try:
        meta = trafilatura.extract_metadata(html, default_url=url)
    except Exception as exc:
        logger.warning("fetch: %s — trafilatura error: %s", url, exc)
        return None
    if meta is None:
        logger.warning("fetch: %s — no metadata extracted", url)
        return None
    return _meta_to_article(url, meta)


def _meta_to_article(url: str, meta: Any) -> FetchedArticle:
    return FetchedArticle(
        url=url,
        title=getattr(meta, "title", "") or "",
        description=getattr(meta, "description", "") or "",
        body=getattr(meta, "text", "") or "",
        published_date=getattr(meta, "date", "") or "",
        author=getattr(meta, "author", "") or "",
        sitename=getattr(meta, "sitename", "") or "",
    )
