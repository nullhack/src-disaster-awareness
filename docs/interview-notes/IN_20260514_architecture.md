# IN_20260514_architecture — Pipeline Architecture and Correlation

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
| Q3 | Why does it exist — what problem does it solve? | Automates multi-source disaster surveillance with deterministic classification. |
| Q4 | When and where is it used? | Scheduled CLI tool, backend batch processing. |
| Q5 | Success — what does "done" look like? | Pipeline processes batches reliably, every time, with deterministic results. |
| Q6 | Failure — what must never happen? | One component failure must not cascade to other components. AI failure must not prevent storage. |
| Q7 | Out-of-scope — what are we explicitly not building? | Dashboard, real-time alerting, multi-process execution. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | Describe the overall architecture. | Three primary sources (GDACS, WHO, GDELT) feed into a Correlator that groups by incident. The correlated bundles go to a ClassifyEngine (deterministic) and then to Storage (JSONL or SQLite). A supplementary source (DDG News) feeds into the correlation stage. An AI Enrichment module (duck.ai + DSPy, batched calls) operates between classification and storage, receiving correlated bundles. |
| Q9 | What is the pipeline flow per batch? | Six steps: (1) Fetch all 3 primary sources → list[RawRecord]. (2) Correlate records about the same real-world incident into IncidentBundles — match by date proximity, country overlap, title similarity; single-source records become bundles with one record. (3) Supplementary search: for bundles needing more context (missing country, low-structure source), search DDG News and append results to the bundle. (4) Classify deterministically → assign level, priority, country_group, overrides — uses best available data from any record in the bundle, marks fields that need AI extraction. (5) AI Enrichment (batched): Extractor batch for bundles needing country/type extraction, Classifier batch for should_report=True bundles. (6) Store the complete IncidentBundle with all raw records and derived classification. |
| Q10 | How does correlation work? | Records about the same real-world incident are grouped into IncidentBundles. Matching criteria: date proximity, country overlap, and title similarity. Single-source records become bundles with one record. |
| Q11 | When is supplementary search triggered? | For bundles needing more context — specifically when country is missing or the source is low-structure. DDG News results are appended to the bundle. |
| Q12 | What happens during the classification step? | Deterministic classification assigns level, priority, country_group, and overrides. It uses the best available data from any record in the bundle. It also marks fields that need AI extraction. |
| Q13 | What are the two AI enrichment batches? | Extractor batch: bundles where country/disaster_type is still None after deterministic pass, about 10 per call. DDG News results provide additional context when available. Classifier batch: should_report=True bundles, about 10 per call. AI generates summaries and detects overrides O1, O3, O5. Total: ~6 calls × 15s = ~1.5 minutes per 50 incidents. |

## Feature: Pipeline Orchestration

| ID | Question | Answer |
|----|----------|--------|
| Q14 | Where does pipeline orchestration live? | In `pipeline.py` — it orchestrates the full flow: fetch → correlate → classify → search-more → AI enrich → store. |
| Q15 | What is the file structure for the pipeline? | The main package is `disaster_surveillance_reporter/` with: types.py, classify.py, correlate.py, pipeline.py at top level. Sub-packages: ai/ (provider.py, extractor.py, classifier.py), adapters/ (gdacs.py, who.py, gdelt.py, news.py), storage/ (jsonl.py, sqlite.py). Plus scripts/capture_fixtures.py and a full tests/ directory. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Performance | 50 incidents classified and stored in < 5 seconds (excluding AI) | < 5 seconds | Must |
| QA2 | Performance | Full batch with AI in < 5 minutes | < 5 minutes | Should |
| QA3 | Reliability | Any source API down — other sources unaffected, no data loss | Graceful degradation | Must |

---

## Pain Points Identified

- Correlation across sources with different data shapes and reliability levels is complex
- Supplementary search adds latency but is necessary for low-structure sources
- AI enrichment is the bottleneck (~1.5 min per 50 incidents) due to rate limits

## Business Goals Identified

- Single pipeline processes all sources in one batch run
- Deterministic classification before AI enrichment ensures reproducibility
- AI enrichment is optional — incidents stored even if AI fails

## Terms to Define (for glossary)

- IncidentBundle
- Correlator
- ClassifyEngine
- Supplementary search
- Batched processing
- Extractor batch
- Classifier batch

## Action Items

- [ ] Validate correlation heuristics (date proximity thresholds, title similarity algorithm)
- [ ] Confirm supplementary search triggering conditions
- [ ] Benchmark AI enrichment latency with real API calls
