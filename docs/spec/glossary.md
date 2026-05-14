# Glossary: Disaster Surveillance Reporter

> Living glossary of domain terms used in this project.
> Source of truth: `docs/spec/contract.md`
>
> Format: genus-differentia definitions.
> Genus = what category the thing belongs to.
> Differentia = what distinguishes it from other things in that category.

---

## Disaster Surveillance Reporter

**Genus:** A backend data pipeline
**Differentia:** that fetches disaster incident data from three free, zero-auth public APIs (GDACS, WHO DON, GDELT), correlates records about the same incident across sources, classifies deterministically with pure Python rules, enriches with AI (DuckDuckGo AI + DSPy), and stores complete bundles locally in JSONL or SQLite.

**Source:** 2026-05-14

---

## RawRecord

**Genus:** A Python dataclass representing an atomic data unit
**Differentia:** fetched from a single external source, containing `source_name` (str), `fetched_at` (datetime), and `raw_fields` (dict — the complete, untouched API response with no normalization).

**Source:** 2026-05-14

---

## IncidentBundle

**Genus:** A Python dataclass representing all information about one real-world incident
**Differentia:** containing one or more `RawRecord`s from any source, plus derived classification fields (country, level, priority, overrides) and AI enrichment fields (summary, rationale, estimates), identified by `incident_id` in the format `YYYYMMDD-CC-TTT`.

**Source:** 2026-05-14

---

## Incident

**Genus:** A Python dataclass representing a flattened query result
**Differentia:** derived from an `IncidentBundle` for reporting and analysis purposes, containing no raw records but instead aggregated fields like `source_names` (list of contributing sources), `source_urls` (all URLs), `record_count` (number of contributing records), and `incident_name` (best title). Returned by `StorageBackend.query()`.

**Source:** 2026-05-14

---

## Incident ID

**Genus:** A deterministic identifier for an incident bundle
**Differentia:** formatted as `YYYYMMDD-CC-TTT` where YYYYMMDD is the report date, CC is the ISO 3166-1 alpha-2 country code, and TTT is the 3-character disaster type code (e.g., EQ=Earthquake, FL=Flood, TC=Cyclone).

**Source:** 2026-05-14

---

## SourceAdapter

**Genus:** A Python Protocol for primary API data fetchers
**Differentia:** defining `source_name: str` and `fetch(client: httpx.Client) -> list[RawRecord]`, with the contract that it never raises exceptions (returns empty list on failure) and each `RawRecord.raw_fields` contains the complete, unmodified API response. Implemented by GDACS, WHO DON, and GDELT adapters.

**Source:** 2026-05-14

---

## NewsSearcher

**Genus:** A Python Protocol for supplementary news search
**Differentia:** defining `search(query, *, region, timelimit, max_results) -> list[RawRecord]`, wrapping `ddgs.DDGS.news()` to find additional articles about incidents when primary sources lack context. Returns empty list on failure, never raises. Records have `source_name="DDG-NEWS"`.

**Source:** 2026-05-14

---

## AIProvider

**Genus:** A Python Protocol for abstract AI chat interfaces
**Differentia:** defining `chat(prompt, *, model) -> str` that raises on unrecoverable failure (auth, network) but auto-retries on rate limits (HTTP 429). Implemented by `DuckAIProvider` which calls DuckDuckGo's `duckchat/v1` API directly via httpx.

**Source:** 2026-05-14

---

## DuckAIProvider

**Genus:** A concrete implementation of the AIProvider protocol
**Differentia:** calling DuckDuckGo's free `duckchat/v1` API via direct HTTP (no wrapper library), using a two-step protocol: GET `/status` to obtain a VQD token, then POST `/chat` with the token and model selection to receive an SSE stream response. Rate limited to ~1 request per 15 seconds.

**Source:** 2026-05-14

---

## StorageBackend

**Genus:** A Python Protocol for persistent storage adapters
**Differentia:** defining three methods: `store(bundles) -> int` (persist bundles, skip existing IDs, return new count), `query(date_from, date_to, **filters) -> list[Incident]` (query flattened incidents by date range and filters), and `exists(incident_id) -> bool` (dedup check). Implemented by JSONLStore and SQLiteStore.

**Source:** 2026-05-14

---

## JSONLStore

**Genus:** A StorageBackend implementation using JSONL files
**Differentia:** that writes one append-only file per date at `incidents/by-date/YYYY-MM-DD/incidents.jsonl`, stores complete `IncidentBundle`s including all raw records, and deduplicates by `incident_id`. The default storage backend.

**Source:** 2026-05-14

---

## SQLiteStore

**Genus:** A StorageBackend implementation using SQLite
**Differentia:** providing the same `StorageBackend` protocol as JSONLStore but with more efficient querying for large datasets. An alternative storage backend.

**Source:** 2026-05-14

---

## ClassifyEngine

**Genus:** A stateless Python classification service
**Differentia:** that deterministically maps an `IncidentBundle`'s raw records through source-specific level derivation (GDACS > WHO > GDELT > DDG-NEWS reliability order), country group lookup (A/B/C), priority matrix (level × group → priority + should_report), and six override criteria (O1–O6) to populate the bundle's classification fields.

**Source:** 2026-05-14

---

## Country Group

**Genus:** A geographic categorization assigned to every country
**Differentia:** as one of three tiers — Group A (25 Asia Pacific primary countries, highest monitoring priority), Group B (41 Asia Pacific secondary + Middle East + North Africa countries), or Group C (rest of world, lowest monitoring priority) — that determines monitoring priority and reporting thresholds via the priority matrix.

**Source:** 2026-05-14

---

## Country Group A

**Genus:** A set of 25 countries
**Differentia:** in the Asia Pacific region (Afghanistan, Bangladesh, Bhutan, Brunei, Cambodia, China, India, Indonesia, Japan, Laos, Malaysia, Maldives, Myanmar, Nepal, North Korea, Pakistan, Philippines, Singapore, South Korea, Sri Lanka, Taiwan, Thailand, Timor Leste, Vietnam) receiving the highest monitoring priority, where all levels (1–4) are reported.

**Source:** 2026-05-14

---

## Country Group B

**Genus:** A set of 41 countries
**Differentia:** spanning Asia Pacific 2, the Middle East, and North Africa receiving secondary monitoring priority, where levels 2–4 are reported but level 1 incidents are excluded.

**Source:** 2026-05-14

---

## Country Group C

**Genus:** The set of all remaining countries not in Groups A or B
**Differentia:** receiving the lowest monitoring priority, where only levels 3–4 are reported and levels 1–2 are excluded.

**Source:** 2026-05-14

---

## Incident Level

**Genus:** An integer severity rating from 1 to 4
**Differentia:** assigned by the deterministic ClassifyEngine using source-specific rules, indicating the scale and impact of the incident: Level 1 (MINOR), Level 2 (SIGNIFICANT), Level 3 (MAJOR), or Level 4 (CRITICAL).

**Source:** 2026-05-14

---

## Priority

**Genus:** A classification outcome of HIGH, MED, or LOW
**Differentia:** derived from the combination of incident level (1–4) and country group (A/B/C) via the priority matrix, determining the urgency of the incident for reporting purposes.

**Source:** 2026-05-14

---

## Priority Matrix

**Genus:** A lookup table mapping incident level × country group
**Differentia:** to a (priority, should_report) pair, where level 4 always produces HIGH/True, and lower levels produce decreasing priority depending on country group (e.g., level 2 in Group C produces LOW/False).

**Source:** 2026-05-14

---

## Should Report

**Genus:** A boolean classification outcome
**Differentia:** derived from the priority matrix and override rules, indicating whether an incident meets the threshold for reporting. Level 4 incidents are always reportable; lower levels depend on country group and override triggers.

**Source:** 2026-05-14

---

## Override

**Genus:** A special classification rule (numbered O1 through O6)
**Differentia:** that modifies the standard priority matrix outcome by detecting specific conditions — Humanitarian Crisis (O1), Multi-Regional (O2), Likely Development (O3), Environmental (O4), Forecast/Early Warning (O5), Singapore/SRC Connection (O6) — and potentially elevating priority or forcing should_report to True.

**Source:** 2026-05-14

---

## Override O1 — Humanitarian Crisis

**Genus:** An override rule detecting humanitarian crisis situations
**Differentia:** using keyword matching for GDACS sources and AI-assisted detection for WHO/GDELT sources. Marks incidents where a humanitarian crisis is declared or evident.

**Source:** 2026-05-14

---

## Override O2 — Multi-Regional

**Genus:** An override rule detecting multi-country impact
**Differentia:** using GDACS's structured `affectedcountries` field for GDACS sources and AI-assisted detection for WHO/GDELT sources. Marks incidents affecting multiple countries or regions.

**Source:** 2026-05-14

---

## Override O3 — Likely Development

**Genus:** An override rule detecting escalation potential
**Differentia:** using AI-assisted text understanding across all source types. Marks incidents likely to escalate or develop further.

**Source:** 2026-05-14

---

## Override O4 — Environmental

**Genus:** An override rule detecting environmental significance
**Differentia:** using a purely deterministic check: disaster type is in {WF (Wildfire), DR (Drought), FL (Flood)} AND the country is in Group A. No AI needed.

**Source:** 2026-05-14

---

## Override O5 — Forecast/Early Warning

**Genus:** An override rule detecting predictive or early warning events
**Differentia:** using GDACS's `istemporary` field for GDACS sources and AI-assisted detection for WHO/GDELT sources. Marks incidents that are forecasts or early warnings rather than current events.

**Source:** 2026-05-14

---

## Override O6 — Singapore/SRC

**Genus:** An override rule detecting Singapore or Singapore Red Cross relevance
**Differentia:** using keyword matching for "Singapore", "SRC", or "Red Cross" across all source types. Forces priority to HIGH and should_report to True.

**Source:** 2026-05-14

---

## GDACS

**Genus:** A free, zero-auth external data source
**Differentia:** the Global Disaster Alert and Coordination System providing natural disaster alerts via a GeoJSON REST API, with ~90% deterministic field availability including alertlevel, eventtype, iso3, and coordinates. The most reliable source for structured fields.

**Source:** 2026-05-14

---

## WHO DON

**Genus:** A free, zero-auth external data source
**Differentia:** the World Health Organization Disease Outbreak News providing disease outbreak reports via an OData REST API, with ~30% deterministic field availability. Country, disaster type, and incident level must be extracted from unstructured HTML content.

**Source:** 2026-05-14

---

## GDELT

**Genus:** A free, zero-auth external data source
**Differentia:** the Global Database of Events, Language, and Tone providing global news articles via a DOC API, with ~20% deterministic field availability. Country and disaster type must be extracted. Tone scores provide severity indication.

**Source:** 2026-05-14

---

## DDG News

**Genus:** A supplementary data source
**Differentia:** DuckDuckGo News accessed via the `ddgs` Python package's `news()` function, used after initial fetch to search for additional articles about specific incidents that need more context (missing country, low-structure source). Returns {date, title, body, url, source} per result.

**Source:** 2026-05-14

---

## Uncertainty Principle

**Genus:** A design principle governing raw data handling
**Differentia:** stating that field availability from any source cannot be guaranteed until real API responses are inspected, therefore all raw data must be preserved verbatim in `RawRecord.raw_fields` and classification/extraction must gracefully handle missing fields.

**Source:** 2026-05-14

---

## raw_fields

**Genus:** A dictionary field on RawRecord
**Differentia:** containing the complete, untouched source-specific API response with no normalization, serving as the single immutable record of what the source actually returned.

**Source:** 2026-05-14

---

## Correlation

**Genus:** A pipeline step that groups records
**Differentia:** matching `RawRecord`s from different sources that describe the same real-world incident into a single `IncidentBundle`, using date proximity, country overlap, and title similarity as matching criteria. Single-source records become bundles with one record.

**Source:** 2026-05-14

---

## Extractor Agent

**Genus:** A batched AI processing module
**Differentia:** that takes `IncidentBundle`s where country or disaster_type is still None after deterministic classification, and uses AI (via DSPy typed signatures) to extract country, disaster_type, estimated_affected, and estimated_deaths from unstructured text in the bundle's raw records. Lives in `ai/extractor.py`.

**Source:** 2026-05-14

---

## Classifier Agent

**Genus:** A batched AI processing module
**Differentia:** that takes `IncidentBundle`s with `should_report=True` and uses AI (via DSPy typed signatures) to generate summaries and detect overrides O1 (Humanitarian Crisis), O3 (Likely Development), and O5 (Forecast/Early Warning). Lives in `ai/classifier.py`.

**Source:** 2026-05-14

---

## DSPy

**Genus:** A Python framework for structured LLM programming
**Differentia:** used alongside direct DuckDuckGo AI calls to provide typed output signatures for incident extraction and classification, prompt optimization over time, and composable AI modules.

**Source:** 2026-05-14

---

## VQD Token

**Genus:** An authentication token for DuckDuckGo AI
**Differentia:** obtained via GET request to `duckduckgo.com/duckchat/v1/status` with the `x-vqd-accept: 1` header, returned as the `x-vqd-4` response header, and cached by `DuckAIProvider` for reuse in subsequent chat requests.

**Source:** 2026-05-14

---

## SSE (Server-Sent Events)

**Genus:** A streaming HTTP response format
**Differentia:** used by DuckDuckGo's `duckchat/v1/chat` endpoint to deliver AI responses as a sequence of `data: {...}` lines terminated by `data: [DONE]`, parsed by `DuckAIProvider._parse_sse()` into a concatenated string.

**Source:** 2026-05-14

---

## Batched Processing

**Genus:** An AI processing strategy
**Differentia:** where the Extractor and Classifier agents process ~10 `IncidentBundle`s per AI API call (rather than one per call) to minimize the total number of API calls (~6 calls per 50 incidents) and stay within the ~1 request/15 seconds rate limit.

**Source:** 2026-05-14

---

## Dedup

**Genus:** A data integrity mechanism
**Differentia:** preventing duplicate incident entries by checking `incident_id` via `StorageBackend.exists()` before storing, so that `StorageBackend.store()` returns only the count of genuinely new bundles.

**Source:** 2026-05-14

---

## Pipeline

**Genus:** The orchestrator module (`pipeline.py`)
**Differentia:** executing the six-step sequential flow: (1) fetch all 3 primary sources, (2) correlate records into bundles, (3) supplementary DDG News search for bundles needing context, (4) classify deterministically, (5) AI enrich in batches, (6) store complete bundles.

**Source:** 2026-05-14

---

## Fixture-First Testing

**Genus:** A testing strategy
**Differentia:** where each API is called once to capture raw JSON fixtures, then all subsequent tests run against those saved fixtures forever, ensuring tests are deterministic, reproducible, and require no live network access.

**Source:** 2026-05-14

---

## Alert Level

**Genus:** A GDACS-specific severity designation
**Differentia:** one of Green, Orange, or Red, mapped deterministically to incident levels: Green → 1, Orange → 3, Red → 4, with a severity bump for Group A countries.

**Source:** 2026-05-14

---

## Tone Score

**Genus:** A GDELT-specific sentiment metric
**Differentia:** a numeric value in `raw_fields` used to derive incident levels: tone < -5 → Level 4, tone < -3 → Level 3, tone >= 0 → Level 1, else → Level 2.

**Source:** 2026-05-14

---

## Disaster Type Code

**Genus:** A 3-character abbreviation used in incident IDs
**Differentia:** representing the disaster category: EQ (Earthquake), FL (Flood), TC (Cyclone), VO (Volcano), TS (Tsunami), DR (Drought), WF (Wildfire), and others. Occupies the TTT portion of the `YYYYMMDD-CC-TTT` incident ID format.

**Source:** 2026-05-14

---

## Source Reliability Order

**Genus:** A priority ordering of data sources
**Differentia:** GDACS > WHO > GDELT > DDG-NEWS, used by the ClassifyEngine to try the most reliable available source first when deriving classification fields from raw records in a bundle.

**Source:** 2026-05-14
