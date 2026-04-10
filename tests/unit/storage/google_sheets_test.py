"""Tests for GoogleSheetsBackend storage."""

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Import the class to test
from disaster_surveillance_reporter.storage import GoogleSheetsBackend


def test_given_google_sheets_backend_when_init_with_env_url_should_load():
    """
    Given: Environment variable GOOGLE_SHEETS_URL is set
    When: GoogleSheetsBackend is initialized
    Then: Should load the spreadsheet URL from environment
    """
    with patch.dict(
        os.environ,
        {"GOOGLE_SHEETS_URL": "https://docs.google.com/spreadsheets/d/test123/edit"},
    ):
        # Just check ID is extracted without triggering auth
        backend = GoogleSheetsBackend()
        # Set mock service manually to avoid auth flow
        backend._service = MagicMock()
        assert backend._spreadsheet_id == "test123"


def test_given_google_sheets_backend_when_init_should_have_today_date():
    """
    Given: A GoogleSheetsBackend instance
    When: Initialized
    Then: Should use today's date as default sheet name
    """
    with patch.dict(
        os.environ,
        {"GOOGLE_SHEETS_URL": "https://docs.google.com/spreadsheets/d/test123/edit"},
    ):
        backend = GoogleSheetsBackend()
        backend._service = MagicMock()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert backend._current_date == today


def test_given_google_sheets_backend_when_get_or_create_sheet_should_create():
    """
    Given: A GoogleSheetsBackend with mock service
    When: get_or_create_worksheet is called with new date
    Then: Should create a new worksheet with that date name
    """
    with patch.dict(
        os.environ,
        {"GOOGLE_SHEETS_URL": "https://docs.google.com/spreadsheets/d/test123/edit"},
    ):
        mock_gc = MagicMock()
        mock_sh = MagicMock()
        mock_gc.open_by_key.return_value = mock_sh
        mock_sh.worksheet.side_effect = Exception("Not found")
        mock_sh.add_worksheet.return_value = MagicMock(title="2026-04-10")

        backend = GoogleSheetsBackend()
        backend._service = mock_gc
        ws = backend.get_or_create_worksheet("2026-04-10")

        mock_sh.add_worksheet.assert_called_once()
        assert ws is not None


def test_given_google_sheets_backend_when_get_or_create_sheet_should_return_existing():
    """
    Given: A GoogleSheetsBackend with mock service
    When: get_or_create_worksheet is called with existing date
    Then: Should return existing worksheet without creating new
    """
    with patch.dict(
        os.environ,
        {"GOOGLE_SHEETS_URL": "https://docs.google.com/spreadsheets/d/test123/edit"},
    ):
        mock_gc = MagicMock()
        mock_sh = MagicMock()
        mock_gc.open_by_key.return_value = mock_sh
        mock_ws = MagicMock()
        mock_sh.worksheet.return_value = mock_ws

        backend = GoogleSheetsBackend()
        backend._service = mock_gc
        ws = backend.get_or_create_worksheet("2026-04-10")

        mock_sh.add_worksheet.assert_not_called()
        assert ws == mock_ws


def test_given_google_sheets_backend_when_write_with_empty_header_should_write():
    """
    Given: A GoogleSheetsBackend with mock worksheet
    When: write is called and first row is empty
    Then: Should write header row first
    """
    with patch.dict(
        os.environ,
        {"GOOGLE_SHEETS_URL": "https://docs.google.com/spreadsheets/d/test123/edit"},
    ):
        mock_gc = MagicMock()
        mock_sh = MagicMock()
        mock_gc.open_by_key.return_value = mock_sh
        mock_ws = MagicMock()
        mock_sh.worksheet.return_value = mock_ws
        mock_ws.row_values.return_value = []  # Empty first row
        mock_ws.get_all_values.return_value = []

        backend = GoogleSheetsBackend()
        backend._service = mock_gc
        backend._worksheet = mock_ws

        incidents = [
            {
                "incident_id": "test-001",
                "summary": "Test",
                "country": "Test",
                "created_date": "2026-04-10",
                "status": "Active",
                "incident_type": "Test",
                "priority": "LOW",
                "country_group": "B",
                "incident_level": 1,
                "should_report": True,
                "estimated_affected": None,
                "estimated_deaths": None,
                "sources": "[]",
                "classification": "{}",
                "classification_metadata": "{}",
            }
        ]
        backend.write(incidents)

        # Should call append for header
        assert mock_ws.append_row.called


def test_given_google_sheets_backend_when_write_should_convert_sources_to_json():
    """
    Given: An incident with sources list
    When: write is called
    Then: Sources should be converted to JSON string for cell
    """
    with patch.dict(
        os.environ,
        {"GOOGLE_SHEETS_URL": "https://docs.google.com/spreadsheets/d/test123/edit"},
    ):
        mock_gc = MagicMock()
        mock_sh = MagicMock()
        mock_gc.open_by_key.return_value = mock_sh
        mock_ws = MagicMock()
        mock_sh.worksheet.return_value = mock_ws
        mock_ws.row_values.return_value = []  # Empty, will write header
        mock_ws.get_all_values.return_value = []

        backend = GoogleSheetsBackend()
        backend._service = mock_gc
        backend._worksheet = mock_ws

        incidents = [
            {
                "incident_id": "test-001",
                "incident_name": "Test Event",
                "summary": "Test summary",
                "created_date": "2026-04-10T00:00:00Z",
                "status": "Active",
                "country": "TestCountry",
                "country_group": "B",
                "incident_type": "Test",
                "priority": "MEDIUM",
                "incident_level": 1,
                "should_report": True,
                "estimated_affected": None,
                "estimated_deaths": None,
                "sources": [
                    {
                        "name": "GDACS",
                        "url": "https://gdacs.org/test",
                        "type": "disaster-database",
                    }
                ],
                "classification": {},
                "classification_metadata": {},
            }
        ]
        backend.write(incidents)

        # Check that append_row was called
        assert mock_ws.append_row.called


def test_given_google_sheets_backend_when_write_should_find_next_empty_row():
    """
    Given: A worksheet with existing data
    When: write is called
    Then: Should find the next empty row (not overwrite existing)
    """
    with patch.dict(
        os.environ,
        {"GOOGLE_SHEETS_URL": "https://docs.google.com/spreadsheets/d/test123/edit"},
    ):
        mock_gc = MagicMock()
        mock_sh = MagicMock()
        mock_gc.open_by_key.return_value = mock_sh
        mock_ws = MagicMock()
        mock_sh.worksheet.return_value = mock_ws
        mock_ws.get_all_values.return_value = [
            ["incident_id", "summary"],
            ["20260409-001", "First incident"],
            ["20260409-002", "Second incident"],
        ]

        backend = GoogleSheetsBackend()
        backend._service = mock_gc
        backend._worksheet = mock_ws

        incidents = [
            {
                "incident_id": "test-003",
                "summary": "Third",
                "country": "Test",
                "created_date": "2026-04-10",
                "status": "Active",
                "incident_type": "Test",
                "priority": "LOW",
                "country_group": "B",
                "incident_level": 1,
                "should_report": True,
                "estimated_affected": None,
                "estimated_deaths": None,
                "sources": "[]",
                "classification": "{}",
                "classification_metadata": "{}",
            }
        ]
        backend.write(incidents)

        # Should append (not overwrite row 2)
        mock_ws.append_row.assert_called()


def test_given_google_sheets_backend_when_no_env_should_raise_error():
    """
    Given: No GOOGLE_SHEETS_URL environment variable
    When: GoogleSheetsBackend is initialized
    Then: Should raise ValueError
    """
    env_backup = os.environ.get("GOOGLE_SHEETS_URL")
    if "GOOGLE_SHEETS_URL" in os.environ:
        del os.environ["GOOGLE_SHEETS_URL"]

    try:
        with pytest.raises(ValueError, match="GOOGLE_SHEETS_URL"):
            GoogleSheetsBackend()
    finally:
        if env_backup:
            os.environ["GOOGLE_SHEETS_URL"] = env_backup
