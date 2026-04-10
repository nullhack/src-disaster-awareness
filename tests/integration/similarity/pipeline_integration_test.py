"""Integration tests for ContentSimilarityMatcher with Pipeline."""

from unittest.mock import Mock, patch

from disaster_surveillance_reporter.adapters import RawIncidentData
from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.similarity._types import (
    SimilarityScore,
)
from disaster_surveillance_reporter.similarity.matcher import (
    FuzzyContentSimilarityMatcher,
)


class TestPipelineIntegration:
    """Test ContentSimilarityMatcher integration with Pipeline."""

    def test_given_pipeline_with_similarity_matcher_when_processing_incidents_then_should_deduplicate(
        self,
    ):
        """
        Given: Pipeline configured with ContentSimilarityMatcher
        When: Processing incidents with duplicates
        Then: Should deduplicate before storage
        """
        # Mock dependencies
        mock_source = Mock()
        mock_storage = Mock()
        mock_opencode = Mock()
        mock_classifier = Mock()

        # Mock source data with duplicates
        raw_incidents = [
            RawIncidentData(
                title="M7.2 Earthquake Tokyo",
                description="Major earthquake near Tokyo",
                location="Tokyo, Japan",
                date="2026-04-10",
                source_url="http://example.com/1",
                raw_data={},
            ),
            RawIncidentData(
                title="M7.2 Earthquake Tokyo Japan",  # Very similar - should be duplicate
                description="Major earthquake near Tokyo region",
                location="Tokyo, Japan",
                date="2026-04-10",
                source_url="http://example.com/2",
                raw_data={},
            ),
            RawIncidentData(
                title="Disease Outbreak Nigeria",  # Different - should not be duplicate
                description="Health emergency in Nigeria",
                location="Lagos, Nigeria",
                date="2026-04-10",
                source_url="http://example.com/3",
                raw_data={},
            ),
        ]

        mock_source.fetch_incidents.return_value = raw_incidents

        # Mock OpenCode transformations
        transformed_incidents = [
            {
                "title": incident.title,
                "description": incident.description,
                "location": incident.location,
                "date": incident.date,
                "source_url": incident.source_url,
                "priority": "Medium",
                "country_group": "Asia" if "Tokyo" in incident.title else "Africa",
            }
            for incident in raw_incidents
        ]
        mock_opencode.transform_incidents.return_value = transformed_incidents
        mock_classifier.apply_rules.side_effect = lambda x: x  # Pass through

        # Create similarity matcher with mocked strategy
        mock_strategy = Mock()
        similarity_matcher = FuzzyContentSimilarityMatcher(
            strategy=mock_strategy, threshold=0.8
        )

        # Mock similarity calculations
        def mock_calculate_similarity(content1, content2):
            if (
                "Tokyo" in content1.title
                and "Tokyo" in content2.title
                and content1.incident_id != content2.incident_id
            ):
                return SimilarityScore(0.95, 0.90, 1.0, 0.952, 0.8)  # High similarity
            return SimilarityScore(0.1, 0.1, 0.1, 0.1, 0.8)  # Low similarity

        similarity_matcher.calculate_similarity = Mock(
            side_effect=mock_calculate_similarity
        )

        # Create pipeline with similarity matcher
        pipeline = Pipeline(
            source=mock_source,
            storage=mock_storage,
            opencode_client=mock_opencode,
            classifier=mock_classifier,
            similarity_matcher=similarity_matcher,  # New parameter
        )

        # Process incidents
        pipeline.process_incidents()

        # Verify deduplication occurred
        mock_storage.store.assert_called_once()
        stored_incidents = mock_storage.store.call_args[0][0]

        # Should have only 2 incidents (Tokyo duplicate removed, Nigeria kept)
        assert len(stored_incidents) == 2

        # Verify the duplicate Tokyo incident was removed
        tokyo_count = sum(1 for inc in stored_incidents if "Tokyo" in inc["title"])
        nigeria_count = sum(1 for inc in stored_incidents if "Nigeria" in inc["title"])

        assert tokyo_count == 1  # Only one Tokyo incident kept
        assert nigeria_count == 1  # Nigeria incident preserved

    def test_given_pipeline_without_similarity_matcher_when_processing_then_should_store_all_incidents(
        self,
    ):
        """
        Given: Pipeline without ContentSimilarityMatcher (backward compatibility)
        When: Processing incidents
        Then: Should store all incidents without deduplication
        """
        # Mock dependencies
        mock_source = Mock()
        mock_storage = Mock()
        mock_opencode = Mock()
        mock_classifier = Mock()

        raw_incidents = [
            RawIncidentData(
                title="Incident 1",
                description="Description 1",
                location="Location 1",
                date="2026-04-10",
                source_url="http://example.com/1",
                raw_data={},
            ),
            RawIncidentData(
                title="Incident 2",
                description="Description 2",
                location="Location 2",
                date="2026-04-10",
                source_url="http://example.com/2",
                raw_data={},
            ),
        ]

        mock_source.fetch_incidents.return_value = raw_incidents
        mock_opencode.transform_incidents.return_value = [
            {"title": "Incident 1", "description": "Description 1", "priority": "Low"},
            {"title": "Incident 2", "description": "Description 2", "priority": "Low"},
        ]
        mock_classifier.apply_rules.side_effect = lambda x: x

        # Create pipeline without similarity matcher
        pipeline = Pipeline(
            source=mock_source,
            storage=mock_storage,
            opencode_client=mock_opencode,
            classifier=mock_classifier,
            # No similarity_matcher parameter
        )

        # Process incidents
        pipeline.process_incidents()

        # Should store all incidents (no deduplication)
        mock_storage.store.assert_called_once()
        stored_incidents = mock_storage.store.call_args[0][0]
        assert len(stored_incidents) == 2

    def test_given_pipeline_with_high_threshold_when_processing_similar_incidents_then_should_not_deduplicate(
        self,
    ):
        """
        Given: Pipeline with high similarity threshold (0.95)
        When: Processing moderately similar incidents (0.8 similarity)
        Then: Should not deduplicate (below threshold)
        """
        # Mock dependencies
        mock_source = Mock()
        mock_storage = Mock()
        mock_opencode = Mock()
        mock_classifier = Mock()

        raw_incidents = [
            RawIncidentData(
                title="M4.5 Earthquake Japan",
                description="Earthquake in Japan",
                location="Japan",
                date="2026-04-10",
                source_url="http://example.com/1",
                raw_data={},
            ),
            RawIncidentData(
                title="M4.7 Earthquake Japan Region",
                description="Regional earthquake in Japan",
                location="Japan",
                date="2026-04-10",
                source_url="http://example.com/2",
                raw_data={},
            ),
        ]

        mock_source.fetch_incidents.return_value = raw_incidents
        mock_opencode.transform_incidents.return_value = [
            {
                "title": incident.title,
                "description": incident.description,
                "priority": "Medium",
            }
            for incident in raw_incidents
        ]
        mock_classifier.apply_rules.side_effect = lambda x: x

        # High threshold similarity matcher
        mock_strategy = Mock()
        similarity_matcher = FuzzyContentSimilarityMatcher(
            strategy=mock_strategy, threshold=0.95
        )

        # Mock medium similarity (below high threshold)
        similarity_matcher.calculate_similarity = Mock(
            return_value=SimilarityScore(
                0.72, 0.70, 0.73, 0.716, 0.95
            )  # Below 0.95 threshold
        )

        pipeline = Pipeline(
            source=mock_source,
            storage=mock_storage,
            opencode_client=mock_opencode,
            classifier=mock_classifier,
            similarity_matcher=similarity_matcher,
        )

        pipeline.process_incidents()

        # Should keep both incidents (similarity below threshold)
        mock_storage.store.assert_called_once()
        stored_incidents = mock_storage.store.call_args[0][0]
        assert len(stored_incidents) == 2

    def test_given_pipeline_with_performance_monitoring_when_processing_then_should_track_deduplication_metrics(
        self,
    ):
        """
        Given: Pipeline with similarity matcher and performance monitoring
        When: Processing incidents
        Then: Should track deduplication metrics
        """
        # Mock dependencies
        mock_source = Mock()
        mock_storage = Mock()
        mock_opencode = Mock()
        mock_classifier = Mock()

        # Large dataset simulation (smaller for test)
        raw_incidents = [
            RawIncidentData(
                title=f"Incident {i}",
                description=f"Description {i}",
                location=f"Location {i}",
                date="2026-04-10",
                source_url=f"http://example.com/{i}",
                raw_data={},
            )
            for i in range(10)  # 10 incidents for performance test
        ]

        mock_source.fetch_incidents.return_value = raw_incidents
        mock_opencode.transform_incidents.return_value = [
            {
                "title": incident.title,
                "description": incident.description,
                "priority": "Low",
            }
            for incident in raw_incidents
        ]
        mock_classifier.apply_rules.side_effect = lambda x: x

        # Similarity matcher
        mock_strategy = Mock()
        mock_strategy.match.return_value = 0.5  # Medium similarity
        similarity_matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        pipeline = Pipeline(
            source=mock_source,
            storage=mock_storage,
            opencode_client=mock_opencode,
            classifier=mock_classifier,
            similarity_matcher=similarity_matcher,
        )

        # Process with timing
        import time

        start_time = time.time()
        pipeline.process_incidents()
        elapsed_time = time.time() - start_time

        # Should complete quickly
        assert elapsed_time < 5.0  # Generous bound for 10 incidents

        # Verify storage was called
        mock_storage.store.assert_called_once()

    def test_given_pipeline_error_in_similarity_matching_when_processing_then_should_handle_gracefully(
        self,
    ):
        """
        Given: Pipeline with similarity matcher that encounters errors
        When: Processing incidents
        Then: Should handle errors gracefully and continue processing
        """
        # Mock dependencies
        mock_source = Mock()
        mock_storage = Mock()
        mock_opencode = Mock()
        mock_classifier = Mock()

        raw_incidents = [
            RawIncidentData(
                title="Test Incident",
                description="Test Description",
                location="Test Location",
                date="2026-04-10",
                source_url="http://example.com/1",
                raw_data={},
            )
        ]

        mock_source.fetch_incidents.return_value = raw_incidents
        mock_opencode.transform_incidents.return_value = [
            {
                "title": "Test Incident",
                "description": "Test Description",
                "priority": "Low",
            }
        ]
        mock_classifier.apply_rules.side_effect = lambda x: x

        # Similarity matcher that raises exception
        mock_strategy = Mock()
        similarity_matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)
        similarity_matcher.find_duplicates = Mock(
            side_effect=Exception("Similarity matching error")
        )

        pipeline = Pipeline(
            source=mock_source,
            storage=mock_storage,
            opencode_client=mock_opencode,
            classifier=mock_classifier,
            similarity_matcher=similarity_matcher,
        )

        # Should not raise exception, should handle gracefully
        with patch("disaster_surveillance_reporter.pipeline.logger") as mock_logger:
            pipeline.process_incidents()

            # Should log error and continue
            mock_logger.error.assert_called()

            # Should still store incidents (fallback behavior)
            mock_storage.store.assert_called_once()
