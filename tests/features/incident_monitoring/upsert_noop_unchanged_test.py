from datetime import datetime, timedelta, timezone

from disaster_surveillance_reporter.storage.store import SQLiteStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_upsert_noops_when_no_new_fingerprints():
    store = SQLiteStore(":memory:")
    now = datetime.now(tz=timezone.utc)
    three_days_ago = now - timedelta(days=3)

    # Seed: insert bundle
    first = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[
            RawRecord(
                source_name="GDACS",
                fetched_at=three_days_ago,
                raw_fields={"eventid": "12345"},
            )
        ],
        source_fingerprints=["GDACS:12345"],
        last_updated=three_days_ago,
    )
    store.upsert(first)

    # Upsert with same fingerprints — should be noop
    second = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[
            RawRecord(
                source_name="GDACS",
                fetched_at=now,
                raw_fields={"eventid": "12345"},
            )
        ],
        source_fingerprints=["GDACS:12345"],
        last_updated=now,
    )
    result = store.upsert(second)
    assert result == "noop"

    # Verify last_updated was NOT reset
    stored_ts = store.get_last_updated("20260514-JP-EQ")
    assert stored_ts is not None
    # last_updated should still be three_days_ago (preserved)
    delta = abs((stored_ts - three_days_ago).total_seconds())
    assert delta < 1.0
