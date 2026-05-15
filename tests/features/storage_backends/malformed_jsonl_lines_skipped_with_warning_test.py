"""Tests for malformed_jsonl_lines_skipped_with_warning."""

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_malformed_jsonl_lines_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Malformed JSONL lines skipped with warning."""
    partition_dir = tmp_path / "incidents" / "by-date" / "2026-05-14"
    partition_dir.mkdir(parents=True)

    valid_bundle = IncidentBundle(
        incident_id="20260514-PH-EQ",
        records=[
            RawRecord(
                source_name="GDACS",
                fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
                raw_fields={},
            )
        ],
        classification_date=date(2026, 5, 14),
    )
    line_valid = json.dumps(valid_bundle, default=str)

    jsonl_path = partition_dir / "incidents.jsonl"
    jsonl_path.write_text(
        line_valid + "\n" + "this is not valid json {{{{\n" + line_valid + "\n"
    )

    store = JSONLStore(base_path=tmp_path)

    with caplog.at_level(logging.WARNING):
        results = store.query(date_from=date(2026, 5, 13), date_to=date(2026, 5, 15))

    assert len(results) == 2
    assert any("malformed" in r.message.lower() for r in caplog.records)
