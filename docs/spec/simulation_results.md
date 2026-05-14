# Simulation Results

> **Status:** DRAFT (2026-05-14) — updated with fix-spec resolutions
> Flow: spec-validation-flow / simulate-spec → fix-spec
> Owner: SA (System Architect)

---

## Resolution Status

All 21 pain points from the simulation review have been resolved via a full rewrite of `behavioral_spec.md`. The resolutions are embedded directly in the rewritten spec.

| ID | Original Classification | Resolution | Status |
|----|------------------------|------------|--------|
| CLS-4 | Contradictory — O1/O3/O5 need AI but live in deterministic Classification context | Split Classification into two phases: Initial Classification (deterministic, O2/O4/O6) and Override Re-evaluation (post-enrichment, O1/O3/O5). Pipeline now has 7 steps. | ✅ Resolved |
| XCS-1 | Contradictory — Pipeline order conflict (classify vs search-more ordering) | Fixed pipeline order: Fetch → Correlate → Initial Classify → Supplementary Search → AI Enrich → Override Re-evaluation → Store. Supplementary search runs AFTER initial classification. | ✅ Resolved |
| STO-4 | Contradictory — Incident.source_urls Required but GDACS has no URL field | Changed `source_urls` from Required to Optional (list[str], default empty). Added source_urls derivation algorithm. GDACS-only bundles have empty source_urls by design. | ✅ Resolved |
| CLS-1 | Ambiguous — GDACS severity bump for Group A undefined | Explicitly defined: Group A only, Orange→Level 4, Green→Level 2, Red unchanged. Group B/C get no bump. | ✅ Resolved |
| CLS-6 | Ambiguous — Multi-source level selection ambiguous | Defined as most-reliable-source-wins. Use level from highest-reliability source (GDACS > WHO > GDELT > DDG-NEWS) that derived a level. | ✅ Resolved |
| CLS-5 | Missing — incident_id generation when country/type unknown | Use "UNX" for unknown country, "OTH" for unknown type. incident_id is stable identity — never regenerated after initial creation. | ✅ Resolved |
| COR-1 | Ambiguous — Date proximity threshold undefined | ±1 calendar day. Records within 1 day are correlation candidates. | ✅ Resolved |
| COR-2 | Ambiguous — Country overlap with missing fields | Two records correlate on country if they share at least one country OR one has no country data (skip country criterion for that pair). | ✅ Resolved |
| CLS-2 | Ambiguous — Correlation with all criteria unavailable → singleton bundles | Records with no date, no country, and no title form singleton bundles with default classification: Level 1, Group C, Priority LOW. | ✅ Resolved |
| XCS-3 | Missing — Title similarity algorithm | Normalized Levenshtein ratio ≥ 0.6. Normalize by lowercasing and stripping whitespace before comparison. | ✅ Resolved |
| XCS-4 | Missing — Supplementary search query generation | Query = `"{title} {country} {disaster_type} latest news"`. Omit unknown country. Substitute "disaster emergency" for unknown type. | ✅ Resolved |
| CLS-3 | Missing — Multiple override interaction | Overrides are independent and cumulative. Each matching override applies its effect. Multiple overrides stack (idempotent for force-HIGH). | ✅ Resolved |
| STO-2 | Ambiguous — Date partitioning key | Use `classification_date` (earliest incident_date from bundle records at classification time). Fallback: `fetched_at` date. | ✅ Resolved |
| STO-5 | Ambiguous — Storage write failure handling | Atomic write via temp file + rename for JSONL, transactions for SQLite. If write fails, temp file deleted, original intact, failure logged, pipeline continues. | ✅ Resolved |
| ENR-1 | Missing — Rate limit retry parameters | Exponential backoff: initial 15s, multiplier 2×, max 3 retries. Total max wait: 15+30+60=105s per call. After exhaustion, raise exception. | ✅ Resolved |
| ENR-2 | Missing — Post-extraction re-classification gap | After Extractor fills missing country/type, re-run deterministic classifier. May upgrade level, change priority, add O4. Do NOT regenerate incident_id. | ✅ Resolved |
| ENR-3 | Missing — Mid-batch DuckAIProvider failure | Keep successfully enriched bundles. Mark remaining as `enrichment_failed=True`, `ai_enriched=False`. Store everything — enriched and unenriched alike. | ✅ Resolved |
| COR-3 | Missing — incident_name derivation | Use title from highest-reliability source's raw_fields. Fallback: `"{disaster_type} in {country} ({date})"` with "Unknown" placeholders. | ✅ Resolved |
| STO-1 | Ambiguous — Inverted date range behavior | If date_from > date_to, return empty list. No error, no swap, no correction. | ✅ Resolved |
| ENR-4 | Missing — O6 priority effect | O6 (Singapore/SRC) forces priority to HIGH and should_report=True regardless of level or country group. Explicitly documented in override table. | ✅ Resolved |
| XCS-2 | Missing — O1/O3/O5 evaluation timing | O1/O3/O5 evaluated in Override Re-evaluation phase AFTER AI enrichment, using AI-extracted data. O2/O4/O6 evaluated during Initial Classification. | ✅ Resolved |

### Rejected Rules — Now Resolved

| Rule | Original Rejection Reason | Resolution |
|------|--------------------------|------------|
| Rule 9 | Not specific enough (correlation combination logic undefined) | Correlation combination logic fully defined: date AND (country OR title) must pass; if only one criterion available, pair correlates on that one; all-unavailable → singleton bundles. |
| Rule 10 | Incomplete (GDACS severity bump undefined) | GDACS severity bump fully defined: Group A only, Orange→4, Green→2, Red unchanged. |
| Rule 19 | Ambiguous (source reliability "tried first" meaning unclear) | Replaced with "most-reliable-source-wins": use level from highest-reliability source that derived one, not first-tried-first-used. |
| Rule 30 | Contradicted by unresolved STO-2 (partition key date undefined) | Partition key defined as `classification_date` with fallback to `fetched_at`. |

---

## Summary

### Review Decision: **FAIL** (pre-fix)

> **Reviewer:** R (Reviewer agent) — adversarial review of simulation completeness
> **Date:** 2026-05-14
> **Stance:** Actively searched for missed scenarios and invalid pain points; did not confirm completeness.

**Five independent failure conditions (pre-fix):**

1. **21 unresolved pain points** (17 original + 4 newly discovered) — including 3 Contradictory, 8 Missing, 9 Ambiguous, 1 Edge-case
2. **Major scenario coverage gaps:** SQLiteStore has zero scenarios; NewsSearcher has no error scenarios; Storage query filters untested; individual overrides O1/O2/O3/O5 untested
3. **2 quality attributes unstressed:** Performance targets (QA-5: < 5s without AI, QA-6: < 5min with AI) have no simulation scenarios
4. **Bilateral data model mismatch:** `Incident.source_urls` (Required) cannot be populated for GDACS-only bundles (GDACS `raw_fields` lack URL field) — hard cross-context inconsistency
5. **4 rules rejected** for insufficient specificity or contradiction with unresolved pain points (rules 9, 10, 19, 30)

**Post-fix status:** All 21 pain points resolved. 4 previously rejected rules now accepted. behavioral_spec.md fully rewritten. Scenario coverage gaps and unstressed quality attributes remain as simulation completeness issues for the next simulation cycle.

### Metrics

| Metric | Count |
|--------|-------|
| Bounded contexts simulated | 5 |
| Total scenarios walked | 42 |
| I/O evidence files | 84 |
| Discovered rules | 34 (30 accepted, 4 rejected → now all 34 accepted) |
| Pain points (original) | 17 (all validated, 0 removed) |
| Pain points (newly added) | 4 |
| **Total pain points** | **21 (all resolved)** |
| E2E test candidates | 12 |
| Scenario coverage gaps | 7 (remain for next simulation cycle) |
| Quality attributes unstressed | 2 (remain for next simulation cycle) |
| Bilateral integration mismatches | 1 → 0 (STO-4 resolved) |
| Rules rejected | 4 → 0 (all resolved) |

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
9. **Correlation uses date proximity, country overlap, and title similarity** — Three matching criteria with defined combination logic (resolved). Source: scenario 01.

### Pain Points

| ID | Classification | Description | Resolution |
|----|---------------|-------------|------------|
| COR-1 | Ambiguous → Resolved | Date proximity threshold undefined | **±1 calendar day.** Records within 1 day are correlation candidates. |
| COR-2 | Ambiguous → Resolved | Country overlap matching unclear when only some sources provide country | **Skip country criterion** for pairs where one record has no country data. Rely on date + title. |
| COR-3 | Missing → Resolved | Title similarity threshold and algorithm undefined | **Normalized Levenshtein ratio ≥ 0.6.** Lowercase, strip whitespace before comparison. |
| COR-4 | Edge-case → Resolved | Correlation behavior when all three matching criteria are unavailable | **Singleton bundles** with default classification: Level 1, Group C, Priority LOW. |

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

10. **GDACS alertlevel maps to levels** — Green → 1, Orange → 3, Red → 4. **Severity bump for Group A: Orange → 4, Green → 2, Red unchanged** (resolved). Source: scenarios 01, 02, 09.
11. **WHO keyword scan maps to levels** — "pandemic"/"PHEIC" → 4, "epidemic"/"widespread" → 3, "cluster"/"cases reported" → 2, "isolated case" → 1, default → 2. Source: scenario 03.
12. **GDELT tone maps to levels** — tone < -5 → 4, < -3 → 3, >= 0 → 1, else → 2. Source: scenario 04.
13. **Unknown country defaults to Group C with warning** — Any country not in Group A or B list. Source: scenario 05.
14. **No source provides level fields defaults to Level 2** — When bundle has no GDACS/WHO/GDELT level data. Source: scenario 06.
15. **Level 4 always produces should_report=True regardless of group** — Priority matrix invariant. Source: scenario 11.
16. **O4 triggers when disaster type is WF/DR/FL AND country is Group A** — Deterministic, no AI needed. Evaluated during Initial Classification. Source: scenario 07.
17. **O6 triggers on keywords Singapore, SRC, Red Cross** — Forces priority HIGH and should_report=True regardless of level or country group (resolved). Evaluated during Initial Classification. Source: scenario 08.
18. **Classification is fully deterministic** — Same raw records in same bundle always produce same result. No randomness. Source: scenario 10.
19. **Source reliability order is GDACS > WHO > GDELT > DDG-NEWS** — **Most-reliable-source-wins**: use level from highest-reliability source that derived one (resolved). Source: scenarios 01–06.
20. **Level must be between 1 and 4 inclusive** — Boundary invariant. Source: scenario 11.
21. **Country group must be one of A, B, or C** — Boundary invariant. Source: scenario 11.
22. **Priority must be one of HIGH, MED, or LOW** — Boundary invariant. Source: scenario 11.

### Pain Points

| ID | Classification | Description | Resolution |
|----|---------------|-------------|------------|
| CLS-1 | Ambiguous → Resolved | GDACS severity bump for Group A undefined | **Explicitly defined:** Group A only, Orange → Level 4, Green → Level 2, Red unchanged. No bump for Group B/C. |
| CLS-2 | Ambiguous → Resolved | Override O6 effect on priority field unclear | **O6 forces priority to HIGH and should_report=True** regardless of level or country group. Explicitly documented. |
| CLS-3 | Missing → Resolved | Multiple overrides interaction undefined | **Independent and cumulative.** Each matching override applies its effect. Multiple overrides stack (idempotent for force-HIGH). |
| CLS-4 | Contradictory → Resolved | O1/O3/O5 require AI but Classification says no AI | **Split into two phases:** Initial Classification (deterministic, O2/O4/O6) and Override Re-evaluation (post-enrichment, O1/O3/O5). |
| CLS-5 | Missing → Resolved | incident_id generation with unknowns | **"UNX" for unknown country, "OTH" for unknown type.** incident_id is stable — never regenerated. |
| CLS-6 | Ambiguous → Resolved | Multi-source level selection | **Most-reliable-source-wins.** Use level from highest-reliability source that derived one. |

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
29. **Extractor runs before Classifier** — Missing fields extracted first, then summaries generated for reportable bundles. **Post-extraction re-classification runs between Extractor and Classifier** (resolved). Source: scenarios 01, 02.

### Pain Points

| ID | Classification | Description | Resolution |
|----|---------------|-------------|------------|
| ENR-1 | Missing → Resolved | Rate limit retry parameters undefined | **Exponential backoff: initial 15s, multiplier 2×, max 3 retries.** Total max wait: 15+30+60=105s. After exhaustion, raise exception. |
| ENR-2 | Missing → Resolved | Post-extraction classification gap | **Re-run deterministic classifier after extraction.** May upgrade level, change priority, add O4. Do NOT regenerate incident_id. |
| ENR-3 | Missing → Resolved | Mid-batch DuckAIProvider failure | **Keep successfully enriched bundles.** Mark remaining as `enrichment_failed=True`, `ai_enriched=False`. Store everything. |

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

30. **JSONL files are date-partitioned at incidents/by-date/YYYY-MM-DD/** — **Partition key is `classification_date`** (earliest incident_date from bundle records, fallback to fetched_at) (resolved). Source: scenario 01.
31. **Dedup by incident_id skips existing bundles** — store() returns count of new bundles only. Source: scenario 03.
32. **Query returns flattened Incident records not raw bundles** — No raw_records in output. Source: scenario 02.
33. **Malformed JSONL lines are skipped with warning** — Partial data loss is tolerated. Source: scenario 05.
34. **Storage preserves complete IncidentBundles including all raw records** — Full fidelity persistence. Source: scenario 01.

### Pain Points

| ID | Classification | Description | Resolution |
|----|---------------|-------------|------------|
| STO-1 | Ambiguous → Resolved | Inverted date range behavior undefined | **Return empty list.** No error, no swap, no correction. |
| STO-2 | Ambiguous → Resolved | Date partitioning key unclear | **`classification_date`** — earliest incident_date from bundle records at classification time. Fallback: fetched_at date. |
| STO-3 | Missing → Resolved | incident_name derivation undefined | **Title from highest-reliability source.** Fallback: `"{disaster_type} in {country} ({date})"` with "Unknown" placeholders. |
| STO-4 | Contradictory → Resolved | Incident.source_urls Required but GDACS has no URL | **Changed to Optional (list[str], default empty).** GDACS-only bundles have empty source_urls by design. Added derivation algorithm. |
| STO-5 | Ambiguous → Resolved | Storage write failure handling vague | **Atomic write:** temp file + rename for JSONL, transactions for SQLite. Failure on one bundle does not prevent storing others. |

### E2E Test Candidates

12. **Dedup prevents duplicate storage on second pipeline run** — Run store twice with same bundles, verify second call returns 0 and file is unchanged.

---

## Cross-Cutting Pain Points

| ID | Classification | Description | Resolution |
|----|---------------|-------------|------------|
| XCS-1 | Contradictory → Resolved | Pipeline order conflict | **Fixed order:** Fetch → Correlate → Initial Classify → Supplementary Search → AI Enrich → Override Re-evaluation → Store. |
| XCS-2 | Missing → Resolved | O1/O3/O5 override evaluation timing | **O1/O3/O5 evaluated in Override Re-evaluation phase AFTER AI enrichment.** O2/O4/O6 evaluated during Initial Classification. |
| XCS-4 | Missing → Resolved | Supplementary search query generation | **Query = `"{title} {country} {disaster_type} latest news"`.** Omit unknown country. Substitute "disaster emergency" for unknown type. |

---

## Pain Points Summary

| Classification | Pre-fix Count | Post-fix Count | IDs |
|---------------|--------------|----------------|-----|
| Ambiguous | 8 | 0 | COR-1, COR-2, CLS-1, CLS-2, CLS-6, STO-1, STO-2, STO-5 — all resolved |
| Contradictory | 3 | 0 | CLS-4, XCS-1, STO-4 — all resolved |
| Missing | 9 | 0 | COR-3, CLS-3, CLS-5, ENR-1, ENR-2, ENR-3, STO-3, XCS-2, XCS-4 — all resolved |
| Edge-case | 1 | 0 | COR-4 — resolved |

**Total pain points: 21 → 0 (all resolved)**

### Remaining Issues for Next Simulation Cycle

These are NOT pain points in the spec itself, but gaps in the simulation coverage:

1. **SQLiteStore: zero scenarios** — needs dedicated simulation
2. **NewsSearcher: no error/edge-case scenarios** — needs simulation
3. **Storage query filters:** only date range tested; country_group, disaster_type, priority, should_report, source_name untested
4. **Individual overrides O1, O2, O3, O5:** no dedicated scenarios (O4 and O6 covered)
5. **StorageBackend.exists():** not directly tested
6. **DuckAIProvider auth/network failure:** not tested
7. **Quality attributes QA-5/QA-6:** no timing scenarios
