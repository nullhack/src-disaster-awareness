"""Production-ready content similarity matching for disaster incident duplication detection.

This module provides a comprehensive, type-safe, and highly configurable system for
identifying duplicate disaster incident reports across various data sources. It uses
modern Python design patterns including protocols, immutable value objects, and
pluggable strategies.

Key Features:
    - Protocol-based architecture for extensible matching strategies
    - Immutable value objects for thread-safe concurrent operation
    - Configurable field weighting for domain-specific optimization
    - High-performance implementations with optional rapidfuzz integration
    - Comprehensive error handling and validation
    - Detailed performance metrics and analysis tools

Example:
    Quick start with default configuration:

    >>> from disaster_surveillance_reporter.similarity import (
    ...     FuzzyContentSimilarityMatcher,
    ...     IncidentContent,
    ...     SequenceMatcherStrategy
    ... )
    >>>
    >>> # Create incidents from your data
    >>> incident1 = IncidentContent(
    ...     title="Earthquake in Japan",
    ...     description="7.2 magnitude earthquake hits Tokyo region",
    ...     location="Tokyo, Japan",
    ...     incident_id="jp_eq_001"
    ... )
    >>>
    >>> incident2 = IncidentContent(
    ...     title="Tokyo Earthquake Alert",
    ...     description="Major earthquake strikes Tokyo area, magnitude 7.2",
    ...     location="Tokyo, Japan",
    ...     incident_id="jp_eq_002"
    ... )
    >>>
    >>> # Configure similarity matcher
    >>> strategy = SequenceMatcherStrategy()
    >>> matcher = FuzzyContentSimilarityMatcher(strategy, threshold=0.8)
    >>>
    >>> # Analyze similarity
    >>> score = matcher.calculate_similarity(incident1, incident2)
    >>> print(f"Similarity: {score.overall_score:.2f}")
    >>> print(f"Is duplicate: {score.is_duplicate}")
    >>>
    >>> # Bulk duplicate detection
    >>> incidents = [incident1, incident2, ...]
    >>> result = matcher.find_duplicates(incidents)
    >>> print(
    ...     f"Found {result.duplicate_count} duplicates "
    ...     f"in {result.processing_time_ms:.1f}ms"
    ... )

Architecture:
    The module follows a layered architecture:

    1. **Value Objects** (`_types.py`):
       - `IncidentContent`: Immutable incident data container
       - `SimilarityScore`: Detailed similarity analysis results
       - `DuplicationResult`: Comprehensive duplicate detection results

    2. **Protocols** (`_types.py`):
       - `ContentSimilarityMatcher`: Main interface for similarity matching
       - `MatchingStrategy`: Pluggable text matching algorithms

    3. **Strategies** (`strategies.py`):
       - `SequenceMatcherStrategy`: High-accuracy standard library implementation
       - `RapidFuzzStrategy`: High-performance with optional dependency

    4. **Matchers** (`matcher.py`):
       - `FuzzyContentSimilarityMatcher`: Production-ready weighted matching

Performance:
    Typical performance characteristics:
    - Small datasets (< 100 incidents): < 10ms processing time
    - Medium datasets (100-1000 incidents): 100ms - 2s processing time
    - Large datasets (1000+ incidents): Scales O(n²), consider chunking
    - Strategy choice significantly impacts performance:
      - SequenceMatcherStrategy: Reliable, moderate performance
      - RapidFuzzStrategy: 2-10x faster with rapidfuzz installed

Usage Patterns:

    **Real-time duplicate checking**:
    ```python
    matcher = FuzzyContentSimilarityMatcher(RapidFuzzStrategy(), threshold=0.85)

    def check_for_duplicates(new_incident, existing_incidents):
        for existing in existing_incidents:
            score = matcher.calculate_similarity(new_incident, existing)
            if score.is_duplicate:
                return existing, score
        return None, None
    ```

    **Batch deduplication**:
    ```python
    def deduplicate_incidents(incidents):
        matcher = FuzzyContentSimilarityMatcher(RapidFuzzStrategy())
        result = matcher.find_duplicates(incidents)

        # Keep only unique incidents
        unique_incidents = [incidents[i] for i in result.unique_incidents]

        # Process duplicate groups for manual review
        for idx1, idx2, score in result.duplicate_pairs:
            handle_duplicate_pair(incidents[idx1], incidents[idx2], score)

        return unique_incidents
    ```

    **Custom matching strategies**:
    ```python
    class CustomStrategy:
        def match(self, text1: str | None, text2: str | None) -> float:
            # Implement domain-specific matching logic
            return custom_similarity_score(text1, text2)

    matcher = FuzzyContentSimilarityMatcher(CustomStrategy(), threshold=0.75)
    ```

Integration:
    This module integrates with the broader disaster surveillance system:
    - Input: IncidentContent objects from data ingestion pipeline
    - Output: DuplicationResult for downstream deduplication workflows
    - Monitoring: Performance metrics for system health monitoring
    - Configuration: Field weights tunable based on domain expertise
"""

from ._types import (
    ContentSimilarityMatcher,
    DuplicationResult,
    IncidentContent,
    SimilarityScore,
)
from .matcher import FuzzyContentSimilarityMatcher
from .strategies import MatchingStrategy, RapidFuzzStrategy, SequenceMatcherStrategy

__all__ = [
    # Core Protocol
    "ContentSimilarityMatcher",
    # Value Objects
    "DuplicationResult",
    "FuzzyContentSimilarityMatcher",
    "IncidentContent",
    # Strategy Protocol and Implementations
    "MatchingStrategy",
    "RapidFuzzStrategy",
    "SequenceMatcherStrategy",
    "SimilarityScore",
]

# Version info for API compatibility tracking
__version__ = "1.0.0"
__api_version__ = "1.0"
