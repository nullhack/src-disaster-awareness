from datetime import datetime, timezone

from disaster_surveillance_reporter.storage.store import SQLiteStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_upsert_inserts_new_bundle():
    store = SQLiteStore(":memory:")
    now = datetime.now(tz=timezone.utc)

    bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[
            RawRecord(
                source_name="GDACS",
                fetched_at=now,
                raw_fields={"eventid": "12345"},
            )
        ],
        last_updated=now,
    )
    result = store.upsert(bundle)
    assert result == "inserted"
    assert store.exists("20260514-JP-EQ") is True
