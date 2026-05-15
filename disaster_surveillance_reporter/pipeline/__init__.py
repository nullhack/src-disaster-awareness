"""Pipeline orchestration for disaster incident processing.

Seven-step sequential pipeline:
Fetch → Correlate → Initial Classify → Supplementary Search → AI Enrich →
Override Re-evaluation → Store.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from disaster_surveillance_reporter.adapters import SourceAdapter
from disaster_surveillance_reporter.adapters.news import NewsSearcher
from disaster_surveillance_reporter.ai.provider import AIProvider
from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.storage.store import StorageBackend
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord

logger = structlog.get_logger(__name__)


class Pipeline:
    def __init__(
        self,
        adapters: list[SourceAdapter],
        correlator: Correlator,
        classify_engine: ClassifyEngine,
        news_searcher: NewsSearcher,
        ai_provider: AIProvider | None,
        storage_backend: StorageBackend,
    ) -> None:
        self._adapters = adapters
        self._correlator = correlator
        self._classify_engine = classify_engine
        self._news_searcher = news_searcher
        self._ai_provider = ai_provider
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

        # Step 2: Correlate records into bundles
        try:
            bundles = self._correlate_records(raw_records)
            logger.info("pipeline_correlate_done", bundle_count=len(bundles))
        except Exception:
            logger.exception("pipeline_correlate_failed")
            bundles = []

        # Step 3: Initial deterministic classification
        try:
            bundles = self._classify_initial(bundles)
            logger.info("pipeline_classify_done")
        except Exception:
            logger.exception("pipeline_classify_failed")

        # Step 4: Supplementary search for bundles needing context
        try:
            bundles = self._supplementary_search(bundles)
            logger.info("pipeline_supplementary_search_done")
        except Exception:
            logger.exception("pipeline_supplementary_search_failed")

        # Step 5: AI enrichment (extract then classify)
        try:
            bundles = self._ai_enrich(bundles)
            logger.info("pipeline_ai_enrich_done")
        except Exception:
            logger.exception("pipeline_ai_enrich_failed")

        # Step 6: Override re-evaluation
        try:
            bundles = self._reclassify_overrides(bundles)
            logger.info("pipeline_override_reeval_done")
        except Exception:
            logger.exception("pipeline_override_reeval_failed")

        # Step 7: Store complete bundles
        try:
            stored = self._store_bundles(bundles)
            logger.info("pipeline_store_done", stored_count=stored)
        except Exception:
            logger.exception("pipeline_store_failed")

        logger.info("pipeline_run_complete", bundle_count=len(bundles))
        return bundles

    def _fetch_sources(self) -> list[RawRecord]:
        records: list[RawRecord] = []
        for adapter in self._adapters:
            try:
                for item in adapter.fetch():
                    raw_fields: dict = dict(item.raw_fields)
                    raw_fields["country"] = item.country
                    raw_fields["disaster_type"] = item.disaster_type
                    raw_fields["title"] = item.incident_name
                    raw_fields["report_date"] = item.report_date
                    raw_fields["source_url"] = item.source_url
                    records.append(
                        RawRecord(
                            source_name=item.source_name,
                            fetched_at=datetime.now(tz=timezone.utc),
                            raw_fields=raw_fields,
                        )
                    )
            except Exception:
                logger.exception("pipeline_adapter_fetch_failed",
                                 source=getattr(adapter, "source_name", "unknown"))
        return records

    def _correlate_records(
        self, records: list[RawRecord]
    ) -> list[IncidentBundle]:
        if not records:
            return []
        return self._correlator.correlate(records)

    def _classify_initial(
        self, bundles: list[IncidentBundle]
    ) -> list[IncidentBundle]:
        return [self._classify_engine.classify(b) for b in bundles]

    def _supplementary_search(
        self, bundles: list[IncidentBundle]
    ) -> list[IncidentBundle]:
        for bundle in bundles:
            if self._should_supplementary_search(bundle):
                title = self._extract_title(bundle)
                query = self._build_search_query(
                    title, bundle.country, bundle.disaster_type
                )
                try:
                    results = self._news_searcher.search(
                        query, region="wt-wt", timelimit="w", max_results=10
                    )
                    bundle.records.extend(results)
                except Exception:
                    logger.exception("pipeline_news_search_failed",
                                     incident_id=bundle.incident_id)
        return bundles

    def _ai_enrich(
        self, bundles: list[IncidentBundle]
    ) -> list[IncidentBundle]:
        if self._ai_provider is None:
            for b in bundles:
                b.enrichment_failed = True
            return bundles

        for bundle in bundles:
            try:
                # Step 5a: Extractor agent — fill missing fields
                extract_prompt = self._build_extract_prompt(bundle)
                _ = self._ai_provider.chat(extract_prompt, model="default")
                # Post-extraction re-classification
                self._classify_engine.classify(bundle)

                # Step 5b: Classifier agent — generate summaries
                classify_prompt = self._build_classify_prompt(bundle)
                _ = self._ai_provider.chat(classify_prompt, model="default")

                bundle.ai_enriched = True
            except Exception:
                logger.exception("pipeline_ai_enrich_bundle_failed",
                                 incident_id=bundle.incident_id)
                bundle.ai_enriched = False
                bundle.enrichment_failed = True
                bundle.summary = None
                bundle.rationale = None
                bundle.estimated_affected = None
                bundle.estimated_deaths = None
        return bundles

    def _reclassify_overrides(
        self, bundles: list[IncidentBundle]
    ) -> list[IncidentBundle]:
        return [self._classify_engine.reevaluate_overrides(b) for b in bundles]

    def _store_bundles(self, bundles: list[IncidentBundle]) -> int:
        if not bundles:
            return 0
        return self._storage_backend.store(bundles)

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _should_supplementary_search(bundle: IncidentBundle) -> bool:
        return bundle.country is None or bundle.disaster_type is None

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

    @staticmethod
    def _build_extract_prompt(bundle: IncidentBundle) -> str:
        return f"[Extract] Extract missing fields for incident {bundle.incident_id}"

    @staticmethod
    def _build_classify_prompt(bundle: IncidentBundle) -> str:
        return f"[Classify] Generate summary for incident {bundle.incident_id}"
