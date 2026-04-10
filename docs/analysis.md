# Project Analysis for Architect

## Executive Summary

**Disaster Surveillance Reporter** is a backend-focused Python application that:
1. Fetches disaster incident data from multiple web sources (as modular adapters)
2. Transforms source data into a defined schema format using OpenCode AI
3. Classifies incidents using rule files via OpenCode CLI with minimax-m2.5-free model
4. Stores processed incidents using pluggable storage backends
5. Excludes dashboard - purely backend processing pipeline

This is a refactored/rearchitected version of the parent project `src-disaster-awareness`, focusing on modular, testable architecture with proper adapter patterns and mockable AI integration.

---

## New Requirements (2026-04-09)

### Summary Enhancement Requirements

The following requirements were added to ensure every incident has a meaningful summary and source attribution:

1. **Sources List**: Each JSONL incident report MUST contain a list of sources
2. **No Null Summaries**: AI must always provide a summary - null summaries are not allowed
3. **Code-Based Fallback**: If no summary data is retrieved from sources, programmatically generate a summary in human language based on available incident JSONL fields
4. **Short Summary**: Keep summary concise - one short paragraph
5. **Source Reference**: Users can check sources if they want more details

---

## Problem Statement

The current `src-disaster-awareness` project has these issues:
- **Tightly coupled CLI**: OpenCode calls embedded directly in CLI code
- **No abstraction**: Hard to swap data sources or storage backends
- **No testability**: Cannot test without hitting free model API (daily quota limits)
- **Dashboard included**: Want backend-only focus

This project solves by:
- Adapter pattern for pluggable sources and storage
- DSPy for structured AI transformations (testable with mocks)
- Rule-based classification via OpenCode CLI (called from code, mockable)
- Pure backend - no dashboard

---

## Stakeholders

### Primary
- **Backend developers**: Want clean, testable architecture
- **Data engineers**: Want to plug in new sources easily
- **CI/CD pipelines**: Need reliable, mockable tests

### Secondary
- **Ops teams**: Want reliable incident processing
- **Researchers**: Want structured incident data

---

## Functional Requirements

### Core Features

#### F1: Modular Source Adapters (Adapter Pattern)
**Description:** Pluggable incident sources that implement a common interface
**Priority:** P0
**Acceptance Criteria:**
- [ ] `SourceAdapter` protocol/abstract base class exists in `disaster_surveillance_reporter.adapters`
- [ ] GDACSAdapter implemented - fetches real data from GDACS API (no mocks in real-data tests)
- [ ] ProMEDAdapter implemented - fetches real data from ProMED RSS feeds
- [ ] ReliefWebAdapter implemented - fetches real data from ReliefWeb API
- [ ] HealthMapAdapter implemented - fetches data from HealthMap
- [ ] WHOAdapter implemented - fetches data from WHO emergencies
- [ ] Can add new sources by implementing protocol (no code changes to core)
- [ ] All adapters return raw incident data in common format
- [ ] **Test Requirement**: GDACS adapter must pass tests with actual HTTP calls to https://www.gdacs.org/
**Architecture:**
```python
class SourceAdapter(Protocol):
    """Protocol for incident source adapters."""
    def fetch(self) -> list[dict]: ...
    @property
    def source_name(self) -> str: ...
```

#### F2: Modular Storage Backends (Adapter Pattern)
**Description:** Pluggable storage backends that implement a common interface
**Priority:** P0
**Acceptance Criteria:**
- [ ] `StorageBackend` protocol/abstract base class exists
- [ ] JSONL backend implemented (matching parent format)
- [ ] JSONL backend stores in date-based subfolders: `incidents/by-date/{YYYY-MM-DD}/incidents.jsonl` (UTC)
- [ ] SQLiteBackend implemented - stores in `incidents.db` with defined schema
- [ ] EmailBackend implemented - sends incidents via SMTP
- [ ] Can add new backends by implementing protocol
- [ ] Supports both read and write operations
- [ ] **Test Requirement**: JSONL storage tests must verify date-based subfolder creation (YYYY-MM-DD format UTC)
**Architecture:**
```python
from dataclasses import dataclass, field
from typing import Protocol

@dataclass(frozen=True, slots=True)
class Incident:
    """Schema-compliant incident record."""
    incident_id: str
    incident_name: str
    created_date: str
    updated_date: str
    status: str
    
    # Extended fields for impact and description
    summary: str | None = None  # Textual description from source
    estimated_affected: int | None = None  # People affected
    estimated_deaths: int | None = None  # Deaths (estimated)
    
    classification: dict = field(default_factory=dict)
    location: dict = field(default_factory=dict)
    impact: dict = field(default_factory=dict)
    sources: list = field(default_factory=list)
    disaster_details: dict | None = None
    disease_details: dict | None = None
    tags: list = field(default_factory=list)
    media_coverage: dict = field(default_factory=dict)
    classification_metadata: dict = field(default_factory=dict)
    src_involvement: dict = field(default_factory=dict)
    escalation_tracking: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    
    should_report: bool = False


class StorageBackend(Protocol):
    """Protocol for storage backends."""
    def write(self, incidents: list[Incident]) -> None: ...
    def read(self) -> list[Incident]: ...
```

#### F3: OpenCode AI Transformation & Classification
**Description:** Use OpenCode CLI with minimax-m2.5-free model for both transformation and classification
**Priority:** P0
**Acceptance Criteria:**
- [ ] OpenCode CLI used for both transformation (raw → schema) and classification
- [ ] Uses fields from `.opencode/skills/data-schema/SKILL.md` in parent
- [ ] Input: raw data from source adapters
- [ ] Output: schema-compliant incident dict with classification
- [ ] Can be mocked for tests (avoid API calls)
- [ ] DSPy NOT used - OpenCode CLI alone is sufficient for this use case

#### F4: Rule-Based Classification
**Description:** Use classification rules to categorize incidents
**Priority:** P0
**Acceptance Criteria:**
- [ ] Classification rules loaded from parent skill files
- [ ] Country groups (A/B/C), levels (1-4), priority (HIGH/MEDIUM/LOW)
- [ ] OpenCode CLI called programmatically (subprocess)
- [ ] Returns classified incidents
- [ ] Can be mocked for tests (avoid API calls to free model)

#### F5: Processing Pipeline
**Description:** Orchestrate fetch → transform → classify → store flow
**Priority:** P0
**Acceptance Criteria:**
- [ ] Pipeline class that coordinates all stages
- [ ] Stages are mockable individually
- [ ] Supports incremental processing (only new incidents)
- [ ] Includes staging area for intermediate data

#### F6: CLI Interface
**Description:** Command-line interface for operations using Fire
**Priority:** P0
**Acceptance Criteria:**
- [ ] Uses Fire library (already in dependencies)
- [ ] Commands: `fetch`, `classify`, `store`, `status`, `full-cycle`
- [ ] Works with existing Pipeline, SourceAdapter, StorageBackend
- [ ] Configurable via environment or flags
- [ ] Help text for each command

#### F7: Test Suite with Mocks
**Description:** Comprehensive tests that avoid actual API calls
**Priority:** P0
**Acceptance Criteria:**
- [ ] All OpenCode CLI calls mockable
- [ ] Minimum 100% coverage per project standards
- [ ] Mock fixtures stored in `tests/fixtures/`

---

## Technical Specifications

### Core Value Objects

#### RawIncidentData (from Source Adapters)
```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True, slots=True)
class RawIncidentData:
    """Common format returned by all source adapters."""
    source_name: str
    incident_name: str
    country: str
    disaster_type: str
    report_date: str
    source_url: str
    raw_fields: dict[str, Any]
```

#### Incident (Schema-Compliant Record)
```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Incident:
    """Schema-compliant incident record per data-schema/SKILL.md."""
    incident_id: str
    incident_name: str
    created_date: str
    updated_date: str
    status: str  # Active | Forecasted | Updating | Resolved | Monitoring
    
    classification: dict
    location: dict
    impact: dict
    sources: list[dict]
    disaster_details: dict | None
    disease_details: dict | None
    tags: list[str]
    media_coverage: dict
    classification_metadata: dict
    src_involvement: dict
    escalation_tracking: dict
    metadata: dict
    
    should_report: bool
```

#### Classification Rules Structure
```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class CountryGroup:
    name: str  # A, B, or C
    countries: set[str]

@dataclass(frozen=True, slots=True)
class PriorityRule:
    level: int  # 1-4
    group: str  # A, B, C
    priority: str  # HIGH, MEDIUM, LOW
    should_report: bool

@dataclass(frozen=True, slots=True)
class ClassificationRules:
    country_groups: list[CountryGroup]
    priority_matrix: list[PriorityRule]
    incident_types: set[str]
```

---

## Feature Specifications

### Feature 1: Source Adapter Protocol
**Purpose:** Allow pluggable incident sources without modifying core code

**Technical Specification:**
```python
from typing import Protocol

class SourceAdapter(Protocol):
    """Protocol for incident source adapters."""
    
    def fetch(self) -> list[RawIncidentData]:
        """Fetch raw incidents from source."""
        ...
    
    @property
    def source_name(self) -> str:
        """Return the source identifier."""
        ...
```

**Adapter Implementations Required:**

#### 1. GDACSAdapter
- **Source**: https://www.gdacs.org/
- **Implementation**: Fetch from GDACS RSS/API feeds
- **Real Data Test**: Must make actual HTTP requests to GDACS
- **Returns**: List of RawIncidentData with disaster information

#### 2. ProMEDAdapter
- **Source**: https://www.promedmail.org/
- **Implementation**: Fetch from ProMED RSS feeds
- **Real Data Test**: Must make actual HTTP requests to ProMED
- **Returns**: List of RawIncidentData with disease outbreaks

#### 3. ReliefWebAdapter
- **Source**: https://reliefweb.int/
- **Implementation**: Fetch from ReliefWeb API
- **Real Data Test**: Must make actual HTTP requests to ReliefWeb
- **Returns**: List of RawIncidentData with humanitarian data

#### 4. HealthMapAdapter
- **Source**: https://www.healthmap.org/
- **Implementation**: Fetch from HealthMap disease data
- **Returns**: List of RawIncidentData with disease surveillance

#### 5. WHOAdapter
- **Source**: https://www.who.int/emergencies/
- **Implementation**: Fetch from WHO emergencies endpoint
- **Returns**: List of RawIncidentData with health emergencies

**Acceptance Criteria:**
- [ ] SourceAdapter protocol exists in `disaster_surveillance_reporter.adapters`
- [ ] GDACSAdapter implements the protocol with real HTTP calls
- [ ] ProMEDAdapter implements the protocol
- [ ] ReliefWebAdapter implements the protocol
- [ ] HealthMapAdapter implements the protocol
- [ ] WHOAdapter implements the protocol
- [ ] Can add new source by creating class that implements protocol
- [ ] All adapters return list[RawIncidentData]
- [ ] GDACS adapter tests fetch real data from https://www.gdacs.org/

---

### Feature 2: Storage Backend Protocol
**Purpose:** Allow pluggable storage backends

**Technical Specification:**
```python
class StorageBackend(Protocol):
    """Protocol for storage backends."""
    
    def write(self, incidents: list[Incident]) -> None:
        """Write incidents to storage."""
        ...
    
    def read(self) -> list[Incident]:
        """Read all incidents from storage."""
        ...
    
    def append(self, incidents: list[Incident]) -> None:
        """Append new incidents to existing storage."""
        ...
```

**Backend Implementations Required:**

#### 1. JSONLBackend (Update Required)
- **Storage Location**: `incidents/by-date/{YYYY-MM-DD}/incidents.jsonl`
- **Date Format**: YYYY-MM-DD (UTC timezone)
- **Example Path**: `incidents/by-date/2026-04-09/incidents.jsonl`
- **Implementation**: Create date-based subfolder automatically
- **Test Requirement**: Must verify date-based subfolder creation with UTC date

#### 2. SQLiteBackend
- **Storage Location**: `incidents.db` (SQLite database file)
- **Schema**: Per defined SQL schema in External Integrations section
- **Implementation**: Use sqlite3 with defined table structure
- **Indexes**: created_date, should_report

#### 3. EmailBackend
- **Protocol**: SMTP
- **Configuration**: Via environment variables (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
- **Implementation**: Use smtplib for sending emails
- **Features**: Batch incidents, configurable HTML template

**Acceptance Criteria:**
- [ ] StorageBackend protocol exists
- [ ] JSONL backend implements protocol with date-based subfolders
- [ ] SQLiteBackend implements protocol
- [ ] EmailBackend implements protocol
- [ ] Can add new backend by implementing protocol
- [ ] JSONL tests verify `incidents/by-date/YYYY-MM-DD/incidents.jsonl` format

---

### Feature 3: Classification Rules Loader
**Purpose:** Load and provide access to classification rules

**Technical Specification:**
```python
class RulesLoader:
    """Loads classification rules from rules/ directory."""
    
    def load_country_groups(self) -> dict[str, set[str]]:
        """Returns {group_name: set(countries)}."""
        ...
    
    def get_priority(self, level: int, group: str) -> str:
        """Returns HIGH/MEDIUM/LOW based on matrix."""
        ...
    
    def should_report(self, level: int, group: str) -> bool:
        """Returns whether incident should be reported."""
        ...
    
    def get_country_group(self, country: str) -> str:
        """Returns A, B, or C based on country."""
        ...
```

**Acceptance Criteria:**
- [ ] RulesLoader class loads from rules/ directory
- [ ] Country groups A, B, C correctly defined per incident-classifier/SKILL.md
- [ ] Priority matrix correctly implemented per incident-classifier/SKILL.md
- [ ] Fallback classification when rules unavailable

---

### Feature 4: OpenCode Client
**Purpose:** Transform raw incidents to schema format and classify using AI

**Technical Specification:**
```python
class OpenCodeClient:
    """Client for OpenCode CLI with minimax-m2.5-free model."""
    
    def transform(self, raw_incident: RawIncidentData) -> Incident:
        """Transform raw incident to schema-compliant Incident."""
        ...
    
    def classify(self, incident: Incident) -> Incident:
        """Classify incident using AI with rules."""
        ...
    
    def transform_batch(self, raw_incidents: list[RawIncidentData]) -> list[Incident]:
        """Transform multiple incidents."""
        ...
    
    def classify_batch(self, incidents: list[Incident]) -> list[Incident]:
        """Classify multiple incidents."""
        ...
```

**Acceptance Criteria:**
- [ ] OpenCodeClient uses subprocess to call opencode CLI
- [ ] Uses minimax-m2.5-free model
- [ ] Can be mocked for tests (avoid API calls)
- [ ] Returns schema-compliant Incident objects

---

### Feature 5: Pipeline Orchestration
**Purpose:** Coordinate fetch → transform → classify → store flow

**Technical Specification:**
```python
class Pipeline:
    """Orchestrates the full incident processing pipeline."""
    
    def __init__(
        self,
        sources: list[SourceAdapter],
        storage: StorageBackend,
        opencode_client: OpenCodeClient,
        rules_loader: RulesLoader,
    ):
        ...
    
    def run_full_cycle(self) -> list[Incident]:
        """Run complete pipeline: fetch → transform → classify → store."""
        ...
    
    def fetch_all(self) -> list[RawIncidentData]:
        """Fetch from all sources."""
        ...
    
    def transform_all(self, raw_incidents: list[RawIncidentData]) -> list[Incident]:
        """Transform all raw incidents."""
        ...
    
    def classify_all(self, incidents: list[Incident]) -> list[Incident]:
        """Classify all incidents."""
        ...
    
    def store_all(self, incidents: list[Incident]) -> None:
        """Store all incidents."""
        ...
```

**Acceptance Criteria:**
- [ ] Pipeline class orchestrates all stages
- [ ] Each stage can be run individually
- [ ] All stages are mockable for testing
- [ ] Handles partial failures gracefully

---

### Feature 6: CLI Interface
**Purpose:** Provide command-line interface for operations using Fire

**Technical Specification:**
```python
import fire

class CLI:
    """Fire-based CLI for disaster surveillance operations."""

    def fetch(self, source: str | None = None):
        """Fetch incidents from source(s).
        
        Args:
            source: Optional source name (gdacs, promed, reliefweb, healthmap, who).
                   If not provided, fetches from all sources.
        
        Returns:
            List of fetched raw incidents.
        """
        ...

    def classify(self, incident_ids: list[str] | None = None):
        """Classify incidents using OpenCode AI.
        
        Args:
            incident_ids: Optional list of incident IDs. If not provided,
                         classifies all stored incidents.
        
        Returns:
            List of classified incidents.
        """
        ...

    def store(self):
        """Store processed incidents to storage backend.
        
        Uses the default storage backend from configuration.
        
        Returns:
            Count of stored incidents.
        """
        ...

    def status(self):
        """Show pipeline status and statistics.
        
        Returns:
            Status info including last run, incident counts by source, etc.
        """
        ...

    def full_cycle(self, source: str | None = None):
        """Run full pipeline: fetch -> transform -> classify -> store.
        
        Args:
            source: Optional source name. If not provided, processes all sources.
        
        Returns:
            List of processed incidents with classification.
        """
        ...
```

**Acceptance Criteria:**
- [ ] Uses Fire library (already in pyproject.toml dependencies)
- [ ] Commands: fetch, classify, store, status, full-cycle
- [ ] Works with existing Pipeline class
- [ ] Works with existing SourceAdapter implementations
- [ ] Works with existing StorageBackend implementations
- [ ] Configurable via environment variables (STORAGE_BACKEND, SOURCES, etc.)
- [ ] Help text for each command via --help
- [ ] Error handling with meaningful messages

---

### Feature 7: Test Suite with Mocks
**Purpose:** Comprehensive tests that avoid actual API calls

**Technical Specification:**
```python
# fixtures/opencode_client_mock.py
@pytest.fixture
def mock_opencode_client():
    """Mock OpenCodeClient to avoid API calls."""
    ...

# fixtures/classification_rules_fixture.py
@pytest.fixture
def classification_rules():
    """Fixture with classification rules."""
    ...

# fixtures/sample_incidents.py
@pytest.fixture
def sample_raw_incidents():
    """Sample RawIncidentData for testing."""
    ...

@pytest.fixture
def sample_incidents():
    """Sample Incident objects for testing."""
    ...
```

**Acceptance Criteria:**
- [ ] All OpenCode CLI calls mockable via fixture
- [ ] Minimum 100% coverage
- [ ] Fixtures in tests/fixtures/

#### Incident (Schema-Compliant Record)
```python
from dataclasses import dataclass
from typing import TypedDict

@dataclass(frozen=True, slots=True)
class Incident:
    """Schema-compliant incident record per data-schema/SKILL.md."""
    incident_id: str
    incident_name: str
    created_date: str
    updated_date: str
    status: str  # Active | Forecasted | Updating | Resolved | Monitoring
    
    classification: dict  # country, country_group, region, incident_type, level, priority
    location: dict
    impact: dict
    sources: list[dict]
    disaster_details: dict | None
    disease_details: dict | None
    tags: list[str]
    media_coverage: dict
    classification_metadata: dict
    src_involvement: dict
    escalation_tracking: dict
    metadata: dict
    
    should_report: bool
```

### Extended Schema Fields (New)

The following fields have been added to enhance incident data with impact metrics and detailed descriptions:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `summary` | str | Optional | Textual description of the incident based on raw data. Captures detailed narrative from sources like ProMED, ReliefWeb, WHO. |
| `estimated_affected` | int | Optional | Estimated number of people affected by the incident. Sources may provide this as "population affected", "casualties", "cases", "displaced", etc. |
| `estimated_deaths` | int | Optional | Estimated number of deaths. Sources may report this as "fatalities", "deaths", "mortality", etc. |

#### Source-Specific Field Mapping

Different sources provide impact data in different formats. The transformation layer should map:

| Source | Impact Fields Available |
|--------|------------------------|
| **USGS (Earthquakes)** | `felt` - number of people who reported feeling the earthquake. No direct deaths field. |
| **ProMED** | Often includes "cases", "deaths", "hospitalizations" for disease outbreaks |
| **ReliefWeb** | "affected", "displaced", " casualties" in humanitarian reports |
| **WHO** | "cases", "deaths", "hospitalizations" for health emergencies |
| **GDACS** | Various fields depending on disaster type (floods, storms, earthquakes) |

#### Schema Examples

```python
# Example with all new fields populated
incident_with_impact = {
    "incident_id": "20260409-ID-EQ",
    "incident_name": "M6.2 Earthquake in Java, Indonesia",
    "summary": "A magnitude 6.2 earthquake struck Java, Indonesia at 14:00 UTC. The earthquake was felt by approximately 50,000 people in the epicentral region. Local authorities report at least 10 casualties and significant damage to infrastructure.",
    "estimated_affected": 50000,
    "estimated_deaths": 10,
    # ... other fields
}

# Example with partial data (only summary, no numeric estimates)
incident_partial = {
    "incident_id": "20260409-PH-TC",
    "incident_name": "Tropical Cyclone warning Philippines",
    "summary": "Tropical Cyclone warning issued for the Philippines. Expected to make landfall within 24 hours.",
    "estimated_affected": None,  # Not available from source
    "estimated_deaths": None,
    # ... other fields
}
```

#### Implementation Notes

1. **Null Handling**: Fields should be `None` when data unavailable (not omitted)
2. **Type Safety**: Use `int | None` for numeric fields, `str | None` for text
4. **Validation**: Positive integers only for `estimated_affected` and `estimated_deaths`

### Sources and Summary Requirements (2026-04-09)

The following requirements ensure every incident has meaningful summary content and proper source attribution:

#### 1. Sources Field (Required)

Each incident JSONL record MUST contain a `sources` list with at least one source entry.

**Schema:**
```python
sources: list[dict]  # Required - cannot be empty or null
```

**Source Entry Structure:**
```python
{
    "name": str,           # Source name (e.g., "GDACS", "ProMED", "WHO")
    "type": str,           # Source type (e.g., "disaster-database", "disease-database", "health-agency")
    "url": str,            # Direct URL to the source report
    "accessed_date": str,  # ISO 8601 timestamp when source was accessed
    "reliability_tier": str,  # "Tier1" (official), "Tier2" (verified news), "Tier3" (other)
    "data_freshness": str, # "real-time", "daily", "weekly"
}
```

**Requirements:**
- `sources` field must always be present in the output
- `sources` list cannot be empty - must have at least one source
- Each source must have a valid URL
- Multiple sources should be listed if available

#### 2. Summary Field (Required - No Null Allowed)

The `summary` field must always contain meaningful content - null summaries are NOT allowed.

**Schema:**
```python
summary: str  # Required - cannot be null or empty
```

**Priority Order for Summary Generation:**

1. **AI-Generated from Sources**: Use AI to extract/generate summary from source content
   - If source provides a description/abstract, use it
   - If source provides raw text, summarize it using AI
   - Preserve source summary if available

2. **Code-Based Fallback**: If no summary data is available from sources, programmatically generate summary from incident fields
   - Use: `incident_name`, `disaster_type`, `country`, `impact` data
   - Format: One short paragraph in human language
   - Example fallback: "Tropical Cyclone NURI-26 is active in Pacific Ocean with winds of 56 km/h. No casualties reported."

**Summary Style Guidelines:**
- Keep it concise: One short paragraph (1-3 sentences, max 150 characters preferred)
- Include key information: disaster type, location, key impact metrics
- Write in plain human language (not technical jargon)
- Example: "A magnitude 6.2 earthquake struck Java, Indonesia on April 9, 2026. At least 10 people were killed and 50,000 were affected. Local authorities are assessing damage."

#### 3. Schema Examples with New Requirements

```python
# Example 1: Full data from sources with AI summary
incident_full = {
    "incident_id": "20260409-ID-EQ",
    "incident_name": "M6.2 Earthquake in Java, Indonesia",
    "created_date": "2026-04-09T14:00:00Z",
    "updated_date": "2026-04-09T14:00:00Z",
    "status": "Active",
    "summary": "A magnitude 6.2 earthquake struck Java, Indonesia at 14:00 UTC. The earthquake was felt by approximately 50,000 people in the epicentral region. Local authorities report at least 10 casualties and significant damage to infrastructure.",
    # ... other fields
    "sources": [
        {
            "name": "GDACS",
            "type": "disaster-database",
            "url": "https://www.gdacs.org/earthquake/12345",
            "accessed_date": "2026-04-09T14:30:00Z",
            "reliability_tier": "Tier1",
            "data_freshness": "real-time",
        },
        {
            "name": "USGS",
            "type": "scientific-agency",
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/usp0001abc/executive",
            "accessed_date": "2026-04-09T14:35:00Z",
            "reliability_tier": "Tier1",
            "data_freshness": "real-time",
        }
    ],
    "impact": {
        "affected_population": 50000,
        "deaths": 10,
        "injuries": 45,
        "displaced_persons": 5000,
        "affected_provinces": 1,
    },
}

# Example 2: Code-generated fallback summary (no source summary available)
incident_fallback = {
    "incident_id": "20260409-PH-TC",
    "incident_name": "Tropical Cyclone warning Philippines",
    "created_date": "2026-04-09T10:00:00Z",
    "updated_date": "2026-04-09T10:00:00Z",
    "status": "Active",
    "summary": "Tropical Cyclone warning issued for the Philippines. Expected to make landfall within 24 hours with winds up to 120 km/h. Residents in coastal areas advised to evacuate.",
    # ... other fields
    "sources": [
        {
            "name": "PAGASA",
            "type": "national-weather-service",
            "url": "https://bagong.pagasa.dost.gov.ph/tropical-cyclone",
            "accessed_date": "2026-04-09T10:30:00Z",
            "reliability_tier": "Tier1",
            "data_freshness": "real-time",
        }
    ],
    "disaster_details": {
        "disaster_type": "Tropical Cyclone",
        "magnitude_or_scale": 120,
    },
}

# Example 3: Minimum required sources (single source)
incident_minimal = {
    "incident_id": "20260409-MM-FL",
    "incident_name": "Flooding in Mandalay, Myanmar",
    "created_date": "2026-04-09T08:00:00Z",
    "updated_date": "2026-04-09T08:00:00Z",
    "status": "Active",
    "summary": "Flash flood warning issued for Mandalay region in Myanmar. Heavy rainfall expected over the next 24 hours. Low-lying areas may experience flooding.",
    # ... other fields
    "sources": [
        {
            "name": "GDACS",
            "type": "disaster-database",
            "url": "https://www.gdacs.org/flood/12347",
            "accessed_date": "2026-04-09T08:30:00Z",
            "reliability_tier": "Tier1",
            "data_freshness": "real-time",
        }
    ],
}
```

#### Implementation Logic for Summary Generation

```python
def generate_summary(incident: dict) -> str:
    """
    Generate a summary for an incident, following priority:
    1. Use AI-generated summary from source content if available
    2. Use code to generate summary from incident fields
    
    Args:
        incident: The incident dictionary with all fields
        
    Returns:
        A non-null, non-empty summary string (one short paragraph)
    """
    # Priority 1: Check if source provided a summary
    if incident.get("source_summary"):
        return incident["source_summary"]
    
    # Priority 2: Check if AI generated a summary
    if incident.get("summary") and incident["summary"].strip():
        return incident["summary"]
    
    # Priority 3: Code-based fallback generation
    # Build summary from available incident fields
    parts = []
    
    # Disaster type and name
    disaster_type = incident.get("disaster_details", {}).get("disaster_type") or "Incident"
    name = incident.get("incident_name", "")
    if name:
        parts.append(name)
    else:
        parts.append(f"{disaster_type} event")
    
    # Location
    location = incident.get("location", {}).get("country")
    if location:
        parts.append(f"in {location}")
    
    # Impact details
    impact = incident.get("impact", {})
    if impact.get("deaths"):
        parts.append(f"caused {impact['deaths']} deaths")
    if impact.get("affected_population"):
        parts.append(f"affected {impact['affected_population']} people")
    
    # Status
    status = incident.get("status", "")
    if status:
        parts.append(f"({status})")
    
    return ". ".join(parts) if parts else "Incident reported."
```

#### Acceptance Criteria for New Requirements

- [ ] Each incident JSONL record MUST have a `sources` list with at least one entry
- [ ] Each incident JSONL record MUST have a non-null, non-empty `summary` field
- [ ] `sources` field cannot be empty list `[]`
- [ ] `summary` field cannot be `null` or empty string `""`
- [ ] If AI fails to get summary from sources, code fallback generates summary
- [ ] Summary is limited to one short paragraph (recommended ~150 chars or less)
- [ ] Source URLs in `sources` list must be valid URLs
- [ ] Users can check `sources` list for more details if needed

### Classification Rules Structure
```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class CountryGroup:
    name: str  # A, B, or C
    countries: set[str]

@dataclass(frozen=True, slots=True)
class PriorityRule:
    level: int  # 1-4
    group: str  # A, B, C
    priority: str  # HIGH, MEDIUM, LOW
    should_report: bool

@dataclass(frozen=True, slots=True)
class ClassificationRules:
    country_groups: list[CountryGroup]
    priority_matrix: list[PriorityRule]
    incident_types: set[str]
```

#### Source Adapter Interface
```python
from dataclasses import dataclass
from typing import TypedDict

@dataclass(frozen=True, slots=True)
class RawIncidentData:
    """Common format returned by all source adapters."""
    source_name: str
    incident_name: str
    country: str
    disaster_type: str
    report_date: str
    source_url: str
    raw_fields: dict


class SourceAdapter(Protocol):
    """Protocol for incident source adapters."""
    def fetch(self) -> list[RawIncidentData]: ...
    @property
    def source_name(self) -> str: ...
```

---

### External Integrations

#### Input Sources (5 Source Adapters Required)
All source adapters must implement the `SourceAdapter` protocol and fetch real data via HTTP:

| Adapter | URL | Data Type | Priority |
|---------|-----|-----------|----------|
| **GDACSAdapter** | https://www.gdacs.org/ | Disaster database | P0 |
| **ProMEDAdapter** | https://www.promedmail.org/ | Disease database | P0 |
| **ReliefWebAdapter** | https://reliefweb.int/ | Humanitarian | P0 |
| **HealthMapAdapter** | https://www.healthmap.org/ | Disease | P1 |
| **WHOAdapter** | https://www.who.int/emergencies/ | Health emergencies | P1 |

##### GDACSAdapter Requirements
- **URL**: https://www.gdacs.org/
- **API**: GDACS provides RSS feeds and API at https://www.gdacs.org/services/
- **Data Format**: XML/JSON feeds for current disasters
- **Test Requirement**: Must fetch real data via HTTP (not mocked)

##### ProMEDAdapter Requirements
- **URL**: https://www.promedmail.org/
- **API**: ProMED-mail provides RSS feeds
- **Data Format**: XML/RSS for disease outbreaks
- **Test Requirement**: Must fetch real data via HTTP (not mocked)

##### ReliefWebAdapter Requirements
- **URL**: https://reliefweb.int/
- **API**: ReliefWeb provides API at https://reliefweb.int/help/api
- **Data Format**: JSON API for humanitarian emergencies
- **Test Requirement**: Must fetch real data via HTTP (not mocked)

##### HealthMapAdapter Requirements
- **URL**: https://www.healthmap.org/
- **API**: HealthMap provides disease outbreak data
- **Data Format**: JSON API for disease surveillance

##### WHOAdapter Requirements
- **URL**: https://www.who.int/emergencies/
- **API**: WHO provides health emergency data
- **Data Format**: JSON/HTML for WHO emergencies

#### Storage Backends (4 Backends Required)

| Backend | Storage Location | Schema | Priority |
|---------|-----------------|--------|----------|
| **JSONLBackend** | `incidents/by-date/{YYYY-MM-DD}/incidents.jsonl` | JSONL | P0 |
| **SQLiteBackend** | `incidents.db` (SQLite database) | SQL schema | P0 |
| **EmailBackend** | SMTP server | Email delivery | P1 |
| **GoogleSheetsBackend** | Google Sheets (per-tab per day) | Spreadsheet | P1 |

##### JSONLBackend Requirements (Update Needed)
- **Location**: `incidents/by-date/{YYYY-MM-DD}/incidents.jsonl` (UTC timezone)
- **Date Format**: YYYY-MM-DD based on current UTC date
- **Example**: `incidents/by-date/2026-04-09/incidents.jsonl`
- **Schema**: One JSON object per line, Incident dataclass serialized

##### SQLiteBackend Requirements
- **Location**: `incidents.db` (SQLite database file)
- **Schema**:
  ```sql
  CREATE TABLE incidents (
      incident_id TEXT PRIMARY KEY,
      incident_name TEXT NOT NULL,
      created_date TEXT NOT NULL,
      updated_date TEXT NOT NULL,
      status TEXT NOT NULL,
      classification_json TEXT NOT NULL,
      location_json TEXT NOT NULL,
      impact_json TEXT NOT NULL,
      sources_json TEXT NOT NULL,
      disaster_details_json TEXT,
      disease_details_json TEXT,
      tags_json TEXT NOT NULL,
      media_coverage_json TEXT NOT NULL,
      classification_metadata_json TEXT NOT NULL,
      src_involvement_json TEXT NOT NULL,
      escalation_tracking_json TEXT NOT NULL,
      metadata_json TEXT NOT NULL,
      should_report INTEGER NOT NULL
  );
  CREATE INDEX idx_created_date ON incidents(created_date);
  CREATE INDEX idx_should_report ON incidents(should_report);
  ```

##### EmailBackend Requirements
- **Protocol**: SMTP
- **Configuration**: Environment variables for SMTP server, port, credentials
- **Format**: HTML email with incident summary
- **Features**: Batch incidents, configurable template

##### GoogleSheetsBackend Requirements
- **Storage Location**: Google Sheets spreadsheet (URL via environment variable)
- **Tab Structure**: One tab per day, tab name = ISO date (YYYY-MM-DD)
- **Row Behavior**: Never overwrite - find next empty row (append mode)
- **Header Row**: All rows share the same header columns (row 1)
- **Multi-Entry Fields**: Fields like `sources` stored as JSON string in single cell

**Environment Variable:**
```bash
# .env file
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/12ueZ6hV8dnS9CaJHDYWDb34sFEltl4niP4ulshqty84/edit
```

**Spreadsheet Schema (Column Headers):**

| Column | Field from Incident JSON | Type | Description |
|--------|--------------------------|------|-------------|
| A | incident_id | STRING | Unique incident identifier |
| B | incident_name | STRING | Name/title of the incident |
| C | created_date | DATETIME | ISO 8601 creation timestamp |
| D | updated_date | DATETIME | ISO 8601 last update timestamp |
| E | status | STRING | Active/Forecasted/Updating/Resolved/Monitoring |
| F | summary | STRING | Incident summary (required, non-null) |
| G | country | STRING | Country name |
| H | country_group | STRING | A, B, or C |
| I | incident_type | STRING | Type of disaster |
| J | incident_level | NUMBER | Level 1-4 |
| K | priority | STRING | HIGH/MEDIUM/LOW |
| L | should_report | BOOLEAN | Whether to include in reports |
| M | affected_population | NUMBER | People affected |
| N | deaths | NUMBER | Death count |
| O | injuries | NUMBER | Injury count |
| P | displaced_persons | NUMBER | Displaced persons |
| Q | disaster_type | STRING | Detailed disaster type |
| R | magnitude_or_scale | NUMBER | Magnitude/scale value |
| P | first_reported | DATETIME | When first reported |
| S | tags | STRING | JSON array of tags |
| T | sources | STRING | JSON array of source objects |
| U | location_json | STRING | Full location object as JSON |
| V | impact_json | STRING | Full impact object as JSON |
| W | disaster_details_json | STRING | Full disaster details as JSON |
| X | disease_details_json | STRING | Full disease details as JSON (can be null) |
| Y | media_coverage_json | STRING | Full media coverage as JSON |
| Y | classification_metadata_json | STRING | Full classification metadata as JSON |
| Z | src_involvement_json | STRING | Full SRC involvement as JSON |
| AA | escalation_tracking_json | STRING | Full escalation tracking as JSON |
| AB | metadata_json | STRING | Full metadata as JSON |

**Multi-Entry Field Handling (sources, tags):**

The `sources` field is a list of objects. To store in a single cell:
- **Format**: JSON string with compact formatting
- **Example**: `[{"name":"GDACS","type":"disaster-database","url":"https://gdacs.org/123","accessed_date":"2026-04-09T00:00:00Z","reliability_tier":"Tier1","data_freshness":"real-time"}]`

The `tags` field is a list of strings:
- **Format**: JSON array string
- **Example**: `["escalation-risk","monitoring"]`

**Implementation Details:**

1. **Google Sheets API**: Use Google Sheets API v4
2. **Authentication**: Service account or OAuth (service account preferred for backend)
3. **Sheet ID Extraction**: Extract sheet ID from URL pattern `spreadsheets/d/{SHEET_ID}/edit`
4. **Tab Creation**: Create new tab if not exists for current date (YYYY-MM-DD)
5. **Row Appending**:
   - Get current tab data
   - Find first empty row (where column A is empty)
   - Write data starting at that row
   - If no header row exists, write header first
6. **Error Handling**: Handle API rate limits, concurrent access

**Priority:** P1 (new feature)

---

#### Classification Rules (from Parent)
- Located: `.opencode/skills/incident-classifier/SKILL.md`
- Country groups: A (25 Asia Pacific countries), B (MENA + Asia Pac 2), C (Rest)
- Priority matrix: Level × Country Group → Priority

#### AI Integration
- **OpenCode CLI**: `opencode run --model minimax-m2.5-free` for transformation and classification

---

## Non-Functional Requirements

### Performance
- Process 100+ incidents in <30 seconds
- Support incremental processing (only new data)
- Staging area for intermediate storage

### Security
- No hardcoded API keys
- Environment-based configuration
- Sanitize inputs before passing to AI

### Scalability
- Adapter pattern for easy source addition
- Backend pattern for easy storage addition
- Support horizontal scaling

### Testability
- All external calls mockable
- Fixtures for mock data
- Minimum 100% coverage

---

## Technical Constraints

### Technology Stack
- **Python**: >=3.13
- **Package Manager**: UV (per project conventions)
- **Testing**: pytest, hypothesis
- **AI**: OpenCode CLI (minimax-m2.5-free model)
- **CLI**: Fire or Click

### Dependencies (to add)
- `opencode-cli` for AI calls
- `jsonlines` or similar for JSONL handling
- `fire` or `click` for CLI

### Classification Rules Loading
- **Location**: Rules stored in `rules/` directory (copied from parent `.opencode/skills/incident-classifier/`)
- **Format**: YAML files for country groups, priority matrix, type definitions
- **Loading**: RulesLoader class that reads, caches, and provides access to classification rules
- **Fallback**: Default classification when rules unavailable (country_group=C, level=3, priority=MEDIUM)

### Error Handling Strategy
- **Exception Hierarchy**:
  - `PipelineError` (base) → `SourceError`, `ClassificationError`, `StorageError`
- **Retry Logic**: 3 retries with exponential backoff for external calls
- **Staging Area**: Failed records go to `staging/failed/` as JSONL for retry
- **Pipeline Abort Conditions**: Continue on source/storage failure; halt on classification error

### Parent Project References
- **Schema**: `src-disaster-awareness/.opencode/skills/data-schema/SKILL.md`
- **Classifier**: `src-disaster-awareness/.opencode/skills/incident-classifier/SKILL.md`
- **CLI**: `src-disaster-awareness/disaster_monitor/cli.py`

---

## Architectural Considerations

### Adapter Pattern
Use the adapter pattern (also known as ports and adapters/hexagonal architecture):
```
┌─────────────────────────────────────┐
│         Pipeline (Core)               │
│  ┌─────────────────────────────┐   │
│  │ Fetch → Transform → Classify │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
           │              │
     ┌─────┴─────┐  ┌────┴────┐
     │ Sources   │  │ Storage │
     │ (Port)    │  │ (Port)  │
     └─────┬─────┘  └────┬────┘
           │              │
     ┌─────┴─────┐  ┌────┴────┐
     │ GDACS     │  │ JSONL   │
     │ ProMED   │  │ SQLite  │
     │ ReliefWeb │  │ S3     │
     │ ...      │  │ ...    │
```

### Mock Strategy
```python
# All external integrations should be injectable
class Pipeline:
    def __init__(
        self,
        sources: list[SourceAdapter],
        storage: StorageBackend,
        opencode_client: OpenCodeClient,  # mockable for transformation + classification
    ): ...
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Free model quota limits | High | Medium | Mock all calls; use fixtures |
| OpenCode CLI availability | Low | Medium | Fallback to rule-based classification |
| Parent schema changes | Low | Medium | Version schema; validate |
| Adapter interface changes | Medium | Medium | Protocol-based; easy to adapt |

---

## Questions for Architect

1. **DSPy Usage**: Should I use DSPy for transformation, or is direct OpenCode CLI sufficient?
2. **Storage Backends**: Which backends should be implementable now vs. later? (JSONL first, others later)
3. **CLI Library**: Fire (parent uses) or Click (more modern)?
4. **Error Handling**: How to handle partial failures in pipeline?
5. **Schema Versioning**: How to handle parent schema changes?

---

## Acceptance Criteria Summary

### Must Have (P0) - Current Session Focus
- [ ] SourceAdapter protocol and all 5 implementations (GDACS, ProMED, ReliefWeb, HealthMap, WHO)
- [ ] StorageBackend protocol and all 3 implementations (JSONL with date-subfolders, SQLite, Email)
- [ ] **GDACS adapter tests must make real HTTP calls to https://www.gdacs.org/**
- [ ] **JSONL storage tests must verify date-based subfolder creation (YYYY-MM-DD UTC)**
- [ ] Pipeline orchestration with all stages
- [ ] **CLI Interface using Fire** with commands: fetch, classify, store, status, full-cycle
- [ ] CLI works with existing Pipeline, SourceAdapter, StorageBackend
- [ ] Test mocks for OpenCode CLI (but GDACS must have real-data tests)
- [ ] Minimum 100% test coverage

### New Requirements (2026-04-09)
- [ ] Each incident JSONL record MUST have a `sources` list with at least one entry
- [ ] Each incident JSONL record MUST have a non-null, non-empty `summary` field
- [ ] If no summary from sources, code fallback generates summary from incident fields
- [ ] Summary limited to one short paragraph
- [ ] Source URLs in `sources` list must be valid URLs
- [ ] Users can check `sources` list for more details if needed

### Should Have (P1)
- [ ] Additional source adapters (ProMED, ReliefWeb) with real data tests
- [ ] Configuration via environment variables
- [ ] Staging area management

### Could Have (P2)
- [ ] HealthMap and WHO adapters (lower priority)
- [ ] Incremental processing
- [ ] Comprehensive documentation
- [ ] CLI auto-completion support

---

## Feature 8: Gmail Email Reporter

### Purpose: Send incident reports via Gmail API

### Overview

Yes, there is a Gmail API in Python. The project already has Google Sheets integration that uses OAuth2, so we can follow a similar pattern for Gmail.

### Gmail API Approach

**Library:** `google-api-python-client` (same as Google Sheets)
**Dependencies to add:**
```
google-api-python-client>=2.100.0
google-auth>=2.20.0
google-auth-oauthlib>=1.0.0
```

**API Method:** `users().messages().send()`
- Scope needed: `https://www.googleapis.com/auth/gmail.send`
- Use `userId="me"` for authenticated user

### Authentication (Similar to Google Sheets)

Following the same pattern as `google_sheets.py`:

#### Option 1: OAuth2 with Refresh Token (Recommended for backend)
```python
from google.oauth2.credentials import Credentials

credentials = Credentials(
    None,
    refresh_token=os.environ.get("GMAIL_REFRESH_TOKEN"),
    client_id=os.environ.get("GMAIL_CLIENT_ID"),
    client_secret=os.environ.get("GMAIL_CLIENT_SECRET"),
    token_uri="https://oauth2.googleapis.com/token",
    scopes=["https://www.googleapis.com/auth/gmail.send"]
)
```

**Environment Variables:**
```bash
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=your-refresh-token
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_RECIPIENT_EMAIL=recipient@example.com
```

#### Option 2: Service Account
```python
# If running on GCP or with service account JSON
import gspread  # Can use similar pattern
# Set GOOGLE_SERVICE_ACCOUNT_JSON env var
```

#### Option 3: Default Credentials
```python
import google.auth
creds, _ = google.auth.default()
# Works if running on GCP or with ADC configured
```

### Setup Steps Required

1. **Enable Gmail API** in Google Cloud Console
2. **Create OAuth 2.0 credentials** (Desktop app or Web app)
3. **Get refresh token** (one-time setup):
   - Option A: Use OAuth Playground
   - Option B: Run OAuth flow locally and save tokens

### Email Format - Simple Table

**HTML Table Structure:**
```html
<h2>Disaster Surveillance Report - 2026-04-09</h2>
<table border="1" cellpadding="5">
  <tr>
    <th>ID</th>
    <th>Name</th>
    <th>Country</th>
    <th>Type</th>
    <th>Level</th>
    <th>Priority</th>
    <th>Status</th>
  </tr>
  <tr>
    <td>20260409-ID-EQ</td>
    <td>M6.2 Earthquake in Java</td>
    <td>Indonesia</td>
    <td>Earthquake</td>
    <td>2</td>
    <td>HIGH</td>
    <td>Active</td>
  </tr>
  ...
</table>
```

**Email Subject:** `Disaster Surveillance Report - {YYYY-MM-DD}`

**Configuration:**
```bash
# Recipient (can be multiple comma-separated)
GMAIL_RECIPIENT_EMAIL=team@example.com,manager@example.com

# Optional: BCC for archive
GMAIL_BCC_EMAIL=archive@example.com
```

### Implementation Architecture

```python
class GmailReporter:
    """Send incident reports via Gmail API."""

    def __init__(
        self,
        sender_email: str | None = None,
        recipient_email: str | None = None,
    ):
        self._sender = sender_email or os.environ.get("GMAIL_SENDER_EMAIL")
        self._recipient = recipient_email or os.environ.get("GMAIL_RECIPIENT_EMAIL")
        self._service = None

    def _get_service(self):
        """Initialize Gmail API service with OAuth2."""
        # Same pattern as Google Sheets backend
        ...

    def send_report(self, incidents: list[Incident], subject: str | None = None) -> dict:
        """Send incident report as HTML table."""
        # Build HTML table from incidents
        # Send via Gmail API
        ...

    def _build_html_table(self, incidents: list[Incident]) -> str:
        """Build HTML table from incidents."""
        ...
```

### Storage Backend Integration

The `GmailReporter` can be used as:
1. **Standalone**: Call after pipeline completes
2. **Integrated**: As a `StorageBackend` that sends instead of stores

```python
class EmailBackend(StorageBackend):
    """Send incidents via email instead of storing."""

    def write(self, incidents: list[Incident]) -> None:
        reporter = GmailReporter()
        reporter.send_report(incidents)

    def read(self) -> list[Incident]:
        return []  # Email doesn't store
```

### Acceptance Criteria

- [ ] GmailReporter class sends HTML table emails
- [ ] Authentication uses OAuth2 (refresh token pattern)
- [ ] Environment variables: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, GMAIL_SENDER_EMAIL, GMAIL_RECIPIENT_EMAIL
- [ ] Simple HTML table format with key incident fields
- [ ] Can be used as StorageBackend or standalone
- [ ] Tests mock Gmail API calls

---

## Questions for Architect

1. **DSPy Usage**: Should I use DSPy for transformation, or is direct OpenCode CLI sufficient?
2. **Storage Backends**: Which backends should be implementable now vs. later? (JSONL first, others later)
3. **CLI Library**: Fire (parent uses) or Click (more modern)?
4. **Error Handling**: How to handle partial failures in pipeline?
5. **Schema Versioning**: How to handle parent schema changes?
6. **Gmail Reporter**: Should it be a standalone reporter or integrated as EmailBackend?