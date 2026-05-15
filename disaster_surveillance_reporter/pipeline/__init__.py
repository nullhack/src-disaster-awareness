"""Pipeline orchestration for disaster incident processing.

Seven-step sequential pipeline:
Fetch → Correlate → Initial Classify → Supplementary Search → AI Enrich →
Override Re-evaluation → Store.
"""

from disaster_surveillance_reporter.adapters import SourceAdapter
from disaster_surveillance_reporter.adapters.news import NewsSearcher
from disaster_surveillance_reporter.ai.provider import AIProvider
from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.storage.store import StorageBackend
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


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
        raise NotImplementedError

    def _fetch_sources(self) -> list[RawRecord]:
        raise NotImplementedError

    def _correlate_records(
        self, records: list[RawRecord]
    ) -> list[IncidentBundle]:
        raise NotImplementedError

    def _classify_initial(
        self, bundles: list[IncidentBundle]
    ) -> list[IncidentBundle]:
        raise NotImplementedError

    def _supplementary_search(
        self, bundles: list[IncidentBundle]
    ) -> list[IncidentBundle]:
        raise NotImplementedError

    def _ai_enrich(
        self, bundles: list[IncidentBundle]
    ) -> list[IncidentBundle]:
        raise NotImplementedError

    def _reclassify_overrides(
        self, bundles: list[IncidentBundle]
    ) -> list[IncidentBundle]:
        raise NotImplementedError

    def _store_bundles(self, bundles: list[IncidentBundle]) -> int:
        raise NotImplementedError
