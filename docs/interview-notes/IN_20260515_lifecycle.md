# IN_20260515_lifecycle — Incident Lifecycle Redesign

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** eol
> **Session type:** Scope refinement

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | What problem are we solving? | `generate_incident_id()` uses `fetched_at` (pipeline run time) instead of source-provided dates. Same WHO article gets different ID every run → storage dedup broken → everything re-processed. |
| Q2 | What does success look like? | Same source article = same ID across runs. Already-seen records skipped. Stale events (>7 days since last update) not re-processed. |
| Q3 | What sources have date fields? | GDACS: `fromdate` (ISO 8601), WHO: `PublicationDate` (ISO 8601), GDELT: `seendate` ("YYYYMMDDTHHMMSSz"), DDG-NEWS: `date` (ISO 8601). Fallback: `fetched_at`. |
| Q4 | How long is the monitoring window? | 7 days from `last_updated`. Events with no updates in 7+ days are stale and skipped. |
| Q5 | What never happens? | Same source record never processed twice (source fingerprint dedup). Incident ID never regenerated after creation. |
| Q6 | Out of scope? | No real-time push alerts, no multi-process pipeline, no cloud storage. |

---

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | How are source fingerprints generated? | Format: `{SOURCE_NAME}:{native_id}`. GDACS uses `eventid`, WHO uses `Id` or `DonId`, GDELT uses `url`, DDG-NEWS uses `url`. |
| Q9 | What new fields are needed on IncidentBundle? | `last_updated: datetime \| None` (most recent modification time) and `source_fingerprints: list[str]` (globally unique source record identifiers). |
| Q10 | When is `last_updated` set? | At bundle creation (correlation time). Reset when new data added (new DDG articles, new primary records). NOT reset when pipeline processes but finds no new data. |
| Q11 | When is a bundle stale? | `now - last_updated > 7 days`. Stale bundles are removed from pipeline before classification. |
| Q12 | What storage protocol additions are needed? | `get_last_updated(incident_id)`, `get_source_fingerprints(incident_id)`, `exists_by_source_fingerprint(fp)`, `upsert(bundle)`. |
| Q13 | How does DDG search gating change? | `should_report AND (active OR missing_fields)`. Stale, fully-known incidents skip DDG. Active incidents always get DDG for updates. |
| Q14 | How is this split? | Feature A: source-stable IDs + fingerprints + `last_updated` (touches types, correlation, record_correlator feature). Feature B: lifecycle gating + storage upsert + pipeline pre-filter (depends on A). |

---

## Feature: incident_lifecycle

| ID | Question | Answer |
|----|----------|--------|
| Q15 | How many pipeline steps? | 9 total: Fetch → Source Pre-filter → Correlate → Active-Status Check → Classify → DDG Search (gated) → AI Enrich → Override Re-eval → Store (upsert). |
| Q16 | What's the new step 2 (Source Pre-filter)? | For each fetched RawRecord, compute `source_fingerprint`. If `storage.exists_by_source_fingerprint(fp)` → discard. Otherwise → pass to correlator. |
| Q17 | What's the new step 4 (Active-Status Check)? | For each bundle: if NEW → proceed. If in storage and ACTIVE → proceed, merge existing fingerprints. If in storage and STALE → remove from pipeline. |
| Q18 | How does upsert work? | NEW bundles: insert. ACTIVE bundles: compare fingerprints. If new fingerprints found → update, reset `last_updated`. If no new fingerprints → no-op, don't reset monitoring window. |
| Q19 | What feature files change? | `domain_types` (add fingerprint rules), `record_correlator` (source-stable ID rule), `storage_backends` (upsert + staleness rules), `pipeline_orchestration` (9 steps + gating rules), new `incident_lifecycle.feature`. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reproducibility | Same source article produces same incident_id regardless of fetch time | 100% stable across runs | Must |
| QA2 | Performance | Pipeline with no new data completes all steps in under 5s | < 5s (stale-skip) | Must |
| QA3 | Data Integrity | Same source record never stored in two different bundles | Zero duplicates | Must |

---

## Pain Points Identified

- `generate_incident_id` uses `fetched_at` making IDs unstable across runs
- Storage dedup broken — `exists()` never finds matches because IDs change
- WHO articles with `datetime.now()` all union into 1 mega-bundle
- All incidents re-processed every run regardless of age or change status

## Business Goals Identified

- Source-stable identity: same article = same ID across pipeline runs
- Fingerprint dedup: same record never processed twice
- Active monitoring window (7 days): re-check incidents with recent updates
- Stale skip: events with no updates in 7+ days skipped entirely
- AI cost reduction: don't re-enrich incidents that haven't changed

## Terms to Define (for glossary)

- Source Fingerprint
- Active Monitoring Window
- Stale Incident
- Source-Stable ID
- Upsert

## Action Items

- [x] Split into Feature A (source-stable IDs + fingerprints) and Feature B (lifecycle gating)
- [ ] Update domain_spec.md with lifecycle model
- [ ] Update product_definition.md delivery order
- [ ] Write incident_lifecycle.feature
- [ ] Simulate new lifecycle rules
