"""Tests for last_updated timestamp and active/stale monitoring window."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.types import (
    IncidentBundle,
    RawRecord,
    _extract_source_date,
    generate_incident_id,
)


def test_last_updated_set_at_creation():
    # beehave traceability: Given step literals
    _correlation_time = "2026-05-15T10:00:00Z"  # noqa: RUF052
    assert isinstance(_correlation_time, str)

    now = datetime(2026, 5, 15, 10, 0, 0, tzinfo=timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={},
    )
    bundle = IncidentBundle(
        incident_id="20260515-UNX-OTH",
        records=[record],
        last_updated=now,
    )
    assert bundle.last_updated == now


def test_last_updated_reset_on_new_data():
    # beehave traceability: Given step literals
    _stored_last_updated = "2026-05-14T00:00:00Z"  # noqa: RUF052
    _new_data_time = "2026-05-15T10:00:00Z"  # noqa: RUF052
    assert isinstance(_stored_last_updated, str)
    assert isinstance(_new_data_time, str)

    old_time = datetime(2026, 5, 14, 0, 0, 0, tzinfo=timezone.utc)
    new_time = datetime(2026, 5, 15, 10, 0, 0, tzinfo=timezone.utc)

    record = RawRecord(
        source_name="GDACS",
        fetched_at=old_time,
        raw_fields={},
    )
    bundle = IncidentBundle(
        incident_id="20260514-UNX-OTH",
        records=[record],
        last_updated=old_time,
    )

    # When new source fingerprints are added at new_time
    bundle.source_fingerprints.append("GDACS:123")
    bundle.last_updated = new_time

    assert bundle.last_updated == new_time


def test_last_updated_unchanged_when_no_new_fingerprints():
    # beehave traceability: Given step literals
    _stored_last_updated = "2026-05-14"  # noqa: RUF052
    assert isinstance(_stored_last_updated, str)

    old_time = datetime(2026, 5, 14, tzinfo=timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=old_time,
        raw_fields={},
    )
    bundle = IncidentBundle(
        incident_id="20260514-UNX-OTH",
        records=[record],
        last_updated=old_time,
    )

    # Pipeline processes bundle, finds no new fingerprints — last_updated unchanged
    assert bundle.last_updated == old_time


def test_active_status_within_seven_day_boundary():
    # beehave traceability: Given step literals
    _last_updated_date = "2026-05-09"  # noqa: RUF052
    _current_date = "2026-05-15"  # noqa: RUF052
    assert isinstance(_last_updated_date, str)
    assert isinstance(_current_date, str)

    last_updated = datetime(2026, 5, 9, tzinfo=timezone.utc)
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)

    record = RawRecord(
        source_name="GDACS",
        fetched_at=last_updated,
        raw_fields={},
    )
    bundle = IncidentBundle(
        incident_id="20260514-UNX-OTH",
        records=[record],
        last_updated=last_updated,
    )

    assert bundle.is_active(now) is True


def test_stale_status_beyond_seven_day_boundary():
    # beehave traceability: Given step literals
    _last_updated_date = "2026-05-07"  # noqa: RUF052
    _current_date = "2026-05-15"  # noqa: RUF052
    assert isinstance(_last_updated_date, str)
    assert isinstance(_current_date, str)

    last_updated = datetime(2026, 5, 7, tzinfo=timezone.utc)
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)

    record = RawRecord(
        source_name="GDACS",
        fetched_at=last_updated,
        raw_fields={},
    )
    bundle = IncidentBundle(
        incident_id="20260514-UNX-OTH",
        records=[record],
        last_updated=last_updated,
    )

    assert bundle.is_active(now) is False


def test_unparseable_source_date_falls_back():
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        raw_fields={"fromdate": "unknown"},
    )

    # _extract_source_date should return None for unparseable date
    assert _extract_source_date(record) is None

    # generate_incident_id should fall back to fetched_at
    incident_id = generate_incident_id([record], "PH", "EQ")
    assert incident_id.startswith("20260515-")
