# ADR_20260514_two_phase_classification

## Status

Accepted

## Context

DSR needs to classify incidents using both deterministic rules (country groups, priority matrix, alert level mapping) and AI-assisted text understanding (detecting humanitarian crises, escalation potential, forecast/early warning status from unstructured text). The quality attributes rank Reproducibility (#1) as the top priority — identical input must always produce identical classification. Reliability (#2, #3) requires graceful AI failure handling. Testability (#4) requires every rule to have a named test.

The spec defines six overrides (O1–O6). Three (O2 Multi-Regional, O4 Environmental, O6 Singapore/SRC) use structured data available at classification time. Three (O1 Humanitarian Crisis, O3 Likely Development, O5 Forecast/Early Warning) require AI text understanding. AI enrichment fills in missing fields (country, disaster type) that may change the classification result.

The forces at play are: (1) classification must be reproducible for the deterministic portion, (2) AI-dependent overrides cannot be evaluated until AI enrichment completes, (3) AI may fill in missing country/type fields that affect the priority matrix and deterministic overrides (e.g., O4 requires country in Group A), (4) re-evaluation must not regenerate the incident_id.

## Interview

| Question | Answer |
|---|---|
| Can AI be used for initial classification? | No — QA #1 (Reproducibility) and the product definition explicitly state classification is always deterministic |
| Should all overrides be evaluated in one pass after enrichment? | No — O2, O4, O6 use structured data and should be evaluated immediately; deferring them adds unnecessary AI dependency |
| What happens if AI fills in a country that changes the country group? | Re-run the deterministic classifier with the new data (country group lookup, level derivation, priority matrix). incident_id stays the same. |

## Decision

Split classification into two phases:

**Phase 1 — Initial Classification** (deterministic, no AI): Apply country group lookup, source-specific level derivation, priority matrix, and deterministic overrides O2, O4, O6. This phase runs after correlation, before supplementary search and AI enrichment. 100% reproducible.

**Phase 2 — Override Re-evaluation** (deterministic, post-enrichment): After AI enrichment fills in missing fields and detects override conditions, re-evaluate overrides O1, O3, O5 using AI-extracted data. If level or priority changes, re-apply the priority matrix. The incident_id is NOT regenerated.

Between Phase 1 and Phase 2, supplementary search (DDG News) adds context, and AI enrichment (Extractor → re-classify → Classifier) fills in missing fields and detects override conditions.

## Reason

The two-phase split ensures that deterministic classification (Phase 1) is always reproducible and testable, while AI-dependent overrides (Phase 2) are evaluated only after the data they need is available. This resolves the conflict between Reproducibility (QA #1) and the need for AI-assisted text understanding.

## Alternatives Considered

- **Single-phase classification (all after AI)**: Evaluate all overrides and classification after AI enrichment. Rejected because: (1) all classification becomes AI-dependent, violating the product definition ("no AI for classification, ever"), (2) bundles that don't need AI (GDACS-only with complete data) would be unnecessarily delayed, (3) testability degrades — deterministic rules would require AI mocking to test.
- **Single-phase classification (all deterministic, no AI overrides)**: Use only deterministic rules, drop O1/O3/O5. Rejected because: (1) these overrides provide significant value (humanitarian crisis detection, escalation warning), (2) the spec explicitly requires them, (3) AI enrichment is already available for extraction.
- **Three-phase classification**: Add a third phase for post-storage re-evaluation. Rejected as unnecessary complexity — all classification data is available by the end of Phase 2, and re-evaluating after storage would require a read-modify-write pattern that risks data inconsistency.

## Consequences

- (+) Phase 1 is 100% deterministic and testable — every rule has a pure-Python test
- (+) Phase 1 completes in <1 second for 50 bundles (no network calls)
- (+) AI failure only affects Phase 2 — bundles are still classified and stored with Phase 1 results
- (+) Clear separation of concerns: deterministic rules in `classify.py`, AI agents in `ai/extractor.py` and `ai/classifier.py`
- (+) Post-extraction re-classification leverages AI-filled data for better classification accuracy
- (-) Two classification passes add conceptual complexity — developers must understand which rules apply in which phase
- (-) Phase 2 may change Phase 1 results (level bump, priority change), which can be surprising
- (-) Testing requires covering both Phase 1 and Phase 2 scenarios, doubling some test cases

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Accepted? |
|------|------------|--------|------------|-----------|
| Developers apply AI-dependent overrides (O1/O3/O5) in Phase 1 by mistake | Medium | High | Code review checklist; Phase 1 function signature explicitly excludes AI fields; `overrides` list populated in two distinct code paths | No |
| Phase 2 level bump creates inconsistency with Phase 1 `should_report` flag | Low | Medium | Phase 2 re-applies the full priority matrix after any level change; overrides are re-evaluated from scratch | Yes |
| Post-extraction re-classification changes country group, causing O4 to newly apply | Medium | Low | This is correct behavior — O4 should apply if AI discovers the country is Group A. The re-classification is intentional. | Yes |
