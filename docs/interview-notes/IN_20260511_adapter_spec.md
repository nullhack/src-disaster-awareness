# IN_20260511_adapter_spec — Adapter Specification Interview

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** Stakeholder (domain expert)
> **Session type:** Feature specification

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | What sources do we need adapters for? | 5 sources: GDACS (disaster alerts, currently uses USGS fallback), ProMED (disease outbreaks, mock only), ReliefWeb (humanitarian reports, stub), HealthMap (disease surveillance, stub), WHO (health emergencies, stub). |
| Q2 | What's the minimum each adapter must produce? | A `RawIncidentData` with 7 fields: source_name, incident_name, country, disaster_type, report_date, source_url, raw_fields. Flat structure, no nesting. |
| Q3 | Should adapters handle errors? | Yes. `fetch()` must never raise to the pipeline. Return empty list on any failure. Log internally. |
| Q4 | What about mock mode? | Every adapter should accept `mock_mode: bool = False`. When true, return representative sample data without HTTP calls. Critical for testing. |
| Q5 | How should adapters filter for freshness? | Each source has a freshness window: GDACS 24h, ProMED 48h, ReliefWeb 24h, HealthMap 48h, WHO 72h. Adapters should not return incidents older than their window. |

---

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q6 | Why is GDACS using USGS instead of GDACS API? | GDACS doesn't have a clean public JSON API. USGS GeoJSON feed is reliable for earthquake data. Should add actual GDACS RSS/GeoJSON for floods, cyclones, volcanoes in future. |
| Q7 | What's the ProMED challenge? | No public API. Would need RSS feed parsing or web scraping. Currently mock-only with 5 hardcoded disease alerts. |
| Q8 | What data does ReliefWeb provide? | Humanitarian crisis reports via REST API at api.reliefweb.int. Requires `appname` parameter. Can filter by date, country, disaster type. |
| Q9 | How should country extraction work? | Three fallback steps: (1) parse from structured source data, (2) parse from location/place text, (3) map coordinates to country. Final fallback: "Unknown". |
| Q10 | Should adapters dedup within a single fetch? | Yes. A single `fetch()` call must not return duplicate incidents. Use source_url or source-specific IDs for dedup within a batch. |

---

## Feature: adapter-protocol

| ID | Question | Answer |
|----|----------|--------|
| Q11 | Should SourceAdapter be a Protocol or base class? | Protocol is better for duck typing and allows different inheritance hierarchies. Current code uses a concrete class — should migrate to Protocol. |
| Q12 | What constructor parameters are universal? | `timeout: float = 10.0` and `mock_mode: bool = False`. Source-specific params (min_magnitude, feed_type) are additional. |
| Q13 | How are adapters registered? | Explicitly imported in `adapters/__init__.py`. New adapters must be importable there and have a unique source_name. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reliability | When a source API is down, the adapter returns empty list | No unhandled exceptions | Must |
| QA2 | Testability | When mock_mode=True, adapter returns valid test data | All required fields populated | Must |
| QA3 | Performance | When fetching from all 5 sources, total time is bounded | < 30 seconds with 10s timeout per source | Should |

---

## Pain Points Identified

- SourceAdapter is a concrete class, not a Protocol — limits flexibility
- Only GDACS has real HTTP calls; 4 adapters are stubs/mocks
- No structured error reporting (just empty list on failure)
- No rate limiting or retry logic in adapters

## Business Goals Identified

- Define a clear adapter contract that new sources can implement easily
- Make adapters testable without external dependencies
- Ensure graceful degradation when sources are unavailable

## Terms to Define

- `SourceAdapter` — Protocol defining the adapter interface
- `RawIncidentData` — flat record produced by adapters
- `mock_mode` — flag to return test data without HTTP calls
- `freshness window` — maximum age of incidents returned by an adapter

## Action Items

- [x] Create `docs/spec/adapter_specification.md`
- [ ] Convert SourceAdapter from concrete class to Protocol
- [ ] Implement ReliefWeb adapter using REST API
- [ ] Add structured error reporting (log + return empty)
