# IN_20260514_product_scope — Product Purpose, Users, and Scope

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** eol
> **Session type:** Initial discovery

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Who are the users? | Three user personas: (1) Backend Developers — they need clean, testable Python code with deterministic behavior; (2) Ops Teams — they need a CLI tool that runs on a schedule and produces reports; (3) Researchers — they need queryable local incident data for analysis. |
| Q2 | What does the product do at a high level? | DSR is a backend pipeline that fetches incident data from free public APIs, correlates information across sources, classifies deterministically, enriches with AI and supplementary news search, and stores locally. It replaces the legacy codebase with a clean rewrite. |
| Q3 | Why does it exist — what problem does it solve? | The legacy codebase needs to be replaced. The system automates disaster incident surveillance by aggregating data from multiple free public sources, removing the need for manual monitoring. It deterministically classifies incidents so human analysts can focus on decision-making rather than data gathering. |
| Q4 | When and where is it used? | It runs as a scheduled CLI tool on ops infrastructure. No web UI, no dashboard — purely backend batch processing. Researchers query the stored data locally. |
| Q5 | Success — what does "done" look like? | A clean Python codebase that fetches from all sources, correlates incidents across sources, classifies deterministically every time, enriches with AI where needed, and stores everything locally in queryable formats. Every classification rule has a passing test with named fixtures. |
| Q6 | Failure — what must never happen? | It must never replace human analyst judgment. It must never lose data when a source API is down. It must never let an AI failure prevent storing an incident. |
| Q7 | Out-of-scope — what are we explicitly not building? | Dashboard or web UI, real-time push notifications, real-time alerting system, account-based API sources (ReliefWeb, HealthMap), AI-based classification (AI only extracts and enriches — it never classifies), email sending (future consideration only), multi-process or distributed execution. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | What is the system fundamentally — what are the three pillars? | (1) A deterministic classification engine that assigns incident levels, priorities, and country groups using fixed rules. (2) A multi-source correlation pipeline that groups information about the same real-world incident from different APIs. (3) An AI-augmented extraction and enrichment system for unstructured text from WHO, GDELT, and DDG News. |
| Q9 | Is this a rewrite or greenfield? | It's a clean rewrite replacing a legacy codebase. All domain knowledge has been distilled into a single contract document. |
| Q10 | What is the incident ID format? | `YYYYMMDD-CC-TTT` where YYYYMMDD is the report date, CC is ISO 3166-1 alpha-2 country code, and TTT is the disaster type code (e.g., EQ=Earthquake, FL=Flood, TC=Cyclone). |
| Q11 | What is the build order? | Four phases: (1) Foundation — types, classify, correlate, storage, all tests — pure Python, no I/O. (2) Adapters — fixture-driven, capture real API responses first. (3) AI — provider, extractor, classifier with DSPy signatures. (4) Pipeline — orchestration and end-to-end test. |
| Q12 | What dependencies does the project use? | Runtime: httpx>=0.28, dspy, ddgs>=9.14. Dev: flowr>=1.0.0, pytest-beehave>=0.2.0. |
| Q13 | What is the testing strategy? | Fixture-first: call each API once, save raw JSON, test against fixtures forever. No BaseAdapter — simple httpx calls. AI responses mocked in tests. Deterministic rules tested exhaustively (all country groups, all priority matrix cells, all overrides). Correlation tested with known multi-source scenarios. |

## Feature: Build Phases

| ID | Question | Answer |
|----|----------|--------|
| Q14 | What goes in Phase 1 (Foundation)? | types.py (RawRecord, IncidentBundle, Incident), classify.py (ClassifyEngine with all deterministic rules), correlate.py (record correlator), storage/jsonl.py (JSONLStore), storage/sqlite.py (SQLiteStore), and tests for all. Pure Python, no I/O. |
| Q15 | What goes in Phase 2 (Adapters)? | scripts/capture_fixtures.py to call each API once and save raw JSON, then run against real APIs, then gdacs.py, who.py, gdelt.py, news.py adapters plus tests — all fixture-driven. |
| Q16 | What goes in Phase 3 (AI)? | ai/provider.py (AIProvider protocol + DuckAIProvider), ai/extractor.py (batched extraction agent with DSPy signatures), ai/classifier.py (batched classification agent with DSPy signatures), integration tests with fixtures and mocked AI. |
| Q17 | What goes in Phase 4 (Pipeline)? | pipeline.py — orchestration: fetch → correlate → classify → search-more → AI enrich → store. End-to-end test. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reproducibility | Same fixtures produce same classified incidents, every time | Deterministic output | Must |
| QA2 | Testability | Every classification rule has a passing test with named fixture | 100% rule coverage | Must |

---

## Pain Points Identified

- Legacy codebase is unmaintainable and needs full rewrite
- Multiple data sources with varying levels of structure make consistent processing difficult
- Without deterministic classification, results are unpredictable and hard to verify

## Business Goals Identified

- Replace legacy codebase with clean, testable Python
- Automate multi-source disaster surveillance
- Provide queryable local incident data for researchers
- Ensure deterministic, reproducible classification every time

## Terms to Define (for glossary)

- DSR (Disaster Surveillance Reporter)
- Deterministic classification
- Incident ID format (YYYYMMDD-CC-TTT)
- ISO 3166-1 alpha-2
- Disaster type code (TTT)
- Fixture-first testing

## Action Items

- [ ] Confirm all three user personas are correctly captured
- [ ] Validate out-of-scope boundaries with stakeholders
- [ ] Verify disaster type code list (EQ, FL, TC, etc.)
