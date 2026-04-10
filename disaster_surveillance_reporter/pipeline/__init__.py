"""Pipeline orchestration for disaster incident processing.

This module provides the Pipeline class that orchestrates the full processing flow:
fetch from sources -> transform to schema -> classify -> store.
"""

from dataclasses import dataclass
from typing import Any

from disaster_surveillance_reporter.adapters import RawIncidentData
from disaster_surveillance_reporter.classification import RulesLoader
from disaster_surveillance_reporter.opencode import OpenCodeClient
from disaster_surveillance_reporter.storage import StorageBackend


@dataclass
class Pipeline:
    """Orchestrates the full incident processing pipeline."""

    def __init__(
        self,
        sources: list,
        storage: StorageBackend,
        opencode_client: OpenCodeClient,
        rules_loader: RulesLoader,
    ):
        self._sources = sources
        self._storage = storage
        self._opencode_client = opencode_client
        self._rules_loader = rules_loader

    def run_full_cycle(self) -> list[dict[str, Any]]:
        """Run complete pipeline: fetch -> transform -> classify -> store."""
        raw_incidents = self.fetch_all()
        transformed = self.transform_all(raw_incidents)
        classified = self.classify_all(transformed)
        self.store_all(classified)
        return classified

    def fetch_all(self) -> list[RawIncidentData]:
        """Fetch incidents from all configured sources."""
        all_incidents = []
        for source in self._sources:
            all_incidents.extend(source.fetch())
        return all_incidents

    def transform_all(
        self, raw_incidents: list[RawIncidentData]
    ) -> list[dict[str, Any]]:
        """Transform all raw incidents to schema format."""
        result = []
        for raw in raw_incidents:
            transformed = self._opencode_client.transform(
                {
                    "source_name": raw.source_name,
                    "source_url": raw.source_url,
                    "incident_name": raw.incident_name,
                    "country": raw.country,
                    "disaster_type": raw.disaster_type,
                    "report_date": raw.report_date,
                    "raw_fields": raw.raw_fields,
                }
            )
            result.append(transformed)
        return result

    def classify_all(self, incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Classify all incidents using OpenCode."""
        result = []
        for incident in incidents:
            classified = self._opencode_client.classify(incident)
            result.append(classified)
        return result

    def store_all(self, incidents: list[dict[str, Any]]) -> None:
        """Store all incidents to the configured backend."""
        self._storage.write(incidents)
