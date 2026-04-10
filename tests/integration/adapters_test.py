"""Real data tests for GDACS adapter and JSONL storage."""

import tempfile
from datetime import datetime, timezone

import pytest

from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter
from disaster_surveillance_reporter.storage.jsonl import JSONLBackend


@pytest.mark.integration
@pytest.mark.slow
def test_gdacs_adapter_fetch_should_return_incidents():
    """
    Given: A GDACSAdapter instance
    When: fetch() is called with real HTTP to GDACS API
    Then: Should return list of RawIncidentData (may be empty if no active incidents)
    """
    adapter = GDACSAdapter()
    result = adapter.fetch()
    assert isinstance(result, list)


@pytest.mark.integration
@pytest.mark.slow
def test_gdacs_adapter_fetch_should_have_source_name():
    """
    Given: A GDACSAdapter instance
    When: fetch() is called
    Then: All returned incidents should have source_name 'GDACS'
    """
    adapter = GDACSAdapter()
    result = adapter.fetch()
    for incident in result:
        assert incident.source_name == "GDACS"


def test_jsonl_backend_should_create_date_subfolder():
    """
    Given: A JSONLBackend with base_path
    When: write() is called
    Then: Should create subfolder in YYYY-MM-DD format (UTC)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path

        base = Path(tmpdir)
        test_date = datetime(2026, 4, 9, 12, 0, 0, tzinfo=timezone.utc)
        backend = JSONLBackend(base, date=test_date)

        backend.write([{"incident_id": "test-001"}])

        expected_path = base / "2026-04-09" / "incidents.jsonl"
        assert expected_path.exists()


def test_jsonl_backend_should_use_utc_date():
    """
    Given: A JSONLBackend initialized without date
    When: write() is called
    Then: Should use current UTC date for subfolder
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path

        base = Path(tmpdir)
        backend = JSONLBackend(base)

        backend.write([{"incident_id": "test-001"}])

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        expected_path = base / today / "incidents.jsonl"
        assert expected_path.exists()


def test_jsonl_backend_should_read_from_date_folder():
    """
    Given: A JSONLBackend that wrote to a date folder
    When: read() is called
    Then: Should return the written incidents
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path

        base = Path(tmpdir)
        test_date = datetime(2026, 4, 9, tzinfo=timezone.utc)
        backend = JSONLBackend(base, date=test_date)

        incidents = [{"incident_id": "test-001"}, {"incident_id": "test-002"}]
        backend.write(incidents)

        result = backend.read()
        assert len(result) == 2
        assert result[0]["incident_id"] == "test-001"
        assert result[1]["incident_id"] == "test-002"


def test_jsonl_backend_should_append_to_date_folder():
    """
    Given: A JSONLBackend with existing data
    When: append() is called
    Then: Should add to the same date folder
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path

        base = Path(tmpdir)
        test_date = datetime(2026, 4, 9, tzinfo=timezone.utc)
        backend = JSONLBackend(base, date=test_date)

        backend.write([{"incident_id": "test-001"}])
        backend.append([{"incident_id": "test-002"}])

        result = backend.read()
        assert len(result) == 2
