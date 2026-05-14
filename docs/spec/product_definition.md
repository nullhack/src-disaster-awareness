# Product Definition: Disaster Surveillance Reporter

> **Status:** BASELINED (2026-05-14)
> Source of truth: `docs/spec/contract.md`

---

## What Disaster Surveillance Reporter IS

- A deterministic classification engine that assigns incident levels (1–4), priorities (HIGH/MED/LOW), and country groups (A/B/C) using fixed Python rules — no AI for classification, ever.
- A multi-source correlation pipeline that groups information about the same real-world incident from different APIs (GDACS, WHO DON, GDELT) into unified bundles, supplementing with DuckDuckGo News search when context is sparse.
- An AI-augmented extraction and enrichment system for unstructured text (WHO, GDELT, DDG News), using a pluggable AIProvider (Ollama, Gemini, or OpenAI) via DSPy for structured output, operating on batched `IncidentBundle`s.

## What Disaster Surveillance Reporter IS NOT

- A dashboard or web UI — backend pipeline only.
- A real-time alerting system — runs as a scheduled batch CLI tool.
- A replacement for human analyst judgment — provides deterministic triage and AI enrichment for analyst review.
- An AI classifier — AI only extracts fields (country, type, casualties) and enriches (summaries, override detection); classification is always deterministic.

## Why does this exist

The legacy codebase was unmaintainable. This clean rewrite automates disaster incident surveillance by aggregating data from multiple free public sources, removing the need for manual monitoring. Deterministic classification ensures reproducibility: the same raw data always produces the same classification, enabling audit and regression testing. AI enrichment adds value (summaries, casualty estimates, override detection) but never blocks storage — incidents are persisted even when AI fails.

## Users

| User | Need |
|------|------|
| Backend Developers | Clean, testable Python code with deterministic behavior, protocol-based adapters, and exhaustive test coverage |
| Ops Teams | A CLI tool that runs on a schedule, fetches from 3 primary sources, correlates, classifies, enriches, and stores results locally |
| Researchers | Queryable local incident data (JSONL or SQLite) for analysis, filterable by date range, country group, priority, disaster type, and source |

## Out of Scope

- Dashboard or web UI
- Real-time push notifications
- Account-based API sources (ReliefWeb, HealthMap)
- AI-based classification (AI only extracts and enriches, never classifies)
- Email sending (future consideration only)
- Multi-process or distributed execution

## Delivery Order

### Phase 1 — Foundation (pure Python, no I/O)

1. `types.py` — `RawRecord`, `IncidentBundle`, `Incident` dataclasses
2. `classify.py` — `ClassifyEngine` with all deterministic rules (country groups, priority matrix, level derivation, overrides O1–O6)
3. `correlate.py` — Record correlator (date proximity + country overlap + title similarity)
4. `storage/jsonl.py` — JSONLStore (date-partitioned, append-only, dedup by incident_id)
5. `storage/sqlite.py` — SQLiteStore (same `StorageBackend` protocol)
6. Tests for all of the above

### Phase 2 — Adapters (fixture-driven)

7. `scripts/capture_fixtures.py` — call each API once, save raw JSON
8. Run capture fixtures against real APIs
9. `adapters/gdacs.py` + tests (GeoJSON REST → `list[RawRecord]`)
10. `adapters/who.py` + tests (OData REST → `list[RawRecord]`)
11. `adapters/gdelt.py` + tests (DOC API → `list[RawRecord]`)
12. `adapters/news.py` + tests (DDG News search → `list[RawRecord]`)

### Phase 3 — AI (from day 1)

13. `ai/provider.py` — `AIProvider` protocol + pluggable backends (OllamaProvider, GeminiProvider, OpenAIProvider)
14. `ai/extractor.py` — batched extraction agent with DSPy signatures
15. `ai/classifier.py` — batched classification agent with DSPy signatures
16. Integration tests (fixtures + mocked AI responses)

### Phase 4 — Pipeline

17. `pipeline.py` — fetch → correlate → classify → search-more → AI enrich → store
18. End-to-end test

## Quality Attributes

| Priority | Attribute | Scenario | Target |
|----------|-----------|----------|--------|
| 1 | Reproducibility | Same fixtures → same classified incidents, every time | Deterministic output, no randomness |
| 2 | Reliability | Any source API down → other sources unaffected, no data loss | Empty list from failed adapter, pipeline continues |
| 3 | Reliability | AI timeout/failure → incident stored without enrichment | `ai_enriched=False`, all AI fields None, bundle persisted |
| 4 | Testability | Every classification rule has a passing test with named fixture | 100% rule coverage: all country groups, all priority matrix cells, all overrides |
| 5 | Performance | 50 incidents classified and stored in < 5 seconds (excluding AI) | Pure Python path fast |
| 6 | Performance | Full batch with AI in < 5 minutes | ~6 AI calls × 15s rate limit ≈ 1.5 min for 50 incidents |
