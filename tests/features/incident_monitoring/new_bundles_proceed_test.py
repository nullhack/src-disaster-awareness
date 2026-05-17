from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def _make_pipeline(storage_backend):
    return Pipeline(
        adapters=[],
        correlator=MagicMock(),
        classify_engine=MagicMock(),
        news_searcher=MagicMock(),
        extractor=MagicMock(),
        classifier=MagicMock(),
        storage_backend=storage_backend,
    )


def test_new_bundle_proceeds_through_pipeline():
    now = datetime.now(tz=timezone.utc)
    storage = MagicMock()
    storage.get_active_bundles.return_value = []
    storage.exists.return_value = False
    pipeline = _make_pipeline(storage)

    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"eventid": "12345"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-PH-EQ",
        records=[record],
        last_updated=now,
    )
    result = pipeline._active_status_check([bundle])
    assert len(result) == 1
    assert result[0].incident_id == "20260514-PH-EQ"
