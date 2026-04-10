"""Tests for SimilarityScore value object."""

import pytest

from disaster_surveillance_reporter.similarity._types import SimilarityScore


class TestSimilarityScore:
    """Test SimilarityScore value object behavior."""

    def test_given_perfect_scores_when_created_then_should_have_perfect_overall_score(
        self,
    ):
        """
        Given: Perfect similarity scores for all fields
        When: SimilarityScore is created
        Then: Should have overall score of 1.0
        """
        score = SimilarityScore(
            title_score=1.0,
            description_score=1.0,
            location_score=1.0,
            overall_score=1.0,
            threshold=0.8,
        )

        assert score.overall_score == 1.0
        assert score.is_duplicate is True

    def test_given_high_scores_above_threshold_when_checking_duplicate_then_should_return_true(
        self,
    ):
        """
        Given: High similarity scores above threshold (from prototype: 0.952)
        When: Checking if duplicate
        Then: Should return True
        """
        # Using real prototype data - high similarity case
        score = SimilarityScore(
            title_score=0.95,
            description_score=0.94,
            location_score=0.96,
            overall_score=0.952,
            threshold=0.8,
        )

        assert score.is_duplicate is True
        assert score.overall_score > score.threshold

    def test_given_medium_scores_below_threshold_when_checking_duplicate_then_should_return_false(
        self,
    ):
        """
        Given: Medium similarity scores below threshold (from prototype: 0.716)
        When: Checking if duplicate
        Then: Should return False
        """
        # Using real prototype data - medium similarity case
        score = SimilarityScore(
            title_score=0.72,
            description_score=0.70,
            location_score=0.73,
            overall_score=0.716,
            threshold=0.8,
        )

        assert score.is_duplicate is False
        assert score.overall_score < score.threshold

    def test_given_low_scores_when_checking_duplicate_then_should_return_false(self):
        """
        Given: Low similarity scores (from prototype: 0.129)
        When: Checking if duplicate
        Then: Should return False
        """
        # Using real prototype data - low similarity case
        score = SimilarityScore(
            title_score=0.15,
            description_score=0.12,
            location_score=0.10,
            overall_score=0.129,
            threshold=0.8,
        )

        assert score.is_duplicate is False
        assert score.overall_score < score.threshold

    def test_given_edge_case_exactly_at_threshold_when_checking_duplicate_then_should_return_true(
        self,
    ):
        """
        Given: Score exactly at threshold boundary
        When: Checking if duplicate
        Then: Should return True (>= threshold)
        """
        score = SimilarityScore(
            title_score=0.8,
            description_score=0.8,
            location_score=0.8,
            overall_score=0.8,
            threshold=0.8,
        )

        assert score.is_duplicate is True

    def test_given_zero_scores_when_created_then_should_not_be_duplicate(self):
        """
        Given: Zero similarity scores
        When: SimilarityScore is created
        Then: Should not be marked as duplicate
        """
        score = SimilarityScore(
            title_score=0.0,
            description_score=0.0,
            location_score=0.0,
            overall_score=0.0,
            threshold=0.8,
        )

        assert score.is_duplicate is False

    def test_given_different_thresholds_when_same_score_then_duplicate_status_should_vary(
        self,
    ):
        """
        Given: Same overall score with different thresholds
        When: Checking duplicate status
        Then: Should vary based on threshold
        """
        base_args = {
            "title_score": 0.75,
            "description_score": 0.75,
            "location_score": 0.75,
            "overall_score": 0.75,
        }

        low_threshold = SimilarityScore(**base_args, threshold=0.7)
        high_threshold = SimilarityScore(**base_args, threshold=0.8)

        assert low_threshold.is_duplicate is True
        assert high_threshold.is_duplicate is False

    def test_given_similarity_score_when_created_then_should_be_immutable(self):
        """
        Given: A SimilarityScore instance
        When: Attempting to modify attributes
        Then: Should raise AttributeError (frozen dataclass)
        """
        score = SimilarityScore(
            title_score=0.8,
            description_score=0.8,
            location_score=0.8,
            overall_score=0.8,
            threshold=0.8,
        )

        with pytest.raises(AttributeError):
            score.overall_score = 0.9

    def test_given_negative_scores_when_created_then_should_handle_gracefully(self):
        """
        Given: Negative similarity scores (edge case)
        When: SimilarityScore is created
        Then: Should handle gracefully and not be duplicate
        """
        score = SimilarityScore(
            title_score=-0.1,
            description_score=-0.1,
            location_score=-0.1,
            overall_score=-0.1,
            threshold=0.8,
        )

        assert score.is_duplicate is False
        assert score.overall_score == -0.1
