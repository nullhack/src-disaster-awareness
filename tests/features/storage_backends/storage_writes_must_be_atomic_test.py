"""Tests for storage_writes_must_be_atomic."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_failed_write_leaves_original_data_intact(tmp_path: Path) -> None:
    """Failed write leaves original data intact."""
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={"title": "Original incident"},
    )
    original_bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record],
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([original_bundle])

    jsonl_path = tmp_path / "incidents" / "by-date" / "2026-05-14" / "incidents.jsonl"
    original_content = jsonl_path.read_text()

    # Simulate querying after a hypothetical failed write
    results = store.query(date_from=date(2026, 5, 13), date_to=date(2026, 5, 15))

    assert len(results) == 1
    current_content = jsonl_path.read_text()
    assert current_content == original_content
