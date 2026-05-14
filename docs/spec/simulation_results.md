# Simulation Results

> **Status:** DRAFT (2026-05-14)
> Flow: spec-validation-flow / simulate-spec
> Owner: SA (System Architect)

---

## Summary

### Review Decision: **FAIL**

> **Reviewer:** R (Reviewer agent) — adversarial review of simulation completeness
> **Date:** 2026-05-14
> **Stance:** Actively searched for missed scenarios and invalid pain points; did not confirm completeness.

**Five independent failure conditions:**

1. **21 unresolved pain points** (17 original + 4 newly discovered) — including 3 Contradictory, 8 Missing, 9 Ambiguous, 1 Edge-case
2. **Major scenario coverage gaps:** SQLiteStore has zero scenarios; NewsSearcher has no error scenarios; Storage query filters untested; individual overrides O1/O2/O3/O5 untested
3. **2 quality attributes unstressed:** Performance targets (QA-5: < 5s without AI, QA-6: < 5min with AI) have no simulation scenarios
4. **Bilateral data model mismatch:** `Incident.source_urls` (Required) cannot be populated for GDACS-only bundles (GDACS `raw_fields` lack URL field) — hard cross-context inconsistency
5. **4 rules rejected** for insufficient specificity or contradiction with unresolved pain points (rules 9, 10, 19, 30)

**Pain points requiring fix-spec resolution — Tier 1 (architectural blockers):**
- CLS-4 + XCS-2: AI-dependent overrides vs "no AI calls" in Classification — must clarify phase boundary
- XCS-1: Pipeline order conflict (classify before or after search-more?) — must choose one
- STO-4 (NEW): Incident.source_urls Required vs GDACS no URL — must resolve data model mismatch

### Metrics

| Metric | Count |
|--------|-------|
| Bounded contexts simulated | 5 |
| Total scenarios walked | 42 |
| I/O evidence files | 84 |
| Discovered rules | 34 (30 accepted, 4 rejected) |
| Pain points (original) | 17 (all validated, 0 removed) |
| Pain points (newly added) | 4 |
| **Total pain points** | **21** |
| E2E test candidates | 12 |
| Scenario coverage gaps | 7 |
| Quality attributes unstressed | 2 |
| Bilateral integration mismatches | 1 |
| Rules rejected | 4 |

---

## Fetching

### Scenarios Walked (10)

| # | Scenario | I/O Evidence | Category |
|---|----------|--------------|----------|
| 01 | GDACS adapter fetches earthquake alerts | `01_gdacs_happy_path` | Happy path |
| 02 | WHO adapter fetches disease outbreak reports | `02_who_happy_path` | Happy path |
| 03 | GDELT adapter fetches news articles | `03_gdelt_happy_path` | Happy path |
| 04 | DDG News supplementary search for context | `04_ddg_news_supplementary` | Happy path |
| 05 | HTTP 5xx returns empty list | `05_http_5xx` | Error path |
| 06 | HTTP 429 rate limit returns empty list | `06_rate_limit` | Error path |
| 07 | Network unreachable returns empty list | `07_network_unreachable` | Error path |
| 08 | Malformed response partial parse | `08_malformed_partial_parse` | Edge case |
| 09 | Empty API response no active disasters | `09_empty_response` | Edge case |
| 10 | One source fails others continue | `10_source_isolation` | Quality: Reliability |

### Discovered Rules

1. **Adapter never raises on HTTP errors** — HTTP 5xx, 429, and timeout all return `[]`. Source: scenario 05, 06, 07.
2. **Adapter never raises on network failure** — Connection refused, DNS failure return `[]`. Source: scenario 07.
3. **Adapter skips malformed records and returns valid ones** — Partial parse succeeds for well-formed entries. Source: scenario 08.
4. **raw_fields preserves complete untouched API response** — No normalization, no field removal. Source: scenarios 01–03.
5. **source_name matches adapter identity exactly** — "GDACS", "WHO", "GDELT", or "DDG-NEWS". Source: scenarios 01–04.

### Pain Points

None found. Fetching context is well-specified with clear error handling rules.

### E2E Test Candidates

1. **Source isolation under failure** — Mock one adapter to return HTTP 503, verify others succeed and pipeline continues.

---

## Correlation

### Scenarios Walked (7)

| # | Scenario | I/O Evidence | Category |
|---|----------|--------------|----------|
| 01 | Multi-source records about same incident grouped | `01_multi_source_grouped` | Happy path |
| 02 | Single-source record becomes bundle | `02_single_source_bundle` | Happy path |
| 03 | Empty record list produces empty bundles | `03_empty_records` | Edge case |
| 04 | Date proximity matching across sources | `04_date_proximity` | Edge case |
| 05 | Country overlap with partial field availability | `05_country_overlap` | Edge case |
| 06 | Records with minimal or no matching fields | `06_minimal_fields` | Edge case |
| 07 | Every record assigned exactly once | `07_exactly_once_assignment` | Quality: Reproducibility |

### Discovered Rules

6. **Every RawRecord assigned to exactly one IncidentBundle** — No duplicates, no orphans. Source: scenario 07.
7. **Single-source records become bundles with one record** — No match still produces a bundle. Source: scenario 02.
8. **Empty record list produces empty bundle list** — Zero records in, zero bundles out. Source: scenario 03.
9. **Correlation uses date proximity, country overlap, and title similarity** — Three matching criteria. Source: scenario 01.

### Pain Points

| ID | Classification | Description |
|----|---------------|-------------|
| COR-1 | **Ambiguous** | Date proximity threshold undefined. Spec says "records within the same date window" but does not define the window. 1 day? 3 days? 7 days? This directly affects correlation accuracy. A WHO article from 2 days ago about a GDACS event today — are they correlated? |
| COR-2 | **Ambiguous** | Country overlap matching unclear when only some sources provide country. GDELT and WHO may not have structured country fields. How does "country overlap" work as a matching criterion when one source lacks country data? Is country extracted from title text? |
| COR-3 | **Missing** | Title similarity threshold and algorithm undefined. No guidance on how similar titles must be, whether to use fuzzy matching, exact substring, or embedding similarity. The word "earthquake" vs "quake" — are these matched? |
| COR-4 | **Edge-case** | Correlation behavior when all three matching criteria (date, country, title) are partially or fully unavailable. Records with empty dates, no country, and generic titles could produce false matches or miss valid ones. |

### E2E Test Candidates

2. **Multi-source correlation groups GDACS+WHO+GDELT about same earthquake** — Feed records about the same event from all 3 sources, verify single bundle output.
3. **Every record assigned exactly once across 5+ records** — Feed 5+ records covering 3 distinct incidents, verify correct grouping with no duplication.

---

## Classification

### Scenarios Walked (12)

| # | Scenario | I/O Evidence | Category |
|---|----------|--------------|----------|
| 01 | GDACS Red in Group A = Level 4 HIGH | `01_gdacs_red_group_a` | Happy path |
| 02 | GDACS Green in Group C = Level 1 LOW no report | `02_gdacs_green_group_c` | Happy path |
| 03 | WHO pandemic keyword = Level 4 | `03_who_pandemic_level4` | Happy path |
| 04 | GDELT extreme negative tone = Level 4 | `04_gdelt_extreme_tone` | Happy path |
| 05 | Unknown country defaults to Group C | `05_unknown_country_group_c` | Edge case |
| 06 | No source fields defaults to Level 2 | `06_no_source_fields_default` | Edge case |
| 07 | Override O4 Environmental for wildfire Group A | `07_override_o4_environmental` | Happy path |
| 08 | Override O6 Singapore keyword forces HIGH | `08_override_o6_singapore` | Happy path |
| 09 | GDACS Orange severity bump for Group A | `09_gdacs_orange_severity_bump` | Edge case |
| 10 | Deterministic same input same output | `10_deterministic` | Quality: Reproducibility |
| 11 | All 12 priority matrix cells verified | `11_priority_matrix_cells` | Quality: Testability |
| 12 | Multiple overrides on same bundle | `12_multiple_overrides` | Edge case |

### Discovered Rules

10. **GDACS alertlevel maps to levels** — Green → 1, Orange → 3, Red → 4. Source: scenarios 01, 02, 09.
11. **WHO keyword scan maps to levels** — "pandemic"/"PHEIC" → 4, "epidemic"/"widespread" → 3, "cluster"/"cases reported" → 2, "isolated case" → 1, default → 2. Source: scenario 03.
12. **GDELT tone maps to levels** — tone < -5 → 4, < -3 → 3, >= 0 → 1, else → 2. Source: scenario 04.
13. **Unknown country defaults to Group C with warning** — Any country not in Group A or B list. Source: scenario 05.
14. **No source provides level fields defaults to Level 2** — When bundle has no GDACS/WHO/GDELT level data. Source: scenario 06.
15. **Level 4 always produces should_report=True regardless of group** — Priority matrix invariant. Source: scenario 11.
16. **O4 triggers when disaster type is WF/DR/FL AND country is Group A** — Deterministic, no AI needed. Source: scenario 07.
17. **O6 triggers on keywords Singapore, SRC, Red Cross** — Across all source types. Source: scenario 08.
18. **Classification is fully deterministic** — Same raw records in same bundle always produce same result. No randomness. Source: scenario 10.
19. **Source reliability order is GDACS > WHO > GDELT > DDG-NEWS** — Most reliable available source tried first. Source: scenarios 01–06.
20. **Level must be between 1 and 4 inclusive** — Boundary invariant. Source: scenario 11.
21. **Country group must be one of A, B, or C** — Boundary invariant. Source: scenario 11.
22. **Priority must be one of HIGH, MED, or LOW** — Boundary invariant. Source: scenario 11.

### Pain Points

| ID | Classification | Description |
|----|---------------|-------------|
| CLS-1 | **Ambiguous** | GDACS severity bump for Group A is mentioned but not defined. Spec says "Orange → 3 (severity bump for Group A)" — does this mean Orange becomes Level 4 for Group A countries? Does the bump apply to Green (1 → 2) and Red (4 → still 4) too? What about Group B — no bump? The bump behavior is referenced but never fully specified. |
| CLS-2 | **Ambiguous** | Override O6 effect on priority field is unclear. Glossary says "Forces priority to HIGH and should_report to True" but behavioral_spec says overrides are "evaluated after priority matrix; override results take precedence" and "potentially elevating priority or forcing should_report to True." Does O6 change the priority field itself to HIGH, or just force should_report=True? |
| CLS-3 | **Missing** | Multiple overrides interaction is undefined. When O2, O4, O5, and O6 all trigger on the same bundle, what is the final priority? Are overrides cumulative (all flags in overrides list) or does the highest-impact one determine the final priority? No precedence rules are defined. |
| CLS-4 | **Contradictory** | O1, O3, and O5 overrides require AI for WHO/GDELT sources, but the Classification context explicitly states "no AI calls" and "All logic is pure Python." These overrides blur the boundary between Classification and Enrichment. The spec says O1 uses "Keywords for GDACS, AI for WHO/GDELT" — but when is AI evaluated? During classification or enrichment? If during enrichment, then O1 for WHO/GDELT is not a classification override — it is an enrichment step. |
| CLS-5 | **Missing** | incident_id generation details undefined. Format is YYYYMMDD-CC-TTT but what happens when country_code is unknown at correlation time? Does the correlator use a placeholder? What if disaster_type is also unknown? The TTT code mapping (EQ, FL, TC, etc.) is listed but no mapping function is defined for WHO/GDELT sources that lack eventtype. |
| CLS-6 | **Ambiguous** | Level derivation when bundle has multiple sources with different levels. If GDACS says Level 3 (Orange) but WHO says Level 4 (pandemic), does the source reliability order mean GDACS wins (most reliable = first tried, first used)? Or does the highest level win? The spec says "tries the most reliable available source first" but does not clarify whether it uses ONLY the first available source's level or considers all sources. |

### E2E Test Candidates

4. **GDACS Red alert in Philippines produces Level 4 HIGH should_report True** — Full classification pipeline with GDACS Red in Group A.
5. **GDACS Green alert in France produces Level 1 LOW should_report False** — Full classification with low-priority scenario.
6. **All 12 priority matrix cells produce correct priority and should_report** — Parameterized test covering every level × group combination.
7. **Override O4 triggers for wildfire in Group A country** — WF eventtype + Thailand = O4 in overrides list.
8. **Override O6 forces HIGH priority on Singapore keyword detection** — Title contains "Singapore Red Cross" → O6 + priority HIGH.
9. **Deterministic classification verified across repeated calls** — Same bundle classified 10 times, all results identical.

---

## Enrichment

### Scenarios Walked (7)

| # | Scenario | I/O Evidence | Category |
|---|----------|--------------|----------|
| 01 | Extractor extracts missing country from WHO text | `01_extractor_missing_country` | Happy path |
| 02 | Classifier generates summary for reportable bundle | `02_classifier_summary` | Happy path |
| 03 | AI timeout stores bundle without enrichment | `03_ai_timeout` | Error path |
| 04 | VQD token expired triggers re-fetch | `04_vqd_expired` | Edge case |
| 05 | Batch of 10 bundles in one AI call | `05_batch_10_bundles` | Happy path |
| 06 | Batch of 23 bundles splits into 3 calls | `06_batch_23_split` | Edge case |
| 07 | HTTP 429 rate limit auto-retry | `07_rate_limit_retry` | Error path |

### Discovered Rules

23. **AI failure does not block storage** — Bundle stored with ai_enriched=False when AI times out or fails. Source: scenario 03.
24. **ai_enriched=False means all AI fields are None** — summary, rationale, estimated_affected, estimated_deaths all None. Source: scenario 03.
25. **Batched processing at approximately 10 bundles per AI call** — 23 bundles = 3 calls (10+10+3). Source: scenarios 05, 06.
26. **VQD token is lazy-initialized on first chat call** — Not obtained until needed. Source: scenario 04.
27. **VQD token expiry triggers re-fetch from /status endpoint** — Automatic recovery. Source: scenario 04.
28. **AI operates on IncidentBundle receiving all raw records** — Full context for extraction/enrichment. Source: scenario 02.
29. **Extractor runs before Classifier** — Missing fields extracted first, then summaries generated for reportable bundles. Source: scenarios 01, 02.

### Pain Points

| ID | Classification | Description |
|----|---------------|-------------|
| ENR-1 | **Missing** | Rate limit retry parameters undefined. Spec says "auto-retry with backoff" on HTTP 429 but does not specify: max retry count, backoff strategy (linear vs exponential), initial delay, or what happens when all retries are exhausted. Does the provider raise? Return empty? Propagate as ai_enriched=False? |
| ENR-2 | **Missing** | Post-extraction classification gap. When the Extractor fills in country/country_code for a bundle that previously had it as None, does classification run again? The bundle already has a (default) country_group=Group C. Should it be re-classified with the now-known country? The spec describes a linear pipeline (classify → enrich → store) but extraction may change fields that affect classification. |
| ENR-3 | **Missing** | DuckAIProvider unrecoverable exception mid-batch. Spec says "Auth/network failure → raise exception (unrecoverable)" but no scenario or pain point addresses what happens to bundles already processed in a batch. If 5 of 10 bundles are processed and the provider raises, are those 5 lost? Stored with partial enrichment? The ai_enriched=False rule covers graceful timeout/failure, not exceptions that propagate out of the batch loop. |

### E2E Test Candidates

10. **AI degradation stores all bundles without enrichment** — Mock AI provider to always fail, verify all bundles stored with ai_enriched=False.
11. **Batch of 23 bundles processes in 3 AI calls** — Verify correct batch splitting and that all bundles are processed.

---

## Storage

### Scenarios Walked (6)

| # | Scenario | I/O Evidence | Category |
|---|----------|--------------|----------|
| 01 | Store bundles to date-partitioned JSONL | `01_store_jsonl` | Happy path |
| 02 | Query returns flattened Incident records | `02_query_flattened` | Happy path |
| 03 | Duplicate incident_id is skipped | `03_duplicate_skipped` | Happy path |
| 04 | Query with no matching results | `04_query_no_results` | Edge case |
| 05 | Malformed JSONL line skipped with warning | `05_malformed_jsonl` | Edge case |
| 06 | Inverted date range precondition violation | `06_inverted_date_range` | Edge case |

### Discovered Rules

30. **JSONL files are date-partitioned at incidents/by-date/YYYY-MM-DD/** — One directory per date. Source: scenario 01.
31. **Dedup by incident_id skips existing bundles** — store() returns count of new bundles only. Source: scenario 03.
32. **Query returns flattened Incident records not raw bundles** — No raw_records in output. Source: scenario 02.
33. **Malformed JSONL lines are skipped with warning** — Partial data loss is tolerated. Source: scenario 05.
34. **Storage preserves complete IncidentBundles including all raw records** — Full fidelity persistence. Source: scenario 01.

### Pain Points

| ID | Classification | Description |
|----|---------------|-------------|
| STO-1 | **Ambiguous** | Inverted date range precondition violation behavior undefined. Spec says "Preconditions: date_from <= date_to" but does not specify what happens when violated. ValueError? Empty list? Silent correction? |
| STO-2 | **Ambiguous** | Date partitioning key unclear. JSONL path uses YYYY-MM-DD but the spec does not state which date determines the partition: incident_id date (YYYYMMDD), fetched_at, classified_at, or report_date? If classified_at differs from incident_id date, which directory does the bundle go into? |
| STO-3 | **Missing** | incident_name derivation algorithm undefined. Incident record has incident_name described as "Best title from available records" but no selection algorithm is given. Longest title? First title? Title from most reliable source? Title with the most information? |
| STO-4 | **Contradictory** | Incident.source_urls is Required but GDACS raw_fields contain no URL field. GDACS has title, description, alertlevel, eventtype, iso3, latitude, longitude, istemporary, affectedcountries — no url. WHO, GDELT, and DDG-NEWS all have url fields. A GDACS-only bundle would produce an Incident with empty source_urls, violating the Required constraint. This is a bilateral data model mismatch between the Fetching context (GDACS data shape) and the Storage context (Incident entity). |
| STO-5 | **Ambiguous** | Storage write failure handling is vague. Spec says "Storage failure → log error, pipeline handles gracefully" but "gracefully" is not defined. Does the pipeline skip the failed bundle and continue? Abort the entire pipeline? Retry once? The handling strategy affects data integrity guarantees across pipeline runs. |

### E2E Test Candidates

12. **Dedup prevents duplicate storage on second pipeline run** — Run store twice with same bundles, verify second call returns 0 and file is unchanged.

---

## Cross-Cutting Pain Points

| ID | Classification | Description |
|----|---------------|-------------|
| XCS-1 | **Contradictory** | Pipeline order conflict. product_definition.md says "fetch → correlate → classify → search-more → AI enrich → store" (classify before search-more). But behavioral_spec.md Fetching context says DDG News search happens for "bundles needing context" after correlation but the pipeline flow implies it runs before classification. If search-more adds records to a bundle, does classification need to re-run? The pipeline ordering between supplementary search and classification is unclear. |
| XCS-2 | **Missing** | O1/O3/O5 override evaluation timing. The Classification context says "no AI calls" but O1 (Humanitarian Crisis) uses "AI for WHO/GDELT," O3 (Likely Development) uses "AI-assisted text understanding," and O5 (Forecast/Early Warning) uses "AI for others." The Enrichment context's Classifier agent detects O1, O3, O5 — but these are listed as classification overrides. If they are evaluated during enrichment, then the overrides list is incomplete after classification and gets updated during enrichment. This means the overrides field is populated in two phases, which the spec does not explicitly state. |
| XCS-4 | **Missing** | Supplementary search query generation algorithm undefined. The Correlation → Fetching integration point says "Payload: Search query derived from bundle records" but no algorithm is specified. What fields from the raw records are used to construct the query? Title concatenation? Title + country? A template like "{disaster_type} in {country}"? This directly affects the quality of supplementary search results and the accuracy of correlation for bundles with sparse data. |

---

## Pain Points Summary

| Classification | Count | IDs |
|---------------|-------|-----|
| Ambiguous | 8 | COR-1, COR-2, CLS-1, CLS-2, CLS-6, STO-1, STO-2, STO-5 |
| Contradictory | 3 | CLS-4, XCS-1, STO-4 |
| Missing | 9 | COR-3, CLS-3, CLS-5, ENR-1, ENR-2, ENR-3, STO-3, XCS-2, XCS-4 |
| Edge-case | 1 | COR-4 |

**Total pain points: 21** (17 original + 4 added by review)

### Priority Pain Points (require stakeholder decision before test writing)

**Tier 1 — Architectural blockers (must resolve before any test writing):**

1. **CLS-4 + XCS-2 (AI-dependent overrides in deterministic classification)** — O1/O2/O3/O5 require AI but Classification says "no AI calls." Must decide: are these evaluated only during Enrichment? If so, remove from Classification overrides table and document as Enrichment-phase overrides. Blurs the Classification/Enrichment boundary.
2. **XCS-1 (Pipeline order)** — product_definition says "classify → search-more" but behavioral_spec has correlator triggering search before classification. Must choose one ordering and update all documents consistently. Affects integration test structure.
3. **STO-4 (source_urls Required vs GDACS no URL)** — Bilateral data model mismatch. Must either: make source_urls Optional, provide a GDACS URL derivation rule, or accept empty list for GDACS-only bundles.

**Tier 2 — Classification logic gaps (must resolve before Classification tests):**

4. **CLS-1 (GDACS severity bump)** — Must define which levels get bumped and by how much for Group A.
5. **CLS-6 (Multi-source level selection)** — Must clarify: first-source-only or highest-level-wins?
6. **CLS-3 (Multiple override interaction)** — Must define precedence rules for concurrent overrides.
7. **CLS-5 (incident_id generation)** — Must define how IDs are generated when country/type are unknown at correlation time.

**Tier 3 — Correlation logic gaps (must resolve before Correlation tests):**

8. **COR-1 (Date proximity threshold)** — Must define the date window (1 day? 3 days? 7 days?).
9. **COR-3 (Title similarity algorithm)** — Must specify matching method and threshold.
10. **COR-2 (Country extraction from unstructured sources)** — Must define how country is extracted from WHO/GDELT text.

**Tier 4 — Enrichment/Storage gaps:**

11. **ENR-2 (Post-extraction re-classification)** — Must decide if extraction triggers re-classification.
12. **ENR-1 (Rate limit retry parameters)** — Must specify max retries, backoff strategy, exhaustion behavior.
13. **ENR-3 (Unrecoverable AI exception mid-batch)** — Must define partial batch handling.
14. **STO-2 (Date partitioning key)** — Must specify which date determines the partition directory.
15. **STO-3 (incident_name derivation)** — Must specify title selection algorithm.
16. **STO-5 (Storage write failure handling)** — Must define "handles gracefully" concretely.
17. **XCS-4 (Search query generation)** — Must specify how DDG News queries are derived from bundles.

### Reviewer Notes

**Scenario coverage gaps found (not pain points, but simulation completeness issues):**
- SQLiteStore: zero scenarios (complete entity coverage failure)
- NewsSearcher: no error or edge case scenarios
- Storage query filters: only date range tested; country_group, disaster_type, priority, should_report, source_name filters untested
- Individual overrides O1, O2, O3, O5: no dedicated scenarios
- StorageBackend.exists(): not directly tested
- DuckAIProvider auth/network failure: not tested

**Quality attributes not stressed by any scenario:**
- QA-5: Performance < 5 seconds for 50 incidents (excluding AI) — no timing scenarios
- QA-6: Performance < 5 minutes full batch with AI — no timing scenarios

**Rules rejected (4 of 34):**
- Rule 9: Not specific enough (correlation combination logic undefined)
- Rule 10: Incomplete (GDACS severity bump undefined, linked to CLS-1)
- Rule 19: Ambiguous (source reliability "tried first" meaning unclear, linked to CLS-6)
- Rule 30: Contradicted by unresolved STO-2 (partition key date undefined)
