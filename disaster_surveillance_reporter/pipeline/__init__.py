"""Pipeline orchestration for disaster incident processing.

Nine-step sequential pipeline with lifecycle gating:
Fetch -> Source Pre-filter -> Correlate -> Active-Status Check -> Initial Classify ->
Supplementary Search -> AI Enrich -> Override Re-evaluation -> Store (upsert).
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import structlog

from disaster_surveillance_reporter.adapters import SourceAdapter
from disaster_surveillance_reporter.adapters.news import NewsSearcher
from disaster_surveillance_reporter.ai.classifier import ClassifierAgent
from disaster_surveillance_reporter.ai.extractor import ExtractorAgent
from disaster_surveillance_reporter.ai.provider import AIProvider
from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.storage.store import StorageBackend
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord, generate_source_fingerprint

logger = structlog.get_logger(__name__)


class Pipeline:
    def __init__(
        self,
        adapters: list[SourceAdapter],
        correlator: Correlator,
        classify_engine: ClassifyEngine,
        news_searcher: NewsSearcher,
        extractor: ExtractorAgent,
        classifier: ClassifierAgent,
        storage_backend: StorageBackend,
    ) -> None:
        self._adapters = adapters
        self._correlator = correlator
        self._classify_engine = classify_engine
        self._news_searcher = news_searcher
        self._extractor = extractor
        self._classifier = classifier
        self._storage_backend = storage_backend

    def run(self) -> list[IncidentBundle]:
        logger.info("pipeline_run_start", step="fetch")

        # Step 1: Fetch all primary sources
        try:
            raw_records = self._fetch_sources()
            logger.info("pipeline_fetch_done", record_count=len(raw_records))
        except Exception:
            logger.exception("pipeline_fetch_failed")
            raw_records = []

        # Step 2: Source pre-filter — discard seen records
        try:
            raw_records = self._pre_filter(raw_records)
            logger.info("pipeline_prefilter_done", record_count=len(raw_records))
        except Exception:
            logger.exception("pipeline_prefilter_failed")

        # Step 3: Correlate records into bundles
        try:
            bundles = self._correlate_records(raw_records)
            logger.info("pipeline_correlate_done", bundle_count=len(bundles))
        except Exception:
            logger.exception("pipeline_correlate_failed")
            bundles = []

        # Step 4: Active-status check — classify bundles as NEW/ACTIVE/STALE
        try:
            bundles = self._active_status_check(bundles)
            logger.info("pipeline_active_check_done", bundle_count=len(bundles))
        except Exception:
            logger.exception("pipeline_active_check_failed")

        # Step 5: Initial deterministic classification
        try:
            bundles = self._classify_initial(bundles)
            logger.info("pipeline_classify_done")
        except Exception:
            logger.exception("pipeline_classify_failed")

        # Step 6: Supplementary search for bundles needing context
        try:
            bundles = self._supplementary_search(bundles)
            logger.info("pipeline_supplementary_search_done")
        except Exception:
            logger.exception("pipeline_supplementary_search_failed")

        # Step 7: AI enrichment (extract -> re-classify -> classify)
        try:
            bundles = self._ai_enrich(bundles)
            logger.info("pipeline_ai_enrich_done")
        except Exception:
            logger.exception("pipeline_ai_enrich_failed")

        # Step 8: Override re-evaluation
        try:
            bundles = self._reclassify_overrides(bundles)
            logger.info("pipeline_override_reeval_done")
        except Exception:
            logger.exception("pipeline_override_reeval_failed")

        # Step 9: Store (upsert) complete bundles
        try:
            upsert_results = self._store_bundles(bundles)
            logger.info("pipeline_store_done", upsert_results=upsert_results)
        except Exception:
            logger.exception("pipeline_store_failed")

        logger.info("pipeline_run_complete", bundle_count=len(bundles))
        return bundles

    def _fetch_sources(self) -> list[RawRecord]:
        records: list[RawRecord] = []
        with httpx.Client() as client:
            for adapter in self._adapters:
                try:
                    for record in adapter.fetch(client):
                        records.append(record)
                except Exception:
                    logger.exception(
                        "pipeline_adapter_fetch_failed",
                        source=getattr(adapter, "source_name", "unknown"),
                    )
        return records

    def _pre_filter(self, records: list[RawRecord]) -> list[RawRecord]:
        """Discard records whose source_fingerprint already exists in storage."""
        raise NotImplementedError

    def _active_status_check(
        self, bundles: list[IncidentBundle],
    ) -> list[IncidentBundle]:
        """Classify bundles as NEW/ACTIVE/STALE. Remove STALE, merge fingerprints for ACTIVE."""
        raise NotImplementedError

    def _correlate_records(
        self, records: list[RawRecord],
    ) -> list[IncidentBundle]:
        if not records:
            return []
        return self._correlator.correlate(records)

    def _classify_initial(
        self, bundles: list[IncidentBundle],
    ) -> list[IncidentBundle]:
        return [self._classify_engine.classify(b) for b in bundles]

    def _supplementary_search(
        self, bundles: list[IncidentBundle],
    ) -> list[IncidentBundle]:
        for bundle in bundles:
            if self._should_supplementary_search(bundle):
                title = self._extract_title(bundle)
                query = self._build_search_query(
                    title, bundle.country, bundle.disaster_type,
                )
                try:
                    results = self._news_searcher.search(
                        query, region="wt-wt", timelimit="w", max_results=10,
                    )
                    bundle.records.extend(results)
                except Exception:
                    logger.exception(
                        "pipeline_news_search_failed",
                        incident_id=bundle.incident_id,
                    )
        return bundles

    def _ai_enrich(
        self, bundles: list[IncidentBundle],
    ) -> list[IncidentBundle]:
        if not bundles:
            return bundles

        relevant = [b for b in bundles if b.should_report]
        if not relevant:
            return bundles

        try:
            relevant = self._extractor.extract(relevant)
        except Exception:
            logger.exception("pipeline_extractor_failed")
            for b in relevant:
                if not b.ai_enriched:
                    b.enrichment_failed = True

        for bundle in relevant:
            try:
                self._classify_engine.classify(bundle)
            except Exception:
                logger.exception(
                    "pipeline_extract_reclassify_failed",
                    incident_id=bundle.incident_id,
                )

        try:
            relevant = self._classifier.enrich(relevant)
        except Exception:
            logger.exception("pipeline_classifier_failed")
            for b in relevant:
                if not b.ai_enriched:
                    b.enrichment_failed = True

        return bundles

    def _reclassify_overrides(
        self, bundles: list[IncidentBundle],
    ) -> list[IncidentBundle]:
        for b in bundles:
            if b.should_report:
                self._classify_engine.reevaluate_overrides(b)
        return bundles

    def _store_bundles(self, bundles: list[IncidentBundle]) -> dict[str, int]:
        """Upsert each bundle. Returns counts keyed by status."""
        raise NotImplementedError

    @staticmethod
    def _should_supplementary_search(bundle: IncidentBundle) -> bool:
        """DDG search gate: should_report AND (active OR missing_fields).

        Stale, fully-known incidents skip DDG search entirely.
        """
        raise NotImplementedError

    @staticmethod
    def _build_search_query(
        title: str,
        country: str | None,
        disaster_type: str | None,
    ) -> str:
        parts = [title]
        if country:
            parts.append(country)
        parts.append(disaster_type or "disaster emergency")
        parts.append("latest news")
        return " ".join(parts)

    @staticmethod
    def _extract_title(bundle: IncidentBundle) -> str:
        for record in bundle.records:
            title = record.raw_fields.get("title", "")
            if title:
                return title
        return "disaster incident"
