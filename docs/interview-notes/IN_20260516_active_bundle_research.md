# IN_20260516_active_bundle_research — Pipeline Flow Fix for Active Incident Re-Search

> **Status:** PLANNED
> **Interviewer:** PO
> **Participant(s):** eol
> **Session type:** Post-mortem discovery

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | What problem was discovered? | The source pre-filter (Step B) correctly discards known source records by `exists_by_source_fingerprint()`, but this prevents stored active bundles from ever reaching active-check (Step E) → search-updates (Step F) → ai-enrich (Step G) on subsequent pipeline runs. A GDACS event stored on Day 1 receives zero DDG re-searches during its 7-day monitoring window. |
| Q2 | What is the concrete Day 2 trace? | (1) Day 1: Pipeline runs. GDACS reports earthquake in Japan. Bundle `20260514-JP-EQ` created, classified, enriched, stored via upsert with `last_updated=Day1`. (2) Day 2: Pipeline runs. Step A fetches GDACS — same earthquake, same `eventid`. Step B computes `source_fingerprint="GDACS:57736"`, calls `storage.exists_by_source_fingerprint("GDACS:57736")` → `True` → record discarded. (3) Zero records reach Step C (correlate). Zero bundles reach Step D (classify). Zero bundles reach Step E (active-check). (4) The stored active bundle — only 1 day old, well within the 7-day window — never gets re-searched via DDG and never gets re-enriched by AI. The monitoring window is dead after Day 1. |
| Q3 | What domain invariants are violated? | (1) `domain_spec.md` Step E: "For each bundle: if NEW → proceed. If in storage and ACTIVE (`now - last_updated <= 7 days`) → proceed, merge existing fingerprints." Active bundles never reach Step E. (2) `domain_spec.md` Step F gating: "Gated: `should_report AND (active OR missing_fields)`." Active bundles cannot trigger search because they don't exist as in-flight bundles. (3) `incident_monitoring.feature` Rule "Seven Day Active Window": "The active monitoring window is 7 days from `last_updated`." The window is circumvented — a Day 1 bundle is never re-checked. |
| Q4 | What is the root cause? | Step B (source-fingerprint pre-filter) and Step E (active-status check) share a single control-flow path. Record identity dedup and incident monitoring are gated by the same source-fingerprint check, but these are independent lifecycle concerns. "Has this source record been seen?" is not the same question as "Is this incident still under active monitoring?" Step B gates correlation AND active re-processing — the pre-filter's "discard on seen" blocks the active-check's "active bundle re-process." |
| Q5 | What is the proposed fix? | Step B remains unchanged — it correctly gates correlation (known source records should not be re-correlated). Step E gains an independent input path: it loads stored active bundles from storage via a new `StorageBackend.get_active_bundles()` method and merges them with in-flight bundles arriving from Step D (the reportable branch). In-flight bundles take precedence on `incident_id` collision. This decouples source dedup (Step B) from active re-processing (Step E). |
| Q6 | What quality attributes are affected? | **QA-2 Reliability: re-search guarantee restored.** Active bundles now reliably reach search-updates (Step F) and ai-enrich (Step G) during their 7-day monitoring window regardless of whether fresh source data triggers the correlation path. The DDG re-search and AI re-enrichment contracts on stored active incidents are re-established. **QA-1 Efficiency (unchanged):** step B all-seen early exit still works when no new source records exist — the pipeline runs the active-check merge as a separate concern, and if no stored active bundles exist, Step E also exits quickly. |
| Q7 | What is out of scope? | No changes to Step B (source pre-filter), Step D (classify), or the not-reportable shortcut. No changes to correlation logic. No changes to upsert semantics. No multi-process parallelization of the active-bundle load. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | Why doesn't the current flow catch this? | The pipeline-flow v4 architecture models Step E as downstream of Step D, which is downstream of Step C, which is downstream of Step B. When Step B discards all records, Step C produces zero bundles, Step D produces zero bundles, and Step E has nothing to check. The flow is a strict sequential chain with no alternative entry path into Step E. The active-check is a child of the correlation step, not a peer lifecycle concern. |
| Q9 | How does `get_active_bundles()` work? | `StorageBackend.get_active_bundles(now: datetime, monitoring_window_days: int = 7) -> list[IncidentBundle]` queries storage for all bundles where `now - last_updated <= monitoring_window_days`. Returns fully-hydrated `IncidentBundle` objects with all stored fields (records, fingerprints, classification, enrichment). This is a read-only operation — it does not modify storage. The returned bundles are the stored active incidents that should be re-searched and re-enriched in the current pipeline run. |
| Q10 | What happens on `incident_id` collision between in-flight and stored bundles? | The in-flight bundle from Step D wins. If the current pipeline run produced a bundle with the same `incident_id` as a stored active bundle, the in-flight bundle already contains the merged fingerprints from the active-check (Step E pre-merge) plus any new records from the current fetch. The stored bundle is discarded from the merge to avoid overwriting fresher data. If a stored active bundle has no corresponding in-flight bundle (the common case on Day 2+), it proceeds as-is through the remainder of the pipeline. |
| Q11 | Does Step B need to change? | No. Step B correctly answers "has this source record been processed before?" and discards seen records to prevent expensive re-correlation. This concern is orthogonal to "should this incident be re-searched this run?" — which Step E should answer independently. The fix adds Step E's independent input without altering Step B's semantics. |
| Q12 | Does the not-reportable shortcut interact with this fix? | No. The not-reportable shortcut (Step D → Step I) bypasses Step E entirely. Stored active bundles loaded by `get_active_bundles()` are only merged into Step E's input — they proceed through search, enrich, and override-reeval just like reportable in-flight bundles. Non-reportable bundles from Step D continue to take their direct-to-store path unchanged. |

## Feature: active_bundle_research

| ID | Question | Answer |
|----|----------|--------|
| Q13 | What new StorageBackend method is needed? | `get_active_bundles(now: datetime, monitoring_window_days: int = 7) -> list[IncidentBundle]`. Returns all stored bundles whose `last_updated` is within the monitoring window. Signature mirrors the existing `get_last_updated()` and `get_source_fingerprints()` patterns — a read-only query against storage. Must be implemented by both `JSONLStore` and `SQLiteStore` (StorageBackend protocol contract). |
| Q14 | What tests are needed? | (1) **Unit test `test_get_active_bundles_returns_within_window`**: store three bundles with `last_updated` at 2 days, 5 days, and 10 days ago. Call `get_active_bundles(now, 7)`. Assert first two returned, third excluded. (2) **Unit test `test_get_active_bundles_empty_when_no_active`**: all stored bundles stale. Assert empty list. (3) **Unit test `test_get_active_bundles_empty_when_no_bundles`**: storage is empty. Assert empty list. (4) **Integration test `test_step_e_merges_stored_active_with_inflight`**: mock Step D output with one bundle (`20260514-JP-EQ`). Mock `get_active_bundles()` returning one stored bundle (`20260514-ID-FL`). Assert Step E receives both bundles. (5) **Integration test `test_step_e_inflight_wins_on_collision`**: mock Step D with `20260514-JP-EQ` (new data), mock `get_active_bundles()` with same `20260514-JP-EQ` (stale). Assert merged list contains only the in-flight copy. (6) **Integration test `test_active_bundle_reaches_search_and_enrich`**: end-to-end trace where Step B discards all records, `get_active_bundles()` returns one active bundle. Assert the bundle proceeds through Step F (search-updates) and Step G (ai-enrich). |
| Q15 | How does this affect the active-check step E? | Step E's input becomes dual-source: (a) in-flight reportable bundles from Step D (existing path, unchanged), and (b) stored active bundles from `storage.get_active_bundles(now, window_days)` (new path). The merge logic: iterate over both lists, build a dict keyed by `incident_id`, with in-flight bundles overwriting stored bundles on collision. The merged list is then processed through the existing active-check logic (NEW/ACTIVE/STALE classification). A stored active bundle that collides with an in-flight bundle skips the "ACTIVE → merge fingerprints" step because the in-flight bundle already carries merged fingerprints from the current run's Step E pre-merge. A stored active bundle without an in-flight counterpart proceeds as ACTIVE (its `last_updated` is guaranteed within the window by `get_active_bundles()`) and retains its existing fingerprints — no merge needed since there are no in-flight records to contribute new fingerprints. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Efficiency | Step B all-seen early exit still active when no new source records AND no stored active bundles | Pipeline exits in < 5s (both paths empty) | Must |
| QA2 | Reliability | Stored active bundle (1 day old) reaches DDG search and AI enrichment on pipeline run with no new source data | Active bundle processed through Step F and Step G; zero skipped re-searches during monitoring window | Must |
| QA3 | Data Integrity | In-flight bundle and stored active bundle share the same `incident_id` | In-flight bundle (Step D output) wins; stored bundle discarded from merge. No duplicate processing. | Must |
| QA4 | Determinism | `get_active_bundles(now, window_days)` called with same arguments | Returns same bundles in same order every time (given unchanged storage) | Must |

---

## Pain Points Identified

- Source pre-filter (Step B) and active-check (Step E) conflate two independent lifecycle concerns on a single control-flow path: record identity dedup vs. incident monitoring
- Step E is a downstream child of Step B via the sequential C→D→E chain, with no independent entry point for stored active bundles
- The 7-day monitoring window is circumvented: a GDACS event stored on Day 1 receives zero DDG re-searches and zero AI re-enrichment from Day 2 through Day 8
- `domain_spec.md` Step E description and `incident_monitoring.feature` Rule "Seven Day Active Window" declare invariants that the current pipeline-flow cannot satisfy

## Business Goals Identified

- Active incident re-search guarantee: every stored active bundle must reach DDG search and AI enrichment on every pipeline run during its 7-day monitoring window, regardless of whether fresh source data exists
- Decouple source dedup from incident monitoring: Step B answers "has this record been seen?"; Step E answers "is this incident still under active monitoring?" — these are independent questions
- Storage as source of truth for active bundles: `get_active_bundles()` provides a query interface that treats storage as the canonical registry of incidents under monitoring

## Terms to Define (for glossary)

- `get_active_bundles` — StorageBackend method returning all stored IncidentBundles whose `last_updated` is within the active monitoring window (default 7 days). Read-only query. Signature: `(now: datetime, monitoring_window_days: int = 7) -> list[IncidentBundle]`.
- `Step E dual-input merge` — the active-check step receiving bundles from two independent sources: in-flight reportable bundles from Step D (correlation path) and stored active bundles from `get_active_bundles()` (storage path). Merged by `incident_id` with in-flight winning on collision.
- `Monitoring window dead zone` — the period from Day 2 through Day 8 of an active bundle's lifecycle during which the v4 pipeline-flow provides zero re-search and zero re-enrichment because Step B discards the source record that would have carried the bundle through to Step E.

## Action Items

- [ ] Add `get_active_bundles(now, monitoring_window_days) -> list[IncidentBundle]` to `StorageBackend` protocol
- [ ] Implement `get_active_bundles()` in `JSONLStore`
- [ ] Implement `get_active_bundles()` in `SQLiteStore`
- [ ] Update pipeline Step E to load stored active bundles via `storage.get_active_bundles()` and merge with Step D in-flight bundles
- [ ] Implement incident_id collision resolution: in-flight bundle wins
- [ ] Write unit tests for `get_active_bundles()` (empty storage, all stale, mixed active/stale)
- [ ] Write integration tests for Step E dual-input merge (both sources, collision, active-only path)
- [ ] Write end-to-end trace test: Step B discards all → `get_active_bundles()` returns one → bundle reaches Step F and Step G
- [ ] Update `domain_spec.md` Step E description to document dual-input source
- [ ] Update `incident_monitoring.feature` with new Rule for `get_active_bundles` retrieval and merge behavior
- [ ] Update `storage_backends.feature` with `get_active_bundles` method contract
- [ ] Update `pipeline_orchestration.feature` Step E description for independent active-bundle load
