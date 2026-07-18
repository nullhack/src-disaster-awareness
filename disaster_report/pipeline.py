
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, cast

from disaster_report._search_keys import derive_repoll_keys
from disaster_report.models import IncidentLog, NewsItem, SourceReport
from disaster_report.sources.errors import SourceFetchError
from disaster_report.store.content import ContentStore

logger = logging.getLogger(__name__)


def _mint_id() -> str:

    return uuid.uuid4().hex


@dataclass(frozen=True)
class IngestReport:

    source_reports_kept: int
    ai_calls: int
    ddg_calls: int


def _places_payload(report: SourceReport) -> list[dict[str, str]]:

    return [
        {
            "country_code": p.country_code,
            "subdivision": p.subdivision,
            "locality": p.locality,
        }
        for p in report.places
    ]


def _ddg_strict_loose(
    ddg_adapter: Any, strict: str, loose: str, news_timelimit: str
) -> list[NewsItem]:

    candidates: list[NewsItem] = []
    if strict:
        candidates.extend(ddg_adapter.search(query=strict, timelimit=news_timelimit))
    if not candidates and loose:
        candidates.extend(ddg_adapter.search(query=loose, timelimit=news_timelimit))
    return candidates


def _passes_gate(adapter: Any, report: SourceReport) -> bool:

    if not hasattr(adapter, "should_monitor"):
        return True
    return adapter.should_monitor(report)


def _commit_news_for_report(
    wh: ContentStore, report_id: str, selected_news: list[NewsItem]
) -> None:

    existing_report_incidents = wh.read_incident_ids_for_report(report_id)
    birthed_incident_id: str | None = (
        existing_report_incidents[0] if existing_report_incidents else None
    )
    for news in selected_news:
        news_id = wh.ingest_news_item(news)
        incident_id = wh.read_incident_for_news(news_id)
        if incident_id is None:
            if birthed_incident_id is None:
                birthed_incident_id = _mint_id()
            incident_id = birthed_incident_id
            wh.assign_news_to_incident(news_id, incident_id)
        elif birthed_incident_id is None:
            birthed_incident_id = incident_id
        wh.add_report_incident(report_id, incident_id)


def _commit_news_for_incident(
    wh: ContentStore, incident_id: str, selected_news: list[NewsItem]
) -> None:

    for news in selected_news:
        news_id = wh.ingest_news_item(news)
        if wh.read_incident_for_news(news_id) is None:
            wh.assign_news_to_incident(news_id, incident_id)


def _ingest_report(wh: ContentStore, report: SourceReport) -> str:

    return wh.ingest_source_report(report)


def _fetch_reports(adapter: Any) -> list[SourceReport]:

    try:
        return adapter.fetch()
    except SourceFetchError as exc:
        logger.warning("adapter %s: fetch failed: %s", type(adapter).__name__, exc)
        return []


def ingest_source_reports(adapters: object, warehouse: object) -> int:

    wh = cast(ContentStore, warehouse)
    existing_keys = wh.read_source_report_keys()
    kept = 0
    adapter_list = list(cast(Any, adapters))
    for ai, adapter in enumerate(adapter_list, 1):
        adapter_name = type(adapter).__name__
        logger.info("ingest: [%d/%d] fetching %s", ai, len(adapter_list), adapter_name)
        reports = _fetch_reports(adapter)
        logger.info("ingest: %s returned %d reports", adapter_name, len(reports))
        for ri, report in enumerate(reports, 1):
            key = f"{report.source}:{report.source_id}"
            if key in existing_keys:
                continue
            report_id = _ingest_report(wh, report)
            wh.ingest_report_places(report_id, report.places)
            existing_keys.add(key)
            kept += 1
            logger.info(
                "ingest: [%d/%d] stored %s:%s — %s",
                ri,
                len(reports),
                report.source,
                report.source_id,
                report.name,
            )
    logger.info("ingest: done, %d new reports stored", kept)
    return kept


def _search_one_report(
    wh: ContentStore,
    adapter: Any,
    report: SourceReport,
    ddg_adapter: Any,
    digest_fn: Any,
    searched_keys: set[str],
    source_id: str | None,
    news_timelimit: str,
    iso_now: str,
) -> None:

    key = f"{report.source}:{report.source_id}"
    forced = source_id is not None and report.source_id == source_id
    if not forced:
        if not _passes_gate(adapter, report):
            logger.info("search: skip %s:%s — gate (should_monitor=False)", report.source, report.source_id)
            return
        if key in searched_keys:
            logger.info("search: skip %s:%s — already searched", report.source, report.source_id)
            return
    else:
        logger.info("search: forced %s:%s", report.source, report.source_id)
    report_id = wh.ingest_source_report(report)
    strict, loose = adapter.derive_keys(report)
    logger.info("search: %s:%s — keys: strict=%r loose=%r", report.source, report.source_id, strict, loose)
    candidates = _ddg_strict_loose(ddg_adapter, strict, loose, news_timelimit)
    logger.info("search: %s:%s — %d DDG candidates", report.source, report.source_id, len(candidates))
    if candidates:
        result = digest_fn.filter(
            candidates,
            incident_type=report.incident_type,
            incident_name=report.name,
            incident_places=_places_payload(report),
            incident_date=report.report_date,
        )
        logger.info("search: %s:%s — %d relevant after filter", report.source, report.source_id, len(result.selected_news))
        if result.selected_news:
            _commit_news_for_report(wh, report_id, result.selected_news)
    wh.mark_report_searched(report.source, report.source_id, iso_now)
    searched_keys.add(key)


def _repoll_one_incident(
    wh: ContentStore,
    incident: Any,
    ddg_adapter: Any,
    digest_fn: Any,
    news_timelimit: str,
) -> None:

    genesis = wh.read_source_report_by_id(incident.genesis_report_id)
    if genesis is None:
        return
    logger.info("repoll: incident %s — %s", incident.incident_id, incident.name)
    seen_urls: set[str] = set()
    all_candidates: list[NewsItem] = []
    for repoll_key in derive_repoll_keys(genesis):
        for item in ddg_adapter.search(query=repoll_key, timelimit=news_timelimit):
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                all_candidates.append(item)
    if not all_candidates:
        logger.info("repoll: incident %s — no DDG candidates", incident.incident_id)
        return
    existing_urls = {n.url for n in wh.read_news(incident.incident_id)}
    fresh = [n for n in all_candidates if n.url not in existing_urls]
    logger.info("repoll: incident %s — %d candidates, %d fresh", incident.incident_id, len(all_candidates), len(fresh))
    if not fresh:
        return
    result = digest_fn.filter(
        fresh,
        incident_type=incident.incident_type,
        incident_name=incident.name,
        incident_places=_places_payload(genesis),
        incident_date=incident.first_seen_at,
    )
    logger.info("repoll: incident %s — %d relevant after filter", incident.incident_id, len(result.selected_news))
    if result.selected_news:
        _commit_news_for_incident(wh, incident.incident_id, result.selected_news)


def search_news(
    warehouse: object,
    adapters: object,
    ddg: object,
    digester: object,
    clock: object,
    news_timelimit: str = "w",
    source_id: str | None = None,
    active_window_days: int = 7,
) -> None:

    wh = cast(ContentStore, warehouse)
    ddg_adapter = cast(Any, ddg)
    digest_fn = cast(Any, digester)
    clock_fn = cast(Any, clock)
    iso_now = clock_fn().replace(microsecond=0).isoformat()
    cast(Any, wh)._clock = clock_fn
    adapter_list = list(cast(Any, adapters))
    if adapter_list:
        searched_keys = wh.read_searched_report_keys()
        all_reports = []
        for adapter in adapter_list:
            all_reports.extend((adapter, r) for r in _fetch_reports(adapter))
        total = len(all_reports)
        logger.info("search: per-report mode, %d reports, %d already searched", total, len(searched_keys))
        for i, (adapter, report) in enumerate(all_reports, 1):
            logger.info("search: [%d/%d] %s:%s", i, total, report.source, report.source_id)
            _search_one_report(
                wh,
                adapter,
                report,
                ddg_adapter,
                digest_fn,
                searched_keys,
                source_id,
                news_timelimit,
                iso_now,
            )
        logger.info("search: per-report mode done")
        return
    active = wh.active_incidents(active_window_days)
    total_active = len(active)
    logger.info("search: repoll mode, %d active incidents (window=%d days)", total_active, active_window_days)
    for i, incident in enumerate(active, 1):
        logger.info("search: [%d/%d] incident %s — %s", i, total_active, incident.incident_id, incident.name)
        _repoll_one_incident(wh, incident, ddg_adapter, digest_fn, news_timelimit)
    logger.info("search: repoll mode done")


def _generate_logs_for_incident(
    wh: ContentStore, digest_fn: Any, incident: Any, min_news_threshold: int
) -> None:

    already_linked = wh.read_summarized_news_ids(incident.incident_id)
    all_news = wh.read_news(incident.incident_id)
    unsummarized = [n for n in all_news if n.news_id not in already_linked]
    if len(unsummarized) < min_news_threshold:
        logger.info(
            "logs: incident %s — %s — %d unsummarized, below threshold %d, skip",
            incident.incident_id, incident.name, len(unsummarized), min_news_threshold,
        )
        return
    logger.info("logs: incident %s — %s — %d unsummarized of %d total", incident.incident_id, incident.name, len(unsummarized), len(all_news))
    prior = wh.read_timeline(incident.incident_id)
    genesis = wh.read_source_report_by_id(incident.genesis_report_id)
    places = _places_payload(genesis) if genesis is not None else []
    summary_result = digest_fn.summarize(
        unsummarized,
        prior,
        incident_type=incident.incident_type,
        incident_name=incident.name,
        incident_places=places,
        incident_date=incident.first_seen_at,
    )
    if not summary_result.has_relevant_updates:
        logger.info("logs: incident %s — no relevant updates, skip", incident.incident_id)
        return
    log_date = cast(Any, wh)._clock().date().isoformat()
    wh.append_timeline_with_provenance(
        IncidentLog(
            incident_id=incident.incident_id,
            log_date=log_date,
            summary=summary_result.summary,
        ),
        {n.news_id for n in unsummarized},
    )
    logger.info("logs: incident %s — wrote log for %s (%d news linked)", incident.incident_id, log_date, len(unsummarized))


def generate_logs(
    warehouse: object, digester: object, min_news_threshold: int = 3
) -> None:

    wh = cast(ContentStore, warehouse)
    digest_fn = cast(Any, digester)
    incidents = wh.read_incidents()
    total = len(incidents)
    logger.info("logs: %d incidents to process (threshold=%d)", total, min_news_threshold)
    for i, incident in enumerate(incidents, 1):
        logger.info("logs: [%d/%d] incident %s — %s", i, total, incident.incident_id, incident.name)
        _generate_logs_for_incident(wh, digest_fn, incident, min_news_threshold)
    logger.info("logs: done")


class _CountingDDG:
    def __init__(self, inner: Any) -> None:

        self._inner = inner
        self.calls = 0

    def search(self, query: str, timelimit: str | None = None) -> Any:

        self.calls += 1
        return self._inner.search(query=query, timelimit=timelimit)


class _CountingDigester:
    def __init__(self, inner: Any) -> None:

        self._inner = inner
        self.filter_calls = 0
        self.summarize_calls = 0

    def filter(self, candidate_news: list[NewsItem], **kwargs: Any) -> Any:

        self.filter_calls += 1
        return self._inner.filter(candidate_news, **kwargs)

    def summarize(
        self,
        selected_news: list[NewsItem],
        prior_summaries: list[IncidentLog],
        **kwargs: Any,
    ) -> Any:

        self.summarize_calls += 1
        return self._inner.summarize(selected_news, prior_summaries, **kwargs)


def run_pipeline(
    adapters: object,
    warehouse: object,
    ddg: object,
    digester: object,
    clock: object,
    min_news_threshold: int = 3,
) -> IngestReport:

    ddg_counter = _CountingDDG(ddg)
    digester_counter = _CountingDigester(digester)
    logger.info("pipeline: phase 1 — ingest records")
    source_reports_kept = ingest_source_reports(adapters, warehouse)
    logger.info("pipeline: phase 2a — search news (per-report)")
    search_news(warehouse, adapters, ddg_counter, digester_counter, clock)
    logger.info("pipeline: phase 2b — search news (repoll active)")
    search_news(warehouse, [], ddg_counter, digester_counter, clock)
    logger.info("pipeline: phase 3 — generate logs")
    generate_logs(warehouse, digester_counter, min_news_threshold)
    logger.info(
        "pipeline: done — reports=%d ai_calls=%d ddg_calls=%d",
        source_reports_kept,
        digester_counter.filter_calls + digester_counter.summarize_calls,
        ddg_counter.calls,
    )
    return IngestReport(
        source_reports_kept=source_reports_kept,
        ai_calls=digester_counter.filter_calls + digester_counter.summarize_calls,
        ddg_calls=ddg_counter.calls,
    )
