"""Tests for dedup_skips_existing_incident_ids."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def _make_bundle(incident_id: str, cls_date: date) -> IncidentBundle:
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    return IncidentBundle(
        incident_id=incident_id,
        records=[record],
        classification_date=cls_date,
    )


def test_existing_incident_id_is_skipped(tmp_path: Path) -> None:
    """Existing incident ID is skipped."""
    store = JSONLStore(base_path=tmp_path)
    bundle = _make_bundle("20260514-JP-EQ", date(2026, 5, 14))

    first = store.store([bundle])
    assert first == 1

    second = store.store([bundle])
    assert second == 0


def test_new_incident_id_bundle_is_stored(tmp_path: Path) -> None:
    """New incident ID bundle is stored."""
    store = JSONLStore(base_path=tmp_path)
    bundle = _make_bundle("20260514-JP-EQ", date(2026, 5, 14))

    count = store.store([bundle])

    assert count == 1
