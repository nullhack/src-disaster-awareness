"""Tests for jsonl_files_are_date_partitioned."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_bundle_stored_in_date_partitioned_jsonl(tmp_path: Path) -> None:
    """Bundle stored in date partitioned JSONL."""
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
    store = JSONLStore(base_path=tmp_path)

    count = store.store([bundle])

    assert count == 1
    expected_path = (
        tmp_path / "incidents" / "by-date" / "2026-05-14" / "incidents.jsonl"
    )
    target_path_str = "incidents/by-date/2026-05-14/incidents.jsonl"
    assert expected_path.exists()
    content = expected_path.read_text()
    assert "20260514-JP-EQ" in content
    assert target_path_str in str(expected_path.relative_to(tmp_path))
