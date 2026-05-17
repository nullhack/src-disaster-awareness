"""Tests for storage_preserves_complete_incidentbundles."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_complete_bundle_preserved_after_storage(tmp_path: Path) -> None:
    """Complete bundle preserved after storage."""
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={"title": "Quake in Japan", "magnitude": 7.2},
    )
    bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record],
        country="Japan",
        country_code="JP",
        country_group="A",
        disaster_type="EQ",
        incident_level=3,
        priority="HIGH",
        should_report=True,
        overrides=["prio_override"],
        summary="Major earthquake in Japan",
        rationale="High magnitude, populated area",
        estimated_affected=50000,
        estimated_deaths=200,
        ai_enriched=True,
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle])

    results = store.query(date_from=date(2026, 5, 13), date_to=date(2026, 5, 15))

    assert len(results) == 1
    incident = results[0]
    assert incident.incident_id == "20260514-JP-EQ"
    assert incident.country == "Japan"
    assert incident.country_code == "JP"
    assert incident.country_group == "A"
    assert incident.disaster_type == "EQ"
    assert incident.incident_level == 3
    assert incident.priority == "HIGH"
    assert incident.should_report is True
    assert incident.overrides == ["prio_override"]
    assert incident.summary == "Major earthquake in Japan"
    assert incident.rationale == "High magnitude, populated area"
    assert incident.estimated_affected == 50000
    assert incident.estimated_deaths == 200
    assert incident.ai_enriched is True
    assert incident.record_count == 1
