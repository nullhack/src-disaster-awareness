# IN_20260514_data_shapes — RawRecord, IncidentBundle, and Incident Dataclasses

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** eol
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Who are the users? | Backend Developers, Ops Teams, Researchers. |
| Q2 | What does the product do at a high level? | Backend pipeline: fetch → correlate → classify → enrich → store. |
| Q3 | Why does it exist — what problem does it solve? | Automates disaster surveillance with deterministic classification. |
| Q4 | When and where is it used? | Scheduled CLI tool, backend batch processing. |
| Q5 | Success — what does "done" look like? | All data shapes correctly model the domain, all fields present and typed. |
| Q6 | Failure — what must never happen? | Raw data must never be lost or mutated during processing. |
| Q7 | Out-of-scope — what are we explicitly not building? | Dashboard, web UI, real-time system. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | What are the three core data shapes? | RawRecord (atomic data unit from any source), IncidentBundle (all information about one real-world incident), and Incident (final output for queries/reports). They live in types.py. |

## Feature: RawRecord

| ID | Question | Answer |
|----|----------|--------|
| Q9 | What is RawRecord? | It's the atomic data unit from any source. A Python dataclass with three fields: source_name (str), fetched_at (datetime), and raw_fields (dict). |
| Q10 | What is source_name? | A string identifying the origin: "GDACS", "WHO", "GDELT", or "DDG-NEWS". |
| Q11 | What is raw_fields? | A dict containing the complete, untouched source-specific fields. No normalization at this layer. It contains the exact API response. We don't assume any field exists until we've seen real data. |
| Q12 | What are example raw_fields per source? | GDACS: {title, description, alertlevel, eventtype, iso3, latitude, longitude, ...}. WHO: {title, url, date, content_html, ...}. GDELT: {title, url, seendate, tone, themes, ...}. DDG-NEWS: {date, title, body, url, source}. All subject to change after seeing real responses. |

## Feature: IncidentBundle

| ID | Question | Answer |
|----|----------|--------|
| Q13 | What is IncidentBundle? | All information about one real-world incident. A Python dataclass containing the incident ID, one or more raw records from any source, derived classification fields, AI enrichment fields, and metadata. |
| Q14 | What are the identity fields? | incident_id (str, format YYYYMMDD-CC-TTT) and records (list[RawRecord] — one or more raw records from any source). |
| Q15 | What are the classification fields? | country (str or None), country_code (str or None, ISO 3166-1 alpha-2), country_group (str or None, one of "A", "B", "C"), disaster_type (str or None), incident_level (int or None, 1-4), priority (str or None, "HIGH"/"MED"/"LOW"), should_report (bool), and overrides (list[str], e.g. ["O1", "O3"]). |
| Q16 | What are the AI enrichment fields? | summary (str or None), rationale (str or None), estimated_affected (int or None), estimated_deaths (int or None), and ai_enriched (bool). |
| Q17 | What metadata fields does it have? | classified_at (datetime or None). |

## Feature: Incident

| ID | Question | Answer |
|----|----------|--------|
| Q18 | What is Incident? | The final output for queries and reports. A flattened view of the IncidentBundle. It's what the StorageBackend.query() method returns — not raw bundles. |
| Q19 | What fields does Incident have? | incident_id (str), source_names (list[str] — all sources that contributed), incident_name (str — best title from available records), country (str), country_code (str), country_group (str — "A"/"B"/"C"), disaster_type (str), incident_level (int — 1-4), priority (str — "HIGH"/"MED"/"LOW"), should_report (bool), overrides (list[str]), report_date (date), source_urls (list[str] — all source URLs), summary (str or None), rationale (str or None), estimated_affected (int or None), estimated_deaths (int or None), ai_enriched (bool), record_count (int — how many raw records contributed). |
| Q20 | How does Incident differ from IncidentBundle? | Incident is a flattened, query-ready view. It doesn't contain the raw records — instead it has derived fields like source_names (list of source names that contributed), incident_name (best title), source_urls (all URLs), and record_count (number of contributing records). IncidentBundle retains the full raw records for processing. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reproducibility | Same raw records always produce same IncidentBundle classification | Deterministic | Must |
| QA2 | Testability | All dataclass fields are directly accessible and type-annotated | Type safety | Must |

---

## Pain Points Identified

- Source field shapes are uncertain until real API calls are made (the uncertainty principle)
- Need to carry Optional types through the pipeline because country/type may not be available until AI extraction
- IncidentBundle has many None-able fields, increasing the cognitive load for downstream processing

## Business Goals Identified

- Preserve all raw data unmodified (raw_fields) for future reprocessing
- Separate the raw/processing view (IncidentBundle) from the query/report view (Incident)
- Type-annotated dataclasses for developer ergonomics and IDE support

## Terms to Define (for glossary)

- RawRecord
- IncidentBundle
- Incident
- incident_id format (YYYYMMDD-CC-TTT)
- ISO 3166-1 alpha-2
- country_group (A/B/C)
- incident_level (1-4)
- priority (HIGH/MED/LOW)
- should_report
- overrides (O1-O6)
- ai_enriched

## Action Items

- [ ] Validate IncidentBundle field names against classify.py implementation needs
- [ ] Confirm Incident is the right shape for StorageBackend.query() return type
- [ ] Consider whether estimated_affected and estimated_deaths should be Optional[int] or have default values
