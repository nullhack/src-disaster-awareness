"""Tests for ExtractorAgent using all raw records as context."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from disaster_surveillance_reporter.ai.extractor import ExtractorAgent
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_ai_extractor_uses_all_multi_source_records() -> None:
    """All raw records from GDACS, WHO, GDELT, and DDG-NEWS appear in the AI prompt."""
    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(source_name="GDACS", fetched_at=now, raw_fields={"eventtype": "EQ", "alertlevel": "Orange"}),
        RawRecord(source_name="WHO", fetched_at=now, raw_fields={"text": "outbreak report"}),
        RawRecord(source_name="GDELT", fetched_at=now, raw_fields={"title": "quake hits region"}),
        RawRecord(source_name="DDG-NEWS", fetched_at=now, raw_fields={"headline": "breaking: earthquake"}),
    ]
    bundle = IncidentBundle(incident_id="20260514-UNX-OTH", records=records)

    mock_provider = Mock()
    mock_provider.chat.return_value = "[]"

    extractor = ExtractorAgent(provider=mock_provider)
    extractor.extract([bundle])

    prompt: str = mock_provider.chat.call_args[0][0]
    assert "GDACS" in prompt
    assert "WHO" in prompt
    assert "GDELT" in prompt
    assert "DDG-NEWS" in prompt
