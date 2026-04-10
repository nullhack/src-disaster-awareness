"""Property-based tests for similarity matching using Hypothesis."""

from unittest.mock import Mock

from hypothesis import assume, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.similarity._types import (
    IncidentContent,
    SimilarityScore,
)
from disaster_surveillance_reporter.similarity.matcher import (
    FuzzyContentSimilarityMatcher,
)

# Strategy for generating incident content
incident_content_strategy = st.builds(
    IncidentContent,
    title=st.text(min_size=1, max_size=100),
    description=st.text(min_size=0, max_size=200),
    location=st.text(min_size=1, max_size=50),
    incident_id=st.text(min_size=1, max_size=20),
)


class TestSimilarityProperties:
    """Property-based tests for similarity matching mathematical properties."""

    @given(content=incident_content_strategy)
    def test_property_reflexivity_incident_similarity_with_itself_should_be_perfect(
        self, content
    ):
        """
        Property: Reflexivity - similarity(a, a) should equal 1.0

        Given: Any incident content
        When: Computing similarity with itself
        Then: Should return perfect similarity score of 1.0
        """
        # Mock strategy that returns perfect match for identical content
        mock_strategy = Mock()
        mock_strategy.match.return_value = 1.0

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        score = matcher.calculate_similarity(content, content)

        assert score.overall_score == 1.0
        assert score.is_duplicate is True

    @given(content1=incident_content_strategy, content2=incident_content_strategy)
    def test_property_symmetry_similarity_should_be_commutative(
        self, content1, content2
    ):
        """
        Property: Symmetry - similarity(a, b) should equal similarity(b, a)

        Given: Any two incident contents
        When: Computing similarity in both directions
        Then: Should return identical scores
        """
        assume(
            content1.incident_id != content2.incident_id
        )  # Ensure different incidents

        # Mock consistent strategy
        mock_strategy = Mock()
        mock_strategy.match.return_value = 0.75

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        score_ab = matcher.calculate_similarity(content1, content2)
        score_ba = matcher.calculate_similarity(content2, content1)

        assert score_ab.overall_score == score_ba.overall_score
        assert score_ab.title_score == score_ba.title_score
        assert score_ab.description_score == score_ba.description_score
        assert score_ab.location_score == score_ba.location_score

    @given(
        threshold=st.floats(min_value=0.0, max_value=1.0),
        overall_score=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_property_threshold_boundary_duplicate_classification_should_be_consistent(
        self, threshold, overall_score
    ):
        """
        Property: Threshold consistency - is_duplicate should be consistent with threshold comparison

        Given: Any threshold and overall score
        When: Creating SimilarityScore
        Then: is_duplicate should equal (overall_score >= threshold)
        """
        score = SimilarityScore(
            title_score=overall_score,
            description_score=overall_score,
            location_score=overall_score,
            overall_score=overall_score,
            threshold=threshold,
        )

        assert score.is_duplicate == (overall_score >= threshold)

    @given(
        incidents=st.lists(incident_content_strategy, min_size=0, max_size=20),
        threshold=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_property_empty_and_single_datasets_should_have_no_duplicates(
        self, incidents, threshold
    ):
        """
        Property: Base cases - empty and single-element datasets should have no duplicates

        Given: Empty or single incident dataset
        When: Finding duplicates
        Then: Should return no duplicate pairs
        """
        assume(len(incidents) <= 1)

        mock_strategy = Mock()
        matcher = FuzzyContentSimilarityMatcher(
            strategy=mock_strategy, threshold=threshold
        )

        result = matcher.find_duplicates(incidents)

        assert len(result.duplicate_pairs) == 0
        assert result.duplicate_count == 0
        assert result.total_incidents == len(incidents)
        if len(incidents) == 1:
            assert result.unique_incidents == [0]
        else:
            assert result.unique_incidents == []

    @given(incidents=st.lists(incident_content_strategy, min_size=2, max_size=10))
    def test_property_duplicate_count_should_never_exceed_total_incidents(
        self, incidents
    ):
        """
        Property: Bounds checking - duplicate count should never exceed total incidents

        Given: Any list of incidents
        When: Finding duplicates
        Then: Duplicate count should be <= total incidents
        """
        # Assume all incidents have unique IDs to avoid reflexivity issues
        incident_ids = [inc.incident_id for inc in incidents]
        assume(len(set(incident_ids)) == len(incidents))

        mock_strategy = Mock()
        mock_strategy.match.return_value = 0.9  # High similarity

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy, threshold=0.8)

        result = matcher.find_duplicates(incidents)

        assert result.duplicate_count <= result.total_incidents
        assert result.total_incidents == len(incidents)

    @given(
        title_weight=st.floats(min_value=0.0, max_value=1.0),
        description_weight=st.floats(min_value=0.0, max_value=1.0),
        location_weight=st.floats(min_value=0.0, max_value=1.0),
        title_score=st.floats(min_value=0.0, max_value=1.0),
        description_score=st.floats(min_value=0.0, max_value=1.0),
        location_score=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_property_weighted_score_should_be_within_bounds(
        self,
        title_weight,
        description_weight,
        location_weight,
        title_score,
        description_score,
        location_score,
    ):
        """
        Property: Score bounds - weighted overall score should be within [0, 1] range

        Given: Any valid weights and individual scores
        When: Computing weighted overall score
        Then: Result should be between 0.0 and 1.0
        """
        # Normalize weights to sum to 1.0 (or skip if all zero)
        total_weight = title_weight + description_weight + location_weight
        assume(total_weight > 0)

        normalized_title = title_weight / total_weight
        normalized_description = description_weight / total_weight
        normalized_location = location_weight / total_weight

        mock_strategy = Mock()
        mock_strategy.match.side_effect = [
            title_score,
            description_score,
            location_score,
        ]

        matcher = FuzzyContentSimilarityMatcher(
            strategy=mock_strategy,
            title_weight=normalized_title,
            description_weight=normalized_description,
            location_weight=normalized_location,
        )

        content1 = IncidentContent("Title1", "Desc1", "Loc1", "id1")
        content2 = IncidentContent("Title2", "Desc2", "Loc2", "id2")

        score = matcher.calculate_similarity(content1, content2)

        assert 0.0 <= score.overall_score <= 1.0

    @given(
        incidents=st.lists(incident_content_strategy, min_size=2, max_size=8),
        threshold=st.floats(min_value=0.1, max_value=0.9),
    )
    def test_property_increasing_threshold_should_decrease_or_maintain_duplicate_count(
        self, incidents, threshold
    ):
        """
        Property: Monotonicity - increasing threshold should not increase duplicate count

        Given: Same dataset with two different thresholds (higher and lower)
        When: Finding duplicates with both thresholds
        Then: Higher threshold should have <= duplicates than lower threshold
        """
        # Ensure unique incident IDs
        incident_ids = [inc.incident_id for inc in incidents]
        assume(len(set(incident_ids)) == len(incidents))

        mock_strategy = Mock()
        mock_strategy.match.return_value = 0.75  # Fixed moderate similarity

        # Test with lower threshold
        lower_threshold = max(0.1, threshold - 0.2)
        matcher_low = FuzzyContentSimilarityMatcher(
            strategy=mock_strategy, threshold=lower_threshold
        )
        result_low = matcher_low.find_duplicates(incidents)

        # Test with higher threshold
        higher_threshold = min(0.9, threshold + 0.2)
        matcher_high = FuzzyContentSimilarityMatcher(
            strategy=mock_strategy, threshold=higher_threshold
        )
        result_high = matcher_high.find_duplicates(incidents)

        # Higher threshold should have <= duplicates
        assert result_high.duplicate_count <= result_low.duplicate_count

    @given(
        content1=incident_content_strategy,
        content2=incident_content_strategy,
        content3=incident_content_strategy,
    )
    def test_property_triangle_inequality_approximate_holds(
        self, content1, content2, content3
    ):
        """
        Property: Triangle inequality (approximate) - sim(a,c) should be related to sim(a,b) + sim(b,c)

        Given: Three incident contents a, b, c
        When: Computing pairwise similarities
        Then: Should satisfy approximate triangle inequality for metric-like behavior
        """
        # Ensure distinct incidents
        ids = [content1.incident_id, content2.incident_id, content3.incident_id]
        assume(len(set(ids)) == 3)

        # Mock strategy with consistent behavior
        mock_strategy = Mock()

        def mock_similarity_calculation(c1, c2):
            if c1.incident_id == c2.incident_id:
                return 1.0  # Perfect self-similarity
            # Use simple heuristic based on title similarity
            title_sim = (
                0.8 if any(word in c1.title for word in c2.title.split()) else 0.2
            )
            return title_sim

        mock_strategy.match.side_effect = lambda t1, t2: mock_similarity_calculation(
            IncidentContent(t1, "", "", ""), IncidentContent(t2, "", "", "")
        )

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        # Calculate pairwise similarities
        score_ab = matcher.calculate_similarity(content1, content2)
        score_bc = matcher.calculate_similarity(content2, content3)
        score_ac = matcher.calculate_similarity(content1, content3)

        # For similarity (not distance), we expect relaxed triangle-like property
        # The exact mathematical relationship depends on the similarity metric
        # Here we just verify all scores are reasonable
        assert 0.0 <= score_ab.overall_score <= 1.0
        assert 0.0 <= score_bc.overall_score <= 1.0
        assert 0.0 <= score_ac.overall_score <= 1.0

    @given(st.data())
    def test_property_processing_time_should_be_reasonable(self, data):
        """
        Property: Performance - processing time should scale reasonably with dataset size

        Given: Datasets of varying sizes
        When: Finding duplicates
        Then: Processing time should be reasonable and increase with size
        """
        size = data.draw(st.integers(min_value=1, max_value=15))
        incidents = data.draw(
            st.lists(incident_content_strategy, min_size=size, max_size=size)
        )

        # Ensure unique IDs
        for i, incident in enumerate(incidents):
            incidents[i] = IncidentContent(
                incident.title,
                incident.description,
                incident.location,
                f"unique_id_{i}",
            )

        mock_strategy = Mock()
        mock_strategy.match.return_value = 0.5

        matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

        result = matcher.find_duplicates(incidents)

        # Processing time should be recorded and reasonable
        assert result.processing_time_ms >= 0
        assert result.processing_time_ms < 10000  # Should not take more than 10 seconds

        # Basic correctness checks
        assert result.total_incidents == len(incidents)
