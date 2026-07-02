from __future__ import annotations

import logging
import os
from datetime import date
from typing import Callable

from disaster_report.ai.base import AIDigester
from disaster_report.classification import (
    NON_EVENT_STATUSES,
    SEVERITY_NAMES,
    ClassifyContext,
    classify,
    derive_initial_severity,
    is_disease_type,
    pandemic_potential_level,
)
from disaster_report.config import Config
from disaster_report.countries import UNKNOWN_ISO2, country_iso2
from disaster_report.deriver import DeriveInput, derive_canonical_name, derive_search_keys
from disaster_report.news_filter import is_relevant
from disaster_report.resolver import IncidentResolver, ResolvedIncident
from disaster_report.sources._dates import parse_date
from disaster_report.sources.base import (
    PRIOR_DIGEST_SOURCE,
    NewsAdapter,
    RawArticle,
    RawIncident,
    SourceAdapter,
)
from disaster_report.store.base import IncidentRecord, IncidentStore, IncidentView

log = logging.getLogger(__name__)


def _news_timelimit(window_days: int) -> str:
    if window_days <= 1:
        return "d"
    if window_days <= 7:
        return "w"
    return "m"


def _parse_date(value: str) -> date:
    parsed = parse_date(value)
    if parsed is None:
        raise ValueError(f"unparseable report_date: {value!r}")
    return parsed


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


def _digest_payload(
    digest: dict,
    name: str,
    severity: str,
    keys: list[str],
    event_status: str,
) -> dict:
    """Build the set_digest body shared by the dedup-merge and new-row paths."""
    return {
        "canonical_name": name,
        "summary": digest.get("summary", ""),
        "severity": severity,
        "search_keys": keys,
        "pandemic_potential": digest.get("pandemic_potential"),
        "event_status": event_status,
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
            if incident.incident_id in known_ids:
                continue
            view = self._safe_ingest_new(incident, today)
            new_count += 1
            if not self._is_today(incident, today):
                continue
            enriched_count += 1
            if view is not None:
                newly_enriched.append(view)
        log.info(
            "ingested %d new incident(s) (%d AI-enriched as today's incidents)",
            new_count, enriched_count,
        )

        backfill_mode = bool(os.environ.get("DR_BACKFILL_NEWS"))
        if backfill_mode:
            log.info(
                "backfill mode active (DR_BACKFILL_NEWS set): _develop will also "
                "process incidents last_updated today"
            )
        to_develop = [
            incident for incident in active_snapshot
            if incident.should_report and incident.search_keys
            and (backfill_mode or incident.last_updated < today)
        ] + newly_enriched
        developed = 0
        for incident in to_develop:
            if self._develop(incident, today):
                developed += 1
        if developed:
            log.info("developed %d incident(s) with new news", developed)

        retried = self._retry_pending_digests(today)
        if retried:
            log.info("retried %d pending digest(s)", retried)

    def _is_today(self, resolved: ResolvedIncident, today: date) -> bool:
        return resolved.is_today(today)

    def _safe_ingest_new(self, incident: ResolvedIncident, today: date) -> IncidentView | None:
        try:
            return self._ingest_new(incident, today)
        except Exception as exc:
            log.exception(
                "incident %s: ingest failed; continuing with next incident",
                incident.incident_id,
            )
            return None

    def _safe_digest(self, incident_id: str, materials: dict) -> dict | None:
        try:
            return self._digester.digest(materials)
        except Exception as exc:
            log.warning(
                "incident %s: digest failed, leaving degraded for retry: %s",
                incident_id, exc,
            )
            return None

    def _bootstrap_news(
        self,
        incident_id: str,
        primary: RawIncident,
        report_day: date,
        window: int,
        disease: str | None,
    ) -> list[RawArticle]:
        """In-window news search + relevance filter for a fresh incident."""
        if country_iso2(primary.country) == UNKNOWN_ISO2:
            query = f"{report_day.isoformat()} {primary.disaster_type}"
        else:
            query = f"{report_day.isoformat()} {primary.disaster_type} {primary.country}"
        timelimit = _news_timelimit(window)
        log.info(
            "ingesting NEW incident %s (report_date=%s, in %d-day window); "
            "bootstrap query=%r timelimit=%r",
            incident_id, report_day, window, query, timelimit,
        )
        raw_articles = self._news.search(query, timelimit=timelimit)
        relevant = [
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
            incident_id, len(raw_articles), len(relevant),
        )
        return relevant

    def _ingest_new(
        self, resolved: ResolvedIncident, today: date
    ) -> IncidentView | None:
        primary = resolved.primary
        report_day = _parse_date(primary.report_date)
        window = self._config.tracking_window_days
        is_today = report_day == today
        in_window = 0 <= (today - report_day).days <= window
        adapter_disease = primary.raw_fields.get("disease")
        is_disease_track = is_disease_type(primary.disaster_type)

        if in_window:
            bootstrap_articles = self._bootstrap_news(
                resolved.incident_id, primary, report_day, window, adapter_disease,
            )
        else:
            bootstrap_articles = []
            log.info(
                "skipping incident %s (report_date=%s is outside %d-day window of today=%s); "
                "persisting without bootstrap news",
                resolved.incident_id, report_day, window, today,
            )

        # AI judge runs BEFORE persistence so its verdict can gate storage.
        # For disease incidents, pandemic_potential/event_status feed the single
        # classify call below; a non_event/elimination_declared verdict drops the
        # candidate news (incident row is kept, suppressed).
        digest: dict | None = None
        event_status = ""
        pandemic_potential: int | None = None
        materials = {
            "source_reports": [_raw_to_dict(raw) for raw in resolved.incidents],
            "news_articles": [_article_to_dict(a) for a in bootstrap_articles],
        }
        log.info("incident %s: requesting AI digest", resolved.incident_id)
        digest = self._safe_digest(resolved.incident_id, materials)
        if digest is not None:
            event_status = str(digest.get("event_status", "")).strip().lower()
            pandemic_potential = pandemic_potential_level(
                digest.get("pandemic_potential")
            )

        # The AI-authored disease label is AUTHORITATIVE (robust to brittle /
        # malformed source titles); fall back to the adapter's best-effort label
        # when no digest ran (non-today incidents) or the model omitted it.
        if digest is not None:
            disease = (digest.get("disease_name") or "").strip() or adapter_disease
        else:
            disease = adapter_disease

        severity_level = derive_initial_severity(resolved.incidents)
        # canonical_name + search_keys are DERIVED from structured facts (always
        # present, always date-anchored) - not AI-authored. AI supplies only the
        # classification (severity/pp/es/disease_name) and the prose summary.
        derived_ctx = DeriveInput(
            incident_type=primary.disaster_type,
            country=primary.country,
            event_date=report_day,
            disease=disease,
            place=str(primary.raw_fields.get("place", "") or ""),
        )
        derived_name = derive_canonical_name(derived_ctx)
        derived_keys = derive_search_keys(derived_ctx)
        if is_disease_track and digest and digest.get("severity"):
            severity_name = str(digest["severity"]).upper()
        else:
            severity_name = SEVERITY_NAMES.get(severity_level, "LOW")
        country_group, region = self._store.country_context(primary.country)
        population = max(
            (
                int(r.raw_fields.get("population", 0) or 0)
                for r in resolved.incidents
            ),
            default=0,
        )
        source_tiers = self._store.source_tiers(
            [r.source_name for r in resolved.incidents]
        )
        ctx = ClassifyContext(
            level=severity_level,
            country_group=country_group,
            region=region or "",
            disease=disease,
            incident_type=primary.disaster_type,
            population=population,
            source_tiers=source_tiers,
            pandemic_potential=pandemic_potential,
            event_status=event_status,
        )
        priority, should_report = classify(ctx)
        rejected = is_disease_track and event_status in NON_EVENT_STATUSES

        # Disease dedup: a recurring re-report of a recent (disease, country)
        # outbreak merges into the existing incident instead of spawning a new
        # row each day. Link the new source + news, refresh last_updated (a real
        # new source arrived), and re-digest so the survivor reflects the latest
        # signal. Noise (non_event) is never merged into a real outbreak.
        if is_disease_track and disease and not rejected:
            existing_key = self._store.find_recent_disease_incident(
                disease,
                primary.country,
                today,
                self._config.disease_dedup_window_days,
            )
            if existing_key is not None:
                for raw in resolved.incidents:
                    self._store.link_source_record(existing_key, raw)
                for article in bootstrap_articles:
                    self._store.link_news(existing_key, article)
                if is_today:
                    self._store.set_last_updated(existing_key, today.isoformat())
                if digest is not None:
                    self._store.set_digest(
                        existing_key,
                        _digest_payload(
                            digest, derived_name, severity_name, derived_keys, event_status,
                        ),
                        today,
                        primary.country,
                    )
                log.info(
                    "incident %s: merged into existing incident_key=%d (disease dedup)",
                    resolved.incident_id, existing_key,
                )
                return None

        record = IncidentRecord(
            incident_id=resolved.incident_id,
            canonical_name=derived_name,
            summary="",
            country=primary.country,
            incident_type=primary.disaster_type,
            priority=priority,
            severity_level=severity_level,
            event_date=report_day.isoformat(),
            first_reported_date=today.isoformat(),
            last_updated_date=today.isoformat(),
            should_report=should_report,
            search_keys=derived_keys,
            disease=disease,
        )
        incident_key = self._store.upsert_incident(record)
        for raw in resolved.incidents:
            self._store.link_source_record(incident_key, raw)

        if rejected:
            log.info(
                "incident %s: event_status=%s — dropping %d candidate news article(s); "
                "incident row kept (should_report=%s)",
                resolved.incident_id, event_status,
                len(bootstrap_articles), should_report,
            )
        else:
            for article in bootstrap_articles:
                self._store.link_news(incident_key, article)

        if digest is not None:
            log.info(
                "incident %s: digested canonical=%r severity=%s pp=%s es=%s keys=%s",
                resolved.incident_id, derived_name, severity_name,
                digest.get("pandemic_potential"), event_status, derived_keys,
            )
            self._store.set_digest(
                incident_key,
                _digest_payload(
                    digest, derived_name, severity_name, derived_keys, event_status,
                ),
                today,
                primary.country,
            )
        else:
            log.warning(
                "incident %s: digest unavailable; persisted degraded (pending retry)",
                resolved.incident_id,
            )
        return self._store.find_by_incident_id(resolved.incident_id)

    def _develop(
        self,
        incident: IncidentView,
        today: date,
    ) -> bool:
        window = self._config.tracking_window_days
        if incident.is_stale(today, window) or not incident.search_keys:
            return False

        timelimit = _news_timelimit(window)
        disease = self._store.find_disease_name(incident.incident_key)

        new_articles: list[RawArticle] = []
        for key in sorted(incident.search_keys, key=len, reverse=True):
            log.debug(
                "incident %s: dev-search key=%r timelimit=%r",
                incident.incident_id, key, timelimit,
            )
            key_articles: list[RawArticle] = []
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
                    key_articles.append(article)
            if key_articles:
                new_articles.extend(key_articles)
                break
            # this key returned no usable results -> fall through to next key

        if not new_articles:
            return False

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
                                "source_name": PRIOR_DIGEST_SOURCE,
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

    def _retry_pending_digests(self, today: date) -> int:
        window = self._config.tracking_window_days
        candidates = [
            incident for incident in self._store.get_active_incidents(as_of=today, within_days=window)
            if incident.ai_digest_date_key is None and incident.event_date == today
        ]
        if not candidates:
            return 0
        log.info("found %d pending digest(s) to retry", len(candidates))
        retried = 0
        for incident in candidates:
            materials = {
                "source_reports": self._store.get_source_records(incident.incident_key),
                "news_articles": self._store.get_incident_news_full(incident.incident_key),
            }
            digest = self._safe_digest(incident.incident_id, materials)
            if digest is None:
                continue
            self._store.set_digest(incident.incident_key, digest, today, incident.country_name)
            retried += 1
            log.info("incident %s: pending digest completed on retry", incident.incident_id)
        return retried
