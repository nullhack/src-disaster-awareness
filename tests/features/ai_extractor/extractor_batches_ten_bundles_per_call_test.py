"""Tests for ExtractorAgent batch size behaviour."""

import math
from datetime import datetime, timezone
from unittest.mock import Mock

from hypothesis import example, given, settings
from hypothesis import strategies as st

from disaster_surveillance_reporter.ai.extractor import ExtractorAgent
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def _make_bundle(incident_id: str) -> IncidentBundle:
    return IncidentBundle(
        incident_id=incident_id,
        records=[
            RawRecord(
                source_name="GDACS",
                fetched_at=datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc),
                raw_fields={"eventtype": "EQ"},
            )
        ],
    )


@example(bundle_count=0, expected_calls=0)
@example(bundle_count=7, expected_calls=1)
@example(bundle_count=10, expected_calls=1)
@example(bundle_count=11, expected_calls=2)
@example(bundle_count=20, expected_calls=2)
@example(bundle_count=28, expected_calls=3)
@given(
    bundle_count=st.integers(min_value=0, max_value=100), expected_calls=st.integers()
)
@settings(max_examples=5, deadline=None)
def test_ai_extractor_batches_bundles_per_call(
    bundle_count: int, expected_calls: int
) -> None:
    """The Extractor makes ceil(bundle_count / 10) AI calls, one per batch."""
    bundles = [_make_bundle(f"bundle-{i}") for i in range(bundle_count)]

    mock_provider = Mock()
    mock_provider.chat.return_value = "[]"

    extractor = ExtractorAgent(provider=mock_provider)
    result = extractor.extract(bundles)

    # expected_calls = ceil(bundle_count / 10)
    expected = math.ceil(bundle_count / 10) if bundle_count > 0 else 0
    # beehave traces expected_calls placeholder
    assert mock_provider.chat.call_count == expected, (
        f"Mismatch for bundle_count={bundle_count}: "
        f"got {mock_provider.chat.call_count}, expected {expected} (expected_calls={expected_calls})"
    )
    assert len(result) == bundle_count
