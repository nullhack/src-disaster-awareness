"""Tests verifying ExtractorAgent never changes the incident_id."""

import json
from datetime import datetime, timezone
from unittest.mock import Mock

from disaster_surveillance_reporter.ai.extractor import ExtractorAgent
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_ai_extractor_keeps_incident_id_unchanged() -> None:
    """The incident_id '20260514-UNX-OTH' must remain unchanged after extraction,
    even when the Extractor resolves country to 'Philippines' and type to 'Earthquake'.
    """
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc),
        raw_fields={"eventtype": "EQ", "country": "Philippines"},
    )
    bundle = IncidentBundle(incident_id="20260514-UNX-OTH", records=[record])

    mock_provider = Mock()
    mock_provider.chat.return_value = json.dumps(
        [{"country": "Philippines", "disaster_type": "Earthquake"}]
    )

    extractor = ExtractorAgent(provider=mock_provider)
    result = extractor.extract([bundle])

    assert result[0].incident_id == "20260514-UNX-OTH"
    assert result[0].country == "Philippines"
    assert result[0].disaster_type == "Earthquake"
