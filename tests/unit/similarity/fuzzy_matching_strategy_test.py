"""Tests for fuzzy matching strategy implementations."""

from unittest.mock import patch

from disaster_surveillance_reporter.similarity.strategies import (
    RapidFuzzStrategy,
    SequenceMatcherStrategy,
)


class TestSequenceMatcherStrategy:
    """Test SequenceMatcherStrategy (difflib-based) implementation."""

    def test_given_identical_texts_when_matching_then_should_return_perfect_score(self):
        """
        Given: Two identical text strings
        When: Calculating similarity using SequenceMatcher
        Then: Should return similarity score of 1.0
        """
        strategy = SequenceMatcherStrategy()

        text1 = "M7.2 Earthquake near Tokyo"
        text2 = "M7.2 Earthquake near Tokyo"

        score = strategy.match(text1, text2)

        assert score == 1.0

    def test_given_completely_different_texts_when_matching_then_should_return_low_score(
        self,
    ):
        """
        Given: Two completely different text strings
        When: Calculating similarity using SequenceMatcher
        Then: Should return low similarity score
        """
        strategy = SequenceMatcherStrategy()

        text1 = "Earthquake Japan"
        text2 = "Disease Outbreak Nigeria"

        score = strategy.match(text1, text2)

        # Should be low but exact value depends on difflib algorithm
        assert score < 0.5  # More realistic threshold for difflib

    def test_given_similar_texts_when_matching_then_should_return_moderate_score(self):
        """
        Given: Two similar but not identical text strings
        When: Calculating similarity using SequenceMatcher
        Then: Should return moderate similarity score
        """
        strategy = SequenceMatcherStrategy()

        text1 = "M4.5 Earthquake Japan"
        text2 = "M4.7 Earthquake Japan Region"

        score = strategy.match(text1, text2)

        # Should be moderate similarity
        assert 0.5 < score < 1.0

    def test_given_empty_strings_when_matching_then_should_handle_gracefully(self):
        """
        Given: Empty or None text strings
        When: Calculating similarity
        Then: Should handle gracefully and return 0.0
        """
        strategy = SequenceMatcherStrategy()

        assert strategy.match("", "") == 0.0
        assert strategy.match("test", "") == 0.0
        assert strategy.match("", "test") == 0.0

    def test_given_none_values_when_matching_then_should_handle_gracefully(self):
        """
        Given: None values as input
        When: Calculating similarity
        Then: Should handle gracefully and return 0.0
        """
        strategy = SequenceMatcherStrategy()

        assert strategy.match(None, None) == 0.0
        assert strategy.match("test", None) == 0.0
        assert strategy.match(None, "test") == 0.0

    def test_given_case_differences_when_matching_then_should_be_case_insensitive(self):
        """
        Given: Text strings with different casing
        When: Calculating similarity
        Then: Should perform case-insensitive comparison
        """
        strategy = SequenceMatcherStrategy()

        text1 = "EARTHQUAKE JAPAN"
        text2 = "earthquake japan"

        score = strategy.match(text1, text2)

        assert score == 1.0  # Should be identical after case normalization


class TestRapidFuzzStrategy:
    """Test RapidFuzzStrategy implementation."""

    @patch("disaster_surveillance_reporter.similarity.strategies.rapidfuzz")
    def test_given_rapidfuzz_available_when_matching_then_should_use_rapidfuzz(
        self, mock_rapidfuzz
    ):
        """
        Given: rapidfuzz library is available
        When: Calculating similarity
        Then: Should use rapidfuzz.fuzz.ratio
        """
        mock_rapidfuzz.fuzz.ratio.return_value = 95

        strategy = RapidFuzzStrategy()

        text1 = "WHO Health Alert China"
        text2 = "WHO Alert China Disease"

        score = strategy.match(text1, text2)

        mock_rapidfuzz.fuzz.ratio.assert_called_once_with(text1.lower(), text2.lower())
        assert score == 0.95  # 95/100

    def test_given_rapidfuzz_unavailable_when_created_then_should_fallback_to_difflib(
        self,
    ):
        """
        Given: rapidfuzz library is not available
        When: RapidFuzzStrategy is created
        Then: Should fallback to SequenceMatcherStrategy
        """
        with patch(
            "disaster_surveillance_reporter.similarity.strategies.rapidfuzz", None
        ):
            strategy = RapidFuzzStrategy()

            # Should behave like SequenceMatcherStrategy
            text1 = "test"
            text2 = "test"
            score = strategy.match(text1, text2)

            assert score == 1.0

    @patch("disaster_surveillance_reporter.similarity.strategies.rapidfuzz")
    def test_given_prototype_high_similarity_case_when_matching_then_should_return_high_score(
        self, mock_rapidfuzz
    ):
        """
        Given: High similarity case from prototype (expected ~0.95)
        When: Calculating similarity with rapidfuzz
        Then: Should return high score matching prototype results
        """
        mock_rapidfuzz.fuzz.ratio.return_value = 95  # Simulating high similarity

        strategy = RapidFuzzStrategy()

        # From prototype: high similarity pair
        text1 = "WHO Health Alert - Disease Outbreak China"
        text2 = "WHO Alert Disease Outbreak China Regional"

        score = strategy.match(text1, text2)

        assert score >= 0.9  # Should be high as per prototype

    @patch("disaster_surveillance_reporter.similarity.strategies.rapidfuzz")
    def test_given_prototype_medium_similarity_case_when_matching_then_should_return_medium_score(
        self, mock_rapidfuzz
    ):
        """
        Given: Medium similarity case from prototype (expected ~0.72)
        When: Calculating similarity with rapidfuzz
        Then: Should return medium score matching prototype results
        """
        mock_rapidfuzz.fuzz.ratio.return_value = 72  # Simulating medium similarity

        strategy = RapidFuzzStrategy()

        # From prototype: medium similarity pair
        text1 = "M4.5 Earthquake Japan"
        text2 = "M4.7 Earthquake Japan Region"

        score = strategy.match(text1, text2)

        assert 0.6 < score < 0.8  # Should be medium as per prototype

    @patch("disaster_surveillance_reporter.similarity.strategies.rapidfuzz")
    def test_given_prototype_low_similarity_case_when_matching_then_should_return_low_score(
        self, mock_rapidfuzz
    ):
        """
        Given: Low similarity case from prototype (expected ~0.13)
        When: Calculating similarity with rapidfuzz
        Then: Should return low score matching prototype results
        """
        mock_rapidfuzz.fuzz.ratio.return_value = 13  # Simulating low similarity

        strategy = RapidFuzzStrategy()

        # From prototype: low similarity pair
        text1 = "Earthquake Japan"
        text2 = "Disease Outbreak Nigeria"

        score = strategy.match(text1, text2)

        assert score < 0.3  # Should be low as per prototype

    @patch("disaster_surveillance_reporter.similarity.strategies.rapidfuzz")
    def test_given_performance_requirements_when_matching_then_should_be_fast(
        self, mock_rapidfuzz
    ):
        """
        Given: Performance requirements (17x faster than difflib)
        When: Using RapidFuzzStrategy
        Then: Should complete quickly (mocked for test)
        """
        mock_rapidfuzz.fuzz.ratio.return_value = 80

        strategy = RapidFuzzStrategy()

        # Simulate rapid processing
        import time

        start_time = time.time()

        for i in range(100):  # Small batch test
            strategy.match(f"incident {i}", f"similar incident {i}")

        elapsed_time = time.time() - start_time

        # Should complete very quickly with mocked rapidfuzz
        assert elapsed_time < 1.0  # Generous bound for mocked test

    @patch("disaster_surveillance_reporter.similarity.strategies.rapidfuzz")
    def test_given_special_characters_when_matching_then_should_handle_gracefully(
        self, mock_rapidfuzz
    ):
        """
        Given: Text with special characters and unicode
        When: Calculating similarity
        Then: Should handle gracefully
        """
        mock_rapidfuzz.fuzz.ratio.return_value = 85

        strategy = RapidFuzzStrategy()

        text1 = "Earthquake in São Paulo, Brazil (M5.2)"
        text2 = "M5.2 earthquake São Paulo Brazil"

        score = strategy.match(text1, text2)

        # Should handle unicode and special chars
        mock_rapidfuzz.fuzz.ratio.assert_called_once()
        assert score == 0.85

    @patch("disaster_surveillance_reporter.similarity.strategies.rapidfuzz")
    def test_given_very_long_texts_when_matching_then_should_process_efficiently(
        self, mock_rapidfuzz
    ):
        """
        Given: Very long text strings (500+ characters)
        When: Calculating similarity
        Then: Should process efficiently
        """
        mock_rapidfuzz.fuzz.ratio.return_value = 70

        strategy = RapidFuzzStrategy()

        # Long descriptions as might occur in real incidents
        long_text1 = "Long earthquake description " * 20  # ~540 chars
        long_text2 = "Extended earthquake report " * 20  # ~520 chars

        score = strategy.match(long_text1, long_text2)

        # Should handle long texts
        mock_rapidfuzz.fuzz.ratio.assert_called_once()
        assert score == 0.70
