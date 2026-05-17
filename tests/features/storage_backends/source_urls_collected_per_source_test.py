"""Tests for source_urls_collected_per_source."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_source_urls_collected_for_each_source(tmp_path: Path) -> None:
    """Source URLs collected for each source."""
    record_gdacs = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={"url": {"report": "https://gdacs.org/report/123"}},
    )
    record_who = RawRecord(
        source_name="WHO",
        fetched_at=datetime(2026, 5, 14, 12, 5, tzinfo=timezone.utc),
        raw_fields={"ItemDefaultUrl": "/emergencies/item/456"},
    )
    record_gdelt = RawRecord(
        source_name="GDELT",
        fetched_at=datetime(2026, 5, 14, 12, 10, tzinfo=timezone.utc),
        raw_fields={"url": "https://gdelt.org/article/789"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record_gdacs, record_who, record_gdelt],
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle])

    results = store.query(date_from=date(2026, 5, 13), date_to=date(2026, 5, 15))

    assert len(results) == 1
    urls = results[0].source_urls
    assert isinstance(urls, list)
    assert "https://gdacs.org/report/123" in urls
    assert "https://www.who.int/emergencies/item/456" in urls
    assert "https://gdelt.org/article/789" in urls
