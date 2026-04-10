# Architecture Summary - Multi-Stage Disaster Surveillance Pipeline

## Overview

The Disaster Surveillance Reporter is being transformed from a simple linear pipeline to a sophisticated **multi-stage surveillance system** with intelligent deduplication and enhancement capabilities.

## New Pipeline Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   STAGE 1       │    │     STAGE 2      │    │    STAGE 3      │    │   OUTPUT        │
│                 │    │                  │    │                 │    │                 │
│  Multi-Source   │───▶│  DSPy-AI         │───▶│  Multi-Storage  │───▶│  Incident       │
│  Fetching +     │    │  Enhancement     │    │  Backends       │    │  Reports        │
│  Deduplication  │    │                  │    │                 │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
│                                                │                     │
├─ GDACS          Local JSONL Storage            ├─ JSONL             ├─ Date-based Files
├─ ProMED         with Upsert Capability         ├─ SQLite            ├─ Database Records  
├─ ReliefWeb      ┌──────────────────┐          ├─ Email             ├─ Email Reports
├─ News           │  Content         │          ├─ Google Sheets     └─ Spreadsheet Tabs
└─ Additional     │  Similarity      │          └─ Additional
   Sources        │  Matching        │             Backends
                  │  (Fuzzy Match)   │
                  └──────────────────┘
```

## Key Architectural Changes

### 1. Local JSONL as Intermediate Storage
- **Purpose**: Deterministic data capture before AI enhancement
- **Location**: `incidents/by-date/YYYY-MM-DD/incidents.jsonl`
- **Format**: Normalized schema (immediate conversion from raw source data)
- **Capability**: Upsert functionality to prevent duplicates

### 2. Content Similarity Deduplication
```python
class ContentSimilarityMatcher:
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
    
    def is_duplicate(self, incident1: dict, incident2: dict) -> bool:
        """Compare title/description similarity using fuzzy matching."""
        
    def find_duplicates(self, incidents: list[dict]) -> list[tuple]:
        """Find all duplicate pairs in incident list."""
```

**Duplicate Detection Strategy**:
- Primary: Fuzzy matching on incident title/name
- Secondary: Description/summary content similarity  
- Configurable threshold via `--duplicate-threshold 0.8`
- Update existing incidents rather than create duplicates

### 3. Multi-Source CLI Interface
```bash
# Process multiple sources simultaneously
python -m disaster_surveillance_reporter.cli full-cycle \
  --sources gdacs,promed,reliefweb,news \
  --storage jsonl,sqlite,email \
  --duplicate-threshold 0.8

# Individual stage processing
python -m disaster_surveillance_reporter.cli fetch --sources gdacs,news
python -m disaster_surveillance_reporter.cli enhance --input incidents.jsonl  
python -m disaster_surveillance_reporter.cli store --storage email,sheets
```

### 4. Enhanced Test Strategy

**Test Categories** (using pytest marks):
- `@pytest.mark.unit` - Isolated unit tests
- `@pytest.mark.integration` - Component integration tests
- `@pytest.mark.e2e` - End-to-end pipeline tests
- `@pytest.mark.slow` - Tests >50ms (database, network)
- `@pytest.mark.mock` - Mocked external services
- `@pytest.mark.real_api` - Real API calls (optional)

**Mock-First Approach**:
```python
# Default: Everything mocked
task test-fast     # Mock tests only (CI/CD)

# Optional: Real API tests  
task test-e2e      # Real API calls - not automated
task test-slow     # Integration with mocks
```

## Data Flow Details

### Stage 1: Multi-Source Fetching with Deduplication

**Input**: Multiple source adapters
**Process**: 
1. Fetch from all specified sources simultaneously
2. Convert raw data to normalized schema immediately
3. Apply content similarity matching to detect duplicates
4. Upsert to local JSONL (update existing, insert new)

**Output**: `incidents/by-date/YYYY-MM-DD/incidents.jsonl`

### Stage 2: DSPy-AI Enhancement (Future)

**Input**: Local JSONL file with normalized incidents
**Process**:
1. Fill missing information using DSPy-AI
2. Standardize formats and fields
3. Search additional sources for high-priority incidents
4. Skip already-processed incidents

**Output**: `incidents/enhanced/YYYY-MM-DD.jsonl`

### Stage 3: Multi-Backend Storage

**Input**: Enhanced JSONL file
**Process**: Simultaneously write to multiple storage backends
**Backends**:
- `jsonl` - File-based storage with date organization
- `sqlite` - Local database with full schema
- `email` - SMTP delivery of incident summaries
- `sheets` - Google Sheets with daily tabs

## CLI Command Examples

### Basic Operations
```bash
# Fetch from multiple sources
cli fetch --sources gdacs,promed,reliefweb

# Apply deduplication  
cli dedupe --input incidents.jsonl --threshold 0.8

# Enhance with AI
cli enhance --input incidents.jsonl --output enhanced.jsonl

# Store to multiple backends
cli store --input enhanced.jsonl --storage sqlite,email
```

### Full Pipeline
```bash
# Complete pipeline with all stages
cli full-cycle \
  --sources gdacs,promed,reliefweb,healthmap,who,news \
  --storage jsonl,sqlite,email,sheets \
  --duplicate-threshold 0.8 \
  --enhance
```

## Implementation Priority

### Phase 1: Local JSONL + Upserts (CRITICAL)
1. Implement `ContentSimilarityMatcher` class
2. Add upsert capability to `JSONLBackend`  
3. Update CLI for `--duplicate-threshold` flag
4. Add fuzzy matching dependencies

### Phase 2: Multi-Source CLI
1. Update CLI for `--sources` multi-selection
2. Update CLI for `--storage` multi-selection
3. Enhance Pipeline class for multi-stage processing

### Phase 3: Test Restructuring
1. Add pytest marks for test categories
2. Convert tests to mock-first approach
3. Add optional E2E test tasks
4. Create comprehensive mock fixtures

### Phase 4: DSPy-AI Enhancement (Future)
1. Implement `DSPyEnhancer` class
2. Add predefined enhancement formats
3. Implement additional source discovery
4. Add processed incident tracking

## Configuration

### Environment Variables
```bash
# Source Configuration
SOURCES_ENABLED=gdacs,promed,reliefweb,news

# Storage Configuration  
STORAGE_BACKENDS=jsonl,sqlite,email

# Deduplication
DUPLICATE_THRESHOLD=0.8

# AI Enhancement
DSPY_AI_MODEL=openai/gpt-4-turbo
ENHANCE_MISSING_FIELDS=true
```

### Dependencies to Add
```toml
# Fuzzy matching for deduplication
fuzzywuzzy = "^0.18.0"
python-levenshtein = "^0.25.0"

# DSPy for AI enhancement (future)
dspy = "^2.0.0"

# Additional storage backends
sqlalchemy = "^2.0.0"  # SQLite backend
smtplib = "stdlib"     # Email backend (built-in)
```

## Benefits

1. **Deterministic Processing**: Local JSONL provides reliable intermediate storage
2. **Intelligent Deduplication**: Prevents duplicate incidents from multiple sources
3. **Scalable Architecture**: Easy to add new sources and storage backends
4. **Enhanced Data Quality**: AI enhancement fills missing information
5. **Flexible Output**: Multiple storage backends for different use cases
6. **Robust Testing**: Mock-first approach with optional real API tests

This architecture provides a solid foundation for scaling disaster surveillance capabilities while maintaining data quality and avoiding duplicates across multiple information sources.