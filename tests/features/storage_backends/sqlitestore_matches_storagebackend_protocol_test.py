"""Tests for sqlitestore_matches_storagebackend_protocol."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import SQLiteStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_sqlitestore_implements_storage_backend_protocol(tmp_path: Path) -> None:
    """SQLiteStore implements storage backend protocol."""
    db_path = tmp_path / "incidents.db"
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record],
        classification_date=date(2026, 5, 14),
    )
    store = SQLiteStore(db_path=db_path)

    count = store.store([bundle])
    assert count == 1

    results = store.query(date_from=date(2026, 5, 13), date_to=date(2026, 5, 15))
    assert len(results) == 1
    assert results[0].incident_id == "20260514-JP-EQ"
