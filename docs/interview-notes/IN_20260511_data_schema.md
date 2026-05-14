# IN_20260511_data_schema — Data Schema Specification Interview

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** Stakeholder (domain expert)
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | What data flows through the pipeline? | Raw incidents from 5 sources → classified/enriched incidents → stored as JSONL. Three schema stages: RawIncidentData (flat, from adapters), ClassifiedIncident (nested, after AI enhancement), MediaCoverage (standalone media records). |
| Q2 | Why JSONL format? | Streaming-friendly, append-only, easy to grep/jq, works with data tools. One JSON object per line. |
| Q3 | What's the incident ID format? | YYYYMMDD-CC-TTT where CC is ISO 3166-1 alpha-2 country code and TTT is 3-letter type code (EQ=Earthquake, FL=Flood, CY=Cyclone, DI=Disease, etc.) |
| Q4 | What validation rules matter most? | (1) Level-priority alignment: Level 4 always HIGH, Level 1 usually LOW. (2) Date consistency: created ≤ updated ≤ now. (3) Impact consistency: deaths ≤ affected_population. (4) At least one source required. |
| Q5 | What about the old schema? | The deleted data-schema skill had a 504-line comprehensive schema with 13+ nested objects. This spec recovers and refines that. |
| Q6 | Are all blocks required in ClassifiedIncident? | Top-level required: incident_id, incident_name, created_date, updated_date, status, classification, sources. All other blocks (location, impact, disaster_details, disease_details, etc.) are optional depending on the incident type. |
| Q7 | How do disease incidents differ from disaster incidents? | Disease incidents use the `disease_details` block (disease_name, confirmed/suspected cases, investigation_status, spread_pattern, potential_pandemic). Disaster incidents use `disaster_details` (magnitude, depth, forecast info). They're mutually conditional. |

---

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | What source reliability tiers exist? | Tier1 (highest — GDACS, ProMED, Reuters, AP, BBC), Tier2 (regional news like Channel NewsAsia, Straits Times), Tier3 (ReliefWeb, Devex). Single Tier3 source → flag `high-uncertainty`. |
| Q9 | What are the status values? | Active, Forecasted, Updating, Resolved, Monitoring. |
| Q10 | What goes in raw_fields? | Source-specific data that doesn't map to the standard schema. GDACS sends USGS properties, ProMED sends disease-specific fields. Catch-all. |
| Q11 | How are media coverage records different from the media_coverage block in incidents? | MediaCoverage is a standalone record for independent media monitoring (not tied to a specific classified incident). The media_coverage block is embedded within a ClassifiedIncident record. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Data Integrity | When a record is stored, all validation rules pass | 100% | Must |
| QA2 | Backwards Compatibility | When schema evolves, old records remain readable | All existing records parseable | Must |
| QA3 | Performance | When storing 100 incidents, write completes | < 1 second | Should |

---

## Pain Points Identified

- Old schema lived entirely in a deleted skill file, not in version-controlled docs
- No schema validation in the current Python code (adapters produce RawIncidentData but there's no ClassifiedIncident dataclass)
- The pipeline uses OpenCodeClient for transform/classify — no typed output schema

## Business Goals Identified

- Establish a canonical schema that adapters, classifiers, and storage all agree on
- Make the schema self-documenting and recoverable without relying on skill files

## Terms to Define

- `RawIncidentData` — minimal flat record from source adapters
- `ClassifiedIncident` — enriched, validated record after classification pipeline
- `MediaCoverage` — standalone media monitoring record
- `JSONL` — JSON Lines format (one JSON object per line)

## Action Items

- [x] Create `docs/spec/data_schema.md` with all three schema stages
- [ ] Implement `ClassifiedIncident` as a Python dataclass matching the spec
- [ ] Add schema validation to the pipeline transform step
