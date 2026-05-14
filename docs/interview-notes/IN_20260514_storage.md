# IN_20260514_storage — JSONL, SQLite, Dedup, and File Structure

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
| Q3 | Why does it exist — what problem does it solve? | Provides queryable local incident storage for researchers and ops reporting. |
| Q4 | When and where is it used? | Final step of the pipeline. Researchers query stored data for analysis. |
| Q5 | Success — what does "done" look like? | Both JSONL and SQLite backends store complete bundles, support queries, and deduplicate correctly. |
| Q6 | Failure — what must never happen? | Data loss — if storage fails, the pipeline must handle it gracefully. Dedup must prevent duplicate entries. |
| Q7 | Out-of-scope — what are we explicitly not building? | Remote storage, cloud databases, multi-process concurrent writes. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | What storage pattern is used? | Adapter pattern with two backends implementing the same StorageBackend protocol: JSONL (default) and SQLite (alternative). Both have the same query interface. Both store the complete IncidentBundle including all raw records. |
| Q9 | How does dedup work? | By incident_id across both backends. The store method skips existing IDs. The exists method checks if an incident_id already exists. |

## Feature: JSONL Backend

| ID | Question | Answer |
|----|----------|--------|
| Q10 | How does the JSONL backend work? | Append-only, date-partitioned files. File structure: `incidents/by-date/YYYY-MM-DD/incidents.jsonl`. Default backend. |
| Q11 | What are the advantages of JSONL? | Simple, human-readable, append-only (no corruption risk), date-partitioned for easy browsing, no database dependency. |

## Feature: SQLite Backend

| ID | Question | Answer |
|----|----------|--------|
| Q12 | How does the SQLite backend work? | Alternative backend with the same StorageBackend protocol and query interface. Provides more efficient querying for researchers. Lives in storage/sqlite.py. |

## Feature: StorageBackend Protocol

| ID | Question | Answer |
|----|----------|--------|
| Q13 | What is the store method? | `store(self, bundles: list[IncidentBundle]) -> int`. Stores bundles, returns count of new bundles stored (skips existing IDs). Stores the complete bundle including all raw records. |
| Q14 | What is the query method? | `query(self, *, date_from: date, date_to: date, **filters: Any) -> list[Incident]`. Queries stored incidents by date range and optional filters. Available filters: country_group, disaster_type, priority, should_report, source_name. Returns Incident (flattened view), not raw bundles. |
| Q15 | What is the exists method? | `exists(self, incident_id: str) -> bool`. Checks if an incident already exists — used for dedup. |

## Feature: File Structure

| ID | Question | Answer |
|----|----------|--------|
| Q16 | What is the overall file structure? | Main package: `disaster_surveillance_reporter/` with __init__.py, types.py, classify.py, correlate.py, pipeline.py. Sub-packages: ai/ (provider.py, extractor.py, classifier.py), adapters/ (gdacs.py, who.py, gdelt.py, news.py), storage/ (jsonl.py, sqlite.py). Scripts: capture_fixtures.py. Tests directory with fixtures/ subdirectory containing gdacs_response.json, who_response.json, gdelt_response.json plus individual test files per module. |
| Q17 | What does the storage directory contain? | storage/__init__.py, storage/jsonl.py (JSONL storage backend), storage/sqlite.py (SQLite storage backend). |
| Q18 | What test files cover storage? | test_jsonl_store.py and test_sqlite_store.py. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Performance | 50 incidents classified and stored in < 5 seconds (excluding AI) | < 5 seconds | Must |
| QA2 | Reliability | Dedup prevents duplicate entries across runs | No duplicates | Must |
| QA3 | Testability | Both backends tested against same test suite | Protocol compliance | Must |

---

## Pain Points Identified

- Two storage backends must stay in sync on the protocol contract
- JSONL query performance will degrade with large datasets
- SQLite requires schema management and migration strategy
- Date-partitioned JSONL means cross-date queries require reading multiple files

## Business Goals Identified

- Local-only storage — no cloud dependencies, no network required for queries
- Adapter pattern allows swapping backends without changing pipeline code
- Complete bundle storage preserves all raw data for future reprocessing
- Date-partitioned JSONL enables easy archival and browsing

## Terms to Define (for glossary)

- StorageBackend (protocol)
- JSONL backend
- SQLite backend
- Adapter pattern
- Date-partitioned storage
- Dedup (by incident_id)
- Append-only storage
- IncidentBundle storage
- Incident (query result)

## Action Items

- [ ] Define SQLite schema for IncidentBundle storage
- [ ] Validate JSONL date-partitioned file structure on disk
- [ ] Test dedup across multiple pipeline runs with same incidents
- [ ] Benchmark query performance for both backends with 100+ incidents
- [ ] Ensure both backends pass the same protocol compliance tests
