from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Callable

from disaster_report.ai.base import AIDigester
from disaster_report.classification import classify
from disaster_report.config import Config
from disaster_report.countries import country_iso2
from disaster_report.news_filter import is_relevant
from disaster_report.resolver import IncidentResolver, ResolvedIncident
from disaster_report.sources.base import NewsAdapter, RawArticle, RawIncident, SourceAdapter
from disaster_report.store.base import IncidentRecord, IncidentStore, IncidentView

log = logging.getLogger(__name__)

_SEVERITY_LEVEL = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _news_timelimit(window_days: int) -> str:
    if window_days <= 1:
        return "d"
    if window_days <= 7:
        return "w"
    return "m"


def _parse_date(value: str) -> date:
    text = (value or "").strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return date.fromisoformat(text[:10])


def _raw_to_dict(raw: RawIncident) -> dict:
    return {
        "incident_name": raw.incident_name,
        "country": raw.country,
        "disaster_type": raw.disaster_type,
        "report_date": raw.report_date,
        "source_name": raw.source_name,
        "source_url": raw.source_url,
        "raw_fields": dict(raw.raw_fields),
    }


def _article_to_dict(article: RawArticle) -> dict:
    return {
        "headline": article.headline,
        "url": article.url,
        "body": article.body,
        "outlet": article.outlet,
        "published_date": article.published_date,
    }


class Pipeline:
    def __init__(
        self,
        *,
        sources: list[SourceAdapter],
        news: NewsAdapter,
        resolver: IncidentResolver,
        digester: AIDigester,
        store: IncidentStore,
        config: Config,
        clock: Callable[[], date],
    ) -> None:
        self._sources = sources
        self._news = news
        self._resolver = resolver
        self._digester = digester
        self._store = store
        self._config = config
        self._clock = clock

    def run(self) -> None:
        today = self._clock()
        window = self._config.tracking_window_days
        log.info("pipeline run for %s (tracking window=%d days)", today, window)

        raw_incidents: list[RawIncident] = []
        for source in self._sources:
            log.debug("fetching source %s", type(source).__name__)
            raw_incidents.extend(source.fetch())
        log.info(
            "fetched %d raw incident(s) from %d source(s)",
            len(raw_incidents), len(self._sources),
        )

        resolved = self._resolver.resolve(raw_incidents)
        log.info("resolved into %d unique incident(s)", len(resolved))

        active_snapshot = self._store.get_active_incidents(as_of=today, within_days=window)
        log.info("%d active incident(s) already tracked", len(active_snapshot))

        known_ids = set(self._store.all_incident_ids())
        new_count = 0
        enriched_count = 0
        newly_enriched: list[IncidentView] = []
        for incident in resolved:
            if incident.incident_id not in known_ids:
                view = self._ingest_new(incident, today)
                new_count += 1
                if self._is_today(incident, today):
                    enriched_count += 1
                    if view is not None:
                        newly_enriched.append(view)
        log.info(
            "ingested %d new incident(s) (%d AI-enriched as today's incidents)",
            new_count, enriched_count,
        )

        to_develop = [
            inc for inc in active_snapshot
            if inc.last_updated < today and inc.search_keys
        ] + newly_enriched
        developed = 0
        for incident in to_develop:
            if self._develop(incident, today):
                developed += 1
        if developed:
            log.info("developed %d incident(s) with new news", developed)

    def _is_today(self, resolved: ResolvedIncident, today: date) -> bool:
        primary = resolved.incidents[0]
        return _parse_date(primary.report_date) == today

    def _ingest_new(
        self, resolved: ResolvedIncident, today: date
    ) -> IncidentView | None:
        primary = resolved.incidents[0]
        report_day = _parse_date(primary.report_date)
        window = self._config.tracking_window_days
        is_today = report_day == today
        disease = primary.raw_fields.get("disease")

        if is_today:
            if country_iso2(primary.country) == "XX":
                query = f"{report_day.isoformat()} {primary.disaster_type}"
            else:
                query = f"{report_day.isoformat()} {primary.disaster_type} {primary.country}"
            timelimit = _news_timelimit(window)
            log.info(
                "ingesting NEW today incident %s (report_date=%s); bootstrap query=%r timelimit=%r",
                resolved.incident_id, report_day, query, timelimit,
            )
            raw_articles = self._news.search(query, timelimit=timelimit)
            bootstrap_articles = [
                a for a in raw_articles
                if is_relevant(
                    a,
                    disaster_type=primary.disaster_type,
                    country=primary.country,
                    incident_name=primary.incident_name,
                    disease=disease,
                )
            ]
            log.info(
                "incident %s: %d bootstrap article(s) returned, %d relevant after filter",
                resolved.incident_id, len(raw_articles), len(bootstrap_articles),
            )
            materials = {
                "source_reports": [_raw_to_dict(raw) for raw in resolved.incidents],
                "news_articles": [_article_to_dict(a) for a in bootstrap_articles],
            }
            log.info("incident %s: requesting AI digest", resolved.incident_id)
            digest = self._digester.digest(materials)
            canonical_name = digest.get("canonical_name") or primary.incident_name
            summary = digest.get("summary", "")
            severity = str(digest.get("severity", "LOW")).upper()
            search_keys = list(digest.get("search_keys", []))
            log.info(
                "incident %s: digested canonical=%r severity=%s keys=%s",
                resolved.incident_id, canonical_name, severity, search_keys,
            )
        else:
            log.info(
                "skipping incident %s (report_date=%s is not today=%s); persisting without AI/news",
                resolved.incident_id, report_day, today,
            )
            bootstrap_articles = []
            canonical_name = primary.incident_name
            summary = ""
            severity = "LOW"
            search_keys = []

        severity_level = _SEVERITY_LEVEL.get(severity, 1)
        priority, should_report = classify(severity_level, primary.country)
        record = IncidentRecord(
            incident_id=resolved.incident_id,
            canonical_name=canonical_name,
            summary=summary,
            country=primary.country,
            incident_type=primary.disaster_type,
            priority=priority,
            severity_level=severity_level,
            event_date=report_day.isoformat(),
            first_reported_date=today.isoformat(),
            last_updated_date=today.isoformat(),
            should_report=should_report,
            search_keys=search_keys,
            disease=disease,
        )
        incident_key = self._store.upsert_incident(record)
        if is_today:
            self._store.set_digest(
                incident_key,
                {
                    "canonical_name": canonical_name,
                    "summary": summary,
                    "severity": severity,
                    "search_keys": search_keys,
                },
                today,
                primary.country,
            )

        for article in bootstrap_articles:
            self._store.link_news(incident_key, article)
        for raw in resolved.incidents:
            self._store.link_source_record(incident_key, raw)
        if is_today:
            return self._store.find_by_incident_id(resolved.incident_id)
        return None

    def _develop(
        self,
        incident: IncidentView,
        today: date,
    ) -> bool:
        window = self._config.tracking_window_days
        if (today - incident.last_updated).days > window:
            return False
        if not incident.search_keys:
            return False

        timelimit = _news_timelimit(window)
        disease = self._store.find_disease_name(incident.incident_key)

        new_articles: list[RawArticle] = []
        for key in incident.search_keys:
            log.debug(
                "incident %s: dev-search key=%r timelimit=%r",
                incident.incident_id, key, timelimit,
            )
            for article in self._news.search(key, timelimit=timelimit):
                if not is_relevant(
                    article,
                    disaster_type=incident.incident_type,
                    country=incident.country_name,
                    incident_name=incident.canonical_name,
                    disease=disease,
                ):
                    continue
                if self._store.link_news(incident.incident_key, article):
                    new_articles.append(article)

        if not new_articles:
            return False

        self._store.set_last_updated(incident.incident_key, today.isoformat())
        log.info(
            "incident %s bumped with %d new article(s)",
            incident.incident_id, len(new_articles),
        )

        threshold = self._config.develop_re_digest_threshold
        if threshold > 0 and len(new_articles) >= threshold:
            log.info(
                "incident %s: re-digesting after %d new articles (threshold=%d)",
                incident.incident_id, len(new_articles), threshold,
            )
            try:
                digest = self._digester.digest(
                    {
                        "source_reports": [
                            {
                                "incident_name": incident.canonical_name,
                                "country": incident.country_name,
                                "disaster_type": incident.incident_type,
                                "report_date": "",
                                "source_name": "PRIOR_DIGEST",
                                "source_url": "",
                                "raw_fields": {"prior_summary": incident.summary},
                            }
                        ],
                        "news_articles": [_article_to_dict(a) for a in new_articles],
                    }
                )
                self._store.set_digest(
                    incident.incident_key, digest, today, incident.country_name
                )
                log.info("incident %s: re-digested", incident.incident_id)
            except RuntimeError as exc:
                log.warning("incident %s: re-digest failed: %s", incident.incident_id, exc)
        return True
