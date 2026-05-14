# Domain Model: Disaster Surveillance Reporter

> Structural view of the business domain.
> Source of truth: `docs/spec/contract.md`
>
> **Evolving document:** Updated during spec creation and refined during architecture.

---

## Summary

The Disaster Surveillance Reporter (DSR) is a backend pipeline that fetches disaster incident data from three free, zero-auth public APIs (GDACS, WHO DON, GDELT), correlates records about the same real-world incident across sources into `IncidentBundle`s, classifies deterministically using pure Python rules, enriches with AI (pluggable AIProvider via DSPy), and stores complete bundles locally (JSONL or SQLite). The domain is divided into five bounded contexts — Fetching, Correlation, Classification, Enrichment, and Storage — connected by a linear pipeline. Classification is the core domain logic: it maps every bundle through source-specific level derivation, a priority matrix (level × country group), and six override criteria (O1–O6) to produce a reproducible `should_report` decision. AI enrichment is optional and failure-safe, never blocking storage.

---

## Bounded Contexts

| Context | Responsibility | Key Entities | Business Capability | Why Separate |
|---------|----------------|--------------|---------------------|-------------|
| Fetching | Retrieves raw data from external sources (GDACS, WHO DON, GDELT) and supplementary news search (DDG News) | `RawRecord`, `SourceAdapter`, `NewsSearcher` | Incident acquisition from heterogeneous external APIs | Each source has unique API shapes and reliability levels; adapters must preserve raw responses unmodified and return empty lists on failure |
| Correlation | Groups `RawRecord`s about the same real-world incident into `IncidentBundle`s | `IncidentBundle`, Correlator | Multi-source record grouping by date proximity, country overlap, and title similarity | Matching across sources with different data shapes and determinism levels is a distinct concern from fetching or classifying |
| Classification | Deterministically assigns incident levels (1–4), priorities (HIGH/MED/LOW), country groups (A/B/C), and overrides (O1–O6) using pure Python rules | `ClassifyEngine`, country groups, priority matrix, overrides | Reproducible, auditable triage of every incident bundle | Pure logic with no I/O; must produce identical results given the same input; separate from fetching to keep classification testable |
| Enrichment | Adds AI-extracted fields (country, type, casualties) and AI-generated content (summaries, override detection) to classified bundles | `AIProvider`, extractor agent, classifier agent, DSPy signatures | Language tasks (extraction, summarization, override detection) from unstructured text | AI is non-deterministic, rate-limited, and may fail; isolating it ensures classification and storage never depend on AI availability |
| Storage | Persists complete `IncidentBundle`s (all raw records + classification + enrichment) and provides flattened `Incident` query results | `StorageBackend`, JSONLStore, SQLiteStore | Durable record of all bundles, queryable by date range and filters | Storage has fundamentally different concerns (file I/O, dedup, schema) from classification or enrichment; different change rate and failure modes |

---

## Entities

| Name | Type | Description | Bounded Context | Aggregate Root? |
|------|------|-------------|-----------------|-----------------|
| `RawRecord` | Value Object | Atomic data unit from any source. Fields: `source_name` (str), `fetched_at` (datetime), `raw_fields` (dict — complete untouched API response). Immutable after creation. | Fetching | No |
| `IncidentBundle` | Entity (Aggregate Root) | All information about one real-world incident. Contains one or more `RawRecord`s plus derived classification and AI enrichment fields. Identified by `incident_id` (format `YYYYMMDD-CC-TTT`). | Correlation / Classification / Enrichment | Yes |
| `Incident` | Value Object | Final flattened output for queries/reports. Derived from `IncidentBundle` — contains no raw records, instead has `source_names`, `source_urls`, `record_count`. What `StorageBackend.query()` returns. | Storage | No |
| `SourceAdapter` | Protocol | Defines the adapter contract for primary API fetchers: `source_name: str` and `fetch(client: httpx.Client) -> list[RawRecord]`. Never raises; returns empty list on failure. Implemented by GDACS, WHO, GDELT adapters. | Fetching | No |
| `NewsSearcher` | Protocol | Defines the supplementary search contract: `search(query, *, region, timelimit, max_results) -> list[RawRecord]`. Wraps `ddgs.DDGS.news()`. Returns empty list on failure. | Fetching | No |
| `ClassifyEngine` | Service | Stateless classification service. Consumes `IncidentBundle`, applies country-group lookup, source-specific level derivation (GDACS > WHO > GDELT > DDG-NEWS reliability order), priority matrix, and six override criteria. Produces classified `IncidentBundle`. | Classification | No |
| `AIProvider` | Protocol | Defines the AI chat contract: `chat(prompt, *, model) -> str`. Implemented by pluggable backends (OllamaProvider, GeminiProvider, OpenAIProvider). Pipeline works without AI (deterministic-only mode). | Enrichment | No |
| `Extractor Agent` | Service | Batched AI extraction: takes bundles with missing country/disaster_type, returns extracted fields. Uses DSPy typed signatures. | Enrichment | No |
| `Classifier Agent` | Service | Batched AI enrichment: takes `should_report=True` bundles, generates summaries and detects overrides O1, O3, O5. Uses DSPy typed signatures. | Enrichment | No |
| `StorageBackend` | Protocol | Defines storage contract: `store(bundles) -> int`, `query(date_from, date_to, **filters) -> list[Incident]`, `exists(incident_id) -> bool`. | Storage | No |
| `JSONLStore` | Service | Append-only, date-partitioned JSONL storage at `incidents/by-date/YYYY-MM-DD/incidents.jsonl`. Dedup by `incident_id`. Default backend. | Storage | No |
| `SQLiteStore` | Service | SQLite storage with same `StorageBackend` protocol. Alternative backend with more efficient querying. | Storage | No |

---

## Relationships

| Subject | Relation | Object | Cardinality | Notes |
|---------|----------|--------|-------------|-------|
| `SourceAdapter` | produces | `RawRecord` | 1:N | Each `fetch()` call returns 0–50+ raw records |
| `NewsSearcher` | produces | `RawRecord` | 1:N | Each `search()` call returns 0–5 supplementary records |
| Correlator | groups | `RawRecord` → `IncidentBundle` | N:1 | Multiple records grouped into one bundle by date + country + title |
| `ClassifyEngine` | classifies | `IncidentBundle` | 1:1 | Adds level, priority, country_group, overrides; deterministic |
| `ClassifyEngine` | references | Priority Matrix | 1:1 | Maps (level × country_group) → (priority, should_report) |
| `ClassifyEngine` | evaluates | Overrides O1–O6 | 1:6 | All six overrides checked per bundle |
| Extractor Agent | enriches | `IncidentBundle` | N:N | Batched: ~10 bundles per AI call |
| Classifier Agent | enriches | `IncidentBundle` | N:N | Batched: ~10 bundles per AI call |
| `StorageBackend` | stores | `IncidentBundle` | 1:N | Complete bundles with all raw records |
| `StorageBackend` | returns | `Incident` | 1:N | Flattened query results, not raw bundles |
| `IncidentBundle` | contains | `RawRecord` | 1:N | One or more raw records from any source |
| `Incident` | derived from | `IncidentBundle` | 1:1 | Flattened view without raw records |

---

## Aggregate Boundaries

| Aggregate | Root Entity | Invariants | Why Grouped | Bounded Context |
|-----------|-------------|------------|-------------|-----------------|
| Incident Bundle | `IncidentBundle` | Every bundle must have a valid `incident_id` (YYYYMMDD-CC-TTT). Classification fields (`country_group`, `incident_level`, `priority`, `should_report`) must be consistent with the priority matrix and overrides. All contained `RawRecord`s must relate to the same real-world incident. | Classification, enrichment, and storage all operate on the same incident identity; splitting them would allow inconsistent state. Raw records are immutable once grouped. | Correlation / Classification / Enrichment / Storage |
