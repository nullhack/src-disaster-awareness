# DDGS Source Specification

> **Status:** BASELINED (2026-05-11)
> API research, field mapping, and adapter design for DDGS (metasearch) as a supplementary news monitoring source.

---

## API Details

| Item | Value |
|------|-------|
| Package | `ddgs` (v9.14.2, May 2026) — formerly `duckduckgo_search` (v8.1.1, deprecated) |
| Install | `pip install ddgs` |
| GitHub | `github.com/deedy5/ddgs` — 2.6k stars, actively maintained (weekly releases) |
| Type | Metasearch aggregator (scrapes Bing, Yahoo, DuckDuckGo, Brave, Google, Mojeek, Yandex, Wikipedia) |
| Auth | **None** — no API key, no registration |
| License | MIT |
| Python | >= 3.10 |
| Disclaimer | "For educational purposes only" — not an official API. Use with awareness of legal gray area. |
| Reliability | Moderate — backends can return empty intermittently. Not a production SLAd API. |

---

## DDGS Class

```python
from ddgs import DDGS

ddgs = DDGS(
    proxy: str | None = None,       # "socks5h://127.0.0.1:9150" or "tb" for Tor
    timeout: int = 5,               # HTTP client timeout in seconds
    verify: bool | str = True,      # SSL verification
)
```

Supports optional P2P DHT cache network for repeated queries (90% faster, 50ms vs 1-2s).

---

## Methods

| Method | Purpose | Backends |
|--------|---------|----------|
| `text()` | Web search | bing, brave, duckduckgo, google, grokipedia, mojeek, yandex, yahoo, wikipedia |
| `news()` | News search | bing, duckduckgo, yahoo |
| `images()` | Image search | bing, duckduckgo |
| `videos()` | Video search | duckduckgo |
| `extract()` | URL content extraction | Direct HTTP fetch |
| `books()` | Book search | annasarchive |

---

## `news()` — Primary Method for Surveillance

### Signature

```python
def news(
    query: str,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: str | None = None,
    max_results: int | None = 10,
    page: int = 1,
    backend: str = "auto",
) -> list[dict[str, str]]:
```

### Parameters

| Parameter | Type | Values | Default | Notes |
|-----------|------|--------|---------|-------|
| `query` | `str` | Free text + DDG operators | **Required** | Supports `"exact phrase"`, `-exclude`, `+include`, `site:`, `intitle:`, `inurl:` |
| `region` | `str` | `{country}-{language}` code | `"us-en"` | 50+ regions (see Region Codes below). Strongly influences result relevance. |
| `safesearch` | `str` | `"on"`, `"moderate"`, `"off"` | `"moderate"` | Use `"off"` for disaster monitoring. |
| `timelimit` | `str \| None` | `"d"` (day), `"w"` (week), `"m"` (month) | `None` | **Critical for surveillance**: use `"d"` for 15-min cycles. |
| `max_results` | `int \| None` | Positive int or `None` | `10` | `None` returns first page only (~20-25 results). |
| `page` | `int` | Positive int | `1` | Pagination for additional results. |
| `backend` | `str` | `"auto"`, or comma-delimited: `"bing"`, `"yahoo"`, `"duckduckgo"` | `"auto"` | Use `"bing,yahoo"` for disaster monitoring (redundant indices). |

### Return Structure

Each result is a `dict`:

```python
{
    "date": "2026-05-11T09:15:00+00:00",   # ISO 8601 (may be "" if unavailable)
    "title": "M6.5 earthquake hits northern Philippines",
    "body": "A magnitude 6.5 earthquake struck...",   # Snippet, max ~300 chars
    "url": "https://www.reuters.com/...",
    "image": "https://img.reuters.com/...",            # May be ""
    "source": "Reuters",
}
```

### Backend-Specific Behavior

| Backend | Quality for disaster news | Notes |
|---------|--------------------------|-------|
| `bing` | Best — rich metadata, reliable dates, strong region filtering | Recommended primary |
| `yahoo` | Good — strong on US/international, weaker on Asia-Pacific | Good redundancy |
| `duckduckgo` | Decent — aggregates multiple sources, may miss localized media | Falls back if Bing/Yahoo fail |
| `auto` | Best coverage but slower | Random order, tries all |

---

## Field Mapping to RawIncidentData

| RawIncidentData Field | DDGS Source | Parsing Logic |
|-----------------------|-------------|---------------|
| `source_name` | Hardcoded `"DDGS"` | — |
| `incident_name` | `result["title"]` | Direct. May include source name fragment; clean if needed. |
| `country` | Query context | Derived from `region` parameter. E.g., `region="ph-en"` → "Philippines". |
| `disaster_type` | Query context | Derived from `query` keyword matched to disaster type enum. |
| `report_date` | `result["date"]` | Parse ISO 8601. May be `""` — fall back to current time. |
| `source_url` | `result["url"]` | Direct. Must be deduped by URL hash. |
| `raw_fields` | All result fields | See below |

### raw_fields for DDGS

```json
{
  "snippet": "A magnitude 6.5 earthquake struck...",
  "image": "https://img.reuters.com/...",
  "publisher": "Reuters",
  "query_used": "earthquake Philippines",
  "region": "ph-en",
  "backend_actual": "bing",
  "retrieved_at": "2026-05-11T10:00:00Z"
}
```

---

## Region Codes — Asia Pacific + MENA

### Available Direct Region Codes

| Code | Country | Code | Country |
|------|---------|------|---------|
| `jp-jp` | Japan | `ph-en` / `ph-tl` | Philippines |
| `id-id` / `id-en` | Indonesia | `my-ms` / `my-en` | Malaysia |
| `in-en` | India | `th-th` | Thailand |
| `cn-zh` | China | `vn-vi` | Vietnam |
| `kr-kr` | Korea | `sg-en` | Singapore |
| `tw-tzh` | Taiwan | `hk-tzh` | Hong Kong |
| `au-en` | Australia | `nz-en` | New Zealand |
| `tr-tr` | Turkey | `xa-ar` / `xa-en` | Arabia (Arabic/English) |
| `il-he` | Israel | `pk-en` | Pakistan |
| `bd-en` | Bangladesh | | |

### Notable Gaps (No Direct Region Codes)

| Country | Workaround |
|---------|------------|
| Myanmar | Use `wt-wt` (global) + `query="flood Myanmar"` |
| Nepal, Sri Lanka | Use `wt-wt` + country name in query |
| Iran | No region code; use `wt-wt` with Farsi/English keywords |
| Egypt, Iraq, Saudi Arabia | Use `xa-ar` or `xa-en` (pan-Arabic) |
| Pacific Islands (Fiji, Vanuatu, Tonga, Samoa, PNG) | Use `wt-wt` + country name in query |
| Afghanistan | Use `wt-wt` + country name in query |

---

## Rate Limiting

### Exception Classes

```python
from ddgs.exceptions import RatelimitException, TimeoutException, DuckDuckGoSearchException
```

### Known Patterns

| Pattern | Cause | Mitigation |
|---------|-------|------------|
| `RatelimitException` (HTTP 202/429) | Too many requests from same IP | Exponential backoff (1s→2s→4s), rotate proxies, use `proxy="tb"` |
| Empty results | IP flagged | Wait 5-10 min, change proxy |
| Successive calls blocked | DDG intermediary rate limiting | Use `backend="bing"` directly |
| `TimeoutException` | Network issues | Retry with 2x timeout |

### Practical Limits

| Scenario | Requests/min | Safe for 15-min cycle? |
|----------|-------------|------------------------|
| No proxy | 10-20 | Yes (1-2 queries/cycle) |
| With Tor/proxy rotation | 30-60 | Yes (5-10 queries/cycle) |
| DHT network (beta) | 90% faster for repeated queries | Yes (but eventual consistency, 1-5 min) |

### Retry Template

```python
import time
from ddgs import DDGS
from ddgs.exceptions import RatelimitException

ddgs = DDGS(timeout=10)

for attempt in range(3):
    try:
        results = ddgs.news("earthquake", region="ph-en", timelimit="d", max_results=20, backend="bing,yahoo")
        break
    except RatelimitException:
        time.sleep(2 ** attempt)
    except Exception:
        time.sleep(5)
```

---

## Polling Strategy

| Setting | Value | Rationale |
|---------|-------|-----------|
| Poll interval | 15 minutes | News indices update within minutes; 15 min catches breaking stories |
| Queries per cycle | 10-20 (1 search term per priority country) | Covers Group A countries with primary disaster terms |
| Max results per query | 20 | First page catches breaking news |
| Timeout | 10 seconds | News search responses are fast (<2s) |
| Retry | 3 attempts, exponential backoff | Transient rate limiting |
| Cache TTL | 5 minutes | Prevent duplicate queries within a cycle |
| Dedup key | MD5 hash of `url` | URL is the dedup anchor; title/body change on republish |

### Query Template

```python
DISASTER_TERMS = [
    "earthquake", "flood", "cyclone", "typhoon", "tsunami",
    "volcano", "landslide", "outbreak", "epidemic", "drought",
    "heatwave", "wildfire", "storm",
]

PRIORITY_REGIONS = [
    ("ph-en", "Philippines"),
    ("id-id", "Indonesia"),
    ("jp-jp", "Japan"),
    ("in-en", "India"),
    ("bd-en", "Bangladesh"),
    ("vn-vi", "Vietnam"),
    ("th-th", "Thailand"),
    ("my-en", "Malaysia"),
    ("pk-en", "Pakistan"),
    ("tr-tr", "Turkey"),
    ("cn-zh", "China"),
    ("xa-en", "Middle East"),
    ("sg-en", "Singapore"),
    ("au-en", "Australia"),
]

# Per-cycle: rotate through priority regions with mixed search terms
for region_code, country_name in PRIORITY_REGIONS[:8]:  # 8 regions/cycle
    for term in DISASTER_TERMS[:3]:  # 3 most likely terms per region
        results = ddgs.news(term, region=region_code, timelimit="d", max_results=15)
```

---

## `text()` as News Fallback

The `text()` method returns web search results (not news-specific) but can catch content that news backends miss:

```python
def text(
    query: str,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: str | None = None,
    max_results: int | None = 10,
    page: int = 1,
    backend: str = "auto",
) -> list[dict[str, str]]:
```

Return fields: `{"title", "href", "body"}` — **no date, no source**. Use only when `news()` returns empty for critical regions.

### Search Operators

| Operator | Example | Effect |
|----------|---------|--------|
| `"exact phrase"` | `"flash flood"` | Exact match |
| `-word` | `earthquake -movie` | Exclude term |
| `+word` | `cyclone +warning` | Require term |
| `site:domain` | `earthquake site:reuters.com` | Restrict to domain |
| `intitle:word` | `intitle:tsunami` | Word in page title |
| `inurl:word` | `inurl:disaster` | Word in URL |

---

## `extract()` for Full Content

When a news article's snippet is insufficient, fetch the full URL content:

```python
result = ddgs.extract(url="https://www.reuters.com/...")
# Returns dict with full page text, title, etc.
```

Use **sparingly** — each `extract()` call is a separate HTTP request to the target site.

---

## What Python Can Extract (No AI Needed)

| Field | Source | Logic |
|-------|--------|-------|
| `incident_name` | `result["title"]` | Direct |
| `country` | Region mapping | `region="ph-en"` → "Philippines" |
| `country_group` | Country lookup | `COUNTRY_GROUPS` dict |
| `disaster_type` | Query keyword match | "earthquake" → "Earthquake", "flood" → "Flood", etc. |
| `report_date` | `result["date"]` | Parse ISO 8601 |
| `source_url` | `result["url"]` | Direct |
| `publisher` | `result["source"]` | Direct |
| Dedup | URL hash | MD5 of `result["url"]` |
| Freshness filter | `report_date` vs cutoff | Per-source window (24 hours for news) |

### What AI Needs to Extract

- `summary` — from `result["body"]` snippet (summarize, clean publisher artifacts)
- `impact.impact_description` — from full article if `extract()` was called
- `classification_metadata.rationale` — why this news item was classified at this level
- Country disambiguation — when region code is absent and title mentions a country (e.g., "Flood hits Myanmar" from `wt-wt` region)
- Disease name standardization — from title/body text

---

## Coverage Gaps

| Gap | Severity | Workaround |
|-----|----------|------------|
| No geolocation | High | No lat/lng in results. Must geocode locations from title/body. |
| No severity classification | Medium | Parse body text for magnitude/intensity keywords. |
| No language translation | Medium | Non-English results in regional queries. Need translation layer. |
| No official source filtering | Low | Filter by `source` field (e.g., prefer Reuters, AP, AFP). |
| Region code gaps | Medium | Countries without region codes (Iran, Myanmar, Nepal, Sri Lanka, Pacific Islands) use `wt-wt` global. |
| Legal gray area | Medium | Library disclaimer: "for educational purposes only." Not an official API. |
| Inconsistent date field | Medium | `date` can be `""`. Fall back to `retrieved_at`. |

---

## Role in Surveillance System

**DDGS is a supplementary news source.** It catches breaking news that official feeds (GDACS, WHO DON) may miss or delay. It is NOT a primary source for:

- Earthquake/tsunami alerts (GDACS is faster and has geolocation)
- Official disease reports (WHO DON is authoritative)
- Humanitarian situation reports (ReliefWeb has structured metadata)

DDGS IS useful for:

- Early detection of disasters in countries without dense seismic/cyclone monitoring
- Flood, landslide, heatwave detection (no global monitoring API for these)
- Disease outbreak rumors that haven't reached WHO publication threshold
- Regional news in local languages about disaster impacts

---

## Comparison: DDGS vs GDELT vs GDACS vs WHO

| Criterion | DDGS | GDELT | GDACS | WHO DON |
|-----------|------|-------|-------|---------|
| Auth | None | None | None | None |
| Data type | News headlines/snippets | Structured events + themes | Natural disasters | Disease outbreaks |
| Geolocation | None | Yes (lat/lng) | Yes (lat/lng) | No (country in text) |
| Severity | None | Tone/sentiment | alertlevel + severitydata | Keywords in prose |
| Update frequency | Minutes (news index) | 15 min | 6 min | Days |
| Rate limits | ~20 req/min | Moderate (API), unlimited (BigQuery) | None | None |
| Reliability | Moderate (scraper) | High (15+ years running) | High | High |
| Asia-Pacific coverage | Good (region codes exist) | Excellent (global) | Excellent | Good |
| Disaster types | Keyword-dependent | Theme-classified | 7 types pre-classified | Disease only |
| Full article content | Via `extract()` | No (metadata only) | No (metadata only) | Yes (Overview/Assessment HTML) |
| Production readiness | Low (unofficial, scraper) | Medium-High (BigQuery) | High | High |
| Primary/Secundary | Secondary | Secondary | Primary | Primary |

---

## Changes

| Date | Source | Change | Reason |
|------|--------|--------|--------|
| 2026-05-11 | API research | Created from DDGS v9.14.2 documentation and testing | Add supplementary news monitoring source |
