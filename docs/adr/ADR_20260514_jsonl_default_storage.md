# ADR_20260514_jsonl_default_storage

## Status

Accepted

## Context

DSR needs to persist complete `IncidentBundle`s (all raw records + classification + AI enrichment) locally. The quality attributes rank Reproducibility (#1) as the top priority, followed by Testability (#4). The tool runs as a CLI storing results under `./incidents/`. Users include researchers who need to query and inspect data. Two storage backends are required: a default that works out of the box, and an alternative for efficient querying at scale.

The forces at play are: (1) Reproducibility demands that stored output is inspectable and byte-identical for identical input, (2) researchers need to visually inspect and grep data without special tools, (3) the tool must work with zero configuration, (4) atomic writes prevent data corruption from interrupted runs, (5) deduplication by `incident_id` prevents duplicate entries across cron runs.

## Interview

| Question | Answer |
|---|---|
| Should researchers need a query tool to inspect data, or should data be human-readable? | Data should be human-readable — researchers often grep/inspect files directly |
| Is the storage path configurable? | Yes — `DSR_STORAGE_PATH` env var, defaulting to `./incidents` |
| Can we rely on SQLite being available everywhere? | SQLite is in Python stdlib, but JSONL is more universally inspectable (any text editor, grep, jq) |

## Decision

Use JSONL (JSON Lines) as the default storage format, with date-partitioned append-only files at `incidents/by-date/YYYY-MM-DD/incidents.jsonl`. SQLite remains available as an alternative backend via `DSR_STORAGE_BACKEND=sqlite`, sharing the same `StorageBackend` protocol.

## Reason

JSONL is human-readable, grep-able, append-friendly, and requires zero configuration or tooling to inspect, directly supporting Reproducibility (QA #1) and Testability (QA #4). The date-partitioned structure maps naturally to the incident date hierarchy researchers expect.

## Alternatives Considered

- **SQLite as default**: More efficient for complex queries and large datasets, but binary format obscures data inspection. Researchers cannot grep or cat the data. Rejected as default but retained as alternative for scale.
- **CSV**: Loses nested structure (`raw_fields` dict, `records` list, `overrides` list). Would require flattening complex fields, losing the complete bundle storage guarantee.
- **Single JSON file (array)**: Not append-friendly — appending requires reading the entire file, parsing the array, appending, and rewriting. Risks data corruption on interrupted writes. No natural partitioning.
- **Parquet/Arrow**: Efficient columnar storage but requires external dependencies (pyarrow) and special tooling to inspect. Overkill for ~50 incidents per run.

## Consequences

- (+) Researchers can inspect data with standard Unix tools (cat, grep, jq, head)
- (+) Append-only writes are naturally atomic (write line + flush)
- (+) Date partitioning maps to researcher workflow (looking at today's incidents)
- (+) Zero-configuration default — no database setup, no schema migration
- (+) Reproducibility: identical input produces byte-identical JSONL output (with sorted keys)
- (+) Dedup by incident_id is straightforward: read existing IDs, skip duplicates
- (-) Full-text search across dates requires reading multiple files (mitigated by date range filtering)
- (-) Complex queries (e.g., "all Level 4 incidents in Group A countries in the last 30 days") require reading all files in the date range
- (-) Large datasets (>10K incidents) benefit from SQLite's indexed queries

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Accepted? |
|------|------------|--------|------------|-----------|
| Query performance degrades with large date ranges (>365 files) | Medium | Low | Provide SQLite alternative for high-query-volume use cases; date range narrowing | Yes |
| File corruption from interrupted write (disk full, kill -9) | Low | Medium | Atomic write via temp file + rename; corrupted temp file is discarded, original intact | Yes |
| JSONL files grow unbounded within a single date partition | Low | Low | Typical: ~50 incidents/day ≈ ~200 KB/day. Monitor and alert if daily file exceeds 10 MB | Yes |
