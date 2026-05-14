# Adapter Specification: Disaster Surveillance Reporter

> **Status:** BASELINED (2026-05-11)
> Defines how source adapters must be structured, what they produce, and how they integrate with the pipeline.

---

## Overview

Adapters are the entry point of the pipeline. Each adapter wraps a single external data source and produces a list of `RawIncidentData` records. The pipeline then transforms, classifies, and stores these records.

### Current Sources

| Source | Type | Status | API Available |
|--------|------|--------|---------------|
| GDACS | Disaster alerts | Functional (via USGS fallback) | Partial (USGS GeoJSON) |
| ProMED | Disease outbreaks | Mock only | No public API |
| ReliefWeb | Humanitarian reports | Stub | REST API available |
| HealthMap | Disease surveillance | Stub | API with key required |
| WHO | Health emergencies | Stub | REST API available |

---

## Adapter Protocol

### Interface Contract

Every adapter MUST implement:

```python
class SourceAdapter(Protocol):
    @property
    def source_name(self) -> str: ...

    def fetch(self) -> list[RawIncidentData]: ...
```

### Source Name Convention

Each adapter returns a stable identifier used for dedup, classification, and storage:

| Adapter | `source_name` |
|---------|---------------|
| GDACSAdapter | `"GDACS"` |
| ProMEDAdapter | `"ProMED"` |
| ReliefWebAdapter | `"ReliefWeb"` |
| HealthMapAdapter | `"HealthMap"` |
| WHOAdapter | `"WHO"` |

### Constructor Contract

All adapters MUST accept these optional parameters:

```python
def __init__(
    self,
    *,
    timeout: float = 10.0,
    mock_mode: bool = False,
) -> None: ...
```

- `timeout`: HTTP request timeout in seconds
- `mock_mode`: When `True`, return representative mock data instead of making HTTP calls

Adapters MAY have additional source-specific parameters (e.g., `min_magnitude` for GDACS, `feed_type` for ReliefWeb).

---

## RawIncidentData Specification

The adapter output record. Flat structure — no nested objects except `raw_fields`.

```python
@dataclass(frozen=True, slots=True)
class RawIncidentData:
    source_name: str           # e.g., "GDACS"
    incident_name: str         # e.g., "M6.1 Earthquake Sumatra, Indonesia"
    country: str               # e.g., "Indonesia" — must match known country
    disaster_type: str         # e.g., "Earthquake" — must match incident type enum
    report_date: str           # ISO 8601 datetime
    source_url: str            # Direct link to source report
    raw_fields: dict[str, Any] # Source-specific extra data
```

### Field Rules

| Field | Rule |
|-------|------|
| `source_name` | Must match the adapter's `source_name` property exactly |
| `incident_name` | Max 500 chars. Should be human-readable. Include magnitude/type/location. |
| `country` | Full country name (not ISO code). If unknown, use `"Unknown"`. |
| `disaster_type` | Must be one of the defined incident type enums. If ambiguous, use `"Other"`. |
| `report_date` | ISO 8601 UTC. When the *source* reported this, not when the adapter fetched it. |
| `source_url` | Must be a valid URL. If unavailable, use the source's homepage. |
| `raw_fields` | Catch-all for source-specific data. Can be empty `{}`. |

---

## Adapter Behavior Rules

### A1: Graceful Failure

`fetch()` MUST return an empty list on any error — never raise exceptions to the pipeline caller. Log the error internally.

```python
def fetch(self) -> list[RawIncidentData]:
    try:
        return self._real_fetch()
    except Exception:
        return []
```

### A2: Idempotency

Calling `fetch()` multiple times within the same minute SHOULD return the same results (same incidents, same data). External data may change between minutes.

### A3: Freshness Filtering

Adapters SHOULD filter to recent incidents only. What "recent" means depends on the source:

| Source | Freshness Window |
|--------|-----------------|
| GDACS/USGS | Last 24 hours |
| ProMED | Last 48 hours |
| ReliefWeb | Last 24 hours |
| HealthMap | Last 48 hours |
| WHO | Last 72 hours |

### A4: Country Extraction

Adapters MUST attempt to extract the country name from source data. If extraction fails:
1. Try parsing from location/place text
2. Try mapping coordinates to country
3. Fall back to `"Unknown"`

### A5: Dedup Within Fetch

A single `fetch()` call MUST NOT return duplicate incidents. Use `source_url` or source-specific IDs for dedup within a single fetch batch.

---

## Source-Specific Specifications

### GDACS Adapter

**Current implementation**: Uses USGS GeoJSON earthquake feed as fallback.

**Required parameters**:
- `min_magnitude: float = 2.0` — minimum earthquake magnitude to include
- `max_age_hours: int = 24` — maximum age of incidents

**Country extraction**: Parse from USGS `place` field (format: "location, Country")

**Raw fields captured**: USGS properties (mag, place, time, url, tsunami, felt, etc.)

**Future**: Should also fetch from actual GDACS RSS/JSON API for non-earthquake disasters (floods, cyclones, volcanoes).

### ProMED Adapter

**Current implementation**: Mock only, returns 5 hardcoded disease alerts.

**Required for real implementation**:
- RSS feed parsing from `promedmail.org`
- Or web scraping of ProMED-posted alerts
- Extract: disease name, country, case counts, investigation status

**Country extraction**: Parse from ProMED title format (e.g., "MEASLES - PERU (TUMBES): OUTBREAK")

### ReliefWeb Adapter

**Current implementation**: Stub.

**API**: `https://api.reliefweb.int/v1/reports`

**Required parameters**:
- `appname: str` — Required by ReliefWeb API
- `query_filter: dict` — Default filter for disaster reports

**Required for real implementation**:
- Query disaster type reports
- Filter by date (last 24h)
- Extract: title, country, disaster type, URL, date

### HealthMap Adapter

**Current implementation**: Stub.

**API**: Requires API key.

**Required for real implementation**:
- Disease surveillance data
- Filter by region and date
- Extract: disease name, country, case counts, alert level

### WHO Adapter

**Current implementation**: Stub.

**API**: `https://ghoapi.azureedge.net/api/` (GHO API) or WHO Disease Outbreak News

**Required for real implementation**:
- Disease outbreak news RSS/JSON
- Filter by date and region
- Extract: disease, country, severity, URL

---

## Adapter Registration

Adapters are registered in `adapters/__init__.py` and imported explicitly:

```python
from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter
from disaster_surveillance_reporter.adapters.promed import ProMEDAdapter
from disaster_surveillance_reporter.adapters.reliefweb import ReliefWebAdapter
from disaster_surveillance_reporter.adapters.healthmap import HealthMapAdapter
from disaster_surveillance_reporter.adapters.who import WHOAdapter
```

New adapters MUST:
1. Inherit from or implement `SourceAdapter`
2. Be importable from `adapters/__init__.py`
3. Have a unique `source_name`
4. Follow the constructor contract

---

## Testing Requirements

Each adapter MUST have:

1. **Unit tests with mock HTTP** — verify parsing logic with canned responses
2. **Mock mode tests** — verify `mock_mode=True` returns valid `RawIncidentData` records
3. **Edge case tests** — empty responses, malformed data, timeout, auth failures
4. **Schema validation tests** — every returned record has all required fields with correct types

---

## Changes

| Date | Source | Change | Reason |
|------|--------|--------|--------|
| 2026-05-11 | Specification recovery | Created from existing code and deleted skills | Define adapter contract clearly |
