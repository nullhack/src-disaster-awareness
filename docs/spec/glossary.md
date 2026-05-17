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
**Differentia:** that fetches disaster incident data from free, zero-auth public APIs (GDACS, WHO DON, GDELT, EONET), correlates records about the same incident across sources, classifies deterministically with pure Python rules, enriches with pluggable AIProvider (Ollama/Gemini/OpenAI/Opencode/DuckAI + DSPy), and stores complete bundles locally in JSONL or SQLite.

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

## last_updated

**Genus:** A datetime field on `IncidentBundle`
**Differentia:** recording the most recent modification time of the bundle. Set at bundle creation (correlation time) and reset only when new data is added (new DDG articles, new primary records). NOT reset when the pipeline processes a bundle but finds no new fingerprints. Used by the Active-Status Check to determine whether a bundle is ACTIVE (≤7 days) or STALE (>7 days).

**Source:** 2026-05-15

---

## Incident ID

**Genus:** A deterministic, source-stable identifier for an incident bundle
**Differentia:** formatted as `YYYYMMDD-CC-TTT` where YYYYMMDD is the earliest source-provided date (GDACS `fromdate`, WHO `PublicationDate`, GDELT `seendate`, EONET `geometry[0].date`, DDG-NEWS `date`; falls back to `fetched_at` only if no source date exists), CC is the ISO 3166-1 alpha-2 country code, and TTT is the 3-character disaster type code (e.g., EQ=Earthquake, FL=Flood, TC=Cyclone). Using source dates makes IDs stable across pipeline runs — the same source article produces the same ID regardless of fetch time.

**Source:** 2026-05-14 (updated 2026-05-15)

---

## SourceAdapter

**Genus:** A Python Protocol for primary API data fetchers
**Differentia:** defining `source_name: str` and `fetch(client: httpx.Client) -> list[RawRecord]`, with the contract that it never raises exceptions (returns empty list on failure) and each `RawRecord.raw_fields` contains the complete, unmodified API response. Implemented by GDACS, WHO DON, GDELT, and EONET adapters.

**Source:** 2026-05-14

---

## Source Fingerprint

**Genus:** A globally unique identifier for a single source record
**Differentia:** formatted as `{SOURCE_NAME}:{native_id}` where SOURCE_NAME is one of "GDACS", "WHO", "GDELT", or "DDG-NEWS" and native_id is source-specific: GDACS uses `eventid`, WHO uses `Id` or `DonId`, GDELT uses `url`, DDG-NEWS uses `url`. Used by the Source Pre-filter (step B) to discard records already seen in previous pipeline runs, and by store upsert for noop detection.

**Source:** 2026-05-15

---

## Stale Incident

**Genus:** An incident bundle lifecycle status
**Differentia:** indicating that no new data has been added to the bundle for 7 or more days (i.e., `now - last_updated > 7 days`). Stale incidents are removed from the pipeline during the Active-Status Check (step E), which runs after classification.

**Source:** 2026-05-15

---

## Active Incident

**Genus:** An incident bundle lifecycle status
**Differentia:** indicating that the bundle has received new data within the last 7 days (i.e., `now - last_updated ≤ 7 days`). Step E independently loads stored active bundles from storage via `get_active_bundles()` and merges them with in-flight bundles from Step D. Active incidents proceed from active-check through search and AI enrichment.

**Source:** 2026-05-15

---

## get_active_bundles

**Genus:** A StorageBackend method
**Differentia:** `get_active_bundles(reference_time=None) -> list[IncidentBundle]` — Returns all stored bundles where `should_report=True` AND `now - last_updated ≤ 7 days`. Used by Step E (active-check) to load bundles that need re-searching even when no new source records are available for them, preventing the source pre-filter from causing active bundles to be lost.

**Source:** 2026-05-16

---

## NewsSearcher

**Genus:** A Python Protocol for supplementary news search
**Differentia:** defining `search(query, *, region, timelimit, max_results) -> list[RawRecord]`, wrapping `ddgs.DDGS.news()` to find additional articles about incidents when primary sources lack context. Returns empty list on failure, never raises. Records have `source_name="DDG-NEWS"`.

**Source:** 2026-05-14

---

## AIProvider

**Genus:** A Python Protocol for abstract AI chat interfaces
**Differentia:** defining `chat(prompt, *, model) -> str` that raises on unrecoverable failure (auth, network) but auto-retries on rate limits (HTTP 429). Implemented by pluggable backends: OllamaProvider (local, free), GeminiProvider (Google, free tier), OpenAIProvider (paid), OpencodeProvider (local, free — uses opencode serve HTTP API), or DuckAIProvider (free — uses DuckDuckGo AI Chat via p2d-duck). The pipeline also supports running with AI disabled entirely.

**Source:** 2026-05-14

---

## DuckAIProvider

**Genus:** A concrete implementation of the AIProvider protocol

**Differentia:** using DuckDuckGo's free AI Chat (`duck.ai`) via the `p2d-duck` Python package, which embeds a mini-racer V8 JavaScript engine to solve the `x-vqd-hash-1` proof-of-work challenge that the `duckchat/v1` API requires. Zero-auth — no API key, no account, no registration. Models: GPT-4o mini (default), GPT-5 mini, Claude Haiku 4.5, Llama 4 Scout, Mistral Small, GPT-OSS 120B. Auto-retries on challenge failures with exponential backoff + jitter. Rate limit: ~1 request per 15 seconds. The model parameter is passed through to DuckChat.ask() but defaults to the DuckChat default model when unrecognized.

**Source:** 2026-05-16

---

## OpencodeProvider

**Genus:** A concrete implementation of the AIProvider protocol
**Differentia:** using opencode serve's embedded HTTP REST API (`POST /session` to create a persistent session, `POST /session/{id}/message` to send prompts and collect text responses). Configured via `OPENCODE_BASE_URL` (default `http://127.0.0.1:4096`), `OPENCODE_SERVER_PASSWORD` (required for `opencode:<password>` basic auth), and `OPENCODE_SESSION_TIMEOUT` (default 120s). Accepts but ignores the `model` parameter (openCode's model is configured server-side). Auto-recreates session on 401/404 from message endpoint. Supports rate-limit retry via same exponential backoff as other providers.

**Source:** 2026-05-15

---

## StorageBackend

**Genus:** A Python Protocol for persistent storage adapters
**Differentia:** defining seven methods: `store(bundles) -> int` (persist bundles, skip existing IDs, return new count), `query(date_from, date_to, **filters) -> list[Incident]` (query flattened incidents by date range and filters), `exists(incident_id) -> bool` (dedup check), `upsert(bundle) -> str` (insert new, update active with new fingerprints resetting `last_updated`, or no-op when no new data), `get_last_updated(incident_id) -> datetime | None` (query last modification time for active-status check), `get_source_fingerprints(incident_id) -> list[str]` (retrieve all source fingerprints for a stored bundle, used during active-status check to merge existing fingerprints into in-flight bundles), and `exists_by_source_fingerprint(fp) -> bool` (dedup by source fingerprint for pre-filter). Implemented by JSONLStore and SQLiteStore.

**Source:** 2026-05-14 (updated 2026-05-15)

---

## Upsert

**Genus:** A storage operation combining insert and update semantics
**Differentia:** used in pipeline step I (Store) as the primary persistence method. For each bundle: if the `incident_id` is not in storage → insert a new record (set `last_updated` to correlation time). If the bundle is in storage and new `source_fingerprints` are found → update the existing record (merge fingerprints, reset `last_updated`). If the bundle is in storage but no new fingerprints are found → no-op (do not change `last_updated`, preserving the monitoring window). Returns one of `"inserted"`, `"updated"`, or `"noop"`.

**Source:** 2026-05-15

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
**Differentia:** as one of three tiers — Group A (24 Asia Pacific primary countries, highest monitoring priority), Group B (41 Asia Pacific secondary + Middle East + North Africa countries), or Group C (rest of world, lowest monitoring priority) — that determines monitoring priority and reporting thresholds via the priority matrix.

**Source:** 2026-05-14

---

## Country Group A

**Genus:** A set of 24 countries
**Differentia:** in the Asia Pacific region (Afghanistan, Bangladesh, Bhutan, Brunei, Cambodia, China, India, Indonesia, Japan, Laos, Malaysia, Maldives, Myanmar, Nepal, North Korea, Pakistan, Philippines, Singapore, South Korea, Sri Lanka, Taiwan, Thailand, Timor Leste, Vietnam) receiving the highest monitoring priority, where all levels (1–4) are reported.

**Source:** 2026-05-14

---

## Country Group B

**Genus:** A set of 46+ countries
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
**Differentia:** the World Health Organization Disease Outbreak News providing disease outbreak reports via a REST API at `https://www.who.int/api/hubs/diseaseoutbreaknews`, with ~30% deterministic field availability. **No structured country or disaster type fields** — these must be extracted from Title/Overview text via AI or regex. `regionscountries` is a GUID reference (often null), not a usable country field. `ItemDefaultUrl` is a relative path, requiring `https://www.who.int` prefix for full URL.

**Source:** 2026-05-14

---

## GDELT

**Genus:** A free, zero-auth external data source
**Differentia:** the Global Database of Events, Language, and Tone providing global news articles via a DOC API, with ~20% deterministic field availability. Country and disaster type must be extracted. ArtList mode has no tone field — level derivation uses title keyword scan instead of tone scores.

**Source:** 2026-05-14

---

## EONET

**Genus:** A free, zero-auth external data source
**Differentia:** the NASA Earth Observatory Natural Event Tracker v3 providing curated near-real-time natural event metadata via a REST API. Returns structured JSON with 13 event categories (earthquakes, floods, volcanoes, wildfires, severe storms, droughts, landslides, and more). Each event includes coordinates, date, categories, source provenance, and optional magnitude. ~60% deterministic field availability: disaster type from categories, date from geometry, title verbatim. Country and impact estimates must be extracted via AI. Events sourced from GDACS (source.id=="GDACS") are duplicates — they are filtered at the adapter level.

**Source:** 2026-05-16

---

## DDG News

**Genus:** A supplementary data source
**Differentia:** DuckDuckGo News accessed via the `ddgs` Python package's `news()` function, used after initial fetch to search for additional articles about specific incidents that need more context (missing country, low-structure source). Returns `{date, title, body, url, source}` per result. Returns `[]` on failure, never raises.

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
**Differentia:** matching `RawRecord`s from different sources that describe the same real-world incident into a single `IncidentBundle`, using date proximity (±1 calendar day), ISO 3166-1 alpha-2 normalized country matching (via pycountry), and title similarity (SequenceMatcher ratio ≥ 0.6 after lowercase/strip/collapse normalization). When both records have country data, a country match is required — title similarity cannot override a country mismatch. Single-source records become bundles with one record.

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
**Differentia:** used alongside pluggable AIProvider backends to provide typed output signatures for incident extraction and classification, prompt optimization over time, and composable AI modules.

**Source:** 2026-05-14

---

## VQD Token (Deprecated)

**Genus:** ~~An authentication token for DuckDuckGo AI~~
**Differentia:** formerly used by DuckAIProvider to authenticate with `duckchat/v1`. **Deprecated** — the pipeline now uses pluggable AIProvider backends (Ollama/Gemini/OpenAI) which do not use VQD tokens.

**Source:** 2026-05-14 (deprecated)

---

## SSE (Server-Sent Events) (Deprecated)

**Genus:** ~~A streaming HTTP response format~~
**Differentia:** formerly used by DuckDuckGo's `duckchat/v1/chat` endpoint. **Deprecated** — the pipeline now uses pluggable AIProvider backends (Ollama/Gemini/OpenAI) which use standard request-response patterns, not SSE streaming.

**Source:** 2026-05-14 (deprecated)

---

## Batched Processing

**Genus:** An AI processing strategy
**Differentia:** where the Extractor and Classifier agents process ~10 `IncidentBundle`s per AI API call (rather than one per call) to minimize the total number of API calls (~6 calls per 50 incidents) and stay within the ~1 request/15 seconds rate limit.

**Source:** 2026-05-14

---

## Dedup

**Genus:** A data integrity mechanism
**Differentia:** preventing duplicate entries through two layers: (1) source-level: `exists_by_source_fingerprint(fp)` in step B prevents the same source record (identified by `{SOURCE_NAME}:{native_id}`) from being processed twice, and (2) bundle-level: `upsert()` in step I merges new fingerprints into existing bundles rather than creating duplicates.

**Source:** 2026-05-14 (updated 2026-05-15)

---

## Pipeline

**Genus:** The orchestrator module (`pipeline.py`)
**Differentia:** executing the nine-state sequential flow per pipeline-flow v4: (A) fetch all configured adapters, (B) source pre-filter (discard records whose source_fingerprint already exists in storage), (C) correlate into IncidentBundles using date proximity, country overlap, and title similarity, (D) classify deterministically (level, country_group, priority, should_report, initial overrides O2/O4/O6), after which not-reportable bundles exit early to store while reportable bundles continue through (E) active-status check (NEW → proceed, ACTIVE → merge fingerprints + proceed, STALE → removed), (F) supplementary DDG News search for active bundles, (G) AI enrich (extract fields → post-extract re-classify → generate summaries and detect O1/O3/O5), (H) override re-evaluation on post-enrichment flags, (I) store with upsert. The pipeline reads `pipeline-flow.yaml` at init time for state ordering and step configuration.

**Source:** 2026-05-14 (updated 2026-05-15)

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

## Active Monitoring Window

**Genus:** A time-based lifecycle boundary for incident bundles
**Differentia:** defined as 7 days from `last_updated`. Bundles with `now - last_updated ≤ 7 days` are ACTIVE — they are re-processed and re-checked for new data. Bundles with `now - last_updated > 7 days` are STALE — they are removed from the pipeline before classification to avoid unnecessary AI enrichment and processing costs.

**Source:** 2026-05-15

---

## Tone Score (Deprecated for ArtList mode)

**Genus:** A GDELT-specific sentiment metric
**Differentia:** a numeric value available via the GDELT ToneChart API (not ArtList mode). The ArtList mode used by the DSR pipeline does not include tone data. Level derivation for GDELT uses title keyword scan instead: "major"/"catastrophic"/"deadly"/"massive" → 3, "devastating"/"hundreds dead"/"thousands displaced"/"PHEIC" → 4.

**Source:** 2026-05-14

---

## Disaster Type Code

**Genus:** A 3-character abbreviation used in incident IDs
**Differentia:** representing the disaster category: EQ (Earthquake), FL (Flood), TC (Cyclone), VO (Volcano), TS (Tsunami), DR (Drought), WF (Wildfire), and others. Occupies the TTT portion of the `YYYYMMDD-CC-TTT` incident ID format.

**Source:** 2026-05-14

---

## Source Reliability Order

**Genus:** A priority ordering of data sources
**Differentia:** GDACS > WHO > GDELT > DDG-NEWS, used by the ClassifyEngine to select the level from the highest-reliability source that derived one (most-reliable-source-wins), not a fallback chain.

**Source:** 2026-05-14

---

## pycountry

**Genus:** A Python library (package `pycountry`)
**Differentia:** providing ISO 3166-1 alpha-2 country code lookups (name → code and code → name). Used by correlation for country normalization and by classification for country group assignment. Replaces the original manual `_COUNTRY_CODE` dictionary.

**Source:** 2026-05-15

---

## ISO 3166-1 alpha-2 Country Normalization

**Genus:** A correlation preprocessing step
**Differentia:** converting country names from source-specific formats to standardized two-letter ISO country codes via `pycountry`, enabling deterministic country matching across sources. Applied in the adapter layer before correlation.

**Source:** 2026-05-15

---

## Title Normalization

**Genus:** A correlation preprocessing step
**Differentia:** normalizing record titles before SequenceMatcher comparison: lowercase, strip leading/trailing whitespace, collapse multiple spaces to single space. Applied by the adapter layer to ensure consistent similarity scoring across sources.

**Source:** 2026-05-15

---

## ddgs

**Genus:** A Python package (`ddgs >= 9.14.2`)
**Differentia:** providing DuckDuckGo News search via `DDGS.news()`. Used for supplementary news search after initial classification for bundles needing context. Returns `[]` on failure, never raises. Supports `region`, `timelimit`, and `max_results` parameters.

**Source:** 2026-05-15
