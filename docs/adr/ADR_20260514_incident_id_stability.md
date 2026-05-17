# ADR_20260514_incident_id_stability

## Status

Accepted

## Context

DSR generates `incident_id` during the Correlation step using the format `YYYYMMDD-CC-TTT` (date, country code, disaster type code). Country and disaster type may initially be unknown (especially for WHO and GDELT records) and filled in later by AI enrichment. The incident_id serves as the deduplication key for storage — `StorageBackend.exists(incident_id)` checks whether an incident is already stored. If the ID were regenerated after AI fills in missing fields, a previously stored bundle would appear as a new incident on the next pipeline run, creating duplicates.

The forces at play are: (1) deduplication requires a stable key across pipeline runs, (2) AI enrichment is optional and may fail (QA #3), meaning some bundles will never have AI-filled fields, (3) the ID format includes country and type codes that may start as "UNX"/"OTH" (unknown), (4) the same real-world incident must always map to the same ID regardless of which pipeline run detects it.

## Interview

| Question | Answer |
|---|---|
| Should incident_id change when AI fills in the country or type? | No — that would break dedup and create phantom duplicates across runs |
| What about the date component — could it change? | The date is the earliest date from any record at correlation time. It is stable because the historical dates of records don't change. |
| Should we use a UUID instead of a deterministic ID? | No — deterministic IDs enable cross-run deduplication and are human-readable |

## Decision

The `incident_id` is generated once during the Correlation step and never regenerated, even when AI enrichment fills in previously unknown country or disaster type fields. Unknown values use sentinel codes: "UNX" for unknown country, "OTH" for unknown disaster type.

## Reason

A stable incident_id is essential for cross-run deduplication — the fundamental invariant that the same real-world incident is stored exactly once. Regenerating the ID after enrichment would break this invariant, creating duplicate storage entries and confusing researchers querying the data.

## Alternatives Considered

- **Regenerate ID after enrichment**: Update the country and type codes once AI fills them in. Rejected because: (1) the previously stored bundle (with UNX/OTH) would not match the new ID, creating duplicates, (2) AI failure means some IDs would regenerate and some wouldn't, creating inconsistent behavior, (3) external systems referencing the original ID would break.
- **UUID-based IDs**: Generate a random UUID for each bundle. Rejected because: (1) UUIDs are not deterministic — the same incident processed in two pipeline runs would get different UUIDs, breaking dedup, (2) UUIDs are not human-readable, making debugging and data inspection harder.
- **Hash-based IDs**: Compute a hash of record fields (titles + dates + sources). Rejected because: (1) minor variations in source data (whitespace, encoding) would produce different hashes, creating false negatives in dedup, (2) hash collisions, while unlikely, would silently merge different incidents.
- **Two-ID system (stable + descriptive)**: Keep a stable correlation ID and add a descriptive label that updates with enrichment. Rejected as unnecessary complexity — the YYYYMMDD-CC-TTT format with UNX/OTH sentinels is already descriptive enough, and a second ID adds confusion about which to use for dedup.

## Consequences

- (+) Cross-run deduplication works reliably: same incident always has the same ID
- (+) `incident_id` is human-readable and self-descriptive (date, country hint, type hint)
- (+) AI failure does not affect ID stability — bundles with UNX/OTH are dedupable
- (+) Storage `exists()` check is a simple string comparison
- (-) IDs may contain "UNX" or "OTH" even after AI fills in the real values, which can look odd in query results
- (-) Two bundles about the same incident but with different initial date extraction could get different IDs (mitigated by ±1 day date proximity in correlation)
- (-) Researchers must understand that UNX/OTH in an ID does not mean the country/type is still unknown — it means it was unknown at correlation time

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Accepted? |
|------|------------|--------|------------|-----------|
| "UNX"/"OTH" in incident IDs confuses researchers querying stored data | Medium | Low | Document in CLI help and README that ID reflects correlation-time knowledge, not current knowledge | Yes |
| Date component differs across runs for the same incident due to source date updates | Low | Medium | Correlation uses earliest date from records; GDACS/WHO dates are stable once published; GDELT dates may vary but ±1 day tolerance handles this | Yes |
| Country code changes (e.g., political boundary changes) make existing IDs inconsistent | Low | Low | ISO 3166-1 alpha-2 codes are stable; country code lookup table can be updated without affecting existing IDs | Yes |
