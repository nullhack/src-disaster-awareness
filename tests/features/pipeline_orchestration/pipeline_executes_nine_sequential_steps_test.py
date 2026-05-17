"""Test: Pipeline executes nine sequential steps."""

from unittest.mock import MagicMock, patch

import datetime as dt

from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_pipeline_completes_all_nine_steps():
    """Pipeline orchestrates all nine steps in specified order."""
    # Create mock dependencies for Pipeline constructor
    mock_correlator = MagicMock()
    mock_classify_engine = MagicMock()
    mock_news_searcher = MagicMock()
    mock_extractor = MagicMock()
    mock_classifier = MagicMock()
    mock_storage = MagicMock()
    mock_adapter = MagicMock()

    pipeline = Pipeline(
        adapters=[mock_adapter],
        correlator=mock_correlator,
        classify_engine=mock_classify_engine,
        news_searcher=mock_news_searcher,
        extractor=mock_extractor,
        classifier=mock_classifier,
        storage_backend=mock_storage,
    )

    now = dt.datetime.now(tz=dt.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"title": "Test Incident"},
    )
    shared_records = [record]

    reportable_bundle = IncidentBundle(
        incident_id="20260514-PH-EQ",
        records=shared_records,
        country="Philippines",
    )
    not_reportable_bundle = IncidentBundle(
        incident_id="20260514-FR-OTH",
        records=shared_records,
        country="France",
    )
    all_bundles = [reportable_bundle, not_reportable_bundle]

    call_order: list[str] = []

    def _step(name, *, passthrough=False, return_value=None):
        """Create a side_effect that records the call and returns the right value."""
        def _fn(*args):
            call_order.append(name)
            if passthrough:
                return args[0]
            return return_value
        return _fn

    def _classify_side_effect(bundles):
        call_order.append("_classify_initial")
        reportable_bundle.should_report = True
        not_reportable_bundle.should_report = False
        return bundles

    with (
        patch.object(pipeline, "_fetch_sources",
                     side_effect=_step("_fetch_sources", return_value=shared_records)),
        patch.object(pipeline, "_pre_filter",
                     side_effect=_step("_pre_filter", passthrough=True)),
        patch.object(pipeline, "_correlate_records",
                     side_effect=_step("_correlate_records", return_value=all_bundles)),
        patch.object(pipeline, "_classify_initial",
                     side_effect=_classify_side_effect),
        patch.object(pipeline, "_store_bundles",
                     side_effect=_step("_store_bundles", return_value={"inserted": 1})),
        patch.object(pipeline, "_active_status_check",
                     side_effect=_step("_active_status_check", passthrough=True)),
        patch.object(pipeline, "_supplementary_search",
                     side_effect=_step("_supplementary_search", passthrough=True)),
        patch.object(pipeline, "_ai_enrich",
                     side_effect=_step("_ai_enrich", passthrough=True)),
        patch.object(pipeline, "_reclassify_overrides",
                     side_effect=_step("_reclassify_overrides", passthrough=True)),
    ):
        pipeline.run()

    # Nine sequential pipeline steps in v4 order:
    # A: Fetch → B: Pre-filter → C: Correlate → D: Classify →
    #   (D-exit: store not-reportable) →
    #   E: Active-Status Check → F: Supplementary Search →
    #   G: AI Enrich → H: Override Re-eval → I: Store (reportable)
    expected_order = [
        "_fetch_sources",        # A: Fetch
        "_pre_filter",           # B: Source Pre-filter
        "_correlate_records",    # C: Correlate
        "_classify_initial",     # D: Classify
        "_store_bundles",        # D-exit: store not-reportable
        "_active_status_check",  # E: Active-Status Check
        "_supplementary_search", # F: Supplementary DDG Search
        "_ai_enrich",            # G: AI Enrich
        "_reclassify_overrides", # H: Override Re-evaluation
        "_store_bundles",        # I: Store (reportable upsert)
    ]

    assert call_order == expected_order
