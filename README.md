# Disaster Surveillance Reporter

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

> Deterministic disaster surveillance pipeline. Fetches from GDACS, WHO DON, EONET, and
> GDELT. Classifies with pure-Python rules, enriches with optional pluggable AI,
> and stores in JSONL (default) or SQLite. No dashboard — pure backend processing.

**Requirements:** Python ≥ 3.14

## Quick Start

```bash
# Install
uv sync
source .venv/bin/activate

# Run the pipeline with defaults
# (GDACS + WHO + EONET, JSONL storage, no AI)
task run
```

Output is written to `./incidents/`. A single run fetches from all selected sources,
correlates records into incident bundles, classifies each deterministically, and
stores the result.

## Source Selection

| Source | Adapter | Auth | Reliability | Deterministic % |
|--------|---------|------|------------|-----------------|
| **GDACS** | GeoJSON REST (events4app) | none | highest | ~90 % |
| **WHO DON** | REST API (diseaseoutbreaknews) | none | high | ~30 % |
| **EONET** | NASA GeoJSON REST | none | medium | ~60 % |
| **GDELT** | DOC 2.0 ArtList | none | low | ~20 % |

Choose sources at run time with `--sources` or the `DSR_SOURCES` env var:

```bash
# Run with specific sources
task run -- --sources gdacs,who,eonet,gdelt
task run -- --sources gdacs,who

# Via env var
DSR_SOURCES=gdacs,who,eonet task run
```

GDELT is not included in the default source list because its API is frequently
unreachable. The source list is comma-separated; unknown sources print a warning
and are skipped.

## Storage Backends

Two storage backends implement the `StorageBackend` protocol. Select with
`DSR_STORAGE_BACKEND=jsonl` or `DSR_STORAGE_BACKEND=sqlite`.

### JSONL (default)

One JSON-line per stored bundle, date-partitioned by the bundle's classification
date.  Human-readable, grep-able, and append-only.  Atomic writes via temp-file +
rename prevent partial-line corruption.

```
incidents/
└── by-date/
    └── 2026-05-16/
        └── incidents.jsonl
```

```bash
# JSONL is the default — no config needed
task run

# Explicit
DSR_STORAGE_BACKEND=jsonl task run
```

The pipeline uses *upsert* semantics: a bundle already in storage receives an
updated `last_updated` timestamp when new data is found; a bundle with no new
data is a no-op and is not written again.

### SQLite

A single SQLite database file at `<output-dir>/incidents.db`.  Stores bundles
as JSON blobs in an `incidents` table keyed by `incident_id`.  Per-bundle
transactions ensure failure isolation.

```bash
DSR_STORAGE_BACKEND=sqlite task run
```

Query the database with any SQLite tool:

```bash
sqlite3 ./incidents/incidents.db "SELECT incident_id FROM incidents LIMIT 10"
```

## AI Provider

AI enrichment fills in missing fields (country, disaster type, estimated impact)
and generates human-readable summaries.  It is **optional** — the pipeline runs
fully deterministically with `DSR_AI_PROVIDER=none` (the default).

| Provider | Description | Auth |
|----------|------------|------|
| `none` (default) | Deterministic-only classification. No AI calls. | — |
| `ollama` | Local Ollama server (`http://localhost:11434`). Models: `llama3.2`, `mistral`. | none |
| `opencode` | [opencode serve][opencode-serve] REST API. Session-managed. | password |
| `gemini` | Google Gemini API (`generativelanguage.googleapis.com`). | API key |
| `openai` | OpenAI API (`api.openai.com/v1/chat/completions`). | API key |

[opencode-serve]: https://opencode.ai/docs/opencode-serve

```bash
# Deterministic only (default)
task run

# Local Ollama
DSR_AI_PROVIDER=ollama task run

# opencode serve
DSR_AI_PROVIDER=opencode OPENCODE_SERVER_PASSWORD=abc123 task run

# Gemini
DSR_AI_PROVIDER=gemini DSR_AI_API_KEY=your-key task run

# OpenAI
DSR_AI_PROVIDER=openai DSR_AI_API_KEY=your-key task run
```

With an AI provider enabled, the pipeline runs ExtractorAgent (country, type,
estimates from raw records) and ClassifierAgent (summary, rationale, override
detection).  Batches of ≤10 bundles per AI call.  Rate limits trigger
exponential backoff (15 s → 30 s → 60 s, max 3 retries).  Mid-batch AI failure
preserves already-processed bundles.

## Pipeline Phases

The pipeline executes nine sequential states per
[pipeline-flow v4][pipeline-flow].  Stale bundles (>7 days since last update)
are removed at the active-status check.  Non-reportable bundles exit early from
the classify step, skipping expensive search and AI steps.

| Step | State | What Happens |
|------|-------|-------------|
| **A** | Fetch | Calls every configured adapter; each returns `list[RawRecord]` and never raises. |
| **B** | Source Pre-filter | Discards records whose `source_fingerprint` is already in storage. |
| **C** | Correlate | Groups records into `IncidentBundle`s using date proximity (±1 day), ISO 3166-1 alpha-2 country overlap, and title similarity (`difflib.SequenceMatcher` ratio ≥ 0.6). |
| **D** | Classify | Deterministic: assigns country group (A/B/C), incident level (1–4), priority (HIGH/MED/LOW), `should_report`, and initial overrides (O2 multi-regional, O4 environmental, O6 Singapore/SRC). **Non-reportable bundles exit here** → stored immediately. |
| **E** | Active-Status Check | For each *reportable* bundle: NEW → proceed; ACTIVE (≤7 d) → merge stored fingerprints + proceed; STALE (>7 d) → removed. |
| **F** | Supplementary Search | DDG News search for active, reportable bundles with unknown country or type. |
| **G** | AI Enrichment | ExtractorAgent extracts fields → re-classify with new fields → ClassifierAgent generates summary + detects O1/O3/O5 override flags. Skipped when `DSR_AI_PROVIDER=none`. |
| **H** | Override Re-evaluation | Applies post-enrichment overrides (O1 humanitarian crisis, O3 likely development, O5 forecast). Level bumps compound (max +2). |
| **I** | Store (upsert) | NEW → insert. Existing + new fingerprints → update and reset `last_updated`. Existing + no new fingerprints → no-op. |

[pipeline-flow]: .flowr/flows/app/pipeline-flow.yaml

## Classification

All classification is **deterministic** — no AI is used for this step.

### Incident Levels

| Level | Label | Indicators |
|-------|-------|-----------|
| **4** | Critical | International assistance requested, ≥50 deaths, humanitarian crisis declared |
| **3** | Major | ≥20 deaths, frequent media coverage |
| **2** | Significant | 5–20 deaths, multiple source coverage |
| **1** | Minor | 0–5 deaths, local coverage only |

### Country Groups

| Group | Region | Example |
|-------|--------|---------|
| **A** | Asia-Pacific | Philippines, Indonesia, Japan, Malaysia |
| **B** | Asia-Pacific 2 + Middle East + North Africa | Australia, Iran, Egypt |
| **C** | Rest of world | France, Brazil, any unknown |

### Priority Matrix

| Level × Group | A | B | C |
|---------------|---|---|---|
| **4 (Critical)** | HIGH, report | HIGH, report | HIGH, report |
| **3 (Major)** | HIGH, report | MED, report | MED, report |
| **2 (Significant)** | MED, report | MED, report | LOW, skip |
| **1 (Minor)** | MED, report | LOW, skip | LOW, skip |

### Override Flags

| Flag | Description | Trigger | Phase |
|------|------------|---------|-------|
| **O1** | Humanitarian Crisis | AI-detected from record text | Post-enrichment |
| **O2** | Multi-Regional | GDACS `affectedcountries` > 1 | Initial |
| **O3** | Likely Development | AI-detected from record text | Post-enrichment |
| **O4** | Environmental | `WF`, `DR`, or `FL` type in Group A | Initial |
| **O5** | Forecast / Early Warning | GDACS `istemporary` = true | Post-enrichment |
| **O6** | Singapore / SRC | Keyword match in record text | Initial |

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DSR_SOURCES` | Comma-separated source adapters | `gdacs,who,eonet` |
| `DSR_OUTPUT_DIR` | Root directory for stored incidents | `./incidents` |
| `DSR_STORAGE_BACKEND` | `jsonl` or `sqlite` | `jsonl` |
| `DSR_AI_PROVIDER` | `ollama`, `opencode`, `gemini`, `openai`, `none` | `none` |
| `DSR_AI_API_KEY` | API key for Gemini or OpenAI | — |
| `OPENCODE_BASE_URL` | opencode serve base URL | `http://localhost:4096` |
| `OPENCODE_SERVER_PASSWORD` | opencode serve basic-auth password | — |
| `OPENCODE_SESSION_TIMEOUT` | opencode HTTP request timeout (seconds) | `120` |

## Development

### Run Tests

```bash
task test          # full suite (160 BDD tests)
task test-fast     # quick run, no coverage
```

### Lint & Format

```bash
ruff check .       # functional lint (bugs, security, complexity)
ruff format .      # auto-format
task conventions   # full lint including naming, docstrings
```

### Flowr Workflow

The project uses [flowr][flowr] for spec-driven development.  Key flows:

```bash
flowr validate                     # validate all flow definitions
flowr states main-flow             # list all states in the main flow
flowr mermaid .flowr/flows/app/pipeline-flow.yaml  # export pipeline diagram
flowr session list                 # list session state
```

[flowr]: https://pypi.org/project/flowr/

### Project Structure

```
disaster_surveillance_reporter/
├── adapters/          # Source adapters (GDACS, WHO, EONET, GDELT, DDG News)
├── ai/                # AI provider, ExtractorAgent, ClassifierAgent
├── classify/          # Classification engine (ClassifyEngine, rules, priority matrix)
├── correlation/       # Union-Find correlator (date, country, title matching)
├── pipeline/          # 9-step pipeline orchestrator
├── storage/           # JSONLStore, SQLiteStore, StorageBackend protocol
├── cli.py             # CLI entry point (argparse)
└── types.py           # RawRecord, IncidentBundle, Incident
```

## Data Model

| Type | Description |
|------|------------|
| **RawRecord** | Atomic unit from any source: `source_name`, `fetched_at`, `raw_fields` (untouched API response). |
| **IncidentBundle** | Groups correlated RawRecords for one real-world incident. Carries classification, AI fields, lifecycle timestamps, and source fingerprints. Identified by `incident_id` (`YYYYMMDD-CC-TTT`). |
| **Incident** | Flattened query result for storage queries. No `raw_records` — carries `source_names`, `source_urls`, and aggregated fields. |

Incident IDs are **source-stable**: the date component comes from source-provided
dates (GDACS `fromdate`, WHO `PublicationDate`, etc.), not from pipeline run
time.  The same article fetched on different days produces the same ID.

## License

MIT — see [LICENSE](LICENSE).

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/nullhack/src-disaster-awareness.svg?style=for-the-badge
[contributors-url]: https://github.com/nullhack/src-disaster-awareness/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/nullhack/src-disaster-awareness.svg?style=for-the-badge
[forks-url]: https://github.com/nullhack/src-disaster-awareness/network/members
[stars-shield]: https://img.shields.io/github/stars/nullhack/src-disaster-awareness.svg?style=for-the-badge
[stars-url]: https://github.com/nullhack/src-disaster-awareness/stargazers
[issues-shield]: https://img.shields.io/github/issues/nullhack/src-disaster-awareness.svg?style=for-the-badge
[issues-url]: https://github.com/nullhack/src-disaster-awareness/issues
[license-shield]: https://img.shields.io/badge/license-MIT-green?style=for-the-badge
[license-url]: https://github.com/nullhack/src-disaster-awareness/blob/main/LICENSE
