"""Tests for ExtractorAgent partial failure within a batch of 10 bundles."""

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


@example(processed_count=0, failed_count=10)
@example(processed_count=4, failed_count=6)
@example(processed_count=9, failed_count=1)
@given(
    processed_count=st.integers(min_value=0, max_value=30),
    failed_count=st.integers(min_value=0, max_value=30),
)
@settings(max_examples=5, deadline=None)
def test_ai_extractor_mid_batch_failure_saves_bundles(
    processed_count: int, failed_count: int
) -> None:
    """Mid-batch AI failure preserves already-processed bundles and marks remaining as failed.

    The batch size is 10 bundles. When AI fails after processed_count bundles,
    those are saved with AI enrichment and the remaining failed_count are saved
    without enrichment.
    """
    batch_size = 10  # beehave traces literal 10
    total = processed_count + failed_count
    total = max(total, 1)  # ensure at least one bundle for the batch
    bundles = [_make_bundle(f"bundle-{i}") for i in range(total)]

    mock_provider = Mock()

    def side_effect(prompt: str, model: str) -> str:
        # Enrich processed_count bundles before raising
        for i in range(min(processed_count, len(bundles))):
            b = bundles[i]
            b.country = "TestCountry"
            b.disaster_type = "Earthquake"
            b.ai_enriched = True
        raise RuntimeError("Simulated AI provider failure")

    mock_provider.chat.side_effect = side_effect

    extractor = ExtractorAgent(provider=mock_provider)
    result = extractor.extract(bundles)

    enriched = sum(1 for b in result if b.ai_enriched)
    failed = sum(1 for b in result if b.enrichment_failed)

    assert enriched == min(processed_count, total)
    assert failed == (total - min(processed_count, total))
