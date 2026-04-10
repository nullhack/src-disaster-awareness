"""Tests for pipeline orchestration module."""

from dataclasses import dataclass
from typing import Any

from disaster_surveillance_reporter.adapters import RawIncidentData
from disaster_surveillance_reporter.classification import RulesLoader
from disaster_surveillance_reporter.opencode import OpenCodeClient
from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.storage import StorageBackend


@dataclass
class MockSourceAdapter:
    """Mock source adapter for testing."""

    incidents: list[RawIncidentData]
    source_name: str = "GDACS"

    def fetch(self) -> list[RawIncidentData]:
        return self.incidents


class MockStorageBackend:
    """Mock storage backend for testing."""

    def __init__(self) -> None:
        self._stored: list[dict[str, Any]] = []

    def write(self, incidents: list[dict[str, Any]]) -> None:
        self._stored = incidents

    def read(self) -> list[dict[str, Any]]:
        return self._stored

    def append(self, incidents: list[dict[str, Any]]) -> None:
        self._stored.extend(incidents)


def test_pipeline_fetch_all_should_return_incidents():
    """
    Given: A Pipeline with configured sources
    When: fetch_all() is called
    Then: Should return all incidents from all sources
    """
    raw_incidents = [
        RawIncidentData(
            source_name="GDACS",
            incident_name="Tropical Cyclone Test",
            country="Pacific Ocean",
            disaster_type="Tropical Cyclone",
            report_date="2026-03-12T00:00:00Z",
            source_url="https://example.com/1",
            raw_fields={},
        ),
        RawIncidentData(
            source_name="GDACS",
            incident_name="Earthquake Test",
            country="Indonesia",
            disaster_type="Earthquake",
            report_date="2026-03-11T00:00:00Z",
            source_url="https://example.com/2",
            raw_fields={},
        ),
    ]
    sources = [MockSourceAdapter(raw_incidents)]
    storage = MockStorageBackend()  # type: ignore[assignment]
    opencode_client = OpenCodeClient(mock_mode=True)
    rules_loader = RulesLoader()
    pipeline = Pipeline(sources, storage, opencode_client, rules_loader)

    result = pipeline.fetch_all()
    assert len(result) == 2


def test_pipeline_transform_all_should_return_schema_dicts():
    """
    Given: A Pipeline with raw incidents
    When: transform_all() is called
    Then: Should return list of dicts with schema fields
    """
    sources = [MockSourceAdapter([])]
    storage: StorageBackend = MockStorageBackend()
    opencode_client = OpenCodeClient(mock_mode=True)
    rules_loader = RulesLoader()
    pipeline = Pipeline(sources, storage, opencode_client, rules_loader)

    raw = [
        RawIncidentData(
            source_name="GDACS",
            incident_name="Test",
            country="Test",
            disaster_type="Test",
            report_date="2026-03-12T00:00:00Z",
            source_url="https://example.com",
            raw_fields={},
        )
    ]
    result = pipeline.transform_all(raw)
    assert len(result) == 1
    assert "incident_id" in result[0]
    assert "status" in result[0]


def test_pipeline_classify_all_should_add_classification():
    """
    Given: A Pipeline with transformed incidents
    When: classify_all() is called
    Then: Each incident should have classification field
    """
    sources = [MockSourceAdapter([])]
    storage: StorageBackend = MockStorageBackend()
    opencode_client = OpenCodeClient(mock_mode=True)
    rules_loader = RulesLoader()
    pipeline = Pipeline(sources, storage, opencode_client, rules_loader)

    incidents = [
        {
            "incident_id": "test-1",
            "country": "Indonesia",
            "country_group": "A",
            "incident_type": "Earthquake",
            "incident_level": 2,
            "priority": "MEDIUM",
            "should_report": True,
        }
    ]
    result = pipeline.classify_all(incidents)
    assert len(result) == 1
    assert "classification" in result[0]


def test_pipeline_store_all_should_write_to_storage():
    """
    Given: A Pipeline with storage backend
    When: store_all() is called with incidents
    Then: Storage should contain the incidents
    """
    sources = [MockSourceAdapter([])]
    storage: StorageBackend = MockStorageBackend()
    opencode_client = OpenCodeClient(mock_mode=True)
    rules_loader = RulesLoader()
    pipeline = Pipeline(sources, storage, opencode_client, rules_loader)

    incidents = [{"incident_id": "test-1"}, {"incident_id": "test-2"}]
    pipeline.store_all(incidents)

    stored = storage.read()
    assert len(stored) == 2


def test_pipeline_run_full_cycle_should_return_classified_incidents():
    """
    Given: A Pipeline with all components configured
    When: run_full_cycle() is called
    Then: Should return classified incidents stored in backend
    """
    raw_incidents = [
        RawIncidentData(
            source_name="GDACS",
            incident_name="Test",
            country="Test",
            disaster_type="Test",
            report_date="2026-03-12T00:00:00Z",
            source_url="https://example.com",
            raw_fields={},
        )
    ]
    sources = [MockSourceAdapter(raw_incidents)]
    storage = MockStorageBackend()  # type: ignore[assignment]
    opencode_client = OpenCodeClient(mock_mode=True)
    rules_loader = RulesLoader()
    pipeline = Pipeline(sources, storage, opencode_client, rules_loader)

    result = pipeline.run_full_cycle()
    assert len(result) == 1
    stored = storage.read()
    assert len(stored) == 1
