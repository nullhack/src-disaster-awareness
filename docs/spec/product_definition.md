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

## Deployment

### Runtime Model

DSR is a **CLI tool** executed as a scheduled batch process. There is no daemon, no web server, and no persistent process.

**Execution:** `dsr-pipeline` CLI command (entry point defined in `pyproject.toml`). Each invocation runs the full 7-step pipeline once and exits.

**Scheduling:** `cron` (Linux) or Task Scheduler (Windows). Recommended interval: every 6 hours. The pipeline is idempotent — duplicate runs produce no duplicate storage entries (dedup by `incident_id`).

**Data location:** Local filesystem under `./incidents/`. JSONL files at `incidents/by-date/YYYY-MM-DD/incidents.jsonl`. SQLite file at `incidents/dsr.db` (if selected). All paths relative to the working directory at invocation time.

**Configuration (environment variables):**

| Variable | Purpose | Default |
|----------|---------|---------|
| `DSR_AI_PROVIDER` | AI backend: `ollama`, `gemini`, `openai`, or `none` | `none` |
| `DSR_AI_MODEL` | Model name for selected provider | Provider-specific |
| `DSR_AI_API_KEY` | API key for Gemini/OpenAI (not needed for Ollama/none) | — |
| `DSR_AI_BASE_URL` | Override base URL for AI provider (e.g., custom Ollama host) | Provider-specific |
| `DSR_STORAGE_BACKEND` | Storage: `jsonl` or `sqlite` | `jsonl` |
| `DSR_STORAGE_PATH` | Base directory for storage | `./incidents` |
| `DSR_LOG_LEVEL` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

**Exit codes:** 0 = success (all steps completed, including partial AI failures), 1 = fatal error (storage completely unavailable, configuration invalid).

**Single-process, single-threaded.** No multiprocessing, no async, no distributed execution. The pipeline processes bundles sequentially within each step.

### Pipeline Execution Flow

```
dsr-pipeline
  ├─ Step 1: Fetch (GDACS, WHO, GDELT in parallel via httpx)
  ├─ Step 2: Correlate (group into IncidentBundles)
  ├─ Step 3: Initial Classify (deterministic, no I/O)
  ├─ Step 4: Supplementary Search (DDG News for bundles missing fields)
  ├─ Step 5: AI Enrich (Extractor → re-classify → Classifier, batched)
  ├─ Step 6: Override Re-evaluation (deterministic, no I/O)
  └─ Step 7: Store (JSONL or SQLite, atomic writes)
```

Step 1 uses three independent HTTP requests (no parallelism framework — sequential or `httpx` connection pooling). Step 5 is the only step with variable latency (AI calls). All other steps are deterministic and fast.

## Quality Attributes

| Priority | Attribute | Scenario | Target | Measurement |
|----------|-----------|----------|--------|-------------|
| 1 | Reproducibility | Same fixtures → same classified incidents, every time | Byte-identical JSON output from identical input fixtures across repeated runs | Deterministic: no randomness, no timestamps in output, no floating-point drift |
| 2 | Reliability | Any single source API down → other sources unaffected, no data loss | Empty list from failed adapter, pipeline continues with available sources | Each adapter returns `[]` on failure; never raises |
| 3 | Reliability | AI timeout/failure → incident stored without enrichment | `ai_enriched=False`, all AI fields None, bundle persisted to storage | Bundle present in storage with `ai_enriched=False` after run |
| 4 | Testability | Every classification rule has a passing test with named fixture | 100% rule coverage: all 66 countries (25+41), all 12 priority matrix cells, all 6 overrides, all 4 source level derivations | `task test-coverage` shows 100% for classify.py, correlate.py |
| 5 | Performance | 50 incidents classified and stored in < 5 seconds (excluding AI) | Pure Python path (Steps 2–3, 6–7) completes in < 5s for 50 bundles | Measured by `pytest` performance marker; ~65ms estimated |
| 6 | Performance | Full batch with AI in < 5 minutes | ~6 AI calls × 15s rate limit ≈ 90s for 50 incidents | Measured by E2E test with mocked AI latency |
| 7 | Maintainability | Adding a new source adapter requires zero changes to core pipeline | New adapter implements `SourceAdapter` protocol, registered in config | No existing files modified when adding adapter |
| 8 | Observability | Every pipeline run produces a structured log of step outcomes | Step-level timing, source fetch counts, classification distribution, storage count | `structlog` JSON output to stderr at `INFO` level |

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.14+ | Type hints (PEP 695), dataclasses, pattern matching; team expertise |
| Architecture | Sequential pipeline (monolith) | 7 ordered steps with data dependencies; single-process CLI; no concurrency needed. See ADR 1. |
| HTTP Client | httpx >= 0.28 | Modern sync HTTP client; connection pooling; timeout control; used by all adapters |
| AI Framework | DSPy | Typed signatures for structured LLM output; prompt optimization; composable modules. See ADR 3. |
| News Search | ddgs >= 9.14.2 | DuckDuckGo News via `DDGS.news()`; supplementary context for sparse bundles |
| Primary Storage | JSONL (date-partitioned) | Human-readable; append-only; grep-able; zero-config; atomic writes. See ADR 2. |
| Alt. Storage | SQLite (stdlib `sqlite3`) | Same `StorageBackend` protocol; efficient queries for large datasets |
| Logging | structlog | Structured JSON output; step-level timing; filterable by log level |
| CLI | argparse (stdlib) | Single entry point `dsr-pipeline`; environment variable config; no framework needed |
| Correlation | difflib.SequenceMatcher (stdlib) | Title similarity ratio; deterministic; no external dependency. See ADR 4. |
| Data Shapes | dataclasses (stdlib) | RawRecord, IncidentBundle, Incident; no validation framework overhead |

### Key Design Principles

1. **Minimal runtime dependencies** — 4 packages (httpx, dspy, ddgs, structlog) plus stdlib
2. **No web framework** — CLI tool, not a server
3. **No async** — single-process, single-threaded, synchronous execution
4. **No ORM** — direct JSONL/SQLite via adapter pattern
5. **No template engine** — no HTML output
6. **Stdlib-first** — difflib for similarity, sqlite3 for alt storage, argparse for CLI, json for serialization

## Dependencies

### Runtime

| Package | Version | Purpose | ADR |
|---------|---------|---------|-----|
| httpx | >= 0.28 | HTTP client for GDACS GeoJSON, WHO OData, GDELT DOC APIs. Connection pooling, timeout control, retry support. | — |
| dspy | * | Structured LLM programming. Typed signatures for Extractor and Classifier agents. Provider-agnostic LM configuration. | ADR 3 |
| ddgs | >= 9.14.2 | DuckDuckGo News search via `DDGS.news()`. Supplementary context when primary sources lack country/type data. | — |
| structlog | * | Structured JSON logging. Step-level timing, source counts, classification distribution to stderr. | — |

### Development

| Package | Version | Purpose |
|---------|---------|---------|
| flowr | >= 1.0.0 | Flow state machine management for project workflow |
| pytest-beehave | >= 0.2.0 | BDD test framework (Given/When/Then) |
| pytest | * | Test runner |
| ruff | * | Linting and formatting |
| pyright | * | Static type checking |

### Standard Library (no install)

| Module | Purpose |
|--------|---------|
| `dataclasses` | RawRecord, IncidentBundle, Incident data shapes |
| `json` | JSONL serialization/deserialization |
| `sqlite3` | SQLite storage backend |
| `difflib` | SequenceMatcher for title similarity (correlation) |
| `re` | Keyword scanning for WHO/GDELT level derivation |
| `pathlib` | File path handling for JSONL storage |
| `datetime` | Timestamps, date parsing, date partitioning |
| `os` | Atomic file writes (temp file + rename) |
| `typing` | Protocol definitions (SourceAdapter, NewsSearcher, AIProvider, StorageBackend) |
| `argparse` | CLI entry point |
| `logging` | Fallback logging (structlog primary) |
| `tempfile` | Atomic write temporary files |
| `collections` | Data grouping utilities |
