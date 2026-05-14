# Disaster Surveillance Reporter v2 — Architecture Plan

> **Status:** WIP (2026-05-11)
> Complete rewrite plan synthesizing all research, specifications, and lessons from v1.

---

## Core Architecture

```
fetch → classify (Python, deterministic) → enrich (AI, optional) → store
```

**Principle:** Python does everything it can deterministically. AI only handles language-understanding tasks (summaries, rationale, free-text extraction) — and AI failure NEVER blocks storage.

---

## Minimum Sources (3, all zero-auth)

| # | Source | Covers | Adapter |
|---|--------|--------|---------|
| 1 | **GDACS** | 7 natural disaster types (EQ, TC, FL, VO, TS, DR, WF) | Rewrite against `events4app` GeoJSON endpoint |
| 2 | **WHO DON** | WHO-confirmed disease outbreaks | New — OData API, parse Title for country/disease |
| 3 | **GDELT** | All global disaster news via theme classification | New — DOC API, tone scoring for severity triage |

**Dropped:** HealthMap (no API), ProMED (no free API), ReliefWeb (deferred — needs appname registration).
**DDGS** kept as optional content retrieval utility, not an adapter.

---

## Package Structure (Minimum)

```
disaster_surveillance_reporter/
├── __init__.py            # Public API exports
├── _types.py              # All dataclasses & protocols (one file)
├── adapters/
│   ├── __init__.py        # SourceAdapter protocol + registry
│   ├── _base.py           # Shared HTTP caching, retry, rate-limit backoff
│   ├── gdacs.py           # GDACS events4app → RawIncidentData
│   ├── who_don.py         # WHO DON OData → RawIncidentData
│   └── gdelt.py           # GDELT DOC API → RawIncidentData
├── classify.py            # Pure Python classification engine
├── store.py               # JSONLStore (canonical, queryable by date)
├── enrich.py              # AI enrichment (optional, failure-safe)
├── pipeline.py            # Orchestrator
├── cli.py                 # Fire-based CLI
├── dedup.py               # URL/ID-based dedup (no fuzzy needed)
└── utils.py               # Date parsing, ISO3 mapping, country normalization
```

**Dropped from v1:** `similarity/` (fuzzy dedup — URL-based suffices), `opencode/` (moved into `enrich.py` with clean abstraction), `storage/google_sheets.py` and `storage/email_reporter.py` (those are reporters, not stores — add later).

---

## What's Fundamentally Different From Old Code

| Old | New | Why |
|-----|-----|-----|
| Pipeline uses AI for transform + classify | Python classifies deterministically, AI only enriches | Cheaper, faster, reproducible, AI-failure-tolerant |
| GDACS adapter calls USGS (earthquakes only) | Calls real GDACS API (all 7 disaster types) | Authority source, no USGS placeholder |
| Adapters mostly stubs (mock-only) | All adapters have real HTTP + mock mode | Actually works |
| `StorageBackend` is one protocol for all backends | `JSONLStore` is the canonical store; reporters separate | Different semantics, different contracts |
| AI `OpenCodeClient` embedded in pipeline | `enrich.py` is an optional, failure-safe step | AI is a plugin, not a dependency |
| CLI only uses GDACS | CLI supports all sources via adapter registry | Discoverable |
| No incident ID generation | `YYYYMMDD-CC-TTT` in pure Python | Traceable, deterministic |

---

## Data Flow (One Incident)

```
GDACSAdapter.fetch()
    ↓
RawIncidentData(source_name="GDACS", country="Indonesia", disaster_type="Earthquake",
                 raw_fields={alertlevel: "Orange", severitydata: {severity: 6.1}, ...})
    ↓
classify.ClassifyEngine.classify(raw)          ← PURE PYTHON
    ├─ country → group lookup: "Indonesia" → "A"
    ├─ alertlevel → level: "Orange" → 3
    ├─ (level=3, group="A") → priority="HIGH", should_report=True
    ├─ override checks: multi-country? no. humanitarian? no. SRC? no.
    └─ incident_id: "20260511-ID-EQ" (date-ISO3-type)
    ↓
ClassifiedIncident(incident_level=3, country_group="A", priority="HIGH", ...)
    ↓
enrich.enrich(classified)                      ← OPTIONAL AI
    ├─ summary: "M6.1 earthquake struck Sumatra, Indonesia..."
    ├─ rationale: "Orange alert from GDACS in Group A country..."
    └─ if AI fails → return classified unchanged, log warning
    ↓
EnrichedIncident (or ClassifiedIncident if AI skipped/failed)
    ↓
store.append(incident)                         ← JSONL, append-only
    ↓
incidents/by-date/2026-05-11.jsonl
```

---

## Type Definitions (`_types.py`)

### Stage 1: Adapter Output

```python
@dataclass(frozen=True, slots=True)
class RawIncidentData:
    """Adapter output — minimal flat record. One per incident per source."""
    source_name: str
    incident_name: str
    country: str
    disaster_type: str
    report_date: str           # ISO 8601
    source_url: str
    raw_fields: dict[str, Any]
```

### Stage 2: Python Classification Output

```python
@dataclass(frozen=True, slots=True)
class ClassifiedIncident:
    """Python-classified record — deterministic, before any AI."""
    incident_id: str           # YYYYMMDD-CC-TTT
    source_name: str
    incident_name: str
    country: str
    country_group: str         # A/B/C
    disaster_type: str
    incident_level: int        # 1-4
    priority: str              # HIGH/MEDIUM/LOW
    should_report: bool
    report_date: str
    source_url: str
    rationale: str             # Which rule produced this classification
    overrides: list[str]       # Which overrides triggered
    raw_fields: dict[str, Any]
    classified_at: str         # ISO 8601 timestamp
```

### Stage 3: AI Enrichment Output (Optional)

```python
@dataclass(frozen=True, slots=True)
class EnrichedIncident:
    """Classified + AI-generated fields. Identical to ClassifiedIncident if AI skipped/failed."""
    # All ClassifiedIncident fields, plus:
    summary: str | None
    ai_rationale: str | None
    estimated_affected: int | None
    estimated_deaths: int | None
    ai_enriched: bool          # True if AI ran successfully
```

---

## Classification Engine (`classify.py`)

### Level Derivation Per Source

| Source | Derivation | Rule |
|--------|-----------|------|
| GDACS | `alertlevel` in `raw_fields` | Green→1, Orange→3, Red→4. Level 2 from `severitydata.severity` if country_group=A. |
| WHO DON | Keywords in Summary/Title | "pandemic"/"PHEIC"→4, "epidemic"/"widespread"→3, "cluster"/"cases reported"→2, "isolated"/"suspected"→1. Default→2. |
| GDELT | Tone score in `raw_fields` | tone<-5.0→4, tone<-3.0→3, tone>=0→1, else→2. |

### Override Criteria (6)

| Code | Override | Trigger | Effect |
|------|----------|---------|--------|
| O1 | Humanitarian Crisis | Keywords in incident_name: "humanitarian crisis", "famine", "mass displacement" | Elevate should_report to True, priority to HIGH |
| O2 | Multi-Regional Impact | GDACS affectedcountries length>1, WHO Title contains "multi-country", GDELT themes cross country boundaries | Elevate should_report to True |
| O3 | Likely Further Development | alertscore decreasing over time (GDACS), tone worsening (GDELT), "spreading" status (WHO) | Elevate level by 1 (max 4) |
| O4 | Environmental/Climate Awareness | WF (wildfire), DR (drought), FL (flood) in Group A | Elevate level by 1 (max 4) if currently level 1 |
| O5 | Forecast/Early Warning | GDACS `istemporary=true`, WHO `investigation_status=under_investigation` | Reduce level by 1 (min 1), tag as "forecast" |
| O6 | Singapore/SRC Connection | country="Singapore" OR incident_name mentions "Singapore"/"SRC"/"Red Cross" | Elevate priority to HIGH, should_report=True |

### Priority Matrix

From `monitoring_rules.md`, encoded as pure Python:

| Level | Group A | Group B | Group C |
|-------|---------|---------|---------|
| 4 | HIGH/Yes | HIGH/Yes | HIGH/Yes |
| 3 | HIGH/Yes | MEDIUM/Yes | MEDIUM/Yes |
| 2 | MEDIUM/Yes | MEDIUM/Yes | LOW/No |
| 1 | MEDIUM/Yes | LOW/No | LOW/No |

### Incident ID Format

```
YYYYMMDD-CC-TTT

YYYYMMDD = report_date in UTC
CC       = 2-letter country code (from ISO2 mapping)
TTT      = 3-letter type code (e.g., EQ=Earthquake, TC=Cyclone, FL=Flood, VO=Volcano,
           TS=Tsunami, DR=Drought, WF=Wildfire, DIS=Disease, OTH=Other)
```

---

## Adapter Base Class (`adapters/_base.py`)

Every adapter gets these behaviors for free:

| Feature | Implementation |
|---------|---------------|
| HTTP caching | In-memory dict, TTL-configured (default 300s). Return cached result if within TTL. |
| Retry with backoff | 3 attempts, exponential (1s, 2s, 4s). Only on transient errors (5xx, timeout). |
| Rate-limit detection | Catch HTTP 429/202. Log warning, return empty list. Don't hammer backends. |
| Graceful failure | `fetch()` NEVER raises. Returns `[]` on any exception. Logs the error. |
| Mock mode | `mock_mode=True` → calls `_mock_fetch()` returning representative test data. |
| Freshness filtering | Optional `max_age_hours` parameter. Filters out events older than the window. |

```python
class BaseAdapter(SourceAdapter):
    def __init__(self, *, timeout=10.0, mock_mode=False, cache_ttl=300, max_age_hours=168):
        self._timeout = timeout
        self._mock_mode = mock_mode
        self._cache_ttl = cache_ttl
        self._max_age_hours = max_age_hours
        self._cache: list[RawIncidentData] | None = None
        self._cache_time: datetime | None = None

    def fetch(self) -> list[RawIncidentData]:
        if self._mock_mode:
            return self._mock_fetch()
        if self._cache_valid():
            return self._cache
        try:
            result = self._with_retry(self._real_fetch)
            self._cache = result
            self._cache_time = datetime.now(timezone.utc)
            return result
        except Exception:
            return self._cache or []

    def _real_fetch(self) -> list[RawIncidentData]:
        raise NotImplementedError

    def _mock_fetch(self) -> list[RawIncidentData]:
        raise NotImplementedError
```

---

## Per-Adapter Specs

### GDACS Adapter

| Item | Value |
|------|-------|
| Endpoint | `GET https://www.gdacs.org/gdacsapi/api/events/geteventlist/events4app` |
| Response | GeoJSON FeatureCollection, ~140KB, 50-80 features |
| Dedup key | `eventid` + `episodeid` |
| Default max_age_hours | 168 (7 days) |
| Poll interval | 6 minutes |
| Level mapping | `alertlevel`: Green→1, Orange→3, Red→4. Level 2 from `severitydata.severity` if country_group=A. |

### WHO DON Adapter

| Item | Value |
|------|-------|
| Endpoint | `GET https://www.who.int/api/hubs/diseaseoutbreaknews?$top=20&$orderby=PublicationDateAndTime desc` |
| Response | OData JSON, ~20 records |
| Dedup key | `DonId` |
| Default max_age_hours | 720 (30 days) |
| Poll interval | 6 hours |
| Country extraction | Parse from Title: "Measles - Bangladesh" → "Bangladesh". "Multi-country" → check Overview HTML. |
| Level mapping | Keyword scanning of Summary/Assessment. Default→2. |

### GDELT Adapter

| Item | Value |
|------|-------|
| Endpoint | `GET https://api.gdeltproject.org/api/v2/doc/doc?query={QUERY}&mode=artlist&format=json&maxrecords=50&timespan=15min` |
| Response | JSON, up to 50 articles |
| Dedup key | `url` (MD5 hash) |
| Default max_age_hours | 24 |
| Poll interval | 15 minutes |
| Query | Theme-based: `NATURAL_DISASTER` OR `HEALTH_PANDEMIC` OR `HEALTH_EPIDEMIC` |
| Level mapping | tone<-5.0→4, tone<-3.0→3, tone>=0→1, else→2 |
| Post-filter | Remove tone>0 articles (recovery stories, not active disasters) |

---

## Canonical Store (`store.py`)

### JSONLStore

```
incidents/
└── by-date/
    ├── 2026-05-09.jsonl
    ├── 2026-05-10.jsonl
    └── 2026-05-11.jsonl
```

- **One file per date.** No subdirectories, no reference files.
- **Append-only.** Records are appended, never modified in place.
- **Dedup by `incident_id`** within today's file.
- **Query by scanning** files in date range, filtering in memory. With <100 incidents/day, O(n) is fine.
- **Updates** to an existing incident produce a NEW record with same `incident_id` and incremented `updated_date`.

### Interface

```python
class JSONLStore:
    def append(self, records: list[dict]) -> int:
        """Append to today's date file. Skips duplicates by incident_id. Returns count written."""

    def query(self, *, date_from: str, date_to: str,
              country_group: str | None = None,
              incident_type: str | None = None,
              priority: str | None = None,
              should_report: bool | None = None) -> list[dict]:
        """Scan date files in range, filter in memory."""

    def read_date(self, date: str) -> list[dict]:
        """Read all incidents for a specific date."""

    def last_seen_incident_ids(self) -> set[str]:
        """Return set of incident_ids seen today (for dedup)."""
```

---

## AI Enrichment (`enrich.py`)

### Contract

```python
class Enricher:
    """Optional AI enrichment. Failure-safe — never blocks storage."""

    def __init__(self, *, timeout: float = 30.0, enabled: bool = True):
        ...

    def enrich(self, classified: ClassifiedIncident) -> EnrichedIncident:
        """Add AI-generated summary and rationale. Returns classified unchanged if AI fails."""
```

### AI Responsibilities

| Task | When | Fail-safe |
|------|------|-----------|
| Generate `summary` | Always (if enabled) | Empty string on failure |
| Generate `ai_rationale` | Level ≥ 3 or should_report=True | Empty string on failure |
| Extract `estimated_affected` | When not in `raw_fields` and level ≥ 3 | None on failure |
| Extract `estimated_deaths` | When not in `raw_fields` and level ≥ 3 | None on failure |

### Design Constraints

1. **Timeout:** 30 seconds per enrichment call. Enricher must not block the pipeline.
2. **Failure = pass-through:** If AI is unreachable, return `EnrichedIncident` with `ai_enriched=False` and all AI fields as `None`. The classified record is stored regardless.
3. **Stateless:** Each call is independent. No context accumulation between incidents.
4. **Pluggable backend:** The AI client is injected, not hardcoded. Swap OpenAI for Anthropic or mock without changing `Enricher`.

---

## Pipeline Orchestrator (`pipeline.py`)

```python
class Pipeline:
    def __init__(self, adapters: list[SourceAdapter], classifier: ClassifyEngine,
                 store: JSONLStore, enricher: Enricher | None = None):
        ...

    def run(self) -> PipelineResult:
        """fetch → classify → enrich → store. Returns counts by stage."""
        raw = self._fetch_all()
        classified = self._classify_all(raw)
        enriched = self._enrich_all(classified)
        stored = self._store_all(enriched)
        return PipelineResult(
            fetched=len(raw),
            classified=len(classified),
            enriched=len([e for e in enriched if e.ai_enriched]),
            stored=stored,
        )
```

---

## CLI (`cli.py`)

```python
class DisasterCLI:
    """Disaster Surveillance Reporter v2 CLI."""

    def fetch(self, source: str = "all"):
        """Fetch incidents from source(s). Sources: gdacs, who, gdelt, all."""

    def run(self, enrich: bool = False):
        """Run full pipeline. --enrich to enable AI enrichment."""

    def query(self, *, date_from: str, date_to: str,
              country_group: str | None = None, priority: str | None = None):
        """Query stored incidents."""

    def status(self):
        """Show pipeline statistics."""
```

---

## Dedup Strategy (`dedup.py`)

Three-tier dedup:

| Tier | Method | When |
|------|--------|------|
| 1 | `incident_id` match | Within same store file — skip append |
| 2 | Source-specific ID (GDACS `eventid`, WHO `DonId`, GDELT `url` hash) | Within same source across cycles — skip fetch output |
| 3 | Content similarity (rapidfuzz) — v1.1 | Cross-source same event detection — merge, don't skip |

v1 implements tiers 1 and 2 only. Tier 3 is deferred to v1.1.

---

## Dependencies (`pyproject.toml`)

```toml
dependencies = [
    "httpx>=0.28.0",       # HTTP client for all adapters
    "fire>=0.7.1",         # CLI
    "python-dotenv>=1.2.2", # Environment config
]
```

**Removed from v1:** `rapidfuzz` (no fuzzy dedup in v1), `google-api-python-client`, `gspread` (reporters deferred), `dotenv` (replaced by `python-dotenv`, but check — `dotenv` was also listed).

---

## Mapping Source Specs to Implementation

| Source Spec Doc | Adapter File | Key Implementation Details |
|-----------------|-------------|---------------------------|
| `gdacs_source_specification.md` | `adapters/gdacs.py` | Single `events4app` call, `GDACS_TYPE_MAP`, `raw_fields.alertlevel` |
| `who_healthmap_source_specification.md` (WHO portion) | `adapters/who_don.py` | OData query, Title→country parse, `raw_fields.don_id` |
| `gdelt_source_specification.md` | `adapters/gdelt.py` | DOC API theme filter, tone scoring, `gdeltdoc` library |
| `adapter_specification.md` | `adapters/_base.py` + `adapters/__init__.py` | Protocol, contract, `SourceAdapter` interface |
| `data_schema.md` | `_types.py` | `RawIncidentData` + `ClassifiedIncident` + `EnrichedIncident` |
| `monitoring_rules.md` | `classify.py` | Country groups, priority matrix, overrides, level mapping |
| `storage_specification.md` | `store.py` | `JSONLStore` with by-date files, query interface |
| `IN_20260511_ai_scope_decision.md` | `enrich.py` | Optional enrichment, failure-safe, AI only for language tasks |

---

## Open Questions

| # | Question | Options |
|---|----------|---------|
| 1 | **Package name:** Keep `disaster_surveillance_reporter`? | Keep (familiar) / Shorten to `dsr` |
| 2 | **Directory structure:** Subpackages or flat modules? | Keep subpackages (clean, existing) / Flatten to modules at root |
| 3 | **Similarity module:** Include fuzzy dedup in v1? | Drop (URL-based suffices for v1) / Include (cross-source dedup is high-value) |
| 4 | **ReliefWeb:** Include or defer? | Defer until appname registered / Include as ready-to-activate stub |
| 5 | **DDGS `extract()`:** Include as utility? | Yes — add `utils.fetch_article_content(url)` / Skip for v1 |
| 6 | **Tests:** Strategy? | TDD from scratch (write test → implement → pass) / Keep existing tests and adapt |
| 7 | **Old code disposal:** How to handle? | Delete all old code, start clean / Keep old code in separate branch, build fresh in `main` |
| 8 | **GDELT backend:** Free DOC API or BigQuery? | Start with free DOC API / Jump straight to BigQuery for production reliability |
| 9 | **Mock data:** Realistic or minimal? | Realistic (representative of actual API responses) / Minimal (just enough to pass tests) |

---

## Changes

| Date | Source | Change | Reason |
|------|--------|--------|--------|
| 2026-05-11 | Architecture plan | Created v2 rewrite plan from all research, specs, and IN files | Synthesize v1 lessons into clean architecture |
