"""Matching strategy implementations for similarity calculation.

This module provides pluggable text matching algorithms that can be used with
the ContentSimilarityMatcher to calculate similarity scores between text fields.
Each strategy implements the MatchingStrategy protocol and can be swapped out
based on performance and accuracy requirements.

Example:
    Using different strategies:

    >>> from disaster_surveillance_reporter.similarity.strategies import (
    ...     SequenceMatcherStrategy, RapidFuzzStrategy
    ... )
    >>> from disaster_surveillance_reporter.similarity import FuzzyContentSimilarityMatcher
    >>>
    >>> # High accuracy with standard library
    >>> accurate_matcher = FuzzyContentSimilarityMatcher(SequenceMatcherStrategy())
    >>>
    >>> # High performance with rapidfuzz (if available)
    >>> fast_matcher = FuzzyContentSimilarityMatcher(RapidFuzzStrategy())
    >>>
    >>> # Compare strategies
    >>> text1, text2 = "earthquake in tokyo", "tokyo earthquake"
    >>> seq_score = SequenceMatcherStrategy().match(text1, text2)
    >>> fuzz_score = RapidFuzzStrategy().match(text1, text2)

Note:
    - All strategies normalize scores to [0.0, 1.0] range
    - Strategies handle None/empty inputs gracefully (return 0.0)
    - Text comparison is case-insensitive by default
    - Strategies are stateless and thread-safe
"""

import difflib
from typing import Protocol, runtime_checkable

try:
    import rapidfuzz
except ImportError:
    rapidfuzz = None


@runtime_checkable
class MatchingStrategy(Protocol):
    """Protocol defining the interface for text similarity matching algorithms.

    This protocol defines the contract that all text matching strategy implementations
    must follow. Strategies are pluggable components that can be swapped out to
    provide different similarity algorithms with varying performance and accuracy
    characteristics.

    The protocol is runtime_checkable, allowing isinstance() checks for duck typing
    validation at runtime.

    Example:
        Implementing a custom strategy:

        >>> class LevenshteinStrategy:
        ...     def match(self, text1: str | None, text2: str | None) -> float:
        ...         '''Custom Levenshtein distance implementation.'''
        ...         if not text1 or not text2:
        ...             return 0.0
        ...         # Custom algorithm implementation
        ...         return levenshtein_similarity(text1, text2)
        >>>
        >>> strategy = LevenshteinStrategy()
        >>> assert isinstance(strategy, MatchingStrategy)  # True

        Using with matchers:

        >>> from disaster_surveillance_reporter.similarity import FuzzyContentSimilarityMatcher
        >>>
        >>> def create_matcher(strategy: MatchingStrategy) -> FuzzyContentSimilarityMatcher:
        ...     '''Create matcher with any compatible strategy.'''
        ...     return FuzzyContentSimilarityMatcher(strategy, threshold=0.8)
        >>>
        >>> # Works with any conforming implementation
        >>> matcher = create_matcher(LevenshteinStrategy())

    Note:
        - Implementations should be stateless and thread-safe
        - All methods should handle None/empty inputs gracefully
        - Scores should be normalized to [0.0, 1.0] range
        - Performance characteristics may vary significantly between algorithms
    """

    def match(self, text1: str | None, text2: str | None) -> float:
        """Calculate normalized similarity score between two text strings.

        This method performs the core text similarity calculation using the
        strategy's specific algorithm. The result is always normalized to
        the [0.0, 1.0] range for consistency across different strategies.

        Args:
            text1: First text string for comparison (can be None)
            text2: Second text string for comparison (can be None)

        Returns:
            Normalized similarity score where:
            - 0.0 = completely different or one/both inputs are None/empty
            - 1.0 = identical text content
            - Values between indicate degree of similarity

        Example:
            >>> strategy = SequenceMatcherStrategy()
            >>>
            >>> # Identical text
            >>> score = strategy.match("hello world", "hello world")
            >>> assert score == 1.0
            >>>
            >>> # Similar text
            >>> score = strategy.match("earthquake in japan", "japan earthquake")
            >>> assert 0.5 < score < 1.0  # Similar but not identical
            >>>
            >>> # Different text
            >>> score = strategy.match("earthquake", "wildfire")
            >>> assert 0.0 <= score < 0.3  # Very different
            >>>
            >>> # Handle None/empty gracefully
            >>> assert strategy.match(None, "text") == 0.0
            >>> assert strategy.match("", "") == 0.0

        Note:
            - Comparison should be case-insensitive by convention
            - Whitespace normalization is algorithm-dependent
            - None and empty strings return 0.0 similarity
            - Results should be deterministic for identical inputs
        """
        ...


class SequenceMatcherStrategy:
    """High-accuracy text similarity strategy using Python's standard library.

    This strategy uses difflib.SequenceMatcher for calculating text similarity
    based on longest common subsequence algorithms. It provides reliable,
    deterministic results with no external dependencies.

    Characteristics:
        - High accuracy for text comparison
        - No external dependencies (uses standard library)
        - Deterministic and reproducible results
        - Moderate performance (suitable for most use cases)
        - Case-insensitive comparison

    Example:
        Using SequenceMatcherStrategy:

        >>> strategy = SequenceMatcherStrategy()
        >>>
        >>> # Test with disaster incident titles
        >>> score = strategy.match(
        ...     "Earthquake hits Tokyo region",
        ...     "Tokyo region struck by earthquake"
        ... )
        >>> print(f"Similarity: {score:.2f}")  # ~0.85
        >>>
        >>> # Test with location variations
        >>> score = strategy.match("Tokyo, Japan", "Tokyo Japan")
        >>> print(f"Location match: {score:.2f}")  # ~0.95

    Note:
        - Uses difflib.SequenceMatcher.ratio() internally
        - Considers character-level and word-level similarity
        - Handles Unicode text correctly
        - Performance scales with O(n*m) where n,m are text lengths
    """

    def match(self, text1: str | None, text2: str | None) -> float:
        """Calculate similarity using difflib.SequenceMatcher algorithm.

        This method uses Python's standard library SequenceMatcher to calculate
        similarity based on longest common subsequence. The algorithm considers
        both character-level and structural similarity between texts.

        Args:
            text1: First text string for comparison (can be None)
            text2: Second text string for comparison (can be None)

        Returns:
            Similarity score in [0.0, 1.0] range where:
            - 0.0 = no similarity or empty inputs
            - 1.0 = identical content
            - Values reflect ratio of matching to total characters

        Example:
            >>> strategy = SequenceMatcherStrategy()
            >>>
            >>> # Exact match
            >>> assert strategy.match("test", "test") == 1.0
            >>>
            >>> # Case insensitive
            >>> score = strategy.match("Test", "TEST")
            >>> assert score == 1.0
            >>>
            >>> # Partial similarity
            >>> score = strategy.match("hello world", "hello earth")
            >>> assert 0.5 < score < 1.0
            >>>
            >>> # Handle edge cases
            >>> assert strategy.match(None, "text") == 0.0
            >>> assert strategy.match("", "") == 0.0

        Note:
            - Comparison is case-insensitive
            - Uses SequenceMatcher's ratio() method internally
            - Handles whitespace and punctuation naturally
            - Returns 0.0 for any None or empty inputs
        """
        # Handle None and empty inputs
        if not text1 or not text2:
            return 0.0

        # Case insensitive comparison
        normalized_text1 = text1.lower().strip()
        normalized_text2 = text2.lower().strip()

        # Handle empty strings after normalization
        if not normalized_text1 or not normalized_text2:
            return 0.0

        matcher = difflib.SequenceMatcher(None, normalized_text1, normalized_text2)
        return matcher.ratio()


class RapidFuzzStrategy:
    """High-performance text similarity strategy using rapidfuzz library.

    This strategy provides optimized fuzzy string matching using the rapidfuzz
    library, with automatic fallback to SequenceMatcherStrategy if rapidfuzz
    is not available. It offers significantly better performance for large
    datasets while maintaining accuracy.

    Characteristics:
        - High performance (significantly faster than difflib)
        - Requires optional rapidfuzz dependency
        - Automatic fallback to SequenceMatcherStrategy if rapidfuzz unavailable
        - Case-insensitive comparison
        - Compatible API with other strategies

    Example:
        Using RapidFuzzStrategy with performance benefits:

        >>> strategy = RapidFuzzStrategy()
        >>> print(f"Using rapidfuzz: {strategy.is_rapidfuzz_available}")
        >>>
        >>> # Performance test with large text
        >>> import time
        >>> large_text1 = "earthquake disaster emergency response" * 100
        >>> large_text2 = "emergency earthquake disaster response" * 100
        >>>
        >>> start = time.time()
        >>> score = strategy.match(large_text1, large_text2)
        >>> duration = time.time() - start
        >>> print(f"Score: {score:.3f}, Time: {duration:.3f}s")

        Graceful degradation without rapidfuzz:

        >>> # Works even if rapidfuzz not installed
        >>> strategy = RapidFuzzStrategy()  # Falls back to SequenceMatcher
        >>> score = strategy.match("test text", "test content")
        >>> # Returns valid similarity score regardless of rapidfuzz availability

    Note:
        - Installation: pip install rapidfuzz (optional dependency)
        - Performance scales better with text length than SequenceMatcher
        - Results should be nearly identical to SequenceMatcher
        - Thread-safe and stateless
    """

    def __init__(self) -> None:
        """Initialize RapidFuzzStrategy with automatic fallback detection.

        The strategy automatically detects rapidfuzz availability and configures
        appropriate fallback behavior. No configuration required by user.

        Example:
            >>> strategy = RapidFuzzStrategy()
            >>> if strategy.is_rapidfuzz_available:
            ...     print("Using high-performance rapidfuzz")
            ... else:
            ...     print("Using standard library fallback")
        """
        self._use_rapidfuzz = rapidfuzz is not None
        if not self._use_rapidfuzz:
            self._fallback = SequenceMatcherStrategy()

    @property
    def is_rapidfuzz_available(self) -> bool:
        """Check if rapidfuzz library is available for high-performance matching.

        Returns:
            True if rapidfuzz is installed and will be used, False if falling
            back to SequenceMatcherStrategy.

        Example:
            >>> strategy = RapidFuzzStrategy()
            >>> if strategy.is_rapidfuzz_available:
            ...     print("Optimized performance available")
            ... else:
            ...     print("Consider installing rapidfuzz for better performance")
        """
        return self._use_rapidfuzz

    def match(self, text1: str | None, text2: str | None) -> float:
        """Calculate similarity using rapidfuzz or fallback to difflib.

        This method automatically selects the best available algorithm:
        rapidfuzz for optimal performance, or SequenceMatcherStrategy fallback
        if rapidfuzz is not installed.

        Args:
            text1: First text string for comparison (can be None)
            text2: Second text string for comparison (can be None)

        Returns:
            Similarity score in [0.0, 1.0] range consistent with other strategies.

        Example:
            >>> strategy = RapidFuzzStrategy()
            >>>
            >>> # High-performance comparison
            >>> score = strategy.match(
            ...     "Major earthquake strikes Tokyo region",
            ...     "Tokyo region hit by major earthquake"
            ... )
            >>> print(f"Similarity: {score:.3f}")
            >>>
            >>> # Handles edge cases consistently
            >>> assert strategy.match(None, "text") == 0.0
            >>> assert strategy.match("", "") == 0.0
            >>> assert strategy.match("same", "same") == 1.0

        Note:
            - Uses rapidfuzz.fuzz.ratio() if available (higher performance)
            - Falls back to SequenceMatcherStrategy if rapidfuzz not installed
            - Results are normalized and consistent across implementations
            - Case-insensitive comparison in both modes
        """
        # Handle None and empty inputs
        if not text1 or not text2:
            return 0.0

        # Case insensitive comparison with whitespace normalization
        normalized_text1 = text1.lower().strip()
        normalized_text2 = text2.lower().strip()

        # Handle empty strings after normalization
        if not normalized_text1 or not normalized_text2:
            return 0.0

        if self._use_rapidfuzz and rapidfuzz is not None:
            # rapidfuzz returns 0-100, normalize to 0-1
            score = rapidfuzz.fuzz.ratio(normalized_text1, normalized_text2)
            return score / 100.0

        # Fallback to SequenceMatcher strategy
        return self._fallback.match(text1, text2)
