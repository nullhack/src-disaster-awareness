# IN_20260516_pipeline_redesign — Pipeline-Flow v4 Redesign Decisions

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** eol
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Who are the users? | Backend Developers, Ops Teams — the pipeline is a scheduled CLI batch processor with no UI. |
| Q2 | What does the product do at a high level? | The pipeline orchestrates a 10-state sequential flow: Fetch → Source Pre-filter → Correlate → Classify → (reportable? → Active-Check → Search → AI Enrich → Override Re-eval) → Store. Non-reportable bundles exit early from classify directly to store. |
| Q3 | Why does it exist — what problem does it solve? | v3 had architectural inefficiencies: classification ran after lifecycle gating (wasting active-check on non-reportable bundles), the source pre-filter was conflated with store upsert, date proximity was absent from correlation, and pipeline configuration was scattered across code. v4 fixes all of these with seven targeted design decisions. |
| Q4 | When and where is it used? | Scheduled CLI tool (`dsr-pipeline`), single-process batch execution. Each run processes fresh data from GDACS, WHO, EONET, and GDELT adapters. |
| Q5 | Success — what does "done" look like? | All seven design decisions implemented in pipeline-flow.yaml v4 (commit `0fd7f1a`) and pipeline.py (commit `2107226`). 143/143 tests pass. Pipeline produces correct results with deterministic classification, source dedup, non-reportable early exit, and date-proximity-based correlation. |
| Q6 | Failure — what must never happen? | Known records must never pass through expensive correlation, AI, or search again (source pre-filter failure). Non-reportable bundles must never consume active-check, search, or AI resources (order failure). Correlation must never group records from different calendar days without date proximity (data quality failure). Classification must never be gated by lifecycle — a non-reportable bundle is always non-reportable regardless of staleness. |
| Q7 | Out-of-scope — what are we explicitly not building? | v5 pipeline architecture, multi-process parallelization, real-time push alerts, stream processing, pipeline DAGs. This session is purely about v4 changes to the existing sequential monolith. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | Why was Source Pre-filter restored as a separate step? | In v3 the source pre-filter was bundled into the store upsert logic. This meant known records still passed through correlation, classification, and all downstream processing before being discarded at the final store step. Restoring it as a distinct step B — before correlation — means the expensive correlation engine never sees records already in storage. The pre-filter calls `StorageBackend.exists_by_source_fingerprint()` per record; surviving records are net-new. This satisfies QA-9 (pipeline with no new data completes in <5s) by enabling early exit: when every record is discarded at the pre-filter, the pipeline exits immediately at the `all-seen → complete` transition with zero downstream work. |
| Q9 | Why does classification run BEFORE active-status check? | In v3, active-check (lifecycle gating) ran before classify. This meant non-reportable bundles — which should never receive search, AI, or override re-evaluation regardless of staleness — still went through active-check. By placing classify before active-check, non-reportable bundles take the `not-reportable → store` shortcut and exit immediately. Only reportable bundles proceed to the lifecycle gate. This saves wasted active-check queries and prevents non-reportable bundles from ever reaching the monitoring window. |
| Q10 | What is the non-reportable shortcut to store? | From the classify step, bundles where `should_report=False` are routed directly to `_store_bundles()` (upsert) via the `not-reportable → store` transition. They completely bypass active-check, DDG search, AI enrichment (ExtractorAgent + ClassifierAgent), and override re-evaluation. The store upsert still runs — new bundles are inserted, unchanged bundles are noop'd — so storage doesn't bloat with stale non-reportables. This is the `not-reportable` exit path from pipeline-flow.yaml state D. |
| Q11 | Why was date proximity restored in correlation? | `domain_spec.md` defines correlation criteria as date proximity (±1 calendar day), country overlap (ISO 3166-1 alpha-2), and title similarity (ratio ≥ 0.6). The combination rule is: date AND (country OR title). During a prior iteration, date proximity was removed ("Change #8: No strict date proximity"), which caused records from different calendar days to be incorrectly grouped into the same bundle. v4 restores the ±1 calendar day criterion as mandatory, reverting Change #8. The correlation step now uses three matching criteria with the correct combination logic, as declared in the pipeline-flow.yaml `correlate` state attrs: `date_proximity_days: 1`, `title_threshold: 0.6`, `match_algorithm: difflib.SequenceMatcher`. |
| Q12 | How does post-extraction re-classification work in v4? | `_ai_enrich()` already calls `ClassifyEngine.classify()` after `ExtractorAgent.extract()` completes (see pipeline.py lines 241–248). The ExtractorAgent extracts country, disaster_type, estimated_affected, and estimated_deaths from ALL raw records via DSPy typed signatures. After extraction, classify runs again on every bundle the Extractor modified — this updates country_group, level, priority, and O4 override from newly-discovered fields. The pipeline-flow.yaml `ai-enrich` state declares `post_extract_reclassify: true`, confirming this as an intentional design feature. |
| Q13 | What is `_now` callable injection? | The Pipeline class stores `self._now = lambda: datetime.now(tz=timezone.utc)` at init (pipeline.py line 50). This replaces hardcoded `datetime.now()` calls throughout pipeline logic. Any method that needs wall-clock time uses `self._now()` instead of calling `datetime.now()` directly. The callable is injectable: tests can supply a frozen clock for deterministic behavior, and the `_now` attribute can be passed to downstream methods that need current-time awareness. |
| Q14 | What are pipeline integration attrs? | `pipeline-flow.yaml` v4 declares per-state integration metadata that `pipeline.py` can read at init time. Each state has: `method` (the pipeline method to invoke, e.g. `_fetch_sources`, `_pre_filter`, `_classify_initial`), `error_action` (one of `skip | abort | continue`, controlling failure handling), and domain-specific attrs (thresholds, env vars, reliability order). Examples: `date_proximity_days: 1`, `monitoring_window_days: 7`, `batch_size: 10`, `provider_env: DSR_AI_PROVIDER`, `reliability: [gdacs, who, eonet, gdelt]`, `overrides_initial: [O2, O4, O6]`, `overrides_post: [O1, O3, O5]`. The flow YAML is the single source of truth for step configuration — changing a threshold means editing one YAML file, not hunting through code. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Efficiency | Pipeline run with zero new records (all source fingerprints already in storage) | Exit at source-prefilter step B via `all-seen → complete`; correlate, classify, active-check, search, AI skip entirely. <5s wall-clock. | Must |
| QA2 | Efficiency | Non-reportable bundle after classification | Exit at classify step D via `not-reportable → store`; no active-check, no search, no AI, no override re-eval consumed. | Must |
| QA3 | Data Quality | Two records from different calendar days | Never grouped into same bundle. ±1 calendar day date proximity enforced by Correlator. | Must |
| QA4 | Determinism | Classification after AI extraction | `ClassifyEngine.classify()` runs on every Extractor-modified bundle before ClassifierAgent enrichment. Classification always reflects newly-extracted fields. | Must |
| QA5 | Testability | Pipeline clock behavior | `_now` callable injection allows tests to supply frozen clocks; no `datetime.now()` hardcoded in pipeline logic. | Must |
| QA6 | Maintainability | Change a pipeline threshold (e.g. monitoring window from 7 to 14 days) | Edit one value in `pipeline-flow.yaml`; no code changes required. | Should |
| QA7 | Reproducibility | Same pipeline-flow.yaml + same adapters → same step sequence and configuration | Pipeline reads YAML at init; no hidden config in code, no env-var-only thresholds. | Must |

---

## Pain Points Identified

- v3 source pre-filter conflated with store upsert: known records passed through correlation and classification before being discarded
- v3 classify ran after active-check: non-reportable bundles wasted lifecycle queries, then search, then AI, before finally being skipped
- Date proximity absent from correlation: records from different days grouped incorrectly (reverted Change #8)
- `datetime.now()` hardcoded in pipeline methods: untestable, nondeterministic behavior
- Pipeline configuration scattered: thresholds, env vars, and reliability order distributed across code rather than centralized in flow YAML

## Business Goals Identified

- Never waste correlation, classification, search, or AI resources on records already in storage
- Never waste active-check, search, or AI resources on non-reportable bundles
- Correlation must respect ±1 calendar day date proximity per domain_spec.md
- Pipeline configuration centralized in pipeline-flow.yaml as single source of truth
- Deterministic, injectable clock for testable pipeline execution

## Terms to Define (for glossary)

- `source-prefilter` — step B in pipeline-flow v4; discards already-seen RawRecords before correlation using `exists_by_source_fingerprint()`
- `not-reportable shortcut` — classify→store direct path for `should_report=False` bundles, bypassing all subsequent processing
- `post-extraction re-classification` — `ClassifyEngine.classify()` call within `_ai_enrich()` after ExtractorAgent extracts fields
- `_now callable` — injectable `lambda: datetime.now(tz=timezone.utc)` stored as `self._now` on Pipeline instance
- `pipeline integration attrs` — per-state YAML metadata (`method`, `error_action`, domain-specific thresholds) read by pipeline.py at init

## Action Items

- [x] Implement source-prefilter as distinct step B: commit `0fd7f1a`
- [x] Implement classify-before-active-check with not-reportable shortcut: commit `2107226`
- [x] Restore ±1 calendar day date proximity in correlation: commit `0fd7f1a`
- [x] Implement `_now` callable injection in Pipeline.__init__: commit `2107226`
- [x] Document post-extraction re-classification as confirmed feature: pipeline-flow.yaml `ai-enrich` state
- [x] Declare pipeline integration attrs in pipeline-flow.yaml v4: commit `0fd7f1a`
- [x] All 143 tests pass against v4 implementation
