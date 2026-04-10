"""Tests for ContentSimilarityMatcher implementations."""

import time
from unittest.mock import Mock

from disaster_surveillance_reporter.similarity._types import (
    IncidentContent,
    SimilarityScore,
)
from disaster_surveillance_reporter.similarity.matcher import (
    FuzzyContentSimilarityMatcher,
)


class TestFuzzyContentSimilarityMatcher:
    """Test FuzzyContentSimilarityMatcher implementation."""

    def test_given_matcher_with_defaults_when_created_then_should_have_correct_configuration(
        self,
    ):
        """
        Given: FuzzyContentSimilarityMatcher with default parameters
        When: Matcher is created
        Then: Should have correct default configuration
        """
        mock_strategy = Mock()
        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        assert matcher._threshold == 0.8  # Default from prototype
        assert matcher._title_weight == 0.4
        assert matcher._description_weight == 0.4
        assert matcher._location_weight == 0.2
        assert matcher._strategy == mock_strategy

    def test_given_custom_configuration_when_created_then_should_use_custom_values(
        self,
    ):
        """
        Given: FuzzyContentSimilarityMatcher with custom parameters
        When: Matcher is created
        Then: Should use custom configuration values
        """
        mock_strategy = Mock()
        matcher = FuzzyContentSimilarityMatcher(
            strategy=mock_strategy,
            threshold=0.9,
            title_weight=0.5,
            description_weight=0.3,
            location_weight=0.2,
        )

        assert matcher._threshold == 0.9
        assert matcher._title_weight == 0.5
        assert matcher._description_weight == 0.3
        assert matcher._location_weight == 0.2

    def test_given_identical_incidents_when_calculating_similarity_then_should_return_perfect_score(
        self,
    ):
        """
        Given: Two identical incident contents
        When: Computing similarity score
        Then: Should return SimilarityScore with perfect scores
        """
        mock_strategy = Mock()
        mock_strategy.match.return_value = 1.0  # Perfect match for all fields

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        content1 = IncidentContent(
            title="M7.2 Earthquake Tokyo",
            description="Magnitude 7.2 earthquake near Tokyo",
            location="Tokyo, Japan",
            incident_id="test_001",
        )
        content2 = IncidentContent(
            title="M7.2 Earthquake Tokyo",
            description="Magnitude 7.2 earthquake near Tokyo",
            location="Tokyo, Japan",
            incident_id="test_002",
        )

        score = matcher.calculate_similarity(content1, content2)

        assert score.title_score == 1.0
        assert score.description_score == 1.0
        assert score.location_score == 1.0
        assert score.overall_score == 1.0
        assert score.threshold == 0.8
        assert score.is_duplicate is True

    def test_given_prototype_high_similarity_when_calculating_similarity_then_should_match_expected_score(
        self,
    ):
        """
        Given: High similarity incidents from prototype (0.952 overall)
        When: Computing similarity score
        Then: Should match prototype expected scores
        """
        mock_strategy = Mock()
        # Mock individual field scores to achieve ~0.952 overall
        mock_strategy.match.side_effect = [0.95, 0.94, 0.96]  # title, desc, location

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        content1 = IncidentContent(
            title="WHO Health Alert - Disease Outbreak China",
            description="World Health Organization reports disease outbreak",
            location="China",
            incident_id="who_001",
        )
        content2 = IncidentContent(
            title="WHO Alert Disease Outbreak China Regional",
            description="WHO health alert for regional disease outbreak",
            location="China",
            incident_id="who_002",
        )

        score = matcher.calculate_similarity(content1, content2)

        # With weights (0.4, 0.4, 0.2): 0.4*0.95 + 0.4*0.94 + 0.2*0.96 = 0.948
        expected_overall = 0.4 * 0.95 + 0.4 * 0.94 + 0.2 * 0.96
        assert abs(score.overall_score - expected_overall) < 0.001
        assert score.is_duplicate is True  # Above 0.8 threshold

    def test_given_prototype_medium_similarity_when_calculating_similarity_then_should_not_be_duplicate(
        self,
    ):
        """
        Given: Medium similarity incidents from prototype (0.716 overall)
        When: Computing similarity score
        Then: Should not be marked as duplicate (below 0.8 threshold)
        """
        mock_strategy = Mock()
        # Mock scores to achieve ~0.716 overall (below threshold)
        mock_strategy.match.side_effect = [0.72, 0.70, 0.73]

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        content1 = IncidentContent(
            title="M4.5 Earthquake Japan",
            description="Magnitude 4.5 earthquake recorded",
            location="Japan",
            incident_id="gdacs_001",
        )
        content2 = IncidentContent(
            title="M4.7 Earthquake Japan Region",
            description="M4.7 earthquake in Japan regional area",
            location="Japan",
            incident_id="gdacs_002",
        )

        score = matcher.calculate_similarity(content1, content2)

        expected_overall = 0.4 * 0.72 + 0.4 * 0.70 + 0.2 * 0.73
        assert abs(score.overall_score - expected_overall) < 0.001
        assert score.is_duplicate is False  # Below 0.8 threshold

    def test_given_prototype_low_similarity_when_calculating_similarity_then_should_be_very_low_score(
        self,
    ):
        """
        Given: Low similarity incidents from prototype (0.129 overall)
        When: Computing similarity score
        Then: Should return very low score and not be duplicate
        """
        mock_strategy = Mock()
        # Mock low scores
        mock_strategy.match.side_effect = [0.15, 0.12, 0.10]

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        content1 = IncidentContent(
            title="Earthquake Japan",
            description="Seismic activity in Japan",
            location="Japan",
            incident_id="gdacs_001",
        )
        content2 = IncidentContent(
            title="Disease Outbreak Nigeria",
            description="Health emergency in Nigeria",
            location="Nigeria",
            incident_id="promed_001",
        )

        score = matcher.calculate_similarity(content1, content2)

        expected_overall = 0.4 * 0.15 + 0.4 * 0.12 + 0.2 * 0.10
        assert abs(score.overall_score - expected_overall) < 0.001
        assert score.overall_score < 0.2  # Very low
        assert score.is_duplicate is False

    def test_given_empty_incident_list_when_finding_duplicates_then_should_return_empty_result(
        self,
    ):
        """
        Given: Empty list of incidents
        When: Finding duplicates
        Then: Should return DuplicationResult with zero counts
        """
        mock_strategy = Mock()
        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        result = matcher.find_duplicates([])

        assert result.total_incidents == 0
        assert len(result.duplicate_pairs) == 0
        assert len(result.unique_incidents) == 0
        assert result.duplicate_count == 0

    def test_given_single_incident_when_finding_duplicates_then_should_return_no_duplicates(
        self,
    ):
        """
        Given: Single incident in list
        When: Finding duplicates
        Then: Should return no duplicate pairs
        """
        mock_strategy = Mock()
        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        incidents = [IncidentContent("Test", "Description", "Location", "001")]

        result = matcher.find_duplicates(incidents)

        assert result.total_incidents == 1
        assert len(result.duplicate_pairs) == 0
        assert result.unique_incidents == [0]
        assert result.duplicate_count == 0

    def test_given_multiple_incidents_with_duplicates_when_finding_duplicates_then_should_identify_pairs(
        self,
    ):
        """
        Given: Multiple incidents with some duplicates above threshold
        When: Finding duplicates
        Then: Should identify duplicate pairs correctly
        """
        mock_strategy = Mock()
        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        incidents = [
            IncidentContent("Earthquake A", "Desc A", "Location A", "001"),
            IncidentContent(
                "Earthquake B", "Desc B", "Location B", "002"
            ),  # Similar to A
            IncidentContent("Disease X", "Desc X", "Location X", "003"),  # Different
        ]

        # Mock similarity calculations
        call_count = 0

        def mock_similarity(content1, content2):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # incidents[0] vs incidents[1]
                return SimilarityScore(0.9, 0.9, 0.9, 0.9, 0.8)  # Duplicate
            # Other comparisons
            return SimilarityScore(0.1, 0.1, 0.1, 0.1, 0.8)  # Not duplicate

        matcher.calculate_similarity = Mock(side_effect=mock_similarity)

        result = matcher.find_duplicates(incidents)

        assert result.total_incidents == 3
        assert len(result.duplicate_pairs) == 1
        assert result.duplicate_pairs[0][0] == 0  # First incident index
        assert result.duplicate_pairs[0][1] == 1  # Second incident index
        assert result.duplicate_pairs[0][2].overall_score == 0.9
        assert result.duplicate_count == 2  # Both incidents involved in duplicate

    def test_given_performance_requirements_when_processing_large_dataset_then_should_complete_within_target(
        self,
    ):
        """
        Given: Performance requirement of <10 seconds for 1000+ incidents
        When: Processing large dataset
        Then: Should complete within performance target
        """
        mock_strategy = Mock()
        mock_strategy.match.return_value = 0.5  # Medium similarity

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        # Create smaller dataset for test (full 1000 would be too slow for unit test)
        incidents = [
            IncidentContent(
                f"Incident {i}", f"Description {i}", f"Location {i}", f"id_{i}"
            )
            for i in range(50)  # 50 incidents = 1225 comparisons
        ]

        start_time = time.time()
        result = matcher.find_duplicates(incidents)
        elapsed_time = time.time() - start_time

        # Should complete quickly (scaled expectation for 50 incidents)
        assert elapsed_time < 1.0  # Generous bound for 50 incidents
        assert result.total_incidents == 50
        assert result.processing_time_ms > 0

    def test_given_threshold_boundary_when_finding_duplicates_then_should_handle_edge_cases(
        self,
    ):
        """
        Given: Similarities exactly at threshold boundary
        When: Finding duplicates
        Then: Should handle edge cases correctly (>= threshold)
        """
        mock_strategy = Mock()
        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy, threshold=0.8)

        incidents = [
            IncidentContent("Test A", "Desc A", "Loc A", "001"),
            IncidentContent("Test B", "Desc B", "Loc B", "002"),
        ]

        # Mock exact threshold match
        exact_threshold_score = SimilarityScore(0.8, 0.8, 0.8, 0.8, 0.8)
        matcher.calculate_similarity = Mock(return_value=exact_threshold_score)

        result = matcher.find_duplicates(incidents)

        assert len(result.duplicate_pairs) == 1  # Should be duplicate (>= threshold)
        assert result.duplicate_pairs[0][2].overall_score == 0.8

    def test_given_missing_fields_when_calculating_similarity_then_should_handle_gracefully(
        self,
    ):
        """
        Given: Incidents with empty or missing fields
        When: Computing similarity
        Then: Should handle gracefully without errors
        """
        mock_strategy = Mock()
        mock_strategy.match.return_value = 0.0  # No match for empty fields

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        content1 = IncidentContent("", "", "", "001")  # Empty fields
        content2 = IncidentContent("Test", "Description", "Location", "002")

        score = matcher.calculate_similarity(content1, content2)

        assert score.title_score == 0.0
        assert score.description_score == 0.0
        assert score.location_score == 0.0
        assert score.overall_score == 0.0
        assert score.is_duplicate is False

    def test_given_custom_weights_when_calculating_similarity_then_should_apply_correct_weighting(
        self,
    ):
        """
        Given: Custom field weights configuration
        When: Computing similarity score
        Then: Should apply custom weighting correctly
        """
        mock_strategy = Mock()
        mock_strategy.match.side_effect = [0.8, 0.6, 1.0]  # title, desc, location

        # Custom weights: prioritize location over other fields
        matcher = FuzzyContentSimilarityMatcher(
            strategy=mock_strategy,
            title_weight=0.2,
            description_weight=0.2,
            location_weight=0.6,  # High weight on location
        )

        content1 = IncidentContent("A", "B", "C", "001")
        content2 = IncidentContent("X", "Y", "C", "002")

        score = matcher.calculate_similarity(content1, content2)

        # Expected: 0.2*0.8 + 0.2*0.6 + 0.6*1.0 = 0.16 + 0.12 + 0.6 = 0.88
        expected_overall = 0.2 * 0.8 + 0.2 * 0.6 + 0.6 * 1.0
        assert abs(score.overall_score - expected_overall) < 0.001

    def test_given_duplicate_result_when_created_then_should_track_processing_time(
        self,
    ):
        """
        Given: Duplicate detection process
        When: DuplicationResult is created
        Then: Should track processing time accurately
        """
        mock_strategy = Mock()
        mock_strategy.match.return_value = 0.5

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        incidents = [
            IncidentContent(f"Incident {i}", f"Desc {i}", f"Loc {i}", f"id_{i}")
            for i in range(5)
        ]

        result = matcher.find_duplicates(incidents)

        # Should have measured processing time
        assert result.processing_time_ms >= 0
        assert isinstance(result.processing_time_ms, float)
