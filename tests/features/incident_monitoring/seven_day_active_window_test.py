from datetime import datetime, timedelta, timezone

from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_bundle_within_7_days_is_active():
    now = datetime.now(tz=timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"eventid": "123"},
    )
    bundle = IncidentBundle(
        incident_id="test-7day",
        records=[record],
        last_updated=now - timedelta(days=3),
    )
    assert bundle.is_active() is True
    assert bundle.is_active(reference_time=now) is True
