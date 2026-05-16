from datetime import datetime, timezone

from disaster_surveillance_reporter.storage.store import SQLiteStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_upsert_merges_bundle_with_new_fingerprints():
    store = SQLiteStore(":memory:")
    now = datetime.now(tz=timezone.utc)

    # Seed: insert bundle with fingerprint "GDACS:12345"
    first = IncidentBundle(
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
    store.upsert(first)

    # Upsert with new fingerprint "WHO:abc-def"
    second = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[
            RawRecord(
                source_name="WHO",
                fetched_at=now,
                raw_fields={"Id": "abc-def"},
            )
        ],
        source_fingerprints=["GDACS:12345", "WHO:abc-def"],
        last_updated=now,
    )
    result = store.upsert(second)
    assert result == "updated"
    stored_fps = store.get_source_fingerprints("20260514-JP-EQ")
    assert "GDACS:12345" in stored_fps
    assert "WHO:abc-def" in stored_fps
