"""ContentSimilarityMatcher implementations for disaster incident duplicate detection.

This module provides concrete implementations of the ContentSimilarityMatcher protocol,
focusing on fuzzy string matching techniques for identifying duplicate incident reports
across various data sources.

Example:
    Basic usage with default configuration:

    >>> from disaster_surveillance_reporter.similarity import (
    ...     FuzzyContentSimilarityMatcher, IncidentContent
    ... )
    >>> from disaster_surveillance_reporter.similarity.strategies import SequenceMatcherStrategy
    >>>
    >>> # Create matcher with sensible defaults
    >>> strategy = SequenceMatcherStrategy()
    >>> matcher = FuzzyContentSimilarityMatcher(strategy)
    >>>
    >>> # Analyze incident similarities
    >>> incident1 = IncidentContent(
    ...     title="Earthquake in Japan",
    ...     description="7.2 magnitude earthquake hits Tokyo region",
    ...     location="Tokyo, Japan",
    ...     incident_id="jp_eq_001"
    ... )
    >>> incident2 = IncidentContent(
    ...     title="Tokyo Earthquake",
    ...     description="Major earthquake strikes Tokyo area, 7.2 magnitude",
    ...     location="Tokyo, Japan",
    ...     incident_id="jp_eq_002"
    ... )
    >>>
    >>> score = matcher.calculate_similarity(incident1, incident2)
    >>> print(f"Similarity: {score.overall_score:.2f}")
    >>> print(f"Is duplicate: {score.is_duplicate}")

    Advanced usage with custom configuration:

    >>> from disaster_surveillance_reporter.similarity.strategies import RapidFuzzStrategy
    >>>
    >>> # High-performance matcher with custom weights
    >>> fast_strategy = RapidFuzzStrategy()
    >>> custom_matcher = FuzzyContentSimilarityMatcher(
    ...     strategy=fast_strategy,
    ...     threshold=0.85,                # Higher threshold for stricter matching
    ...     title_weight=0.5,              # Emphasize title importance
    ...     description_weight=0.4,        # Standard description weight
    ...     location_weight=0.1             # De-emphasize location
    ... )
    >>>
    >>> # Bulk duplicate detection
    >>> incidents = [incident1, incident2, ...]  # List of incidents
    >>> result = custom_matcher.find_duplicates(incidents)
    >>>
    >>> print(f"Processed {result.total_incidents} incidents in {result.processing_time_ms:.1f}ms")
    >>> print(f"Found {result.pair_count} duplicate pairs")
    >>> print(f"Duplication rate: {result.duplication_rate:.1%}")

Note:
    - All implementations are thread-safe and stateless (after initialization)
    - Weighted scoring allows domain-specific tuning for different incident types
    - Performance scales O(n²) with number of incidents for find_duplicates()
    - Memory usage is optimized for large datasets
"""

import time
from typing import ClassVar

from ._types import DuplicationResult, IncidentContent, SimilarityScore
from .strategies import MatchingStrategy


class FuzzyContentSimilarityMatcher:
    """Production-ready fuzzy string matching for disaster incident duplicate detection.

    This class implements the ContentSimilarityMatcher protocol using weighted
    fuzzy string matching across incident content fields. It supports pluggable
    matching strategies and configurable weighting schemes optimized for disaster
    incident data characteristics.

    The matcher uses a three-field approach:
    1. Title similarity (typically news headlines or alert titles)
    2. Description similarity (detailed incident descriptions)
    3. Location similarity (geographic location information)

    These are combined using configurable weights to produce an overall similarity
    score that accounts for the relative importance of each field type.

    Attributes:
        DEFAULT_THRESHOLD: Class-level default similarity threshold (0.8)
        DEFAULT_TITLE_WEIGHT: Class-level default title field weight (0.4)
        DEFAULT_DESCRIPTION_WEIGHT: Class-level default description field weight (0.4)
        DEFAULT_LOCATION_WEIGHT: Class-level default location field weight (0.2)

    Example:
        Production deployment configuration:

        >>> from disaster_surveillance_reporter.similarity import FuzzyContentSimilarityMatcher
        >>> from disaster_surveillance_reporter.similarity.strategies import RapidFuzzStrategy
        >>>
        >>> # Create production matcher
        >>> strategy = RapidFuzzStrategy()  # High performance
        >>> matcher = FuzzyContentSimilarityMatcher(
        ...     strategy=strategy,
        ...     threshold=0.82,              # Slightly higher threshold
        ...     title_weight=0.45,           # Emphasize headlines
        ...     description_weight=0.45,     # Balanced with description
        ...     location_weight=0.10         # Location often varies in format
        ... )
        >>>
        >>> # Validate configuration
        >>> assert matcher.threshold == 0.82
        >>> assert matcher.total_weight == 1.0  # Weights sum to 1.0
        >>>
        >>> # Process real incident data
        >>> incidents = load_incident_data()  # Your data loading function
        >>> result = matcher.find_duplicates(incidents)
        >>>
        >>> # Log performance metrics
        >>> logger.info(f"Processed {result.total_incidents} incidents")
        >>> logger.info(f"Found {result.duplicate_count} duplicates")
        >>> logger.info(f"Processing speed: {result.processing_speed:.0f} incidents/sec")

    Note:
        - Thread-safe for concurrent use after initialization
        - Weights should sum to 1.0 for optimal score interpretation
        - Higher thresholds reduce false positives but may miss true duplicates
        - Strategy choice significantly impacts performance characteristics
    """

    # Class-level defaults for consistent configuration
    DEFAULT_THRESHOLD: ClassVar[float] = 0.8
    DEFAULT_TITLE_WEIGHT: ClassVar[float] = 0.4
    DEFAULT_DESCRIPTION_WEIGHT: ClassVar[float] = 0.4
    DEFAULT_LOCATION_WEIGHT: ClassVar[float] = 0.2

    def __init__(
        self,
        strategy: MatchingStrategy,
        threshold: float = DEFAULT_THRESHOLD,
        title_weight: float = DEFAULT_TITLE_WEIGHT,
        description_weight: float = DEFAULT_DESCRIPTION_WEIGHT,
        location_weight: float = DEFAULT_LOCATION_WEIGHT,
    ) -> None:
        """Initialize FuzzyContentSimilarityMatcher with strategy and configuration.

        Args:
            strategy: Text matching algorithm implementing MatchingStrategy protocol
            threshold: Minimum similarity score for duplicate classification (0.0-1.0)
            title_weight: Relative importance of title field similarity (0.0-1.0)
            description_weight: Relative importance of description field similarity (0.0-1.0)
            location_weight: Relative importance of location field similarity (0.0-1.0)

        Raises:
            TypeError: If strategy doesn't implement MatchingStrategy protocol
            ValueError: If threshold not in [0.0, 1.0] or weights are invalid

        Example:
            >>> from disaster_surveillance_reporter.similarity.strategies import SequenceMatcherStrategy
            >>>
            >>> # Basic configuration
            >>> strategy = SequenceMatcherStrategy()
            >>> matcher = FuzzyContentSimilarityMatcher(strategy)
            >>>
            >>> # Custom configuration for specific use case
            >>> news_matcher = FuzzyContentSimilarityMatcher(
            ...     strategy=strategy,
            ...     threshold=0.75,              # Lower threshold for news matching
            ...     title_weight=0.6,            # Headlines are very important
            ...     description_weight=0.3,      # Content similarity matters less
            ...     location_weight=0.1          # Location format varies widely
            ... )
            >>>
            >>> # Validate weights sum appropriately
            >>> total_weight = news_matcher.total_weight
            >>> assert 0.95 <= total_weight <= 1.05  # Allow small floating point error

        Note:
            - Strategy parameter is required and must implement MatchingStrategy protocol
            - Weights don't need to sum to 1.0 but typically should for score interpretation
            - Higher threshold values require stronger similarity for duplicate classification
            - Weight configuration should reflect domain knowledge about data characteristics
        """
        # Validate strategy protocol compliance
        if not hasattr(strategy, "match") or not callable(strategy.match):
            raise TypeError(
                "strategy must implement MatchingStrategy protocol with match() method"
            )

        # Validate threshold range
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(f"threshold must be in range [0.0, 1.0], got {threshold}")

        # Validate weight ranges
        for weight_name, weight_value in [
            ("title_weight", title_weight),
            ("description_weight", description_weight),
            ("location_weight", location_weight),
        ]:
            if not (0.0 <= weight_value <= 1.0):
                raise ValueError(
                    f"{weight_name} must be in range [0.0, 1.0], got {weight_value}"
                )

        # Store configuration
        self._strategy = strategy
        self._threshold = threshold
        self._title_weight = title_weight
        self._description_weight = description_weight
        self._location_weight = location_weight

    @property
    def threshold(self) -> float:
        """Get the similarity threshold for duplicate classification.

        Returns:
            Current threshold value (0.0 to 1.0).
        """
        return self._threshold

    @property
    def total_weight(self) -> float:
        """Get the sum of all field weights.

        Returns:
            Sum of title_weight + description_weight + location_weight.

        Example:
            >>> matcher = FuzzyContentSimilarityMatcher(strategy)
            >>> matcher.total_weight  # 1.0 (default weights sum to 1.0)
        """
        return self._title_weight + self._description_weight + self._location_weight

    @property
    def strategy_info(self) -> str:
        """Get information about the matching strategy being used.

        Returns:
            Human-readable string describing the strategy.

        Example:
            >>> from disaster_surveillance_reporter.similarity.strategies import RapidFuzzStrategy
            >>> matcher = FuzzyContentSimilarityMatcher(RapidFuzzStrategy())
            >>> print(matcher.strategy_info)  # "RapidFuzzStrategy"
        """
        return self._strategy.__class__.__name__

    def calculate_similarity(
        self, content1: IncidentContent, content2: IncidentContent
    ) -> SimilarityScore:
        """Calculate comprehensive similarity score between two incident contents.

        This method performs detailed similarity analysis across all incident content
        fields, applying the configured weighting scheme to produce both individual
        field scores and a weighted overall assessment.

        The calculation process:
        1. Calculate individual field similarities using the configured strategy
        2. Apply weighted combination based on field importance configuration
        3. Return comprehensive SimilarityScore with all metrics

        Args:
            content1: First incident content for comparison
            content2: Second incident content for comparison

        Returns:
            SimilarityScore containing detailed similarity analysis including:
            - Individual field scores (title, description, location)
            - Weighted overall similarity score
            - Threshold and duplicate classification

        Raises:
            TypeError: If either parameter is not an IncidentContent instance
            ValueError: If either incident content is invalid

        Example:
            >>> from disaster_surveillance_reporter.similarity import IncidentContent
            >>>
            >>> incident1 = IncidentContent(
            ...     title="Wildfire Emergency in California",
            ...     description="Large wildfire burning in Napa County, evacuations ordered",
            ...     location="Napa County, CA, USA",
            ...     incident_id="ca_fire_001"
            ... )
            >>>
            >>> incident2 = IncidentContent(
            ...     title="California Wildfire Alert",
            ...     description="Major fire in Napa area, residents evacuating",
            ...     location="Napa County, California",
            ...     incident_id="ca_fire_002"
            ... )
            >>>
            >>> score = matcher.calculate_similarity(incident1, incident2)
            >>>
            >>> # Analyze detailed results
            >>> print(f"Title similarity: {score.title_score:.2f}")
            >>> print(f"Description similarity: {score.description_score:.2f}")
            >>> print(f"Location similarity: {score.location_score:.2f}")
            >>> print(f"Overall score: {score.overall_score:.2f}")
            >>> print(f"Is duplicate: {score.is_duplicate}")
            >>> print(f"Confidence: {score.confidence:.1%}")
            >>>
            >>> # Check strength of match
            >>> if score.margin_above_threshold > 0.1:
            ...     print("Strong duplicate match")
            >>> elif score.is_duplicate:
            ...     print("Weak duplicate match")
            >>> else:
            ...     print("Not a duplicate")

        Note:
            - Individual field scores are calculated independently
            - Overall score uses configured field weights for combination
            - Empty fields are handled gracefully (return 0.0 similarity)
            - Results are deterministic for identical inputs
            - Performance scales with text length and strategy complexity
        """
        # Validate input types
        if not isinstance(content1, IncidentContent):
            raise TypeError(f"content1 must be IncidentContent, got {type(content1)}")
        if not isinstance(content2, IncidentContent):
            raise TypeError(f"content2 must be IncidentContent, got {type(content2)}")

        # Calculate individual field similarities using the configured strategy
        title_score = self._strategy.match(content1.title, content2.title)
        description_score = self._strategy.match(
            content1.description, content2.description
        )
        location_score = self._strategy.match(content1.location, content2.location)

        # Calculate weighted overall score using configured field weights
        overall_score = (
            self._title_weight * title_score
            + self._description_weight * description_score
            + self._location_weight * location_score
        )

        return SimilarityScore(
            title_score=title_score,
            description_score=description_score,
            location_score=location_score,
            overall_score=overall_score,
            threshold=self._threshold,
        )

    def find_duplicates(self, incidents: list[IncidentContent]) -> DuplicationResult:
        """Find all duplicate incident pairs in a dataset using pairwise similarity analysis.

        This method performs comprehensive duplicate detection across a collection of
        incident content, comparing every pair to identify duplicates above the
        configured similarity threshold. It provides detailed performance metrics
        and handles edge cases gracefully.

        Algorithm:
        1. Validate input data and handle edge cases (empty/single incident)
        2. Perform pairwise similarity comparison (O(n²) complexity)
        3. Identify all pairs exceeding the similarity threshold
        4. Classify incidents as unique or duplicate based on relationships
        5. Calculate performance metrics and return comprehensive results

        Args:
            incidents: List of IncidentContent objects to analyze for duplicates.
                      Can be empty (returns empty result) or single item (no duplicates possible).

        Returns:
            DuplicationResult containing:
            - All duplicate pairs with similarity scores
            - Indices of unique (non-duplicate) incidents
            - Performance metrics (processing time, throughput)
            - Summary statistics (counts, rates)

        Raises:
            TypeError: If incidents is not a list or contains non-IncidentContent items
            ValueError: If incidents contain invalid data (empty incident_id, etc.)

        Example:
            Real-world duplicate detection workflow:

            >>> from disaster_surveillance_reporter.similarity import (
            ...     FuzzyContentSimilarityMatcher, IncidentContent
            ... )
            >>> from disaster_surveillance_reporter.similarity.strategies import RapidFuzzStrategy
            >>>
            >>> # Load incident data (typically from JSON/database)
            >>> incidents = [
            ...     IncidentContent("Earthquake Japan", "7.2 quake hits Tokyo", "Tokyo", "001"),
            ...     IncidentContent("Tokyo Earthquake", "Major 7.2 earthquake", "Tokyo", "002"),  # Duplicate
            ...     IncidentContent("Wildfire CA", "Fire in Napa County", "California", "003"),
            ...     IncidentContent("Flood Alert", "Heavy rain causes flooding", "Bangkok", "004"),
            ... ]
            >>>
            >>> # Configure high-performance matcher
            >>> strategy = RapidFuzzStrategy()
            >>> matcher = FuzzyContentSimilarityMatcher(strategy, threshold=0.8)
            >>>
            >>> # Perform duplicate detection
            >>> result = matcher.find_duplicates(incidents)
            >>>
            >>> # Analyze results
            >>> print(f"Dataset: {result.total_incidents} incidents")
            >>> print(f"Performance: {result.processing_time_ms:.1f}ms ({result.processing_speed:.0f} inc/sec)")
            >>> print(f"Duplicates: {result.duplicate_count} incidents in {result.pair_count} pairs")
            >>> print(f"Unique: {result.unique_count} incidents")
            >>> print(f"Duplication rate: {result.duplication_rate:.1%}")
            >>>
            >>> # Process duplicate pairs for deduplication
            >>> for idx1, idx2, score in result.duplicate_pairs:
            ...     incident1, incident2 = incidents[idx1], incidents[idx2]
            ...     print(f"\\nDuplicate pair (confidence: {score.confidence:.1%}):")
            ...     print(f"  [{idx1}] {incident1.title} (ID: {incident1.incident_id})")
            ...     print(f"  [{idx2}] {incident2.title} (ID: {incident2.incident_id})")
            ...     print(f"  Scores: title={score.title_score:.2f}, desc={score.description_score:.2f}, loc={score.location_score:.2f}")
            >>>
            >>> # Access unique incidents for further processing
            >>> unique_incidents = [incidents[i] for i in result.unique_incidents]
            >>> print(f"\\nProcessing {len(unique_incidents)} unique incidents...")

        Performance Characteristics:
            - Time complexity: O(n²) where n is number of incidents
            - Space complexity: O(k) where k is number of duplicate pairs found
            - Typical performance: 100-1000 incidents/second (depends on strategy and text length)
            - Memory usage scales with result size, not input size

        Note:
            - Algorithm compares every incident pair exactly once (i < j ordering)
            - Empty or single-incident datasets are handled efficiently
            - Processing time includes all similarity calculations and result compilation
            - Duplicate classification is based on overall_score >= threshold
            - An incident involved in any duplicate pair is excluded from unique_incidents
        """
        # Validate input type
        if not isinstance(incidents, list):
            raise TypeError(f"incidents must be a list, got {type(incidents)}")

        # Validate list contents
        for i, incident in enumerate(incidents):
            if not isinstance(incident, IncidentContent):
                raise TypeError(
                    f"incidents[{i}] must be IncidentContent, got {type(incident)}"
                )

        # Start performance timing
        start_time = time.time()

        duplicate_pairs = []
        total_incidents = len(incidents)

        # Handle empty or single incident cases efficiently
        if total_incidents <= 1:
            processing_time_ms = (time.time() - start_time) * 1000
            return DuplicationResult(
                total_incidents=total_incidents,
                duplicate_pairs=[],
                unique_incidents=list(range(total_incidents)),
                processing_time_ms=processing_time_ms,
            )

        # Perform pairwise similarity comparison
        # Use (i < j) ordering to avoid duplicate comparisons and self-comparison
        for i in range(total_incidents):
            for j in range(i + 1, total_incidents):
                similarity = self.calculate_similarity(incidents[i], incidents[j])
                if similarity.is_duplicate:
                    duplicate_pairs.append((i, j, similarity))

        # Determine unique incidents (those not involved in any duplicate pair)
        # An incident is unique if it doesn't appear in any duplicate relationship
        duplicated_indices = {idx for pair in duplicate_pairs for idx in pair[:2]}
        unique_incidents = [
            i for i in range(total_incidents) if i not in duplicated_indices
        ]

        # Calculate final processing time
        processing_time_ms = (time.time() - start_time) * 1000

        return DuplicationResult(
            total_incidents=total_incidents,
            duplicate_pairs=duplicate_pairs,
            unique_incidents=unique_incidents,
            processing_time_ms=processing_time_ms,
        )
