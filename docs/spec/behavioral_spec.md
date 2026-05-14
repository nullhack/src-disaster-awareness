# Behavioral Specification

> **Status:** DRAFT (2026-05-14) — fix-spec rewrite resolving 21 pain points
> Source of truth: `docs/spec/contract.md`
> Monolithic: all bounded contexts in one file.
> Each `## <Context Name>` section is a context boundary.

---

## Pipeline Overview

The DSR pipeline is a seven-step sequential flow executed by `pipeline.py`:

```
Fetch → Correlate → Initial Classify → Supplementary Search → AI Enrich → Override Re-evaluation → Store
```

1. **Fetch**: Call all three primary adapters (GDACS, WHO, GDELT). Collect `list[RawRecord]`.
2. **Correlate**: Group records about the same incident into `list[IncidentBundle]`.
3. **Initial Classify**: Apply deterministic rules to assign preliminary level, priority, country group, and deterministic overrides (O2, O4, O6). No AI calls.
4. **Supplementary Search**: For bundles needing more context (missing country or disaster type), query DDG News and append results to the bundle.
5. **AI Enrich**: Run Extractor (fill missing fields) and Classifier (generate summaries, detect AI-assisted overrides O1, O3, O5) on batched bundles.
6. **Override Re-evaluation**: Re-apply override evaluation now that AI-extracted data is available. Evaluate O1, O3, O5 using enriched fields. Re-run priority matrix if level changed.
7. **Store**: Persist complete bundles to JSONL or SQLite.

This ordering resolves the pipeline-order conflict (XCS-1): classification happens before supplementary search so we know what needs context, and override re-evaluation happens after AI enrichment so O1/O3/O5 can use AI-extracted data (CLS-4/XCS-2).

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

#### GDACS raw_fields (verified 2026-05-14)

| Field | Type | Notes |
|-------|------|-------|
| eventtype | str | Disaster type code (EQ, TC, FL, VO, TS, DR, WF) |
| alertlevel | str | "Green", "Orange", or "Red" |
| name | str | Event name, e.g. "Earthquake in Japan" |
| description | str | Event description |
| htmldescription | str | HTML description with severity prefix |
| country | str | Primary affected country name |
| iso3 | str | ISO 3166-1 alpha-3 country code |
| fromdate | str | Event start date (ISO 8601) |
| todate | str | Event end date (ISO 8601) |
| eventid | int | GDACS event ID |
| episodeid | int | GDACS episode ID |
| istemporary | str | "true" or "false" as STRING, not bool. Whether this is a forecast/early warning |
| iscurrent | str | "true" or "false" as STRING |
| url | dict | Dict with keys: geometry (str), report (str), details (str). `url.report` is the event page URL |
| affectedcountries | list[dict] | List of {iso2, iso3, countryname} |
| severitydata | dict | {severity: float, severitytext: str, severityunit: str} |
| alertscore | float | Alert score |
| glide | str | GLIDE identifier, e.g. "EQ-2026-000057-JPN" |
| source | str | Data source, e.g. "NEIC" |
| geometry | GeoJSON | Point coordinates [lon, lat] |

> **Note:** GDACS `url` field is a dict. Use `url.report` for the event page URL (resolves STO-4 for GDACS bundles). `istemporary` is a string ("true"/"false"), parse to bool in adapter.

#### WHO raw_fields (verified 2026-05-14)

| Field | Type | Notes |
|-------|------|-------|
| Title | str | Article title, e.g. "Avian influenza – situation in Egypt" |
| ItemDefaultUrl | str | Relative URL path, e.g. "/2006_03_20-en". Prepend "https://www.who.int" for full URL |
| PublicationDateAndTime | str | ISO 8601 publication datetime |
| PublicationDate | str | ISO 8601 publication date |
| Overview | str | Full HTML body content (may be long) |
| Summary | str | Summary text (often empty) |
| DonId | str | DON article ID (often empty string) |
| Id | str | UUID identifier |
| FormattedDate | str | Human-readable date |
| UrlName | str | URL slug |
| Assessment | str | WHO assessment (often empty) |
| Advice | str | WHO advice (often empty) |
| Epidemiology | str \| null | Epidemiological data |
| regionscountries | str \| null | GUID reference to country entity (or null). NOT a usable country field |

> **Critical:** WHO DON has NO structured country or disaster type field. `regionscountries` is a GUID reference (often null). Country and disaster type MUST be extracted from Title/Overview text via AI or regex. This confirms WHO is ~30% deterministic. `ItemDefaultUrl` is a relative path — prepend `https://www.who.int`.

#### GDELT raw_fields (verified 2026-05-14, ArtList mode)

| Field | Type | Notes |
|-------|------|-------|
| title | str | Article title |
| url | str | Article URL |
| seendate | str | Date GDELT saw this article. Format: "YYYYMMDDTHHMMSSz" (NOT ISO 8601) |
| domain | str | Source domain, e.g. "reuters.com" |
| language | str | Article language, e.g. "English", "Chinese" |
| sourcecountry | str | Country where the news SOURCE is located (NOT the incident country) |
| socialimage | str | Image URL (often empty) |
| url_mobile | str | Mobile URL (often empty) |

> **Critical:** GDELT ArtList mode has NO `tone` field. Tone data requires a separate ToneChart API call. The `sourcecountry` field is where the news source is based, NOT where the incident occurred. Incident country must be extracted from title text. The level derivation rule "tone < -5 → 4" is NOT usable with ArtList mode — see Classification section for revised GDELT level derivation.

#### DDG-NEWS raw_fields (verified 2026-05-14)

| Field | Type | Notes |
|-------|------|-------|
| title | str | Article title |
| url | str | Article URL |
| body | str | Article body snippet |
| date | str | Publication date (ISO 8601) |
| source | str | Publisher name, e.g. "ABC7 KABC" |
| image | str | Image URL |

### Integration Points

#### Fetching -> Correlation
- Purpose: Pass all raw records from primary sources to the correlator
- Trigger: Pipeline orchestrator collects all adapter results
- Payload: `list[RawRecord]` (combined from GDACS, WHO, GDELT)
- Response: `list[IncidentBundle]` (grouped by incident)

#### Fetching -> Correlation (supplementary)
- Purpose: Append supplementary DDG News results to bundles needing context
- Trigger: Pipeline step after initial classification identifies bundles with missing fields
- Payload: Search query derived from bundle records (see XCS-4 resolution below)
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
- **Trigger**: Bundle needs more context (missing country, missing disaster type)
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

The Correlation context groups `RawRecord`s from different sources that describe the same real-world incident into `IncidentBundle`s. This is necessary because GDACS, WHO, and GDELT may each report on the same earthquake, flood, or outbreak from different perspectives and with different data shapes. Matching criteria combine date proximity (±1 calendar day), country overlap (shared country or one record has no country data), and title similarity (normalized Levenshtein ratio ≥ 0.6). Single-source records become bundles with one record. Records with no date, no country, and no title form singleton bundles with default classification.

### Entities

#### IncidentBundle
- Purpose: Container for all information about one real-world incident. Holds one or more `RawRecord`s from any source, plus derived classification and AI enrichment fields.
- Lifecycle: created (by correlator) → classified (by ClassifyEngine) → enriched (by AI agents) → override re-evaluated → stored (by StorageBackend)

### Data Shapes

#### IncidentBundle

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| incident_id | str | Yes | Format: `YYYYMMDD-CC-TTT`. CC="UNX" when country unknown. TTT="OTH" when type unknown. |
| records | list[RawRecord] | Yes | One or more raw records from any source |
| country | str \| None | No | Resolved from any record or AI |
| country_code | str \| None | No | ISO 3166-1 alpha-2 |
| country_group | str \| None | No | "A", "B", or "C" |
| disaster_type | str \| None | No | Disaster type string |
| incident_level | int \| None | No | 1–4 |
| priority | str \| None | No | "HIGH", "MED", or "LOW" |
| should_report | bool | Yes | Default False; set by classification |
| overrides | list[str] | Yes | Override codes, e.g. ["O1", "O3"]; default []. Populated in two phases: initial (O2, O4, O6) and post-enrichment (O1, O3, O5). |
| summary | str \| None | No | AI-generated summary |
| rationale | str \| None | No | AI-generated rationale |
| estimated_affected | int \| None | No | AI-extracted estimate |
| estimated_deaths | int \| None | No | AI-extracted estimate |
| ai_enriched | bool | Yes | Whether AI enrichment succeeded |
| enrichment_failed | bool | Yes | Whether AI enrichment failed mid-batch (default False). When True, AI fields are None but bundle is still stored. |
| classified_at | datetime \| None | No | Timestamp of classification |
| classification_date | date \| None | No | The date used for storage partitioning. Set to the earliest incident_date from the bundle's records at classification time. |

#### Incident ID Generation

Format: `YYYYMMDD-CC-TTT`

- **YYYYMMDD**: Earliest date from any record in the bundle. If no date is available, use the current UTC date.
- **CC**: ISO 3166-1 alpha-2 country code. If country is unknown, use `"UNX"`. If AI later fills in the country, the incident_id does NOT change — it is stable identity.
- **TTT**: Disaster type code. Known codes: EQ (Earthquake), FL (Flood), TC (Cyclone), VO (Volcano), TS (Tsunami), DR (Drought), WF (Wildfire). If disaster type is unknown, use `"OTH"`.

Examples:
- `20260514-PH-EQ` → Earthquake in Philippines on 2026-05-14
- `20260514-UNX-OTH` → Unknown disaster type in unknown country on 2026-05-14
- `20260514-ID-FL` → Flood in Indonesia on 2026-05-14

### Integration Points

#### Fetching -> Correlation
- Purpose: Raw records grouped into incident bundles
- Trigger: Pipeline orchestrator passes combined raw records to correlator
- Payload: `list[RawRecord]`
- Response: `list[IncidentBundle]`

#### Correlation -> Classification
- Purpose: Bundles flow to deterministic initial classification
- Trigger: Pipeline orchestrator passes bundles to ClassifyEngine
- Payload: `list[IncidentBundle]`
- Response: `list[IncidentBundle]` (with preliminary classification fields populated)

#### Correlation -> Fetching (supplementary search)
- Purpose: Bundles needing context trigger DDG News search
- Trigger: Pipeline step after initial classification, when bundles have `country is None` or `disaster_type is None`
- Payload: Search query (see query generation algorithm below)
- Response: Additional `RawRecord`s appended to bundle

### External Contracts

#### Correlator: correlate()

- **Actor**: Pipeline orchestrator
- **Trigger**: `correlate(records: list[RawRecord])` called after fetch
- **Input**: `list[RawRecord]` (combined from all primary sources)
- **Output**: `list[IncidentBundle]` — each bundle contains one or more records about the same incident
- **Errors**: none (pure grouping logic)
- **Side Effects**: none (supplementary search is a separate pipeline step)
- **Preconditions**: Raw records have `source_name`, `fetched_at`, and `raw_fields`

#### Correlation Matching Algorithm

Two records are candidates for correlation if ALL of the following pass:

1. **Date proximity**: The dates of the two records are within **±1 calendar day** of each other. If a record has no parseable date, it passes this criterion vacuously (date is not used as a disqualifier).

2. **Country overlap**: The records share at least one country, OR at least one record has no country data (skip the country criterion for that pair, relying on date + title only). Country is extracted from source-specific fields: GDACS uses `iso3`/`affectedcountries`, WHO and GDELT use title/text parsing (deferred to AI extraction if not deterministically available).

3. **Title similarity**: Normalized Levenshtein ratio ≥ **0.6**. Normalization: lowercase both titles, strip leading/trailing whitespace, collapse multiple spaces to single space. If either record has no title, this criterion is skipped (rely on date + country only).

**Correlation combination logic (resolves Rule 9):**
- A pair correlates if date AND (country passes OR title passes). At least two criteria must be available — if only one is available, the pair correlates on that one criterion.
- If ALL three criteria are unavailable (no date, no country, no title on both records), the records do NOT correlate. Each forms its own singleton bundle.

**Records with all criteria unavailable** (resolves CLS-2):
- Records with no date, no country, and no title form singleton bundles (one record per bundle).
- These receive default classification: Level 1, Group C, Priority LOW, should_report=False.

### Invariants

- Every `RawRecord` from the primary fetch MUST be assigned to exactly one `IncidentBundle`
- An `IncidentBundle` MUST contain at least one `RawRecord`
- `incident_id` MUST follow the `YYYYMMDD-CC-TTT` format with "UNX" for unknown country and "OTH" for unknown type
- `incident_id` is stable — once generated, it MUST NOT change even if AI enrichment fills in missing fields
- Single-source records (no match found) MUST still become bundles with one record
- Date proximity threshold: ±1 calendar day
- Title similarity threshold: normalized Levenshtein ratio ≥ 0.6

---

## Classification

### Context

The Classification context applies deterministic rules to classify `IncidentBundle`s. It operates in **two phases**:

**Phase 1 — Initial Classification (deterministic, no AI):** Applied during the Initial Classify pipeline step. Uses only structured data from `raw_fields` to assign preliminary level, priority, country group, and deterministic overrides (O2, O4, O6). All logic is pure Python — no AI calls. This phase is 100% reproducible: the same raw records always produce the same result.

**Phase 2 — Override Re-evaluation (after AI enrichment):** Applied during the Override Re-evaluation pipeline step, after AI enrichment has filled in missing fields and detected AI-assisted override conditions. Re-evaluates overrides O1, O3, O5 using AI-extracted data. If level or priority changes, the priority matrix is re-applied. The incident_id is NOT regenerated.

This split resolves CLS-4/XCS-2: O1 (Humanitarian Crisis), O3 (Likely Development), and O5 (Forecast/Early Warning) require AI-extracted text understanding and are therefore evaluated AFTER AI enrichment, not during initial deterministic classification. O2 (Multi-Regional), O4 (Environmental), and O6 (Singapore/SRC) use structured data and are evaluated during initial classification.

### Entities

#### ClassifyEngine
- Purpose: Stateless classification service. Consumes an `IncidentBundle`, applies country-group lookup, source-specific level derivation, priority matrix, and override checks. Produces a classified `IncidentBundle`.
- Lifecycle: instantiated → `classify(bundle)` called per bundle → `reevaluate_overrides(bundle)` called after enrichment

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

Uses **most-reliable-source-wins** (resolves CLS-6/Rule 19): when multiple sources in a bundle provide level-relevant data, use the level from the highest-reliability source that derived a level. Source reliability order: GDACS > WHO > GDELT > DDG-NEWS. If only one source derived a level, use that.

| Source | Rule |
|--------|------|
| GDACS | Green → 1, Orange → 3, Red → 4. **Severity bump for Group A** (resolves CLS-1/Rule 10): when the bundle's primary country is in Group A, bump Orange from Level 3 to Level 4, and Green from Level 1 to Level 2. Red (Level 4) is not bumped (already max). Group B and Group C receive no bump. |
| WHO | Keyword scan: "pandemic"/"PHEIC" → 4, "epidemic"/"widespread" → 3, "cluster"/"cases reported" → 2, "isolated case" → 1, default → 2 |
| GDELT | ArtList mode has no tone field. Default Level 2 unless title keyword scan suggests higher: "major"/"catastrophic"/"deadly"/"massive" → 3, "devastating"/"hundreds dead"/"thousands displaced"/"PHEIC" → 4. Otherwise Level 1 if title seems minor. Default: Level 2. |

**Default when no source provides level data:** Level 2.

#### Level Indicators

- **Level 4 (CRITICAL)**: International assistance requested, 300K+ affected, 50+ deaths, multi-state impact, humanitarian crisis declared
- **Level 3 (MAJOR)**: 100K+ affected, 20–50 deaths, frequent media coverage, ongoing humanitarian crisis
- **Level 2 (SIGNIFICANT)**: <100K affected, 5–20 deaths, multiple source coverage, regional impact developing
- **Level 1 (MINOR)**: <50K affected, 0–5 deaths, local coverage only, contained impact

#### Overrides (O1–O6)

Overrides are **independent and cumulative** (resolves CLS-3): each override that matches is applied. If multiple overrides match, apply ALL of them. The override effects are:

| Override | Name | Effect | Evaluation Phase | Method |
|----------|------|--------|-------------------|--------|
| O1 | Humanitarian Crisis | Force priority HIGH, force should_report=True | **Post-enrichment** | AI-assisted for WHO/GDELT; keyword matching for GDACS |
| O2 | Multi-Regional | Force priority HIGH, force should_report=True | Initial (deterministic) | GDACS: structured `affectedcountries` count > 1; AI for others (post-enrichment) |
| O3 | Likely Development | Bump level +1 (max 4), force should_report=True | **Post-enrichment** | AI-assisted text understanding |
| O4 | Environmental | Force priority HIGH if country is Group A | Initial (deterministic) | Disaster type in {WF, DR, FL} AND country in Group A |
| O5 | Forecast/Early Warning | Bump level +1 (max 4), force should_report=True | **Post-enrichment** | GDACS: `istemporary="true"` (string, not bool); AI for others |
| O6 | Singapore/SRC | **Force priority HIGH, force should_report=True** regardless of level or country group (resolves ENR-4) | Initial (deterministic) | Keyword: "Singapore", "SRC", "Red Cross" in any record's text |

**Override application order:**
1. Priority matrix produces base (priority, should_report) from level × country_group.
2. Each matching override applies its effect independently:
   - Force HIGH → priority = "HIGH"
   - Bump level +1 → incident_level = min(incident_level + 1, 4); re-apply priority matrix if level changed
   - Force should_report=True → should_report = True
3. Cumulative: if O4 forces HIGH and O6 also triggers, priority stays HIGH (idempotent).
4. If O3 bumps level from 3→4, re-apply priority matrix: Level 4 in any group = HIGH/True.

### Integration Points

#### Correlation -> Initial Classification
- Purpose: Bundles with raw records flow to deterministic classification
- Trigger: Pipeline orchestrator passes bundles to ClassifyEngine
- Payload: `list[IncidentBundle]` (classification fields may be None)
- Response: `list[IncidentBundle]` (preliminary classification fields populated, O2/O4/O6 in overrides)

#### Initial Classification -> Supplementary Search
- Purpose: Classified bundles with missing fields trigger supplementary search
- Trigger: `country is None` or `disaster_type is None` after initial classification
- Payload: Search query (see Supplementary Search Query Generation below)
- Response: Additional `RawRecord`s from DDG News appended to bundles

#### AI Enrichment -> Override Re-evaluation
- Purpose: Enriched bundles receive override re-evaluation with AI data
- Trigger: Pipeline orchestrator passes enriched bundles back to ClassifyEngine
- Payload: `list[IncidentBundle]` (enriched with AI fields, O1/O3/O5 detected by Classifier agent)
- Response: `list[IncidentBundle]` (final overrides list, possibly updated level/priority)

#### Override Re-evaluation -> Storage
- Purpose: Fully classified and enriched bundles flow to storage
- Trigger: Pipeline orchestrator passes bundles to StorageBackend
- Payload: `list[IncidentBundle]`
- Response: `{stored_count: int}`

### External Contracts

#### ClassifyEngine: classify()

- **Actor**: Pipeline orchestrator
- **Trigger**: `ClassifyEngine.classify(bundle: IncidentBundle)` called per bundle
- **Input**: `IncidentBundle` with raw records
- **Output**: `IncidentBundle` with preliminary classification fields populated (`country_group`, `incident_level`, `priority`, `should_report`, `overrides` containing deterministic overrides O2/O4/O6)
- **Errors**:
  - Country not found in group lookup → assign Group C, log warning
  - No source provides level-relevant fields → default to level 2
- **Side Effects**: none (pure function)
- **Preconditions**: Bundle contains at least one `RawRecord`

#### ClassifyEngine: reevaluate_overrides()

- **Actor**: Pipeline orchestrator
- **Trigger**: After AI enrichment step, `ClassifyEngine.reevaluate_overrides(bundle: IncidentBundle)` called per bundle
- **Input**: `IncidentBundle` with AI-enriched fields and AI-detected override flags
- **Output**: `IncidentBundle` with final overrides list, updated level/priority if O3/O5 bumped level
- **Side Effects**: none (pure function)
- **Preconditions**: Bundle has been through initial classification AND AI enrichment

### Invariants

- Initial classification MUST be 100% deterministic: identical records in identical bundles MUST always produce identical classification
- `incident_level` MUST be between 1 and 4 (inclusive)
- `country_group` MUST be one of "A", "B", "C"
- `priority` MUST be one of "HIGH", "MED", "LOW"
- `incident_id` MUST follow `YYYYMMDD-CC-TTT` format with "UNX"/"OTH" for unknowns
- `incident_id` MUST NOT be regenerated during re-evaluation — it is stable identity
- Level 4 incidents MUST always have `should_report=True` regardless of country group
- Overrides MUST be evaluated after the priority matrix; override results take precedence
- O1, O3, O5 MUST be evaluated in the Override Re-evaluation phase AFTER AI enrichment
- O2, O4, O6 MUST be evaluated during Initial Classification
- Overrides are independent and cumulative — ALL matching overrides apply
- GDACS severity bump: Group A only, Orange→4, Green→2, Red unchanged
- Multi-source level: most-reliable-source-wins (GDACS > WHO > GDELT > DDG-NEWS)
- Initial classification MUST complete in < 1 second for 50 bundles (no network calls)
- Source reliability order MUST be GDACS > WHO > GDELT > DDG-NEWS

---

## Enrichment

### Context

The Enrichment context adds AI-extracted and AI-generated fields to classified `IncidentBundle`s. It operates in two batched phases: (1) the Extractor batch processes bundles where country or disaster_type is still None after initial classification, extracting structured data from unstructured text using all raw records in the bundle plus any supplementary DDG News results; (2) the Classifier batch processes `should_report=True` bundles, generating summaries and detecting overrides O1 (Humanitarian Crisis), O3 (Likely Development), and O5 (Forecast/Early Warning). After extraction, re-run the deterministic classifier with the newly populated fields (ENR-2). AI enrichment is optional — the pipeline supports pluggable AI backends (Ollama, Gemini, OpenAI, or disabled) via DSPy typed signatures. Enrichment is failure-safe: if AI fails or is unavailable, the bundle is stored with `ai_enriched=False` and all AI fields as None.

### Supplementary Search Query Generation (resolves XCS-4)

When a bundle needs supplementary search (missing country or disaster type after initial classification), the query is constructed as:

```
"{incident_title} {country} {disaster_type} latest news"
```

Where:
- `incident_title`: the title from the highest-reliability source's `raw_fields`. If no title is available, use "disaster incident".
- `country`: the resolved country name if known. If unknown, omit from the query.
- `disaster_type`: the resolved disaster type if known. If unknown, substitute "disaster emergency".

Examples:
- `"Magnitude 7.2 earthquake Philippines latest news"` (all fields known)
- `"Disease outbreak latest news"` (country unknown, type derived from title)
- `"disaster incident disaster emergency latest news"` (nothing known)

### Entities

#### AIProvider (Protocol)
- Purpose: Abstract AI chat interface. `chat(prompt, *, model) -> str`. Raises on unrecoverable failure; auto-retries on HTTP 429.

#### AIProvider Implementation

The pipeline supports pluggable AI backends. The default implementation is **optional** — the pipeline runs fully without AI, using deterministic classification only.

**Supported implementations (pick one):**

1. **OllamaProvider** (recommended, free): Calls local Ollama server. No API key needed. Models: llama3, mistral, etc. Requires Ollama running locally.
2. **GeminiProvider** (free tier): Calls Google Gemini API. Requires free API key from Google AI Studio. Models: gemini-2.0-flash.
3. **OpenAIProvider**: Calls OpenAI API. Requires paid API key. Models: gpt-4o-mini.
4. **None (AI disabled)**: Pipeline skips enrichment steps 5-6 entirely. All bundles classified deterministically. AI fields remain None.

All implementations use the same `AIProvider` protocol: `chat(prompt, *, model) -> str`.

#### DSPy Integration

Both Extractor and Classifier agents use DSPy typed signatures for structured LLM programming. DSPy handles prompt engineering, output parsing, and retry logic. The underlying LM is configured via `dspy.configure(lm=dspy.LM("provider/model"))`.

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
- **Output**: `summary`, `rationale`, override flags (humanitarian_crisis, likely_development, forecast_warning) per bundle
- **Batch size**: ~10 bundles per AI call

#### AI Call Budget

- ~6 calls × 15 seconds = ~1.5 minutes per 50 incidents

### Integration Points

#### Initial Classification -> Enrichment (Extractor batch)
- Purpose: Bundles with missing fields receive AI extraction
- Trigger: Pipeline identifies bundles where `country is None` or `disaster_type is None`
- Payload: `list[IncidentBundle]` (~10 per batch)
- Response: Extracted fields populated in bundles

#### Enrichment -> Classification (re-classification after extraction)
- Purpose: Re-run deterministic classification with newly extracted fields
- Trigger: Extractor fills in `country` or `disaster_type` that were previously None
- Payload: `list[IncidentBundle]` (extracted fields populated)
- Response: Updated `country_group`, `incident_level`, `priority` (incident_id unchanged)

#### Initial Classification -> Enrichment (Classifier batch)
- Purpose: Reportable bundles receive AI summaries and override detection
- Trigger: Pipeline identifies bundles where `should_report=True`
- Payload: `list[IncidentBundle]` (~10 per batch)
- Response: `summary`, `rationale`, override flags populated in bundles

#### Enrichment -> Override Re-evaluation
- Purpose: AI-detected overrides (O1, O3, O5) applied to classification
- Trigger: Classifier agent returns override flags
- Payload: `list[IncidentBundle]` (with AI override flags)
- Response: Updated `overrides` list and possibly updated `level`, `priority`

#### Enrichment -> Storage
- Purpose: Enriched (or classified-only) bundles are stored
- Trigger: Pipeline passes bundles to StorageBackend
- Payload: `list[IncidentBundle]`
- Response: `{stored_count: int}`

### External Contracts

#### AIProvider: chat()

- **Actor**: Extractor agent or Classifier agent
- **Trigger**: Agent needs AI response for a batch
- **Input**: `{prompt: str, model: str}` — model depends on provider
- **Output**: `str` — AI-generated text response
- **Errors**:
  - AI provider unavailable (Ollama not running, API key invalid, network failure) → bundles stored without enrichment (`ai_enriched=False`, `enrichment_failed=True`). Pipeline continues.
  - HTTP 429 (rate limit) → auto-retry with exponential backoff: initial delay 15s, multiplier 2×, max 3 retries. After exhaustion, mark bundles as failed and continue.
  - Mid-batch failure → keep successfully enriched bundles, mark remaining as `enrichment_failed=True` (resolves ENR-3).
- **Side Effects**: AI API calls (local or remote)
- **Preconditions**: None — if AI is unavailable, pipeline proceeds without enrichment

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

#### Mid-Batch Failure Handling (resolves ENR-3)

If `AIProvider` fails mid-batch (unrecoverable exception during a batch of ~10 bundles):
1. All bundles already successfully processed in the current batch are kept with their AI fields populated.
2. All remaining unprocessed bundles in the batch are marked `enrichment_failed=True` and `ai_enriched=False`.
3. ALL bundles (enriched and unenriched) proceed to storage.
4. The pipeline does NOT abort — it continues with the next batch or step.

### Post-Extraction Re-classification (resolves ENR-2)

After the Extractor agent fills in missing `country` or `disaster_type` fields:
1. Re-run the deterministic ClassifyEngine on the updated bundle (country_group lookup, level derivation, priority matrix).
2. This may upgrade the level (e.g., unknown country was Group C default, now classified as Group A), change the priority, or add O4 if the newly known country is Group A with environmental disaster type.
3. Do NOT regenerate `incident_id` — it is stable identity from correlation time.
4. Re-classified bundles then proceed to the Classifier agent for summary generation and override detection.

### Invariants

- AI failure MUST NOT block storage — the bundle is stored with `ai_enriched=False`
- `ai_enriched=False` MUST mean all AI fields (`summary`, `rationale`, `estimated_affected`, `estimated_deaths`) are None
- `enrichment_failed=True` indicates partial batch failure — the bundle was in a batch where AI failed partway through
- AI MUST NEVER be used for initial classification — only for extraction, enrichment, and override detection (O1, O3, O5)
- AI operates on `IncidentBundle`s, receiving ALL raw records in each bundle for full context
- AI responses MUST be mocked in tests — prompt engineering tested separately
- Batched processing: ~10 bundles per AI call, ~6 calls per 50 incidents
- Rate limit retry: exponential backoff, initial 15s, multiplier 2×, max 3 retries
- Post-extraction re-classification MUST NOT regenerate incident_id
- Mid-batch failure: keep successful results, mark remaining as enrichment_failed, store everything

---

## Storage

### Context

The Storage context persists complete `IncidentBundle`s (all raw records + classification + enrichment) using the adapter pattern with two backends: JSONL (default, append-only, date-partitioned) and SQLite (alternative, same protocol). Both implement the `StorageBackend` protocol. Queries return flattened `Incident` records (not raw bundles), filterable by date range, country group, disaster type, priority, should_report, and source name. Deduplication by `incident_id` prevents duplicate entries across pipeline runs. Storage uses atomic writes to prevent data corruption.

### Entities

#### StorageBackend (Protocol)
- Purpose: Storage contract with three methods: `store`, `query`, `exists`. Implemented by JSONLStore and SQLiteStore.

#### JSONLStore
- Purpose: Default backend. Append-only, date-partitioned files at `incidents/by-date/YYYY-MM-DD/incidents.jsonl`. Stores complete bundles. Dedup by incident_id. Uses atomic write (temp file + rename).

#### SQLiteStore
- Purpose: Alternative backend with same protocol and query interface. More efficient querying for large datasets. Uses atomic transactions.

### Data Shapes

#### Incident (query result)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| incident_id | str | Yes | YYYYMMDD-CC-TTT format |
| source_names | list[str] | Yes | All sources that contributed records |
| incident_name | str | Yes | Derived per algorithm below |
| country | str \| None | No | Full country name (None if unknown) |
| country_code | str \| None | No | ISO 3166-1 alpha-2 (None if unknown) |
| country_group | str | Yes | "A", "B", or "C" (defaults to "C" if unknown) |
| disaster_type | str \| None | No | Disaster type string (None if unknown) |
| incident_level | int | Yes | 1–4 |
| priority | str | Yes | "HIGH", "MED", or "LOW" |
| should_report | bool | Yes | Reporting decision |
| overrides | list[str] | Yes | Applied overrides (may be empty) |
| report_date | date | Yes | Report date |
| source_urls | list[str] | **Optional** | All source URLs. Default: empty list. Collected from raw_fields where available: WHO has `ItemDefaultUrl` (prepend base), GDELT has url, DDG-NEWS has url, GDACS has `url.report`. |
| summary | str \| None | No | AI summary (if enriched) |
| rationale | str \| None | No | AI rationale (if enriched) |
| estimated_affected | int \| None | No | AI-extracted estimate |
| estimated_deaths | int \| None | No | AI-extracted estimate |
| ai_enriched | bool | Yes | Whether AI enrichment succeeded |
| record_count | int | Yes | Number of raw records in bundle |

#### incident_name Derivation (resolves COR-3/STO-3)

The `incident_name` field is derived using the following algorithm:
1. Use the title from the highest-reliability source's `raw_fields` (reliability order: GDACS > WHO > GDELT > DDG-NEWS).
2. If the highest-reliability source has no title, try the next most reliable source.
3. If no source has a title, generate a synthetic name: `"{disaster_type} in {country} ({date})"` using whatever fields are available. Substitute "Unknown disaster" for missing type, "Unknown location" for missing country, and the incident date for missing date.

Examples:
- GDACS bundle with title → use GDACS title
- WHO-only bundle → use WHO title
- Bundle with no titles, type=EQ, country=Philippines, date=2026-05-14 → "Earthquake in Philippines (2026-05-14)"
- Bundle with no titles, no type, no country → "Unknown disaster in Unknown location (2026-05-14)"

#### source_urls Derivation (resolves STO-4)

The `source_urls` field is built by collecting `url` fields from each record's `raw_fields`:
- WHO records: `raw_fields["url"]` (usually present)
- GDELT records: `raw_fields["url"]` (usually present)
- DDG-NEWS records: `raw_fields["url"]` (usually present)
- GDACS records: `raw_fields["url"]["report"]` if `url` dict is present (may be None if missing)

Result: a GDACS-only bundle will have `source_urls` populated from `url.report` if available. A mixed GDACS+WHO bundle will have URLs from both GDACS and WHO records.

#### Date Partitioning (resolves STO-2/Rule 30)

JSONL files are partitioned by `classification_date` — the date the bundle was classified, defined as the earliest `incident_date` from the bundle's records at classification time. If no date is available from any record, use the `fetched_at` date.

Storage path: `incidents/by-date/YYYY-MM-DD/incidents.jsonl` where `YYYY-MM-DD` is the `classification_date`.

### Integration Points

#### Override Re-evaluation -> Storage
- Purpose: Persist fully classified and enriched bundles
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
- **Trigger**: `store.store(bundles)` called after override re-evaluation
- **Input**: `list[IncidentBundle]` — complete bundles with all raw records and derived classification
- **Output**: `int` — count of new bundles stored (skips existing IDs)
- **Errors**: Storage failure → log error, pipeline continues with next bundle
- **Side Effects**: Writes to JSONL files or SQLite database
- **Preconditions**: Bundles have valid `incident_id` fields

**Atomic write (resolves STO-5):** JSONLStore writes using a temp-file-then-rename strategy:
1. Write bundle data to a temporary file at `incidents/by-date/YYYY-MM-DD/.tmp_incidents.jsonl`.
2. After successful write, `os.rename()` the temp file to `incidents/by-date/YYYY-MM-DD/incidents.jsonl`.
3. If the write fails (disk full, permission error, etc.), the temp file is deleted and the original file remains intact. The failure is logged.
4. For append operations to existing files: read existing content, merge with new content (dedup by incident_id), write to temp file, rename.

SQLiteStore uses database transactions with COMMIT/ROLLBACK for the same atomicity guarantee.

#### StorageBackend: query()

- **Actor**: Pipeline orchestrator or CLI
- **Trigger**: `store.query(date_from=..., date_to=..., **filters)` called
- **Input**: `{date_from: date, date_to: date, country_group: str?, disaster_type: str?, priority: str?, should_report: bool?, source_name: str?}`
- **Output**: `list[Incident]` — flattened view, not raw bundles
- **Errors**: Date file missing → skip (not an error). Malformed data → log warning, skip.
- **Side Effects**: Reads from disk, no writes
- **Preconditions**: `date_from <= date_to`. **If `date_from > date_to`, return empty list** (resolves STO-1). No error, no swap, no correction.

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
- JSONL path: `incidents/by-date/YYYY-MM-DD/incidents.jsonl` where the date is `classification_date`
- JSONL is append-only — records are never modified in place
- Both backends MUST implement the same `StorageBackend` protocol
- File encoding: UTF-8, one JSON object per line
- `source_urls` MAY be empty (some bundles may have no URLs) — this is not an error
- Inverted date range (`date_from > date_to`) returns empty list, not an error
- Storage writes MUST be atomic (temp file + rename for JSONL, transactions for SQLite)
- Storage write failure on one bundle MUST NOT prevent storage of other bundles
