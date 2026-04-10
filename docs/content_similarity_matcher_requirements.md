# ContentSimilarityMatcher Feature Definition

## Overview

The **ContentSimilarityMatcher** is a component that enables intelligent duplicate detection in the disaster surveillance pipeline using fuzzy string matching on incident content. This component is part of Phase 8.1 architecture changes to implement a 3-stage pipeline with deduplication.

## Purpose

Enable intelligent duplicate detection using fuzzy string matching on incident content (title, description, location) to prevent storing duplicate incidents in our JSONL pipeline.

## Architecture Context

This component integrates into the multi-stage pipeline:
- **Stage 1**: Multi-source incident ingestion → Normalized JSONL (with deduplication) 
- **Stage 2**: JSONL → AI enhancement → Enhanced JSONL  
- **Stage 3**: Enhanced JSONL → Multi-storage backends

The ContentSimilarityMatcher operates in Stage 1 to deduplicate incidents before storage.

## Requirements

### Functional Requirements

1. **Duplicate Detection**: Compare incident content using fuzzy string matching
2. **Configurable Threshold**: Support similarity threshold configuration (default: 0.8)
3. **Multi-Field Matching**: Compare title, description, and location fields
4. **Bulk Processing**: Handle large datasets efficiently
5. **Results Reporting**: Provide similarity scores and duplicate identification

### Non-Functional Requirements

1. **Performance**: Handle datasets of 1000+ incidents efficiently
2. **Memory Efficiency**: Process incidents in batches if needed
3. **Testability**: Full unit test coverage with mocked dependencies
4. **Extensibility**: Support for additional matching algorithms via Strategy pattern

### Quality Requirements (from Architect Review)

1. **Rich Domain Objects**: Use `SimilarityScore` and `DuplicationResult` classes instead of primitive types
2. **Strategy Pattern**: Support different matching algorithms (starting with fuzzy matching)
3. **SOLID Compliance**: Single responsibility, dependency injection, protocol-based design
4. **No External Dependencies**: Use only standard library for matching algorithms

## Domain Objects

### SimilarityScore Value Object
```python
@dataclass(frozen=True)
class SimilarityScore:
    """Value object representing similarity between two pieces of content."""
    
    title_score: float
    description_score: float 
    location_score: float
    overall_score: float
    threshold: float
    
    @property
    def is_duplicate(self) -> bool:
        """Check if overall score exceeds threshold."""
        return self.overall_score >= self.threshold
```

### DuplicationResult Value Object
```python
@dataclass(frozen=True)
class DuplicationResult:
    """Value object representing duplicate detection results for a dataset."""
    
    total_incidents: int
    duplicate_pairs: list[tuple[int, int, SimilarityScore]]
    unique_incidents: list[int]  # indices of unique incidents
    processing_time_ms: float
    
    @property
    def duplicate_count(self) -> int:
        """Count of incidents identified as duplicates."""
        return len({idx for pair in self.duplicate_pairs for idx in pair[:2]})
```

### Incident Content Value Object
```python
@dataclass(frozen=True)
class IncidentContent:
    """Value object for incident content used in similarity matching."""
    
    title: str
    description: str
    location: str
    incident_id: str
    
    @classmethod
    def from_dict(cls, incident: dict[str, Any]) -> 'IncidentContent':
        """Create from incident dictionary."""
        # Extract relevant fields from incident dict
```

## Protocols and Interfaces

### ContentSimilarityMatcher Protocol
```python
class ContentSimilarityMatcher(Protocol):
    """Protocol for content similarity matching strategies."""
    
    def calculate_similarity(
        self, 
        content1: IncidentContent, 
        content2: IncidentContent
    ) -> SimilarityScore:
        """Calculate similarity score between two incident contents."""
        ...
    
    def find_duplicates(
        self, 
        incidents: list[IncidentContent]
    ) -> DuplicationResult:
        """Find duplicate incidents in a dataset."""
        ...
```

### Matching Strategy Protocol  
```python
class MatchingStrategy(Protocol):
    """Protocol for text matching algorithms."""
    
    def match(self, text1: str, text2: str) -> float:
        """Calculate similarity score between two text strings."""
        ...
```

## Implementation Classes

### FuzzyContentSimilarityMatcher
```python
class FuzzyContentSimilarityMatcher:
    """Fuzzy string matching implementation for content similarity."""
    
    def __init__(
        self, 
        strategy: MatchingStrategy,
        threshold: float = 0.8,
        title_weight: float = 0.4,
        description_weight: float = 0.4, 
        location_weight: float = 0.2
    ):
        # Constructor with configurable weights and threshold
    
    def calculate_similarity(
        self, 
        content1: IncidentContent, 
        content2: IncidentContent
    ) -> SimilarityScore:
        # Implementation using strategy pattern
        
    def find_duplicates(
        self, 
        incidents: list[IncidentContent]
    ) -> DuplicationResult:
        # Pairwise comparison with early termination optimization
```

### SequenceMatcherStrategy
```python
class SequenceMatcherStrategy:
    """Standard library difflib.SequenceMatcher strategy."""
    
    def match(self, text1: str, text2: str) -> float:
        # Implementation using difflib.SequenceMatcher
```

## Integration Points

### Pipeline Integration
The ContentSimilarityMatcher integrates into the Pipeline class in the following way:

1. **Before Storage**: Run deduplication on transformed incidents before storage
2. **Upsert Support**: Use similarity matching to identify existing incidents for updates
3. **CLI Integration**: Support `--duplicate-threshold` flag for threshold configuration

### JSONLBackend Enhancement
The JSONLBackend will be enhanced with upsert capabilities:

```python
def upsert(
    self, 
    incidents: list[dict], 
    similarity_matcher: ContentSimilarityMatcher
) -> None:
    """Insert new incidents and update existing ones based on similarity matching."""
    # Read existing incidents
    # Find duplicates using similarity matcher
    # Merge/update existing incidents, append new ones
```

## Acceptance Criteria

### Content Similarity Detection
- [ ] **Given** two incidents with 90% similar titles **When** similarity is calculated **Then** title score should be ≥ 0.9
- [ ] **Given** two incidents with identical descriptions **When** similarity is calculated **Then** description score should be 1.0
- [ ] **Given** two incidents with different locations **When** similarity is calculated **Then** location score should be < 0.5
- [ ] **Given** overall similarity of 0.85 and threshold 0.8 **When** checked **Then** should be marked as duplicate

### Bulk Processing
- [ ] **Given** 1000 incidents **When** duplicate detection runs **Then** should complete within 10 seconds
- [ ] **Given** dataset with 10% duplicates **When** processed **Then** should identify all duplicate pairs
- [ ] **Given** dataset with no duplicates **When** processed **Then** should return empty duplicate pairs

### Configuration
- [ ] **Given** threshold of 0.9 **When** incidents with 0.85 similarity **Then** should not be marked as duplicates
- [ ] **Given** custom field weights **When** similarity calculated **Then** should apply correct weighting
- [ ] **Given** different matching strategy **When** injected **Then** should use new strategy

### Integration
- [ ] **Given** Pipeline with ContentSimilarityMatcher **When** incidents processed **Then** should deduplicate before storage
- [ ] **Given** JSONLBackend with existing incidents **When** upsert called **Then** should merge duplicates
- [ ] **Given** CLI with --duplicate-threshold **When** pipeline runs **Then** should apply specified threshold

## Testing Strategy

### Unit Tests
- **SimilarityScore**: Value object validation and properties
- **DuplicationResult**: Calculation methods and properties
- **IncidentContent**: Factory methods and validation
- **FuzzyContentSimilarityMatcher**: Algorithm logic with mocked strategy
- **SequenceMatcherStrategy**: Text matching accuracy

### Integration Tests
- **Pipeline Integration**: End-to-end deduplication in pipeline
- **JSONLBackend Upsert**: File operations with similarity matching
- **CLI Integration**: Command-line flag processing

### Property-Based Tests
- **Reflexivity**: incident.similarity(incident) == 1.0
- **Symmetry**: incident1.similarity(incident2) == incident2.similarity(incident1)
- **Triangle Inequality**: Validate transitivity properties
- **Threshold Boundaries**: Edge cases around threshold values

## Performance Considerations

### Optimization Strategies
1. **Early Termination**: Stop comparison if partial scores indicate no match
2. **Indexing**: Create text-based indices for large datasets  
3. **Batch Processing**: Process incidents in configurable batch sizes
4. **Caching**: Cache similarity calculations for repeated comparisons

### Memory Management
- Stream processing for large datasets
- Configurable batch sizes to control memory usage
- Cleanup of intermediate results

## Future Enhancements

### Additional Strategies
- **Levenshtein Distance**: Character-level edit distance
- **Jaccard Similarity**: Set-based similarity for location matching
- **Semantic Matching**: Embedding-based similarity (future with AI integration)

### Advanced Features
- **Clustering**: Group similar incidents beyond pairwise comparison
- **Temporal Matching**: Consider time proximity in similarity
- **Geospatial Matching**: Geographic distance for location similarity

## Dependencies

### Internal
- `disaster_surveillance_reporter.adapters._types.RawIncidentData`
- `disaster_surveillance_reporter.storage.jsonl.JSONLBackend`
- `disaster_surveillance_reporter.pipeline.Pipeline`

### External (Standard Library Only)
- `difflib.SequenceMatcher`: For fuzzy string matching
- `typing`: For protocols and type hints
- `dataclasses`: For value objects
- `time`: For performance measurement

## File Structure

```
disaster_surveillance_reporter/
├── similarity/
│   ├── __init__.py           # Public API exports
│   ├── _types.py             # Domain objects (SimilarityScore, etc.)
│   ├── matcher.py            # ContentSimilarityMatcher implementations
│   └── strategies.py         # Matching strategy implementations
├── storage/
│   └── jsonl.py             # Enhanced with upsert method
└── pipeline/
    └── __init__.py          # Enhanced with deduplication
```

## Documentation Requirements

- [ ] **API Documentation**: Full docstrings for all public interfaces
- [ ] **Usage Examples**: Code examples for common use cases
- [ ] **Performance Benchmarks**: Timing data for different dataset sizes
- [ ] **Strategy Comparison**: Accuracy and performance of different matching strategies

## Migration Notes

This is a new component with no breaking changes to existing code. Integration points require:

1. **Pipeline Enhancement**: Add optional deduplication step
2. **JSONLBackend Extension**: Add upsert method alongside existing read/write/append
3. **CLI Extension**: Add new optional flags

No existing functionality will be modified or removed.