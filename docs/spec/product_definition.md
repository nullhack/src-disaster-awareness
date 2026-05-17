# Product Definition: Disaster Surveillance Reporter

> **Status:** BASELINED (2026-05-14)
> Source of truth: `docs/spec/contract.md`

---

## What Disaster Surveillance Reporter IS

- A deterministic classification engine that assigns incident levels (1–4), priorities (HIGH/MED/LOW), and country groups (A/B/C) using fixed Python rules — no AI for classification, ever. Source selection (GDACS, WHO, GDELT, EONET) is CLI-driven via the `dsr-pipeline` entry point.
- A multi-source correlation pipeline that groups information about the same real-world incident from different APIs (GDACS, WHO DON, EONET) into unified bundles, supplementing with DuckDuckGo News search when context is sparse.
- An AI-augmented extraction and enrichment system for unstructured text (WHO, GDELT, DDG News), using a pluggable AIProvider (Ollama, Gemini, OpenAI, OpencodeProvider, or DuckAI via p2d-duck) via DSPy for structured output, operating on batched `IncidentBundle`s.

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

1. [DONE] `domain_types.py` — `RawRecord`, `IncidentBundle`, `Incident` dataclasses
2. [DONE] `classify.py` — `ClassifyEngine` with all deterministic rules (24 Group A + 46+ Group B countries, priority matrix, level derivation, overrides O1–O6)
3. [DONE] `correlate.py` — Record correlator (date proximity + ISO-normalized country match + title similarity via SequenceMatcher)
4. [DONE] `storage/jsonl.py` — JSONLStore (date-partitioned, atomic temp-file+rename, dedup by incident_id)
5. [DONE] `storage/sqlite.py` — SQLiteStore (same `StorageBackend` protocol)
6. [DONE] Tests for all of the above (fixture-based, deterministic)

### Phase 2 — Adapters (fixture-driven)

7. [DONE] `scripts/capture_fixtures.py` — call each API once, save raw JSON
8. [DONE] Run capture fixtures against real APIs
9. [DONE] `adapters/gdacs.py` + tests (GeoJSON REST → `list[RawRecord]`)
10. [DONE] `adapters/who.py` + tests (WHO DON REST → `list[RawRecord]`)
11. [DONE] `adapters/gdelt.py` + tests (GDELT DOC ArtList API → `list[RawRecord]`; gracefully returns [] when unreachable)
12. [ ] `adapters/eonet.py` + tests (NASA EONET v3 REST API → `list[RawRecord]`; zero-auth, 13 categories, global event tracking)
13. [DONE] `adapters/news.py` + tests (DDG News supplementary search via ddgs → `list[RawRecord]`)

### Phase 3 — AI (from day 1)

14. [DONE] `ai/provider.py` — `AIProvider` protocol + pluggable backends (Ollama, Gemini, OpenAI, Opencode, DuckAI)
15. [DONE] `ai/extractor.py` — batched extraction agent
16. [DONE] `ai/classifier.py` — batched classification agent
17. [DONE] Integration tests (fixtures + mocked AI responses)

### Phase 4 — Pipeline

18. [DONE] `pipeline.py` — 9-state orchestration per pipeline-flow v4
19. [DONE] End-to-end test

### Phase 5 — Incident Lifecycle

20. [DONE] Feature A — source-stable IDs, source_fingerprints, upsert
21. [DONE] Feature B — lifecycle gating, pre-filter, active-check, DDG gate, stale skip

## Deployment

### Runtime Model

DSR is a **CLI tool** executed as a scheduled batch process. There is no daemon, no web server, and no persistent process.

**Execution:** `dsr-pipeline` CLI command (entry point defined in `pyproject.toml`). Each invocation runs the pipeline once and exits.

**Scheduling:** `cron` (Linux) or Task Scheduler (Windows). Recommended interval: every 6 hours. The pipeline is idempotent — duplicate runs produce no duplicate storage entries (dedup by `incident_id`).

**Data location:** Local filesystem under `./incidents/`. JSONL files at `incidents/by-date/YYYY-MM-DD/incidents.jsonl`. SQLite file at `incidents/dsr.db` (if selected). All paths relative to the working directory at invocation time.

**Configuration (environment variables):**

| Variable | Purpose | Default |
|----------|---------|---------|
| `DSR_AI_PROVIDER` | AI backend: `ollama`, `gemini`, `openai`, `opencode`, `duckai`, or `none` | `duckai` |
| `DSR_AI_MODEL` | Model name for selected provider | Provider-specific |
| `DSR_AI_API_KEY` | API key for Gemini/OpenAI (not needed for Ollama/opencode/none) | — |
| `DSR_AI_BASE_URL` | Override base URL for AI provider (e.g., custom Ollama host) | Provider-specific |
| `OPENCODE_BASE_URL` | Base URL for opencode serve (opencode provider only) | `http://127.0.0.1:4096` |
| `OPENCODE_SERVER_PASSWORD` | Password for opencode serve basic auth (required if provider=opencode) | — |
| `OPENCODE_SESSION_TIMEOUT` | HTTP request timeout in seconds for opencode | 120 |
| `DSR_SOURCES` | Comma-separated source list: `gdacs,who,eonet,gdelt` | `gdacs,who,eonet` |
| `DSR_STORAGE_BACKEND` | Storage: `jsonl` or `sqlite` | `jsonl` |
| `DSR_OUTPUT_DIR` | Base directory for storage | `./incidents` |
| `DSR_LOG_LEVEL` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

**Exit codes:** 0 = success (all steps completed, including partial AI failures), 1 = fatal error (storage completely unavailable, configuration invalid).

**Single-process, single-threaded.** No multiprocessing, no async, no distributed execution. The pipeline processes bundles sequentially within each state.

### Pipeline Execution Flow

State ordering is configured in `pipeline-flow.yaml`; the `dsr-pipeline` entry point reads this file to determine the execution sequence.

```
Fetch → Source Pre-filter → Correlate → Classify →
  ├─ reportable → Active-Check → Search → AI Enrich → Override Re-eval → Store (upsert)
  └─ not-reportable → Store (as-is)
```

AI enrichment is the only step with variable latency (AI calls). All other steps are deterministic and fast.

## Quality Attributes

| Priority | Attribute | Scenario | Target | Measurement |
|----------|-----------|----------|--------|-------------|
| 1 | Reproducibility | Same fixtures → same classified incidents, every time | Byte-identical JSON output from identical input fixtures across repeated runs | Deterministic: no randomness, no timestamps in output, no floating-point drift |
| 2 | Reliability | Any single source API down → other sources unaffected, no data loss | Empty list from failed adapter, pipeline continues with available sources | Each adapter returns `[]` on failure; never raises |
| 3 | Reliability | AI timeout/failure → incident stored without enrichment | `ai_enriched=False`, all AI fields None, bundle persisted to storage | Bundle present in storage with `ai_enriched=False` after run |
| 4 | Testability | Every classification rule has a passing test with named fixture | 100% rule coverage: all 70+ countries (24+46+), all 12 priority matrix cells, all 6 overrides, all 4 source level derivations | `task test-coverage` shows 100% for classify.py, correlate.py |
| 5 | Performance | 50 incidents classified and stored in < 5 seconds (excluding AI) | Pure Python path (Steps 2–3, 6–7) completes in < 5s for 50 bundles | Measured by `pytest` performance marker; ~65ms estimated |
| 6 | Performance | Full batch with AI in < 5 minutes | ~6 AI calls × 15s rate limit ≈ 90s for 50 incidents | Measured by E2E test with mocked AI latency |
| 7 | Maintainability | Adding a new source adapter requires zero changes to core pipeline | New adapter implements `SourceAdapter` protocol, registered in config | No existing files modified when adding adapter |
| 8 | Observability | Every pipeline run produces a structured log of step outcomes | Step-level timing, source fetch counts, classification distribution, storage count | `structlog` JSON output to stderr at `INFO` level |
| 9 | Efficiency | Pipeline with no new data completes all steps in under 5s | Source pre-filter discards all stale/seen records; active-status check skips stale bundles; pipeline exits fast | Measured by E2E test with pre-populated storage and no new source data |
| 10 | Data Integrity | Same source record never stored in two different bundles | Source fingerprint dedup via `exists_by_source_fingerprint`; upsert merges rather than duplicates | `pytest` integration: inject duplicate fingerprint, verify single stored result |

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.14+ | Type hints (PEP 695), dataclasses, pattern matching; team expertise |
| Architecture | Sequential pipeline (monolith) | 9 ordered states with data dependencies; single-process CLI; no concurrency needed. See ADR 1. |
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

1. **Minimal runtime dependencies** — 5 packages (httpx, dspy, ddgs, structlog, p2d-duck) plus stdlib
2. **No web framework** — CLI tool, not a server
3. **No async** — single-process, single-threaded, synchronous execution
4. **No ORM** — direct JSONL/SQLite via adapter pattern
5. **No template engine** — no HTML output
6. **Stdlib-first** — difflib for similarity, sqlite3 for alt storage, argparse for CLI, json for serialization

## Dependencies

### Runtime

| Package | Version | Purpose | ADR |
|---------|---------|---------|-----|
| httpx | >= 0.28 | HTTP client for GDACS GeoJSON, WHO DON REST, GDELT DOC APIs. Connection pooling, timeout control, retry support. | — |
| dspy | * | Structured LLM programming. Typed signatures for Extractor and Classifier agents. Provider-agnostic LM configuration. | ADR 3 |
| ddgs | >= 9.14.2 | DuckDuckGo News search via `DDGS.news()`. Supplementary context when primary sources lack country/type data. | — |
| pycountry | >= 24 | ISO 3166-1 alpha-2 country code lookups. Used by correlation for country normalization (name → code) and classification for country group assignment. | — |
| structlog | * | Structured JSON logging. Step-level timing, source counts, classification distribution to stderr. | — |
| p2d-duck | >= 1.2.0 | Free DuckDuckGo AI Chat client. Zero-auth, no API key. Solves JS challenge via embedded mini-racer V8 engine. Default AI backend for DSR. | — |

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
