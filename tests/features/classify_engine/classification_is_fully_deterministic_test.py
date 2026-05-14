"""Tests for classification_is_fully_deterministic."""

import datetime
import pickle  # noqa: S403

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_identical_input_bundles_produce_identical_classification_output():
    """Test identical input bundles produce identical classification output."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record1 = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Orange", "country": "Japan"},
    )
    record2 = RawRecord(
        source_name="WHO",
        fetched_at=now,
        raw_fields={"text": "pandemic outbreak"},
    )
    bundle1 = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record1, record2],
        country="Japan",
    )
    # Deep copy via pickle for a truly independent identical input
    bundle2 = pickle.loads(pickle.dumps(bundle1))  # noqa: S301

    result1 = ClassifyEngine().classify(bundle1)
    result2 = ClassifyEngine().classify(bundle2)

    assert result1.incident_level == result2.incident_level
    assert result1.priority == result2.priority
    assert result1.country_group == result2.country_group
    assert result1.should_report == result2.should_report
    assert result1.overrides == result2.overrides
