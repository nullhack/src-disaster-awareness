# Behavioral Specification

> **Status:** BASELINED (2026-05-14)
> Source of truth: `docs/spec/contract.md`
> Monolithic: all bounded contexts in one file.
> Each `## <Context Name>` section is a context boundary.

---

## Fetching

### Context

The Fetching context wraps external disaster data sources behind uniform protocols. Three primary source adapters (GDACS, WHO DON, GDELT) implement `SourceAdapter` to fetch incidents from free, zero-auth public APIs. One supplementary source adapter (DDG News) implements `NewsSearcher` to find additional articles when primary sources lack context. Each adapter receives an `httpx.Client`, makes HTTP requests to its source, and returns `list[RawRecord]`. Adapters never raise — they return empty lists on failure. Raw responses are preserved verbatim in `RawRecord.raw_fields` because field availability varies across sources and cannot be assumed until real data is observed (the uncertainty principle).

### Entities

#### RawRecord
- Purpose: Atomic data unit from any source. The pipeline's internal lingua franca for raw events. Never normalized — `raw_fields` contains the exact, untouched API response.
- Lifecycle: created (by adapter parse) → grouped (by Correlator into IncidentBundle) → preserved (stored in IncidentBundle)

#### SourceAdapter (Protocol)
- Purpose: Contract for primary API fetchers. Each adapter wraps a single API. No base class, no caching, no TTL — just httpx calls returning raw records.
- Defined by: `source_name: str` and `fetch(client: httpx.Client) -> list[RawRecord]`

#### NewsSearcher (Protocol)
- Purpose: Contract for supplementary news search. Wraps `ddgs.DDGS.news()`. Used to find additional articles about an incident when primary sources don't provide enough context.
- Defined by: `search(query: str, *, region: str = "wt-wt", timelimit: str | None = None, max_results: int = 5) -> list[RawRecord]`

### Data Shapes

#### RawRecord

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| source_name | str | Yes | One of: "GDACS", "WHO", "GDELT", "DDG-NEWS" |
| fetched_at | datetime | Yes | UTC timestamp of when the record was fetched |
| raw_fields | dict | Yes | Complete, untouched source-specific API response. No normalization. |

#### GDACS raw_fields (expected, subject to change)

| Field | Type | Notes |
|-------|------|-------|
| title | str | Event title |
| description | str | Event description |
| alertlevel | str | "Green", "Orange", or "Red" |
| eventtype | str | Disaster type code (EQ, TC, FL, VO, TS, DR, WF) |
| iso3 | str | ISO 3166-1 alpha-3 country code |
| latitude | float | Event latitude |
| longitude | float | Event longitude |
| istemporary | bool | Whether this is a forecast/early warning |
| affectedcountries | list[dict] | List of {iso2, iso3, countryname} |

#### WHO raw_fields (expected, subject to change)

| Field | Type | Notes |
|-------|------|-------|
| title | str | Article title |
| url | str | Article URL |
| date | str | Publication date |
| content_html | str | Full HTML content |

#### GDELT raw_fields (expected, subject to change)

| Field | Type | Notes |
|-------|------|-------|
| title | str | Article title |
| url | str | Article URL |
| seendate | str | When GDELT saw this article |
| tone | float | Sentiment/negativity score |
| themes | list[str] | GDELT theme tags |

#### DDG-NEWS raw_fields

| Field | Type | Notes |
|-------|------|-------|
| date | str | Article date |
| title | str | Article title |
| body | str | Article body |
| url | str | Article URL |
| source | str | Publisher name |

### Integration Points

#### Fetching -> Correlation
- Purpose: Pass all raw records from primary sources to the correlator
- Trigger: Pipeline orchestrator collects all adapter results
- Payload: `list[RawRecord]` (combined from GDACS, WHO, GDELT)
- Response: `list[IncidentBundle]` (grouped by incident)

#### Fetching -> Correlation (supplementary)
- Purpose: Append supplementary DDG News results to bundles needing context
- Trigger: Correlator identifies bundles with missing country or low-structure sources
- Payload: `str` (search query), returns `list[RawRecord]` with `source_name="DDG-NEWS"`
- Response: Records appended to existing bundles

### External Contracts

#### SourceAdapter: fetch()

- **Actor**: Pipeline orchestrator
- **Trigger**: `adapter.fetch(client)` called by pipeline
- **Input**: `client: httpx.Client` (shared HTTP client)
- **Output**: `list[RawRecord]` — each record's `raw_fields` contains the complete, unmodified API response
- **Errors**:
  - HTTP 5xx / timeout → return `[]` (never raises)
  - HTTP 429 (rate limit) → return `[]`
  - Malformed response → log error, return successfully parsed records, skip malformed ones
  - Network unreachable → return `[]`
- **Side Effects**: HTTP requests to external APIs
- **Preconditions**: None (graceful failure returns `[]`)

#### NewsSearcher: search()

- **Actor**: Pipeline orchestrator (supplementary search step)
- **Trigger**: Bundle needs more context (missing country, low-structure source)
- **Input**: `{query: str, region: str = "wt-wt", timelimit: str | None, max_results: int = 5}`
- **Output**: `list[RawRecord]` with `source_name="DDG-NEWS"`
- **Errors**: Returns empty list on failure, never raises
- **Side Effects**: HTTP requests to DDG News API via `ddgs` package
- **Preconditions**: None

### Invariants

- `fetch()` MUST NEVER raise an exception — always returns `list[RawRecord]` (possibly empty)
- Every `RawRecord.raw_fields` MUST contain the complete, untouched API response — no normalization, no field removal
- `source_name` in each record MUST exactly match the adapter's source: "GDACS", "WHO", "GDELT", or "DDG-NEWS"
- No BaseAdapter — each adapter is a standalone class implementing the `SourceAdapter` protocol via structural typing

---

## Correlation

### Context

The Correlation context groups `RawRecord`s from different sources that describe the same real-world incident into `IncidentBundle`s. This is necessary because GDACS, WHO, and GDELT may each report on the same earthquake, flood, or outbreak from different perspectives and with different data shapes. Matching criteria combine date proximity, country overlap, and title similarity. Single-source records become bundles with one record. The correlator also triggers supplementary DDG News search for bundles needing more context.

### Entities

#### IncidentBundle
- Purpose: Container for all information about one real-world incident. Holds one or more `RawRecord`s from any source, plus derived classification and AI enrichment fields.
- Lifecycle: created (by correlator) → classified (by ClassifyEngine) → enriched (by AI agents) → stored (by StorageBackend)

### Data Shapes

#### IncidentBundle

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| incident_id | str | Yes | Format: `YYYYMMDD-CC-TTT` |
| records | list[RawRecord] | Yes | One or more raw records from any source |
| country | str \| None | No | Resolved from any record or AI |
| country_code | str \| None | No | ISO 3166-1 alpha-2 |
| country_group | str \| None | No | "A", "B", or "C" |
| disaster_type | str \| None | No | Disaster type string |
| incident_level | int \| None | No | 1–4 |
| priority | str \| None | No | "HIGH", "MED", or "LOW" |
| should_report | bool | Yes | Default False; set by classification |
| overrides | list[str] | Yes | Override codes, e.g. ["O1", "O3"]; default [] |
| summary | str \| None | No | AI-generated summary |
| rationale | str \| None | No | AI-generated rationale |
| estimated_affected | int \| None | No | AI-extracted estimate |
| estimated_deaths | int \| None | No | AI-extracted estimate |
| ai_enriched | bool | Yes | Whether AI enrichment succeeded |
| classified_at | datetime \| None | No | Timestamp of classification |

### Integration Points

#### Fetching -> Correlation
- Purpose: Raw records grouped into incident bundles
- Trigger: Pipeline orchestrator passes combined raw records to correlator
- Payload: `list[RawRecord]`
- Response: `list[IncidentBundle]`

#### Correlation -> Classification
- Purpose: Bundles flow to deterministic classification
- Trigger: Pipeline orchestrator passes bundles to ClassifyEngine
- Payload: `list[IncidentBundle]`
- Response: `list[IncidentBundle]` (with classification fields populated)

#### Correlation -> Fetching (supplementary search)
- Purpose: Bundles needing context trigger DDG News search
- Trigger: Bundles with missing country or from low-structure sources
- Payload: Search query derived from bundle records
- Response: Additional `RawRecord`s appended to bundle

### External Contracts

#### Correlator: correlate()

- **Actor**: Pipeline orchestrator
- **Trigger**: `correlate(records: list[RawRecord])` called after fetch
- **Input**: `list[RawRecord]` (combined from all primary sources)
- **Output**: `list[IncidentBundle]` — each bundle contains one or more records about the same incident
- **Errors**: none (pure grouping logic)
- **Side Effects**: May trigger supplementary DDG News search via `NewsSearcher`
- **Preconditions**: Raw records have `source_name`, `fetched_at`, and `raw_fields`

Matching criteria:
- Date proximity: records within the same date window
- Country overlap: same country extracted from different sources
- Title similarity: similar event descriptions across sources
- Single-source records: become bundles with one record

### Invariants

- Every `RawRecord` from the primary fetch MUST be assigned to exactly one `IncidentBundle`
- An `IncidentBundle` MUST contain at least one `RawRecord`
- `incident_id` MUST follow the `YYYYMMDD-CC-TTT` format
- Single-source records (no match found) MUST still become bundles with one record

---

## Classification

### Context

The Classification context applies deterministic rules to classify `IncidentBundle`s. It works on `bundle.records`, trying each source's `raw_fields` in order of reliability (GDACS > WHO > GDELT > DDG-NEWS). All logic is pure Python — no AI calls. This context exists because classification must be 100% reproducible: the same raw records must always produce the same level, priority, country group, and overrides. The ClassifyEngine assigns incident levels (1–4) using source-specific rules, maps levels and country groups through a priority matrix to determine priority (HIGH/MED/LOW) and `should_report` (true/false), and evaluates six override criteria (O1–O6).

### Entities

#### ClassifyEngine
- Purpose: Stateless classification service. Consumes an `IncidentBundle`, applies country-group lookup, source-specific level derivation, priority matrix, and override checks. Produces a classified `IncidentBundle`.
- Lifecycle: instantiated → `classify(bundle)` called per bundle

### Data Shapes

#### Country Groups

- **Group A** (25 countries, highest priority): Afghanistan, Bangladesh, Bhutan, Brunei, Cambodia, China, India, Indonesia, Japan, Laos, Malaysia, Maldives, Myanmar, Nepal, North Korea, Pakistan, Philippines, Singapore, South Korea, Sri Lanka, Taiwan, Thailand, Timor Leste, Vietnam
- **Group B** (41 countries, secondary priority): Asia Pacific 2 (Australia, Fiji, etc.) + Middle East (Bahrain, Cyprus, Iran, Iraq, Jordan, Kuwait, Lebanon, Oman, Palestine, Israel, Qatar, Saudi Arabia, Syria, Turkey, UAE, Yemen) + North Africa (Algeria, Egypt, Morocco, Tunisia)
- **Group C** (rest of world, lowest priority)

#### Priority Matrix

```
          Group A    Group B    Group C
Level 4  HIGH/✓    HIGH/✓     HIGH/✓
Level 3  HIGH/✓    MED/✓      MED/✓
Level 2  MED/✓     MED/✓      LOW/✗
Level 1  MED/✓     LOW/✗      LOW/✗
```

(✓ = `should_report=True`, ✗ = `should_report=False`)

#### Level Derivation (source-specific)

Tries the most reliable available source first:

| Source | Rule |
|--------|------|
| GDACS | Green → 1, Orange → 3, Red → 4 (severity bump for Group A) |
| WHO | Keyword scan: "pandemic"/"PHEIC" → 4, "epidemic"/"widespread" → 3, "cluster"/"cases reported" → 2, "isolated case" → 1, default → 2 |
| GDELT | tone < -5 → 4, < -3 → 3, >= 0 → 1, else → 2 |

#### Level Indicators

- **Level 4 (CRITICAL)**: International assistance requested, 300K+ affected, 50+ deaths, multi-state impact, humanitarian crisis declared
- **Level 3 (MAJOR)**: 100K+ affected, 20–50 deaths, frequent media coverage, ongoing humanitarian crisis
- **Level 2 (SIGNIFICANT)**: <100K affected, 5–20 deaths, multiple source coverage, regional impact developing
- **Level 1 (MINOR)**: <50K affected, 0–5 deaths, local coverage only, contained impact

#### Overrides (O1–O6)

| Override | Name | Method |
|----------|------|--------|
| O1 | Humanitarian Crisis | Keywords for GDACS, AI for WHO/GDELT |
| O2 | Multi-Regional | GDACS: structured `affectedcountries`; AI for others |
| O3 | Likely Development | AI-assisted text understanding |
| O4 | Environmental | Deterministic: disaster type in {WF, DR, FL} AND Group A |
| O5 | Forecast/Early Warning | GDACS: `istemporary` field; AI for others |
| O6 | Singapore/SRC | Keyword: "Singapore", "SRC", "Red Cross" |

### Integration Points

#### Correlation -> Classification
- Purpose: Bundles with raw records flow to deterministic classification
- Trigger: Pipeline orchestrator passes bundles to ClassifyEngine
- Payload: `list[IncidentBundle]` (classification fields may be None)
- Response: `list[IncidentBundle]` (classification fields populated)

#### Classification -> Enrichment
- Purpose: Classified bundles flow to AI enrichment for missing fields and summaries
- Trigger: Pipeline orchestrator passes classified bundles to AI agents
- Payload: `list[IncidentBundle]` (classified, some fields still None needing AI extraction)
- Response: `list[IncidentBundle]` (enriched with AI fields)

#### Classification -> Storage
- Purpose: Classified bundles (with or without enrichment) are stored
- Trigger: Pipeline orchestrator passes bundles to StorageBackend
- Payload: `list[IncidentBundle]`
- Response: `{stored_count: int}`

### External Contracts

#### ClassifyEngine: classify()

- **Actor**: Pipeline orchestrator
- **Trigger**: `ClassifyEngine.classify(bundle: IncidentBundle)` called per bundle
- **Input**: `IncidentBundle` with raw records
- **Output**: `IncidentBundle` with classification fields populated (`country_group`, `incident_level`, `priority`, `should_report`, `overrides`)
- **Errors**:
  - Country not found in group lookup → assign Group C, log warning
  - No source provides level-relevant fields → default to level 2
- **Side Effects**: none (pure function)
- **Preconditions**: Bundle contains at least one `RawRecord`

### Invariants

- Classification MUST be 100% deterministic: identical records in identical bundles MUST always produce identical classification
- `incident_level` MUST be between 1 and 4 (inclusive)
- `country_group` MUST be one of "A", "B", "C"
- `priority` MUST be one of "HIGH", "MED", "LOW"
- `incident_id` MUST follow `YYYYMMDD-CC-TTT` format
- Level 4 incidents MUST always have `should_report=True` regardless of country group
- Overrides MUST be evaluated after the priority matrix; override results take precedence
- Classification MUST complete in < 1 second for 50 bundles (no network calls)
- Source reliability order MUST be GDACS > WHO > GDELT > DDG-NEWS

---

## Enrichment

### Context

The Enrichment context adds AI-extracted and AI-generated fields to classified `IncidentBundle`s. It operates in two batched phases: (1) the Extractor batch processes bundles where country or disaster_type is still None after deterministic classification, extracting structured data from unstructured text using all raw records in the bundle plus any supplementary DDG News results; (2) the Classifier batch processes `should_report=True` bundles, generating summaries and detecting overrides O1 (Humanitarian Crisis), O3 (Likely Development), and O5 (Forecast/Early Warning). The AI provider is DuckDuckGo AI via direct HTTP (no wrapper library), with DSPy providing structured output signatures. Enrichment is failure-safe: if AI fails, the bundle is stored with `ai_enriched=False` and all AI fields as None.

### Entities

#### AIProvider (Protocol)
- Purpose: Abstract AI chat interface. `chat(prompt, *, model) -> str`. Raises on unrecoverable failure; auto-retries on HTTP 429.

#### DuckAIProvider
- Purpose: Concrete implementation calling DuckDuckGo's `duckchat/v1` API directly via httpx. Two-step protocol: GET `/status` for VQD token, POST `/chat` for SSE stream response. Rate limited to ~1 request/15 seconds.

#### Extractor Agent
- Purpose: Batched AI extraction. Takes bundles with missing country/disaster_type, returns extracted fields. Uses DSPy typed signatures. Lives in `ai/extractor.py`.

#### Classifier Agent
- Purpose: Batched AI enrichment. Takes `should_report=True` bundles, generates summaries and detects overrides O1, O3, O5. Uses DSPy typed signatures. Lives in `ai/classifier.py`.

### Data Shapes

#### Extractor Batch Input/Output

- **Input**: `list[IncidentBundle]` where `country is None` or `disaster_type is None`
- **Output**: Extracted `country`, `disaster_type`, `estimated_affected`, `estimated_deaths` per bundle
- **Batch size**: ~10 bundles per AI call

#### Classifier Batch Input/Output

- **Input**: `list[IncidentBundle]` where `should_report=True`
- **Output**: `summary`, `rationale`, override flags (humanitarian_crisis, likely_development) per bundle
- **Batch size**: ~10 bundles per AI call

#### AI Call Budget

- ~6 calls × 15 seconds = ~1.5 minutes per 50 incidents

### Integration Points

#### Classification -> Enrichment (Extractor batch)
- Purpose: Bundles with missing fields receive AI extraction
- Trigger: Pipeline identifies bundles where `country is None` or `disaster_type is None`
- Payload: `list[IncidentBundle]` (~10 per batch)
- Response: Extracted fields populated in bundles

#### Classification -> Enrichment (Classifier batch)
- Purpose: Reportable bundles receive AI summaries and override detection
- Trigger: Pipeline identifies bundles where `should_report=True`
- Payload: `list[IncidentBundle]` (~10 per batch)
- Response: `summary`, `rationale`, override flags populated in bundles

#### Enrichment -> Storage
- Purpose: Enriched (or classified-only) bundles are stored
- Trigger: Pipeline passes bundles to StorageBackend
- Payload: `list[IncidentBundle]`
- Response: `{stored_count: int}`

### External Contracts

#### DuckAIProvider: chat()

- **Actor**: Extractor agent or Classifier agent
- **Trigger**: Agent needs AI response for a batch
- **Input**: `{prompt: str, model: str = "gpt-4o-mini"}`
- **Output**: `str` — AI-generated text response
- **Errors**:
  - HTTP 429 (rate limit) → auto-retry with backoff
  - Auth/network failure → raise exception (unrecoverable)
  - VQD token expired → re-fetch from `/status` endpoint
- **Side Effects**: HTTP requests to `duckduckgo.com/duckchat/v1/*`
- **Preconditions**: VQD token obtained (lazy-initialized on first call)

Available models: gpt-4o-mini, claude-3-haiku, llama-3.3-70b, o3-mini, mistral-small

#### Extractor Agent: extract()

- **Actor**: Pipeline orchestrator
- **Trigger**: Bundles identified with missing country or disaster_type
- **Input**: `list[IncidentBundle]` with raw text records
- **Output**: Extracted `country`, `disaster_type`, `estimated_affected`, `estimated_deaths` per bundle
- **Errors**: AI failure → bundles stored without extraction (`ai_enriched=False`)
- **Side Effects**: AI API calls (batched)
- **Preconditions**: Bundles contain raw records with text content

#### Classifier Agent: enrich()

- **Actor**: Pipeline orchestrator
- **Trigger**: Bundles with `should_report=True`
- **Input**: `list[IncidentBundle]` (classified, reportable)
- **Output**: `summary`, `rationale`, override flags per bundle
- **Errors**: AI failure → bundles stored without enrichment (`ai_enriched=False`)
- **Side Effects**: AI API calls (batched)
- **Preconditions**: Bundles are classified with `should_report=True`

### Invariants

- AI failure MUST NOT block storage — the bundle is stored with `ai_enriched=False`
- `ai_enriched=False` MUST mean all AI fields (`summary`, `rationale`, `estimated_affected`, `estimated_deaths`) are None
- AI MUST NEVER be used for classification — only for extraction and enrichment
- AI operates on `IncidentBundle`s, receiving ALL raw records in each bundle for full context
- AI responses MUST be mocked in tests — prompt engineering tested separately
- Batched processing: ~10 bundles per AI call, ~6 calls per 50 incidents

---

## Storage

### Context

The Storage context persists complete `IncidentBundle`s (all raw records + classification + enrichment) using the adapter pattern with two backends: JSONL (default, append-only, date-partitioned) and SQLite (alternative, same protocol). Both implement the `StorageBackend` protocol. Queries return flattened `Incident` records (not raw bundles), filterable by date range, country group, disaster type, priority, should_report, and source name. Deduplication by `incident_id` prevents duplicate entries across pipeline runs.

### Entities

#### StorageBackend (Protocol)
- Purpose: Storage contract with three methods: `store`, `query`, `exists`. Implemented by JSONLStore and SQLiteStore.

#### JSONLStore
- Purpose: Default backend. Append-only, date-partitioned files at `incidents/by-date/YYYY-MM-DD/incidents.jsonl`. Stores complete bundles. Dedup by incident_id.

#### SQLiteStore
- Purpose: Alternative backend with same protocol and query interface. More efficient querying for large datasets.

### Data Shapes

#### Incident (query result)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| incident_id | str | Yes | YYYYMMDD-CC-TTT format |
| source_names | list[str] | Yes | All sources that contributed records |
| incident_name | str | Yes | Best title from available records |
| country | str | Yes | Full country name |
| country_code | str | Yes | ISO 3166-1 alpha-2 |
| country_group | str | Yes | "A", "B", or "C" |
| disaster_type | str | Yes | Disaster type string |
| incident_level | int | Yes | 1–4 |
| priority | str | Yes | "HIGH", "MED", or "LOW" |
| should_report | bool | Yes | Reporting decision |
| overrides | list[str] | Yes | Applied overrides (may be empty) |
| report_date | date | Yes | Report date |
| source_urls | list[str] | Yes | All source URLs |
| summary | str \| None | No | AI summary (if enriched) |
| rationale | str \| None | No | AI rationale (if enriched) |
| estimated_affected | int \| None | No | AI-extracted estimate |
| estimated_deaths | int \| None | No | AI-extracted estimate |
| ai_enriched | bool | Yes | Whether AI enrichment succeeded |
| record_count | int | Yes | Number of raw records in bundle |

### Integration Points

#### Enrichment -> Storage
- Purpose: Persist enriched (or classified-only) bundles
- Trigger: Pipeline orchestrator calls `store.store(bundles)`
- Payload: `list[IncidentBundle]`
- Response: `{stored_count: int}` — count of new bundles (skips existing IDs)

#### Storage -> CLI query
- Purpose: Allow users to query stored incidents
- Trigger: User or researcher queries by date range and filters
- Payload: `{date_from: date, date_to: date, **filters}`
- Response: `list[Incident]` — flattened query results

### External Contracts

#### StorageBackend: store()

- **Actor**: Pipeline orchestrator
- **Trigger**: `store.store(bundles)` called after enrichment
- **Input**: `list[IncidentBundle]` — complete bundles with all raw records and derived classification
- **Output**: `int` — count of new bundles stored (skips existing IDs)
- **Errors**: Storage failure → log error, pipeline handles gracefully
- **Side Effects**: Writes to JSONL files or SQLite database
- **Preconditions**: Bundles have valid `incident_id` fields

#### StorageBackend: query()

- **Actor**: Pipeline orchestrator or CLI
- **Trigger**: `store.query(date_from=..., date_to=..., **filters)` called
- **Input**: `{date_from: date, date_to: date, country_group: str?, disaster_type: str?, priority: str?, should_report: bool?, source_name: str?}`
- **Output**: `list[Incident]` — flattened view, not raw bundles
- **Errors**: Date file missing → skip (not an error). Malformed data → log warning, skip.
- **Side Effects**: Reads from disk, no writes
- **Preconditions**: date_from <= date_to

#### StorageBackend: exists()

- **Actor**: Pipeline (dedup check)
- **Trigger**: `store.exists(incident_id)` called before store
- **Input**: `{incident_id: str}`
- **Output**: `bool` — whether the incident already exists
- **Errors**: none
- **Side Effects**: Reads from disk
- **Preconditions**: None

### Invariants

- Storage MUST preserve complete `IncidentBundle`s including all raw records
- Query MUST return `Incident` (flattened view), not raw `IncidentBundle`s
- Dedup by `incident_id` — `store()` MUST skip bundles with existing IDs
- JSONL path: `incidents/by-date/YYYY-MM-DD/incidents.jsonl` (one directory per date)
- JSONL is append-only — records are never modified in place
- Both backends MUST implement the same `StorageBackend` protocol
- File encoding: UTF-8, one JSON object per line
