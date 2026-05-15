"""Tests for incident_name_from_most_reliable_source."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_incident_name_uses_highest_reliability_title(tmp_path: Path) -> None:
    """Incident name uses highest reliability title."""
    record_gdacs = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={"title": "Quake in Japan"},
    )
    record_who = RawRecord(
        source_name="WHO",
        fetched_at=datetime(2026, 5, 14, 12, 5, tzinfo=timezone.utc),
        raw_fields={"ReportTitle": "Tsunami alert"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record_gdacs, record_who],
        classification_date=date(2026, 5, 14),
        country="Japan",
        disaster_type="EQ",
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle])

    results = store.query(date_from=date(2026, 5, 13), date_to=date(2026, 5, 15))

    assert len(results) == 1
    assert results[0].incident_name == "Quake in Japan"
