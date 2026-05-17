from datetime import datetime, timezone

from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_incident_id_unchanged_after_ai_enrichment():
    # Given an IncidentBundle with incident_id "20260514-UNX-OTH"
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, tzinfo=timezone.utc),
        raw_fields={"eventtype": "EQ"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-UNX-OTH",
        records=[record],
    )

    # When AI enrichment fills country as "Japan" and disaster_type as "Earthquake"
    bundle.country = "Japan"
    bundle.disaster_type = "Earthquake"

    # Then the incident_id remains "20260514-UNX-OTH"
    assert bundle.incident_id == "20260514-UNX-OTH"
