# IN_20260511_storage_spec — Storage Specification Interview

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** Stakeholder (domain expert)
> **Session type:** Scope refinement

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | What's wrong with the old storage approach? | The old v2.0 system used reference-tracking JSONL files (by-country-group.jsonl, by-incident-type.jsonl, etc.) with line-number pointers. These drifted when records were appended, needed daily/weekly rebuild scripts, and was massively over-engineered for <100 incidents/day. |
| Q2 | What's the new approach? | Simple: one JSONL file per date in `by-date/`. No reference files, no index files. Queries scan files directly. At our scale (<100/day), this is instant. |
| Q3 | How do the three backends differ? | JSONLStore is the canonical data store (append-only, queryable). EmailReporter is a distribution endpoint (fire-and-forget, not readable). GoogleSheetsStore is for team visibility (shared spreadsheet). They are NOT interchangeable. |
| Q4 | How are updates handled? | Append-only. If an incident changes, a new record with the same `incident_id` is appended to today's file with an incremented `updated_date`. The most recent record wins. |
| Q5 | How does dedup work? | Before appending, check today's file for the same `incident_id`. Skip if exists. Use content similarity (rapidfuzz) for near-duplicate detection across sources. |
| Q6 | What's the retention policy? | 0-30 days: active. 30-365 days: keep as-is. 1+ years: optional compress to .jsonl.gz. No automated archival needed at current scale. |

---

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q7 | Why separate StorageBackend and ReportBackend protocols? | Because email doesn't have a meaningful `read()` — it's a delivery endpoint, not storage. The current code forces EmailReporter to implement `read()` returning `[]`, which is a code smell. Better to have distinct protocols for distinct purposes. |
| Q8 | What about the media/ directory? | Separate `media/` directory for standalone MediaCoverage records, same structure: one file per date. |
| Q9 | How does Google Sheets fit? | One tab per date (YYYY-MM-DD). Append classified incidents for visibility. Column headers map to key ClassifiedIncident fields. Used by the team for manual review and filtering. |
| Q10 | What's the PipelineConfig change? | Instead of a single `storage: StorageBackend`, the pipeline should have: `store: JSONLStore` (canonical), `reporters: list[ReportBackend]` (email), `viewers: list[StorageBackend]` (sheets). |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reliability | When pipeline crashes mid-write, existing data is intact | Append-only ensures no corruption | Must |
| QA2 | Simplicity | When a new developer reads the storage code, they understand it immediately | No reference files, no indexes | Must |
| QA3 | Performance | When querying 30 days of data (3000 records), results return | < 2 seconds | Should |

---

## Pain Points Identified

- Reference tracking was brittle (line numbers drift)
- Three backends forced into one Protocol
- No query capability in JSONLBackend (just write/read all)
- Google Sheets column headers not aligned with schema

## Business Goals Identified

- Storage that "just works" without maintenance scripts
- Clear separation between data store and distribution
- Query support for the canonical JSONL store

## Terms to Define

- `JSONLStore` — canonical append-only data store, one file per date
- `ReportBackend` — protocol for distribution endpoints (email)
- `StorageBackend` — protocol for readable storage (JSONL, Sheets)

## Action Items

- [x] Create `docs/spec/storage_specification.md`
- [ ] Refactor JSONLBackend into JSONLStore with query() method
- [ ] Create ReportBackend protocol and refactor EmailReporter
- [ ] Implement dedup check before append
