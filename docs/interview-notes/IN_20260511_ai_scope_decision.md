# IN_20260511_ai_scope_decision — AI Scope and Pipeline Architecture Decision

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** Stakeholder (domain expert)
> **Session type:** Scope refinement

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Should the pipeline rely on AI for classification? | No. Principle: "Python does what Python can; AI only summarizes." All deterministic classification logic must be Python code, not AI calls. AI is expensive, non-deterministic, and a single point of failure for core routing decisions. |
| Q2 | What triggered this decision? | The old pipeline used AI for both transform and classify stages. Every incident required two AI round-trips before storage. This was slow, costly, and produced inconsistent classifications for the same input data. Deterministic rules (country group lookup, level mapping, priority matrix) should never depend on an LLM. |
| Q3 | What does the new pipeline look like? | Old: fetch → transform (AI) → classify (AI) → store. New: fetch → classify (Python) → enrich (AI, summaries only) → store. Classification happens before AI, using pure Python. AI enrichment is an optional enhancement step, not a gate. |
| Q4 | What if the AI step fails? | The incident is still classified and stored. The record will have empty summary/rationale fields but valid classification. AI failure must never block incident storage. |
| Q5 | What if a source has no API and only free text? | ProMED is the exception. It has no public API — only free-text disease alerts. AI must extract structured fields (disease name, country, case counts) from unstructured text. But once extracted, the same deterministic Python pipeline handles classification. |

---

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q6 | What classification logic must be pure Python? | (1) Country → Country Group (A/B/C) lookup via COUNTRY_GROUPS dict. (2) GDACS alertlevel → Incident Level mapping: Green→1, Orange→3, Red→4. (3) (Level, Group) → Priority via PRIORITY_MATRIX. (4) Should_report decision from the matrix. (5) Override criteria checks: humanitarian crisis, multi-regional, Singapore/SRC connection. (6) Incident ID generation in YYYYMMDD-CC-TTT format. (7) Date filtering and freshness checks against source-specific windows. |
| Q7 | What is AI allowed to do? | Only language-understanding tasks: (1) `summary` — human-readable event summary. (2) `impact.impact_description` — description of impact. (3) `classification_metadata.rationale` — why this classification was chosen. (4) Extracting `estimated_affected` and `estimated_deaths` from unstructured text when the API doesn't provide them. (5) Sentiment analysis for media coverage. (6) Disease-specific field extraction from ProMED free-text alerts. |
| Q8 | How does each source split between Python and AI? | **GDACS**: Python extracts all fields from GeoJSON (eventtype, alertlevel, country, iso3, severitydata, coordinates, affectedcountries). AI generates summary and rationale only. **ProMED**: AI extracts disease name, country, case counts from free text. Python classifies the extracted data. AI writes summary. **ReliefWeb**: Python extracts title, country, date, disaster type, URL from structured API. AI generates summary. **HealthMap**: Python extracts structured disease surveillance fields. AI generates summary if needed. **WHO**: Python extracts structured health emergency data. AI generates summary if needed. |

---

## Feature: pipeline-architecture

| ID | Question | Answer |
|----|----------|--------|
| Q9 | Should RawIncidentData change? | No. Adapters still produce RawIncidentData with 7 flat fields. The change is downstream: the classifier consumes RawIncidentData directly without an AI transform step. |
| Q10 | What about the incident_id generation? | Pure Python. YYYYMMDD-CC-TTT format is fully deterministic from the event date, country ISO code, and disaster type code. No AI needed. |
| Q11 | How should the enrich step be designed? | As an optional pipeline stage. It receives a ClassifiedIncident, calls AI for summary/rationale fields, and returns the enriched record. If it fails, return the original ClassifiedIncident unchanged. Must have a timeout. |
| Q12 | What about estimated_affected and estimated_deaths extraction? | Only when the source API doesn't provide them AND the incident is significant enough to warrant the AI cost. For GDACS, severitydata often has these. For ProMED, AI must parse case counts from text. Make this a per-source decision, not a blanket rule. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Determinism | When the same incident is classified twice, the result is identical | 100% reproducible classification | Must |
| QA2 | Reliability | When the AI service is unavailable, incidents are still classified and stored | Zero data loss on AI failure | Must |
| QA3 | Latency | When classifying 50 incidents, the Python classification step completes | < 1 second (no network calls) | Must |
| QA4 | Auditability | When reviewing a classification, the decision path is traceable | Every classified field links to its rule or AI prompt | Should |
| QA5 | Cost Efficiency | When running the pipeline daily, AI calls are minimized | < 1 AI call per incident on average for structured sources | Should |

---

## Pain Points Identified

- Old pipeline required two AI round-trips per incident (transform + classify), causing high latency and cost
- Classification was non-deterministic — same incident could get different priority/level on different runs
- AI failure blocked the entire pipeline — no fallback path
- Override criteria and priority matrix logic was buried in AI prompts instead of testable Python code
- ProMED extraction forced all sources through an AI-first path even when 4 of 5 sources have structured APIs

## Business Goals Identified

- Make classification 100% deterministic and testable
- Reduce AI cost by limiting AI calls to language tasks only
- Ensure the pipeline degrades gracefully when AI is unavailable
- Make the classification decision tree auditable and version-controlled

## Terms to Define

- `Classify step` — pure Python stage that maps RawIncidentData to ClassifiedIncident using deterministic rules
- `Enrich step` — optional AI stage that adds summary and rationale fields to an already-classified incident
- `AI-optional` — design principle that AI enhances but never gates core pipeline logic
- `Deterministic classification` — classification that produces identical output for identical input without any LLM calls

## Action Items

- [ ] Refactor pipeline from fetch → transform (AI) → classify (AI) → store to fetch → classify (Python) → enrich (AI) → store
- [ ] Implement classify step in pure Python: country group lookup, level mapping, priority matrix, override checks, incident ID generation, date filtering
- [ ] Implement enrich step as an optional stage with fallback (return ClassifiedIncident unchanged on failure)
- [ ] Move all classification prompt logic out of AI calls and into Python functions
- [ ] Add tests for deterministic classification: same input → same output, no mocks needed for AI
- [ ] Add ProMED-specific AI extraction for structured fields from free text (disease name, country, case counts)
- [ ] Ensure GDACS adapter extracts all structured fields (eventtype, alertlevel, country, iso3, severitydata, coordinates, affectedcountries) into RawIncidentData without AI
- [ ] Add timeout and graceful degradation to the enrich step
