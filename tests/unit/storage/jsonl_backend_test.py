"""Tests for storage backend module."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from disaster_surveillance_reporter.storage.jsonl import JSONLBackend


@pytest.fixture
def temp_base_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_date():
    """Create a fixed test date."""
    return datetime(2026, 4, 9, 12, 0, 0, tzinfo=timezone.utc)


def test_jsonl_backend_write_should_create_file(temp_base_dir, test_date):
    """
    Given: A JSONLBackend instance with base_path and date
    When: write() is called with incidents
    Then: Should create the file in date subfolder
    """
    backend = JSONLBackend(temp_base_dir, date=test_date)
    incidents = [{"incident_id": "test-001", "name": "Test"}]
    backend.write(incidents)
    expected_path = temp_base_dir / "2026-04-09" / "incidents.jsonl"
    assert expected_path.exists()


def test_jsonl_backend_write_should_write_jsonl_format(temp_base_dir, test_date):
    """
    Given: A JSONLBackend instance
    When: write() is called with multiple incidents
    Then: Should write in JSONL format (one JSON per line)
    """
    backend = JSONLBackend(temp_base_dir, date=test_date)
    incidents = [
        {"incident_id": "test-001", "name": "Test 1"},
        {"incident_id": "test-002", "name": "Test 2"},
    ]
    backend.write(incidents)

    expected_path = temp_base_dir / "2026-04-09" / "incidents.jsonl"
    with expected_path.open("r") as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["incident_id"] == "test-001"
    assert json.loads(lines[1])["incident_id"] == "test-002"


def test_jsonl_backend_read_should_return_empty_for_nonexistent(temp_base_dir):
    """
    Given: A JSONLBackend instance with nonexistent date folder
    When: read() is called
    Then: Should return empty list
    """
    future_date = datetime(2099, 1, 1, tzinfo=timezone.utc)
    backend = JSONLBackend(temp_base_dir, date=future_date)
    result = backend.read()
    assert result == []


def test_jsonl_backend_read_should_return_written_data(temp_base_dir, test_date):
    """
    Given: A JSONLBackend with previously written data
    When: read() is called
    Then: Should return the written incidents
    """
    backend = JSONLBackend(temp_base_dir, date=test_date)
    incidents = [
        {"incident_id": "test-001", "name": "Test 1"},
        {"incident_id": "test-002", "name": "Test 2"},
    ]
    backend.write(incidents)

    result = backend.read()
    assert len(result) == 2
    assert result[0]["incident_id"] == "test-001"
    assert result[1]["incident_id"] == "test-002"


def test_jsonl_backend_append_should_add_to_existing(temp_base_dir, test_date):
    """
    Given: A JSONLBackend with existing data
    When: append() is called with new incidents
    Then: Should add new incidents to file
    """
    backend = JSONLBackend(temp_base_dir, date=test_date)
    backend.write([{"incident_id": "test-001"}])
    backend.append([{"incident_id": "test-002"}])

    result = backend.read()
    assert len(result) == 2
    assert result[0]["incident_id"] == "test-001"
    assert result[1]["incident_id"] == "test-002"


def test_jsonl_backend_append_should_create_if_not_exists(temp_base_dir):
    """
    Given: A JSONLBackend with date
    When: append() is called on new file
    Then: Should create file and write data
    """
    test_date = datetime(2026, 4, 9, tzinfo=timezone.utc)
    backend = JSONLBackend(temp_base_dir, date=test_date)
    backend.append([{"incident_id": "test-001"}])

    expected_path = temp_base_dir / "2026-04-09" / "incidents.jsonl"
    assert expected_path.exists()
    result = backend.read()
    assert len(result) == 1
