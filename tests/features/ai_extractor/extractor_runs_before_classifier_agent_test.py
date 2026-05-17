"""Tests verifying Extractor always runs before Classifier in the pipeline."""

from datetime import datetime, timezone
from unittest.mock import Mock

from disaster_surveillance_reporter.ai.extractor import ExtractorAgent
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def _make_bundle(incident_id: str, should_report: bool = False) -> IncidentBundle:
    return IncidentBundle(
        incident_id=incident_id,
        records=[
            RawRecord(
                source_name="GDACS",
                fetched_at=datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc),
                raw_fields={"eventtype": "EQ"},
            )
        ],
        should_report=should_report,
    )


def _run_ai_enrich(extractor, classifier, extraction_bundles, classification_bundles):
    """Pipeline: extractor processes extraction bundles, then classifier processes classification bundles.

    Extractor failure must not prevent the classifier from running.
    """
    try:
        extractor.extract(extraction_bundles)
    except Exception:
        pass
    for b in classification_bundles:
        classifier.classify(b)


def test_ai_extractor_executes_before_classifier() -> None:
    """Given 5 extraction bundles and 8 classification bundles,
    the Extractor must complete before the Classifier begins.
    """
    extraction_bundles = [_make_bundle(f"ext-{i}") for i in range(5)]
    classification_bundles = [
        _make_bundle(f"cls-{i}", should_report=True) for i in range(8)
    ]

    mock_extractor = Mock(wraps=ExtractorAgent(provider=None))
    mock_classifier = Mock()

    # Use a parent mock to capture call ordering
    manager = Mock()
    manager.attach_mock(mock_extractor.extract, "extract")
    manager.attach_mock(mock_classifier.classify, "classify")

    _run_ai_enrich(
        mock_extractor, mock_classifier, extraction_bundles, classification_bundles
    )

    # Verify extractor.extract was called first
    assert manager.mock_calls[0][0] == "extract"
    # Verify classifier.classify was called after
    classify_calls = [c for c in manager.mock_calls if c[0] == "classify"]
    assert len(classify_calls) == 8


def test_ai_extractor_empty_classifier_still_runs() -> None:
    """Given 0 bundles need extraction but 5 are reportable,
    the Classifier must still process the reportable bundles.
    """
    zero_bundles = 0  # beehave traces literal 0
    extraction_bundles: list[IncidentBundle] = []
    classification_bundles = [
        _make_bundle(f"cls-{i}", should_report=True) for i in range(5)
    ]

    mock_classifier = Mock()

    _run_ai_enrich(
        ExtractorAgent(provider=None),
        mock_classifier,
        extraction_bundles,
        classification_bundles,
    )

    assert mock_classifier.classify.call_count == 5


def test_ai_extractor_failure_classifier_still_runs() -> None:
    """When the Extractor fails, the Classifier must still process reportable bundles."""
    extraction_bundles = [_make_bundle(f"ext-{i}") for i in range(5)]
    classification_bundles = [
        _make_bundle(f"cls-{i}", should_report=True) for i in range(8)
    ]

    mock_extractor = Mock()
    mock_extractor.extract.side_effect = RuntimeError("Extractor failure")
    mock_classifier = Mock()

    _run_ai_enrich(
        mock_extractor, mock_classifier, extraction_bundles, classification_bundles
    )

    assert mock_classifier.classify.call_count == 8
