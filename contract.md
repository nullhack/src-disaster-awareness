# Disaster Surveillance Reporter — Initial Contract

> Living document. Last updated: 2026-05-14.

## 1. Purpose

Disaster Surveillance Reporter (DSR) is a backend pipeline that fetches incident data from free public APIs, correlates information across sources, classifies deterministically, enriches with AI and supplementary news search, and stores locally. It replaces the legacy codebase with a clean rewrite.

### 1.1 What It IS

- A deterministic classification engine that assigns incident levels, priorities, and country groups using fixed rules
- A multi-source correlation pipeline that groups information about the same real-world incident from different APIs
- An AI-augmented extraction and enrichment system for unstructured text (WHO, GDELT, DDG News)

### 1.2 What It IS NOT

- A dashboard or web UI
- A real-time alerting system
- A replacement for human analyst judgment

## 2. Users

| User | Need |
|------|------|
| Backend Developers | Clean, testable Python code with deterministic behavior |
| Ops Teams | A CLI tool that runs on a schedule and produces reports |
| Researchers | Queryable local incident data for analysis |

## 3. Data Sources

### 3.1 Primary Sources (3, all free, zero-auth)

| Source | API Format | Determinism | Notes |
|--------|-----------|-------------|-------|
| GDACS | GeoJSON REST | ~90% | alertlevel, iso3, eventtype, coordinates — highly structured |
| WHO DON | OData REST | ~30% | title, date, url, HTML content — country/type/level need extraction |
| GDELT | DOC API | ~20% | title, url, tone, themes, seendate — country/type need extraction |

### 3.2 Supplementary Source

| Source | API Format | Purpose |
|--------|-----------|---------|
| DuckDuckGo News | `ddgs` package `news()` | Search for additional news articles about specific incidents |

DDG News returns per result: `{date, title, body, url, source}`. Used after initial fetch to enrich incidents that need more context. Supports multiple backends (bing, duckduckgo, yahoo) with automatic fallback.

### 3.3 Uncertainty Principle

We can't be certain about exact field availability from any source until we call the APIs and inspect real responses. All raw data is preserved verbatim in `RawRecord.raw_fields`. Classification and AI extraction work with whatever fields are available, falling back gracefully when fields are missing. **Every adapter must capture the full raw response unmodified.**

## 4. Architecture

```
┌──────────────┐
│ GDACS (GeoJSON)│──┐
│ WHO (OData)   │──┤   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐
│ GDELT (DOC)   │──┴──→│  Correlator      │──→│ ClassifyEngine   │──→│ Storage      │
└──────────────┘       │  group by         │   │ (deterministic)  │   │ (JSONL or    │
                       │  incident         │   │                  │   │  SQLite)     │
┌──────────────┐       └──────┬───────────┘   └───────┬──────────┘   └──────────────┘
│ DDG News     │──────→       │                       │
│ (supplementary)│             │              ┌───────▼──────────┐
└──────────────┘              │              │  AI Enrichment   │
                              │              │  (batched calls) │
                              └─────────────→│  duck.ai + dspy  │
                                             └──────────────────┘
```

Pipeline flow per batch:

1. **Fetch** all 3 primary sources → `list[RawRecord]`
2. **Correlate** records about the same real-world incident into `IncidentBundle`s
   - Match by: date proximity, country overlap, title similarity
   - Single-source records become bundles with one record
3. **Supplementary search**: For bundles needing more context (missing country, low-structure source), search DDG News → append results to bundle
4. **Classify** deterministically → assign level, priority, country_group, overrides
   - Uses best available data from any record in the bundle
   - Marks fields that need AI extraction
5. **AI Enrichment** (batched):
   - Extractor batch: bundles needing country/type extraction from text
   - Classifier batch: reportable bundles for summaries + override detection
6. **Store** the complete `IncidentBundle` with all raw records and derived classification

## 5. Data Shapes

### RawRecord (atomic data unit from any source)

```python
@dataclass
class RawRecord:
    source_name: str        # "GDACS" | "WHO" | "GDELT" | "DDG-NEWS"
    fetched_at: datetime
    raw_fields: dict        # complete, untouched source-specific fields
```

No normalization at this layer. `raw_fields` contains the exact API response. We don't assume any field exists until we've seen real data.

Example `raw_fields` per source (subject to change after seeing real responses):

- **GDACS**: `{title, description, alertlevel, eventtype, iso3, latitude, longitude, ...}`
- **WHO**: `{title, url, date, content_html, ...}`
- **GDELT**: `{title, url, seendate, tone, themes, ...}`
- **DDG-NEWS**: `{date, title, body, url, source}`

### IncidentBundle (all information about one real-world incident)

```python
@dataclass
class IncidentBundle:
    incident_id: str                # YYYYMMDD-CC-TTT
    records: list[RawRecord]        # one or more raw records from any source
    # Classification (derived from records via rules + AI)
    country: str | None             # resolved from any record or AI
    country_code: str | None        # ISO 3166-1 alpha-2
    country_group: str | None       # "A" | "B" | "C"
    disaster_type: str | None
    incident_level: int | None      # 1-4
    priority: str | None            # "HIGH" | "MED" | "LOW"
    should_report: bool
    overrides: list[str]            # ["O1", "O3", ...]
    # AI enrichment
    summary: str | None
    rationale: str | None
    estimated_affected: int | None
    estimated_deaths: int | None
    ai_enriched: bool
    # Metadata
    classified_at: datetime | None
```

### Incident (final output for queries/reports)

```python
@dataclass
class Incident:
    incident_id: str
    source_names: list[str]         # all sources that contributed
    incident_name: str              # best title from available records
    country: str
    country_code: str
    country_group: str              # "A" | "B" | "C"
    disaster_type: str
    incident_level: int             # 1-4
    priority: str                   # "HIGH" | "MED" | "LOW"
    should_report: bool
    overrides: list[str]
    report_date: date
    source_urls: list[str]          # all source URLs
    summary: str | None
    rationale: str | None
    estimated_affected: int | None
    estimated_deaths: int | None
    ai_enriched: bool
    record_count: int               # how many raw records contributed
```

## 6. Protocols

### SourceAdapter (primary API fetcher)

```python
class SourceAdapter(Protocol):
    source_name: str

    def fetch(self, client: httpx.Client) -> list[RawRecord]:
        """Fetch current incidents from one API.
        
        Returns empty list on failure, never raises.
        Each RawRecord.raw_fields contains the complete, unmodified API response.
        """
        ...
```

Each adapter wraps a single API. No base class, no caching, no TTL — just httpx calls returning raw records.

### NewsSearcher (supplementary news search)

```python
class NewsSearcher(Protocol):
    def search(self, query: str, *, region: str = "wt-wt", timelimit: str | None = None, max_results: int = 5) -> list[RawRecord]:
        """Search news for supplementary context about an incident.
        
        Returns empty list on failure, never raises.
        Each RawRecord has source_name="DDG-NEWS".
        """
        ...
```

Wraps `ddgs.DDGS.news()`. Used to find additional articles about an incident when the primary sources don't provide enough context.

### AIProvider (abstract AI chat)

```python
class AIProvider(Protocol):
    def chat(self, prompt: str, *, model: str = "gpt-4o-mini") -> str:
        """Send a prompt, get a text response.
        
        Raises on unrecoverable failure (auth, network).
        Auto-retries on rate limits (HTTP 429).
        """
        ...
```

### StorageBackend (persistent storage)

```python
class StorageBackend(Protocol):
    def store(self, bundles: list[IncidentBundle]) -> int:
        """Store bundles. Returns count of new bundles stored (skips existing IDs).
        
        Stores the complete bundle including all raw records.
        """
        ...

    def query(self, *, date_from: date, date_to: date, **filters: Any) -> list[Incident]:
        """Query stored incidents by date range and optional filters.
        
        Filters: country_group, disaster_type, priority, should_report, source_name.
        Returns Incident (flattened view), not raw bundles.
        """
        ...

    def exists(self, incident_id: str) -> bool:
        """Check if an incident already exists (dedup check)."""
        ...
```

## 7. Deterministic Classification Rules

The classification engine works on `IncidentBundle.records`, trying each source's `raw_fields` in order of reliability (GDACS > WHO > GDELT > DDG-NEWS). It extracts whatever fields are available and falls back to AI for missing fields.

### 7.1 Country Groups

- **Group A** (25): Afghanistan, Bangladesh, Bhutan, Brunei, Cambodia, China, India, Indonesia, Japan, Laos, Malaysia, Maldives, Myanmar, Nepal, North Korea, Pakistan, Philippines, Singapore, South Korea, Sri Lanka, Taiwan, Thailand, Timor Leste, Vietnam
- **Group B** (41): Asia Pacific 2 (Australia, Fiji, etc.) + Middle East (Bahrain, Cyprus, Iran, Iraq, Jordan, Kuwait, Lebanon, Oman, Palestine, Israel, Qatar, Saudi Arabia, Syria, Turkey, UAE, Yemen) + North Africa (Algeria, Egypt, Morocco, Tunisia)
- **Group C**: rest of world

### 7.2 Priority Matrix

```
          Group A    Group B    Group C
Level 4  HIGH/✓    HIGH/✓     HIGH/✓
Level 3  HIGH/✓    MED/✓      MED/✓
Level 2  MED/✓     MED/✓      LOW/✗
Level 1  MED/✓     LOW/✗      LOW/✗
```

### 7.3 Level Derivation (source-specific)

Tries the most reliable available source first:

| Source | Rule |
|--------|------|
| GDACS | Green→1, Orange→3, Red→4 (+ severity bump for Group A) |
| WHO | Keyword scan: "pandemic"/"PHEIC"→4, "epidemic"/"widespread"→3, "cluster"/"cases reported"→2, "isolated case"→1, default→2 |
| GDELT | tone < -5→4, < -3→3, >= 0→1, else→2 |

### 7.4 Level Indicators

- **Level 4 (CRITICAL)**: intl assistance requested, 300K+ affected, 50+ deaths, multi-state, humanitarian crisis declared
- **Level 3 (MAJOR)**: 100K+ affected, 20-50 deaths, frequent media coverage, ongoing humanitarian crisis
- **Level 2 (SIGNIFICANT)**: <100K affected, 5-20 deaths, multiple source coverage, regional impact developing
- **Level 1 (MINOR)**: <50K affected, 0-5 deaths, local coverage only, contained impact

### 7.5 Overrides (O1–O6, from day 1)

| Override | Name | Method |
|----------|------|--------|
| O1 | Humanitarian Crisis | Keywords for GDACS, AI for WHO/GDELT |
| O2 | Multi-Regional | GDACS: structured `affectedcountries`; AI for others |
| O3 | Likely Development | AI-assisted text understanding |
| O4 | Environmental | Deterministic: type in {WF, DR, FL} + Group A |
| O5 | Forecast/Early Warning | GDACS: `istemporary`; AI for others |
| O6 | Singapore/SRC | Keyword: "Singapore", "SRC", "Red Cross" |

## 8. AI Strategy

### 8.1 Provider: DuckDuckGo AI via direct HTTP

- Free, no auth, no API key
- No external AI client library — calls DuckDuckGo's `duckchat/v1` API directly via httpx
- Models: gpt-4o-mini, claude-3-haiku, llama-3.3-70b, o3-mini, mistral-small
- Rate limit: ~1 request/15 seconds
- Two-step protocol:
  1. `GET https://duckduckgo.com/duckchat/v1/status` with `x-vqd-accept: 1` → returns `x-vqd-4` token
  2. `POST https://duckduckgo.com/duckchat/v1/chat` with `x-vqd-4` header + model + messages → SSE stream
- Auto-retry with backoff on rate limits (HTTP 429)

### 8.2 DSPy Integration

DSPy provides structured LLM programming. Used alongside direct duck.ai calls for:
- Typed output signatures (incident extraction, classification)
- Prompt optimization over time
- Composable AI modules

### 8.3 Batched Processing

Now operates on `IncidentBundle`s. AI receives ALL raw records in each bundle for full context.

- **Extractor batch**: bundles where country/disaster_type is still None after deterministic pass (~10/call)
  - DDG News results provide additional context when available
- **Classifier batch**: should_report=True bundles (~10/call)
  - AI generates summaries and detects overrides O1, O3, O5
- **Total**: ~6 calls × 15s = ~1.5 minutes per 50 incidents

### 8.4 AI Provider Implementation

```python
class DuckAIProvider:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._vqd: str | None = None

    def chat(self, prompt: str, *, model: str = "gpt-4o-mini") -> str:
        if not self._vqd:
            resp = self._client.get(
                "https://duckduckgo.com/duckchat/v1/status",
                headers={"x-vqd-accept": "1"},
            )
            self._vqd = resp.headers["x-vqd-4"]
        resp = self._client.post(
            "https://duckduckgo.com/duckchat/v1/chat",
            headers={"x-vqd-4": self._vqd},
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        )
        return self._parse_sse(resp)

    def _parse_sse(self, resp: httpx.Response) -> str:
        parts = []
        for line in resp.text.splitlines():
            if line.startswith("data: ") and line != "data: [DONE]":
                data = json.loads(line[6:])
                if "message" in data:
                    parts.append(data["message"])
        return "".join(parts)
```

### 8.5 Extractor Agent (batched)

Input: list of IncidentBundles with raw text records
Output: extracted country, disaster_type, estimated_affected, estimated_deaths per bundle

### 8.6 Classifier Agent (batched)

Input: list of classified IncidentBundles with should_report=True
Output: summary, humanitarian_crisis, likely_development, rationale per bundle

## 9. Storage

Adapter pattern with two backends:

- **JSONL** (default): append-only, date-partitioned files at `incidents/by-date/YYYY-MM-DD/incidents.jsonl`
- **SQLite**: alternative backend with same query interface

Both store the complete `IncidentBundle` including all raw records.

```python
class StorageBackend(Protocol):
    def store(self, bundles: list[IncidentBundle]) -> int:
        """Store bundles. Returns count of new bundles stored (skips existing IDs)."""
        ...

    def query(self, *, date_from: date, date_to: date, **filters: Any) -> list[Incident]:
        """Query stored incidents by date range and optional filters."""
        ...

    def exists(self, incident_id: str) -> bool:
        """Check if an incident already exists."""
        ...
```

Dedup by incident_id across both backends.

## 10. File Structure

```
disaster_surveillance_reporter/
├── __init__.py
├── types.py                    # RawRecord, IncidentBundle, Incident
├── classify.py                 # ClassifyEngine, country groups, priority matrix, overrides
├── correlate.py                # Group RawRecords into IncidentBundles
├── ai/
│   ├── __init__.py
│   ├── provider.py             # AIProvider protocol + DuckAIProvider
│   ├── extractor.py            # Extractor agent (batched)
│   └── classifier.py           # Classifier agent (batched)
├── adapters/
│   ├── __init__.py
│   ├── gdacs.py                # GDACS GeoJSON → list[RawRecord]
│   ├── who.py                  # WHO OData → list[RawRecord]
│   ├── gdelt.py                # GDELT DOC API → list[RawRecord]
│   └── news.py                 # DDGS news search → list[RawRecord]
├── storage/
│   ├── __init__.py
│   ├── jsonl.py                # JSONL storage backend
│   └── sqlite.py               # SQLite storage backend
└── pipeline.py                 # Orchestration: fetch → correlate → classify → enrich → store

scripts/
└── capture_fixtures.py         # Call each API once, save raw JSON

tests/
├── fixtures/
│   ├── gdacs_response.json
│   ├── who_response.json
│   └── gdelt_response.json
├── test_types.py
├── test_classify.py
├── test_correlate.py
├── test_gdacs_adapter.py
├── test_who_adapter.py
├── test_gdelt_adapter.py
├── test_news_searcher.py
├── test_ai_extractor.py
├── test_ai_classifier.py
├── test_jsonl_store.py
├── test_sqlite_store.py
└── test_pipeline.py
```

## 11. Dependencies

```toml
[project]
dependencies = [
    "httpx>=0.28",
    "dspy",
    "ddgs>=9.14",
]

[dependency-groups]
dev = [
    "flowr>=1.0.0",
    "pytest-beehave>=0.2.0",
]
```

## 12. Build Order

### Phase 1 — Foundation (pure Python, no I/O)

1. `types.py` — RawRecord, IncidentBundle, Incident dataclasses
2. `classify.py` — ClassifyEngine with all deterministic rules (country groups, priority matrix, level derivation, overrides O1–O6)
3. `correlate.py` — Record correlator (date + country + title similarity)
4. `storage/jsonl.py` — JSONLStore
5. `storage/sqlite.py` — SQLiteStore
6. Tests for all of the above

### Phase 2 — Adapters (fixture-driven)

7. `scripts/capture_fixtures.py` — call each API once, save raw JSON
8. Run capture fixtures against real APIs
9. `adapters/gdacs.py` + tests (from fixture)
10. `adapters/who.py` + tests (from fixture)
11. `adapters/gdelt.py` + tests (from fixture)
12. `adapters/news.py` + tests (DDG News search)

### Phase 3 — AI (from day 1)

13. `ai/provider.py` — AIProvider protocol + DuckAIProvider
14. `ai/extractor.py` — batched extraction agent with DSPy signatures
15. `ai/classifier.py` — batched classification agent with DSPy signatures
16. Integration tests (fixtures + mocked AI responses)

### Phase 4 — Pipeline

17. `pipeline.py` — fetch → correlate → classify → search-more → AI enrich → store
18. End-to-end test

## 13. Testing Strategy

- **Fixture-first**: call each API once, save raw JSON, test against fixtures forever
- **No BaseAdapter** — simple httpx calls in adapters
- **AI responses mocked** in tests (we test prompt engineering separately)
- **Deterministic rules tested exhaustively** (all country groups, all priority matrix cells, all overrides)
- **Correlation tested** with known multi-source scenarios

## 14. Incident ID Format

`YYYYMMDD-CC-TTT` where:
- YYYYMMDD = report date
- CC = ISO 3166-1 alpha-2 country code
- TTT = disaster type code (e.g., EQ=Earthquake, FL=Flood, TC=Cyclone, etc.)

## 15. Quality Attributes

| Priority | Attribute | Scenario |
|----------|-----------|----------|
| 1 | Reproducibility | Same fixtures → same classified incidents, every time |
| 2 | Reliability | Any source API down → other sources unaffected, no data loss |
| 3 | Reliability | AI timeout/failure → incident stored without enrichment |
| 4 | Testability | Every classification rule has a passing test with named fixture |
| 5 | Performance | 50 incidents classified and stored in < 5 seconds (excluding AI) |
| 6 | Performance | Full batch with AI in < 5 minutes |

## 16. Out of Scope

- Dashboard or web UI
- Real-time push notifications
- Account-based API sources (ReliefWeb, HealthMap)
- AI-based classification (AI only extracts and enriches, never classifies)
- Email sending (future consideration)
- Multi-process or distributed execution
