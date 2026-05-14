# GDELT Source Specification

> **Status:** BASELINED (2026-05-11)
> API research, field mapping, and adapter design for GDELT Project as a global event/news monitoring source.

---

## API Details

| Item | Value |
|------|-------|
| Project | GDELT Project (Global Database of Events, Language, and Tone) |
| Website | `https://www.gdeltproject.org/` |
| Type | Global event monitoring database processing news from 100+ languages, 15+ years of data |
| Auth | **None** — fully open, no API key or registration needed for free APIs |
| License | Open data |
| Python library | `gdeltdoc` (v1.12.0, April 2025) — `pip install gdeltdoc` |
| GitHub | `github.com/alex9smith/gdelt-doc-api` — 200+ stars |
| Update frequency | Every 15 minutes (GDELT ingests and processes global news continuously) |

---

## GDELT APIs Available

| API | Best For | Access |
|-----|----------|--------|
| **GDELT DOC API** | Keyword + theme search returning article metadata | Free REST API, rate-limited |
| **GKG GeoJSON v1** | Georeferenced disaster dashboards with real-time lat/lon | Free REST API |
| **GKG BigQuery** | Sustained automated polling, full historical data, no rate limits | Google BigQuery (free tier: 1TB/mo) |
| **GDELT Visuals** | Image/visual content monitoring | Free REST API |
| **Raw File Downloads** | Bulk processing, no rate limits at all | Free HTTP download |

For disaster surveillance, use the **DOC API** for keyword/theme search and **BigQuery** for sustainable production polling.

---

## GDELT DOC API — Primary for Surveillance

### Endpoint

```
GET https://api.gdeltproject.org/api/v2/doc/doc?query={QUERY}&mode=artlist&format=json&maxrecords=250
```

### Parameters

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `query` | URL-encoded keyword + theme filters | Complex queries combining terms, themes, domains, countries |
| `mode` | `artlist` (article list), `timelinevol` (volume over time), `timelinetone` (tone over time) | `artlist` for surveillance |
| `format` | `json`, `csv`, `html` | `json` for adapter |
| `maxrecords` | 1–250 | Results per call |
| `startdatetime` | `YYYYMMDDHHMMSS` | Start of time range |
| `enddatetime` | `YYYYMMDDHHMMSS` | End of time range |
| `timespan` | `15min`, `1h`, `1d`, etc. | Alternative to explicit start/end |
| `sort` | `datedesc`, `dateasc`, `toneasc`, `tonedesc`, `hybridrel` | `datedesc` for latest-first |

### Response Structure

```json
{
  "articles": [
    {
      "url": "https://www.reuters.com/world/asia-pacific/philippines-typhoon-category4-2026-05-11/",
      "url_mobile": "https://mobile.reuters.com/...",
      "title": "Typhoon Haiyan intensifies to Category 4 as it approaches Philippines",
      "seendate": "20260511T091500Z",
      "socialimage": "https://cdn.reuters.com/...",
      "domain": "reuters.com",
      "language": "English",
      "sourcecountry": "United Kingdom",
      "tonepositive": 2.5,
      "tonenegative": 7.3,
      "tone": -4.8,
      "themes": [
        "NATURAL_DISASTER_TROPICAL_CYCLONE",
        "NATURAL_DISASTER",
        "GENERAL_HEALTH",
        "WB_2284_DISASTER_RISK_MANAGEMENT",
        "SOC_POINTSOFINTEREST_NATIONAL_PARK_SITES"
      ]
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Canonical URL of the article |
| `title` | string | Article headline |
| `seendate` | string | When GDELT first saw the article (`YYYYMMDDHHMMSS` format) |
| `socialimage` | string | Social media image URL (may be empty) |
| `domain` | string | Publisher domain (e.g., "reuters.com", "reliefweb.int") |
| `language` | string | Article language |
| `sourcecountry` | string | Country where the publisher is based |
| `tonepositive` | float | Positive tone score (0–100) |
| `tonenegative` | float | Negative tone score (0–100) |
| `tone` | float | Net tone (positive – negative). Negative values = more negative sentiment. |
| `themes` | list[str] | GDELT GKG themes assigned to the article (see Themes below) |

---

## GDELT Themes — Disaster-Relevant

GDELT classifies every article with one or more themes from the GKG (Global Knowledge Graph). **Themes, NOT CAMEO codes, are the primary filter for disasters.**

### Natural Disaster Themes

| Theme | Covers |
|-------|--------|
| `NATURAL_DISASTER` | Any natural disaster (parent theme) |
| `NATURAL_DISASTER_EARTHQUAKE` | Earthquakes, seismic activity |
| `NATURAL_DISASTER_FLOOD` | Floods, flash floods, inundation |
| `NATURAL_DISASTER_TROPICAL_CYCLONE` | Cyclones, typhoons, hurricanes, tropical storms |
| `NATURAL_DISASTER_VOLCANO` | Volcanic eruptions, ash falls, lava flows |
| `NATURAL_DISASTER_TSUNAMI` | Tsunamis, tidal waves |
| `NATURAL_DISASTER_WILDFIRE` | Wildfires, forest fires, bushfires |
| `NATURAL_DISASTER_DROUGHT` | Drought, water scarcity |
| `NATURAL_DISASTER_LANDSLIDE` | Landslides, mudslides, avalanches |
| `NATURAL_DISASTER_EXTREME_WEATHER` | Heatwaves, cold snaps, storms, hail |
| `NATURAL_I` | Natural disaster (legacy) |

### Disease/Health Themes

| Theme | Covers |
|-------|--------|
| `HEALTH_PANDEMIC` | Pandemics, global disease spread |
| `HEALTH_EPIDEMIC` | Epidemics, localized disease outbreaks |
| `HEALTH_OUTBREAK` | Disease outbreaks |
| `HEALTH_DISEASE` | Disease reporting (general) |
| `WB_2284_DISASTER_RISK_MANAGEMENT` | World Bank disaster risk management topics |
| `UNGP_EPIDEMIC_PREPAREDNESS` | UN Global Pulse epidemic preparedness |
| `WB_1981_PANDEMIC` | World Bank pandemic-related |

### Humanitarian Themes

| Theme | Covers |
|-------|--------|
| `HUMANITARIAN_CRISIS` | Humanitarian crises, complex emergencies |
| `HUMANITARIAN_AID` | Humanitarian aid, relief operations |
| `REFUGEE` | Refugee situations, displacement |
| `FOOD_SECURITY` | Food crises, famine |
| `WATER_CRISIS` | Water crises |

### CAMEO Event Codes — NOT for Natural Disasters

Traditional CAMEO event codes (01–20) cover **political conflict only** (protests, battles, diplomatic actions). They do NOT cover natural disasters. Use GKG Themes for disaster filtering.

GDELT Cloud (commercial, API key required) introduced CAMEO+ codes (EN01–EN05, HE01–HE05) for environmental and health events, but these are NOT available in the free APIs. Stick with GKG Themes.

---

## Field Mapping to RawIncidentData

| RawIncidentData Field | GDELT Source | Parsing Logic |
|-----------------------|-------------|---------------|
| `source_name` | Hardcoded `"GDELT"` | — |
| `incident_name` | `article["title"]` | Direct |
| `country` | Query context | Derived from query country filter, not from article. GDELT articles can have global scope. |
| `disaster_type` | `article["themes"]` | Map first matching disaster theme: `NATURAL_DISASTER_EARTHQUAKE` → "Earthquake". |
| `report_date` | `article["seendate"]` | Parse `YYYYMMDDHHMMSS` → ISO 8601 |
| `source_url` | `article["url"]` | Direct |
| `raw_fields` | All article fields | See below |

### raw_fields for GDELT

```json
{
  "seen_date": "20260511T091500Z",
  "domain": "reuters.com",
  "language": "English",
  "source_country": "United Kingdom",
  "tone_positive": 2.5,
  "tone_negative": 7.3,
  "tone": -4.8,
  "themes": [
    "NATURAL_DISASTER_TROPICAL_CYCLONE",
    "NATURAL_DISASTER",
    "GENERAL_HEALTH"
  ],
  "social_image": "https://cdn.reuters.com/...",
  "gdelt_query": "NATURAL_DISASTER site:reuters.com"
}
```

### Tone Interpretation

| Tone Range | Meaning | Relevance for Surveillance |
|------------|---------|---------------------------|
| < -5.0 | Strongly negative (likely severe disaster, high casualties) | Escalation signal — check immediately |
| -2.0 to -5.0 | Moderately negative (disaster with impacts) | Normal disaster reporting |
| > -2.0 | Mildly negative or neutral | Background reporting, political/response rather than active crisis |
| > 0 | Positive (recovery, aid success, resilience) | Not an active disaster — filter out |

---

## GKG GeoJSON v1 — Georeferenced Events

### Endpoint

```
GET https://api.gdeltproject.org/api/v1/gkg_geojson?QUERY={QUERY}&OUTPUTFIELDS=name,themes,tone,url&FORMAT=JSON
```

Returns georeferenced news mentions with lat/lng coordinates. Each result includes:
- Geographic coordinates of the location mentioned in the article
- The associated theme(s)
- Tone values
- Source URL

**Use for:** Mapping active disaster zones within a geographic bounding box.

For disaster surveillance, the DOC API (article-centric) is more useful than the GKG GeoJSON (location-centric). Use GKG GeoJSON when you need to answer "what's happening within X km of Y?"

---

## BigQuery — Production Polling (Recommended)

### Why BigQuery

The free REST APIs (DOC, GKG) are rate-limited with no formal SLA. For sustained automated polling every 15 minutes:

| Approach | Limits | Reliability |
|----------|--------|-------------|
| Free DOC API | ~100 requests/day (observed), no SLA | Moderate |
| **BigQuery** | 1 TB/month free tier, unlimited queries | High (Google infrastructure SLA) |
| Raw file downloads | No limits, batch processing | High (download once, process locally) |

### GDELT GKG BigQuery Table

```
`gdelt-bq.gdeltv2.gkg_partitioned`
```

Partitioned by date. Queries scan ~15-20 GB/day of recent data.

### Sample BigQuery SQL for Disaster Surveillance

```sql
SELECT
  DocumentIdentifier AS url,
  V2Themes AS themes,
  V2Tone as gkgtone,
  DATE as date,
  SourceCommonName AS source_name,
  TranslationInfo AS lang
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE DATE >= CURRENT_DATE() - 1
  AND V2Themes LIKE '%NATURAL_DISASTER%'
ORDER BY DATE DESC
LIMIT 250;
```

### Python BigQuery Access

```python
from google.cloud import bigquery

client = bigquery.Client()
query = """
    SELECT DocumentIdentifier as url, V2Themes as themes, V2Tone as tone, DATE as date
    FROM `gdelt-bq.gdeltv2.gkg_partitioned`
    WHERE DATE >= CURRENT_DATE() - 1
      AND V2Themes LIKE '%NATURAL_DISASTER%'
    ORDER BY DATE DESC
    LIMIT 250
"""
results = client.query(query).result()
for row in results:
    print(row.url, row.themes, row.tone)
```

Requires: `pip install google-cloud-bigquery` + Google Cloud project with BigQuery API enabled.

---

## `gdeltdoc` Python Library

### Installation

```bash
pip install gdeltdoc
```

### Usage

```python
from gdeltdoc import GdeltDoc, Filters

f = Filters(
    keyword="flood OR earthquake OR cyclone",
    start_date="2026-05-10",
    end_date="2026-05-11",
    theme="NATURAL_DISASTER",
    country="ID",       # ISO 3166-1 alpha-2 country code
    domain="reuters.com",  # Restrict to specific sources
)

gd = GdeltDoc()
articles = gd.article_search(f)

# Returns pandas DataFrame with columns:
# url, url_mobile, title, seendate, socialimage, domain,
# language, sourcecountry, tonepositive, tonenegative, tone, themes
```

### Available Filters

| Filter | Example | Purpose |
|--------|---------|---------|
| `keyword` | `"flood OR earthquake"` | Full-text search across title + body (250 char limit) |
| `start_date` | `"2026-05-10"` | Start of date range |
| `end_date` | `"2026-05-11"` | End of date range |
| `theme` | `"NATURAL_DISASTER"` | Filter by GKG theme |
| `country` | `"ID"`, `"PH"`, `"IN"` | ISO alpha-2 country code |
| `domain` | `"reuters.com"` | Restrict to specific news domain |
| `near` | `"Manila, Philippines"` + `radius` (km) | Geographic proximity search |
| `timespan` | `"15min"`, `"1h"`, `"1d"` | Alternative to start/end dates |

### Limits

- `gdeltdoc` wraps the free DOC API — same rate limits apply
- 250 results per query maximum
- For production with sustained polling, prefer BigQuery

---

## Polling Strategy

### Free DOC API Strategy

| Setting | Value | Rationale |
|---------|-------|-----------|
| Poll interval | 15 minutes | Matches GDELT ingestion cycle |
| Query | Single theme-based query: `NATURAL_DISASTER` + country filters | One query per cycle covers all types |
| Max results | 50 | Recent 50 articles in the last 15 minutes is sufficient |
| Time window | `timespan=15min` or `startdatetime={15min ago}` | Only new articles since last cycle |
| Dedup key | `url` | URL is unique per article in GDELT |
| Cache | In-memory, 14-minute TTL | Prevent duplicate queries |
| Fallback | `enddatetime={now}` without `startdatetime` | If no results, extend to 1 hour |
| Backfill | Increase `maxrecords` to 250, extend to 24h | For catch-up after downtime |

### BigQuery Strategy (Production)

| Setting | Value | Rationale |
|---------|-------|-----------|
| Poll interval | 15 minutes | Same as GDELT update cycle |
| Table | `gdelt-bq.gdeltv2.gkg_partitioned` | Partitioned for cost-efficient querying |
| Date filter | `DATE >= CURRENT_DATE() - 1` | No need for 15-min precision; BigQuery partitions by day |
| Cost | ~15-20 GB scanned/day (well within 1 TB free tier) | Free tier is 1 TB/month |
| Theme filter | `V2Themes LIKE '%NATURAL_DISASTER%'` | One query catches all types |
| Country filter | `REGEXP_CONTAINS(V2Locations, ...)` | Post-query or within SQL |

---

## What Python Can Extract (No AI Needed)

| Field | Source | Logic |
|-------|--------|-------|
| `incident_name` | `article["title"]` | Direct |
| `disaster_type` | `article["themes"]` | Map first matching theme: `NATURAL_DISASTER_EARTHQUAKE` → "Earthquake" |
| `report_date` | `article["seendate"]` | Parse `YYYYMMDDHHMMSS` → ISO 8601 |
| `source_url` | `article["url"]` | Direct |
| `publisher` | `article["domain"]` | Direct |
| `tone` | `article["tone"]` | Severity signal: < -5.0 = critical |
| `language` | `article["language"]` | Direct |
| Dedup | URL | URL hash |
| Freshness filter | `seendate` vs cutoff | Per-source window (24 hours) |

### What AI Needs to Extract

- `country` — GDELT articles are not always locatable to a single country; AI parses title for country mentions
- `summary` — article title is available, but AI can generate a richer summary
- `impact.impact_description` — from full article URL content if needed
- `classification_metadata.rationale` — why this GDELT article was classified at this level
- Association with actual disaster events (link to GDACS eventid if known)

---

## Coverage Assessment

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Global coverage | **Excellent** | 100+ languages, 15+ years of data |
| Asia-Pacific coverage | **Excellent** | Monitors local media in regional languages |
| Disaster type coverage | **Good** | 10 natural disaster themes + 7 disease/health themes |
| Freshness | **Excellent** | 15-minute update cycle |
| Geolocation | **Partial** | GKG GeoJSON has coordinates; DOC API articles don't |
| Severity signal | **Good** | Tone scores (negative = crisis). No magnitude/casualty estimates. |

---

## Theme False Positives

GDELT theme classification can produce false positives (ONS UK study confirmed this). An article may get tagged `NATURAL_DISASTER_EARTHQUAKE` because it mentions an earthquake in passing, not as the primary subject.

**Mitigation:**
1. Use negative tone as a severity filter — articles about earthquake preparedness have neutral tone
2. Filter by `domain` to prioritize disaster-focused sources (reliefweb.int, reuters.com)
3. Post-query: validate article title against disaster keywords before storing
4. URL dedup across sources (GDELT + DDGS + GDACS) to suppress redundant articles

---

## Role in Surveillance System

**GDELT is a strong secondary source for news-based disaster detection.** It provides:

- **Global coverage** of disaster news from local and international media
- **Structured themes** that classify articles by disaster type
- **Tone scoring** as an early severity indicator
- **Coverage of disaster types** that have no dedicated monitoring API (floods, landslides, heatwaves)

GDELT is NOT a replacement for GDACS (authoritative natural disaster alerts) or WHO DON (official disease reports), but it IS a better general news monitor than DDGS because:

- GDELT is a dedicated database, not a scraper — more reliable long-term
- Theme classification means you don't need to guess keywords
- Tone scoring provides automated severity triage
- BigQuery option means unlimited, reliable polling

---

## DDGS vs GDELT Comparison for News Monitoring

| Criterion | DDGS | GDELT |
|-----------|------|-------|
| Method | Metasearch scraper | Purpose-built news database |
| Reliability | Moderate (backends change) | High (15+ year project) |
| Theme classification | No (keyword only) | Yes (300+ themes) |
| Severity signal | No | Tone scores |
| Production polling | Fragile (rate limits) | BigQuery (unlimited) |
| Article metadata | Title, date, URL, source, snippet | Title, date, URL, domain, language, tone, themes |
| Asia-Pacific coverage | Good (region codes) | Excellent (local language monitoring) |
| News recency | Minutes (search index timing) | 15 minutes (guaranteed) |
| Rate limits | ~20 req/min | ~100 req/day (free API), unlimited (BigQuery) |
| Python library | `ddgs` v9.14.2 | `gdeltdoc` v1.12.0 |
| Licensing risk | Medium (scraping gray area) | Low (open data project) |
| **Recommendation** | **Drop in favor of GDELT** | **Adopt as primary news monitor** |

---

## Changes

| Date | Source | Change | Reason |
|------|--------|--------|--------|
| 2026-05-11 | API research | Created from GDELT DOC API, BigQuery, and `gdeltdoc` documentation | Add structured global news monitoring source |
