"""Tests for query_returns_flattened_incident_records."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import Incident, IncidentBundle, RawRecord


def test_query_returns_incident_without_raw_records(tmp_path: Path) -> None:
    """Query returns Incident without raw records."""
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={"title": "Quake in Philippines"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-PH-EQ",
        records=[record],
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle])

    results = store.query(date_from=date(2026, 5, 13), date_to=date(2026, 5, 15))

    assert len(results) == 1
    incident = results[0]
    assert isinstance(incident, Incident)
    assert not hasattr(incident, "raw_records")
