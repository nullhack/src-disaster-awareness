"""Tests for DuplicationResult value object."""

import pytest

from disaster_surveillance_reporter.similarity._types import (
    DuplicationResult,
    SimilarityScore,
)


class TestDuplicationResult:
    """Test DuplicationResult value object behavior."""

    def test_given_no_duplicates_when_created_then_should_have_zero_duplicate_count(
        self,
    ):
        """
        Given: Dataset with no duplicates
        When: DuplicationResult is created
        Then: Should have duplicate count of zero
        """
        result = DuplicationResult(
            total_incidents=10,
            duplicate_pairs=[],
            unique_incidents=list(range(10)),
            processing_time_ms=100.5,
        )

        assert result.duplicate_count == 0
        assert len(result.duplicate_pairs) == 0
        assert len(result.unique_incidents) == 10

    def test_given_duplicate_pairs_when_calculating_count_then_should_count_unique_incidents(
        self,
    ):
        """
        Given: Multiple duplicate pairs with some overlapping incidents
        When: Calculating duplicate count
        Then: Should count unique incidents involved in duplicates
        """
        # Create mock similarity scores
        high_score = SimilarityScore(0.95, 0.94, 0.96, 0.952, 0.8)
        medium_score = SimilarityScore(0.85, 0.84, 0.86, 0.851, 0.8)

        # Incident 0 duplicates with 1, and 1 duplicates with 2
        # So incidents 0, 1, 2 are all involved in duplicates = 3 total
        result = DuplicationResult(
            total_incidents=5,
            duplicate_pairs=[(0, 1, high_score), (1, 2, medium_score)],
            unique_incidents=[3, 4],
            processing_time_ms=50.2,
        )

        assert result.duplicate_count == 3  # incidents 0, 1, 2
        assert len(result.duplicate_pairs) == 2

    def test_given_multiple_separate_duplicate_pairs_when_calculating_count_then_should_count_all_involved(
        self,
    ):
        """
        Given: Multiple separate duplicate pairs (no overlap)
        When: Calculating duplicate count
        Then: Should count all incidents involved
        """
        high_score = SimilarityScore(0.95, 0.94, 0.96, 0.952, 0.8)

        # Two separate pairs: (0,1) and (2,3)
        result = DuplicationResult(
            total_incidents=6,
            duplicate_pairs=[(0, 1, high_score), (2, 3, high_score)],
            unique_incidents=[4, 5],
            processing_time_ms=75.8,
        )

        assert result.duplicate_count == 4  # incidents 0, 1, 2, 3

    def test_given_single_duplicate_pair_when_calculating_count_then_should_count_both_incidents(
        self,
    ):
        """
        Given: Single duplicate pair
        When: Calculating duplicate count
        Then: Should count both incidents as duplicates
        """
        high_score = SimilarityScore(0.95, 0.94, 0.96, 0.952, 0.8)

        result = DuplicationResult(
            total_incidents=3,
            duplicate_pairs=[(0, 1, high_score)],
            unique_incidents=[2],
            processing_time_ms=25.1,
        )

        assert result.duplicate_count == 2  # incidents 0, 1

    def test_given_large_dataset_results_when_created_then_should_handle_performance_metrics(
        self,
    ):
        """
        Given: Results from large dataset processing (1000+ incidents)
        When: DuplicationResult is created
        Then: Should handle performance metrics correctly
        """
        # Simulate prototype performance: 1000 incidents in ~7400ms
        result = DuplicationResult(
            total_incidents=1000,
            duplicate_pairs=[],  # Assume no duplicates for simplicity
            unique_incidents=list(range(1000)),
            processing_time_ms=7400.0,
        )

        assert result.total_incidents == 1000
        assert result.processing_time_ms == 7400.0
        assert result.duplicate_count == 0

    def test_given_prototype_threshold_results_when_created_then_should_match_expected_rates(
        self,
    ):
        """
        Given: Results matching prototype threshold analysis (0.3% at 0.8 threshold)
        When: DuplicationResult is created
        Then: Should match expected duplicate rates
        """
        high_score = SimilarityScore(0.90, 0.91, 0.89, 0.901, 0.8)

        # Prototype showed 5 duplicate pairs out of 1584 comparisons = 0.3%
        # With 33 incidents, that's ~1-2 pairs
        result = DuplicationResult(
            total_incidents=33,
            duplicate_pairs=[(5, 12, high_score), (8, 15, high_score)],
            unique_incidents=list(range(33)),
            processing_time_ms=8.5,  # Fast processing for small dataset
        )

        duplicate_rate = (result.duplicate_count / result.total_incidents) * 100
        assert duplicate_rate <= 15.0  # Should be low rate as per prototype

    def test_given_duplication_result_when_created_then_should_be_immutable(self):
        """
        Given: A DuplicationResult instance
        When: Attempting to modify attributes
        Then: Should raise AttributeError (frozen dataclass)
        """
        result = DuplicationResult(
            total_incidents=5,
            duplicate_pairs=[],
            unique_incidents=[0, 1, 2, 3, 4],
            processing_time_ms=50.0,
        )

        with pytest.raises(AttributeError):
            result.total_incidents = 10

    def test_given_empty_dataset_when_created_then_should_handle_gracefully(self):
        """
        Given: Empty dataset results
        When: DuplicationResult is created
        Then: Should handle gracefully with zero counts
        """
        result = DuplicationResult(
            total_incidents=0,
            duplicate_pairs=[],
            unique_incidents=[],
            processing_time_ms=0.1,
        )

        assert result.duplicate_count == 0
        assert result.total_incidents == 0
        assert len(result.duplicate_pairs) == 0
        assert len(result.unique_incidents) == 0

    def test_given_complex_overlap_scenario_when_calculating_count_then_should_handle_correctly(
        self,
    ):
        """
        Given: Complex scenario with overlapping duplicate relationships
        When: Calculating duplicate count
        Then: Should correctly count unique incidents
        """
        high_score = SimilarityScore(0.95, 0.94, 0.96, 0.952, 0.8)

        # Complex case: 0-1, 1-2, 3-4, 4-5
        # Unique incidents involved: 0,1,2,3,4,5 = 6 total
        result = DuplicationResult(
            total_incidents=10,
            duplicate_pairs=[
                (0, 1, high_score),
                (1, 2, high_score),
                (3, 4, high_score),
                (4, 5, high_score),
            ],
            unique_incidents=[6, 7, 8, 9],
            processing_time_ms=85.0,
        )

        assert result.duplicate_count == 6  # incidents 0,1,2,3,4,5
