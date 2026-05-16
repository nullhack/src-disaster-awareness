"""Tests for EONET level from default or volcano."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_eonet_non_volcano_event_defaults_to_level_2():
    """EONET event without volcano category defaults to Level 2."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="EONET",
        fetched_at=now,
        raw_fields={
            "id": "EONET_12345",
            "title": "Flood event in the region",
            "categories": [{"id": "floods", "title": "Floods"}],
        },
    )
    bundle = IncidentBundle(
        incident_id="20260514-XX-FL",
        records=[record],
        country="France",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.incident_level == 2


def test_eonet_volcano_event_elevated_to_level_3():
    """EONET volcano event is elevated to Level 3."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="EONET",
        fetched_at=now,
        raw_fields={
            "id": "EONET_67890",
            "title": "Volcanic eruption detected",
            "categories": [{"id": "volcanoes", "title": "Volcanoes"}],
        },
    )
    bundle = IncidentBundle(
        incident_id="20260514-XX-VO",
        records=[record],
        country="France",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.incident_level == 3
