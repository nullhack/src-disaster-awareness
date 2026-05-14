# ADR_20260514_raw_record_uncertainty_principle

## Status

Accepted

## Context

DSR fetches data from four sources (GDACS, WHO DON, GDELT, DDG News), each with different API response structures, field names, and field availability. GDACS provides ~90% deterministic fields (alertlevel, eventtype, iso3, coordinates). WHO provides ~30% deterministic fields — country and disaster type are buried in unstructured HTML. GDELT ArtList mode has no tone field (tone requires a separate API call) and `sourcecountry` is the news source location, not the incident location. DDG News provides basic article metadata.

Field availability cannot be guaranteed until real API responses are inspected. APIs may add, rename, or deprecate fields without notice. Normalizing or filtering fields at fetch time would lose data that may be valuable for future extraction rules or AI enrichment. The behavioral spec formalizes this as the "uncertainty principle."

The forces at play are: (1) API responses are external and uncontrolled — fields may change without warning, (2) future AI enrichment or classification rules may need fields that seem irrelevant today, (3) normalization at fetch time couples the adapter to specific field assumptions, (4) the pipeline must handle missing fields gracefully everywhere downstream.

## Interview

| Question | Answer |
|---|---|
| Should adapters normalize field names across sources? | No — normalization would lose the original field structure and couple adapters to assumptions about what fields are "important" |
| Should adapters filter out fields they don't recognize? | No — unrecognized fields may be valuable for future extraction or may indicate API changes that need attention |
| How should downstream code access raw fields? | Direct dict access with `.get()` and explicit None handling; no field mapping layer |

## Decision

Every `RawRecord.raw_fields` contains the complete, untouched API response as a Python dict. Adapters never normalize, filter, rename, or transform fields. Downstream code accesses fields directly with defensive handling (`dict.get()`, None checks). The adapter's only responsibility is parsing the HTTP response into `RawRecord` objects with the correct `source_name` and `fetched_at`.

## Reason

Preserving raw fields verbatim decouples adapters from downstream field assumptions, ensures no data is lost at the fetch boundary, and allows future extraction rules and AI enrichment to access any field without adapter changes. This directly supports Maintainability (QA #7: adding a new source adapter requires zero changes to core pipeline).

## Alternatives Considered

- **Normalized field mapping**: Adapters map source-specific fields to a canonical schema (e.g., `event_type`, `severity`, `country_code`). Rejected because: (1) WHO and GDELT don't have structured fields for many canonical attributes, (2) the mapping would be lossy (GDACS has many fields with no canonical equivalent), (3) adding a new source requires defining the full mapping upfront, (4) field changes in the source API require adapter code changes rather than just extraction rule updates.
- **Field whitelist**: Adapters extract only known useful fields, discarding the rest. Rejected because: (1) discarded fields are permanently lost and cannot be recovered, (2) "known useful" is a premature judgment — future needs are unpredictable, (3) API field additions would be silently ignored.
- **Schema validation (Pydantic models per source)**: Each source defines a Pydantic model for its response structure. Rejected because: (1) source schemas change without notice, causing validation failures, (2) strict validation would reject responses with new/renamed fields, (3) the added complexity of maintaining 4 Pydantic models provides no value over simple dict access.
- **Two-layer storage (raw + normalized)**: Store both raw and normalized copies. Rejected as unnecessary complexity — the raw dict IS the storage, and normalization happens at extraction/classification time, not at fetch time.

## Consequences

- (+) Adapters are simple: HTTP call → parse → wrap in RawRecord. No field knowledge needed.
- (+) New source adapters require zero changes to downstream code (QA #7)
- (+) Future extraction rules can access any field without adapter changes
- (+) API field changes are detectable by inspecting raw_fields without adapter breakage
- (+) Complete audit trail: the exact API response is always available
- (+) AI enrichment sees the full response context, improving extraction quality
- (-) Downstream code must handle source-specific field names and missing fields defensively
- (-) `raw_fields` dicts may be large (GDACS responses include geometry, severity data, etc.)
- (-) No compile-time safety on field access — typos in field names fail at runtime, not at import time
- (-) Storage includes full raw responses, increasing disk usage (mitigated by JSONL compression potential)

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Accepted? |
|------|------------|--------|------------|-----------|
| Downstream code has typos in raw_fields key names, causing silent None returns | Medium | Medium | Adapter-specific field access tested via fixtures; integration tests verify field extraction for each source | Yes |
| Raw_fields dicts consume excessive memory for large batches | Low | Low | Typical: ~200 records × ~2 KB each ≈ ~400 KB. Monitor and add chunking if needed | Yes |
| Source API adds breaking field changes (renamed/deleted fields) | Medium | Medium | Fixture-based testing catches changes; adapters tested against real fixtures; failures are visible, not silent | Yes |
| JSONL storage grows large due to full raw_fields preservation | Low | Low | ~50 incidents/day × ~5 KB each ≈ ~250 KB/day. Acceptable. Compress old files if needed | Yes |
