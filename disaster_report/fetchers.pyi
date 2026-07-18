import logging
import httpx

from disaster_report.models import FetchedArticle

logger: logging.Logger


def fetch_article(url: str, timeout: float = 10.0) -> FetchedArticle | None: ...
