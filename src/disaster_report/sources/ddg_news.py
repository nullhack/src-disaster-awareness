from __future__ import annotations

import logging
import threading
import time
from typing import Any

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from disaster_report.sources._dates import parse_date
from disaster_report.sources.base import RawArticle

log = logging.getLogger(__name__)

_DEFAULT_QUERY = "disaster"
_DEFAULT_MAX_RESULTS = 25
_DEFAULT_REGION = "wt-wt"
# DDG's yahoo_news engine intermittently swallows an internal IndexError during
# rapid successive calls and returns [] with a warning log (looks like an empty
# result). Retry with a short backoff so a transient failure does not silently
# starve an incident of news.
_DEFAULT_RETRY_ATTEMPTS = 2
_DEFAULT_RETRY_BACKOFF = 1.5
# Hard wall-clock cap on a single DDGS().news() call. The ddgs library's
# internal ThreadPoolExecutor calls shutdown(wait=True) on exit, which joins its
# worker threads; those workers use primp, whose own timeout is not reliably
# honoured when a connection stalls. A single stalled search can therefore block
# the whole pipeline indefinitely. We run the call on a daemon thread and
# abandon it past this deadline so ingest can never freeze on DuckDuckGo.
_DEFAULT_SEARCH_DEADLINE = 15.0


def _to_iso(s: str) -> str:
    parsed = parse_date(s)
    return parsed.isoformat() if parsed is not None else s


def _news_with_deadline(
    query: str,
    region: str,
    timelimit: str | None,
    max_results: int,
    deadline: float,
) -> tuple[list[dict[str, Any]], bool]:
    """Call ``DDGS().news(...)`` on a daemon thread with a hard deadline.

    Returns ``(results, hung)``. ``hung`` is True when the call did not finish
    in time; in that case ``results`` is ``[]`` and the worker is left running
    (daemon, so it will not block process exit). Caller should stop retrying on
    a hung result — DuckDuckGo is clearly stalled.
    """
    box: dict[str, Any] = {}

    def _call() -> None:
        try:
            box["results"] = DDGS().news(
                query=query,
                region=region,
                safesearch="on",
                timelimit=timelimit,
                max_results=max_results,
            )
        except BaseException as exc:  # noqa: BLE001 — surfaced to caller
            box["error"] = exc

    worker = threading.Thread(target=_call, daemon=True, name="ddg-news-guard")
    worker.start()
    worker.join(timeout=deadline)
    if worker.is_alive():
        log.warning(
            "DDG news search %r exceeded %.0fs deadline; abandoning "
            "(stalled worker left as daemon)", query, deadline,
        )
        return [], True
    if "error" in box:
        raise box["error"]
    return box.get("results") or [], False


class DdgNewsAdapter:
    source_name = "DuckDuckGo News"

    def __init__(
        self,
        query: str = _DEFAULT_QUERY,
        max_results: int = _DEFAULT_MAX_RESULTS,
        region: str = _DEFAULT_REGION,
        timelimit: str | None = None,
        retries: int = _DEFAULT_RETRY_ATTEMPTS,
        backoff: float = _DEFAULT_RETRY_BACKOFF,
        deadline: float = _DEFAULT_SEARCH_DEADLINE,
    ) -> None:
        self.query = query
        self.max_results = max_results
        self.region = region
        self.timelimit = timelimit
        self.retries = max(1, retries)
        self.backoff = backoff
        self.deadline = deadline

    def fetch(self) -> list[RawArticle]:
        return self.search(self.query, timelimit=self.timelimit)

    def search(self, query: str, timelimit: str | None = None) -> list[RawArticle]:
        results: list[dict[str, Any]] = []
        for attempt in range(self.retries):
            try:
                results, hung = _news_with_deadline(
                    query, self.region, timelimit, self.max_results, self.deadline,
                )
            except DDGSException:
                results, hung = [], False
            except Exception as exc:  # noqa: BLE001 — never let DDG kill ingest
                log.warning("DDG news search %r failed: %s", query, exc)
                results, hung = [], False
            if results:
                break
            if hung:
                # DuckDuckGo is stalled — retrying would just burn the deadline
                # again. Surface an empty result so the pipeline moves on.
                break
            if attempt < self.retries - 1:
                time.sleep(self.backoff)
        return self._build(results)

    def _build(self, results: list[dict]) -> list[RawArticle]:
        out: list[RawArticle] = []
        for result in results:
            out.append(
                RawArticle(
                    source_name=self.source_name,
                    headline=result.get("title", "") or "",
                    body=result.get("body", "") or "",
                    url=result.get("url", "") or "",
                    outlet=result.get("source", "") or "",
                    published_date=_to_iso(result.get("date", "") or ""),
                    image=result.get("image", "") or "",
                    raw_fields=result,
                )
            )
        return out
