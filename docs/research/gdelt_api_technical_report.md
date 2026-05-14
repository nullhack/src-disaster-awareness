# GDELT API Technical Assessment for Disaster Surveillance
## Asia-Pacific + MENA Coverage

> **Date:** 2026-05-11
> **Scope:** Feasibility, API surface, data model, integration strategy for automated disaster monitoring.

---

## 1. What Is GDELT?

The **Global Database of Events, Language, and Tone** (GDELT) is the world's largest open database of
human society. Created by Kalev H. Leetaru, it monitors broadcast, print, and online news from nearly
every country in **over 100 languages**, processing them through machine translation (65 languages),
geocoding, entity extraction, theme classification, and tone analysis.

**Core data products:**

| Product | Description | Update Rate |
|---------|-------------|-------------|
| **GDELT 1.0 Event DB** | Quarter-billion CAMEO-coded events, 1979–present | Daily (6 AM EST) |
| **GDELT 2.0 Event DB** | Events + Mentions table, 65 languages | Every 15 min |
| **GDELT 2.0 GKG** | Global Knowledge Graph — entities, themes, tone, locations, counts | Every 15 min |
| **GDELT Visual GKG** | Deep-learning image cataloging (Google Cloud Vision API) | Every 15 min |
| **GDELT Global Frontpage Graph** | Homepage links from 50,000 outlets every hour | Hourly |
| **GDELT Global Difference Graph** | Stealth-edit detection on news articles | Periodic |

**Data Model Hierarchy (GKG 2.0):**

Each GKG row is a **nameset** — a unique combination of entities, themes, and locations extracted from
one or more articles. Fields per row:

```
DATE  NUMARTS  COUNTS  THEMES  LOCATIONS  PERSONS  ORGANIZATIONS  TONE  CAMEOEVENTIDS  SOURCES  SOURCEURLS
```

- **COUNTS**: Semicolon-delimited counts. Format: `COUNTTYPE#NUMBER#OBJECTTYPE#GEO_TYPE#GEO_FULLNAME#COUNTRYCODE#ADM1CODE#LAT#LON#FEATUREID`
  - Example: `KILL#309##1#Pakistan#PK#PK#30#70#PK;WOUND#500##1#Pakistan#PK#PK#30#70#PK`
  - ObjectType can identify affected groups (refugees, children, etc.)
- **THEMES**: Semicolon-delimited theme tags (GKG taxonomy + World Bank + CRISISLEX + UNGP + CAMEO)
- **LOCATIONS**: `Type#FullName#CountryCode#ADM1Code#ADM2Code#Lat#Lon#FeatureID#CharOffset`
- **TONE**: Comma-delimited tone scores: `tone, positive_score, negative_score, polarity, activity_refs, self_refs`
  - Tone range: typically -10 to +10 (can extend to -100/+100)
  - `< -2` strongly negative, `> 2` strongly positive, `-1 to +1` neutral

**Key insight for disaster surveillance:** GDELT works by *computing metadata* from articles, not
providing raw full-text search like Google News. Searches run against extracted themes, entities,
locations, and counts — not article bodies. The DOC API provides full-text search but is rate-limited.

---

## 2. GDELT APIs Available

### 2.1 API Inventory

| API | Base URL | Purpose | Window | Rate Limits |
|-----|----------|---------|--------|-------------|
| **DOC 2.0** | `https://api.gdeltproject.org/api/v2/doc/doc` | Full-text article search | 15 min – 1 year | Rate-limited ElasticSearch cluster |
| **GEO 2.0** | `https://api.gdeltproject.org/api/v2/geo/geo` | Geographic mapping of keywords/themes | 15 min – 7 days | Rate-limited |
| **GKG GeoJSON v1** | `https://api.gdeltproject.org/api/v1/gkg_geojson` | GeoJSON of GKG themes/names/locations | 15 min – 24 hours (1440 min) | Moderate |
| **GDELT Summary** | `https://summary.gdeltproject.org` | Human-friendly web wrapper around APIs | N/A | N/A |
| **GDELT Cloud** | `https://gdeltcloud.com` | Commercial API (events, stories, entities) | Jan 2025+ | API key, plan-based |
| **GDELT Analysis Service** | `http://analysis.gdeltproject.org` | Visualization/exporter (GDELT 1.0 only) | N/A | Email delivery |

### 2.2 Relevance for Disaster Monitoring

| API | Relevance | Strength |
|-----|-----------|----------|
| **DOC 2.0** | ★★★★★ PRIMARY | Full-text search for disaster keywords, theme filtering, tone, source country, 250 max results, JSON output |
| **GKG GeoJSON v1** | ★★★★ SECONDARY | Real-time GeoJSON of disaster themes with lat/lon, counts (KILL/WOUND/AFFECT), limited to 24h window |
| **GEO 2.0** | ★★★ VISUAL | Interactive maps, GeoJSON export, supports theme + keyword, up to 7 days |
| **BigQuery GKG** | ★★★★★ DEEP | Full query power, unlimited date range, all fields, costs $ for TB scanned |
| **GDELT Cloud** | ★★★ NEW | Structured events with disaster-specific domains (ENVIRONMENT, HEALTH), API key required, Jan 2025+ |

---

## 3. GDELT 2.0 DOC API — Primary Interface for Disaster Monitoring

### 3.1 Base URL

```
https://api.gdeltproject.org/api/v2/doc/doc
```

### 3.2 Query Parameters

| Parameter | Description | Values |
|-----------|-------------|--------|
| `query` | Search expression | Keywords, phrases, operators (see below) |
| `mode` | Output mode | `ArtList`, `ArtGallery`, `TimelineVol`, `TimelineVolRaw`, `TimelineVolInfo`, `TimelineTone`, `TimelineLang`, `TimelineSourceCountry`, `ToneChart`, `ImageCollage`, `ImageCollageInfo`, `ImageGallery`, `WordCloudImageTags`, `WordCloudImageWebTags` |
| `format` | Output format | `HTML`, `CSV`, `JSON`, `JSONP`, `RSS`, `RSSArchive`, `JSONFeed` |
| `timespan` | Relative time window | `15min` – `3m` (default 3 months, max 1 year) |
| `startdatetime` | Start datetime | `YYYYMMDDHHMMSS` (UTC) |
| `enddatetime` | End datetime | `YYYYMMDDHHMMSS` (UTC) |
| `maxrecords` | Max results (ArtList/Image modes only) | 1–250 (default 75) |
| `sort` | Sort order | `DateDesc`, `DateAsc`, `ToneDesc`, `ToneAsc`, `HybridRel` |
| `timelinesmooth` | Moving-window smoothing | 1–30 |

### 3.3 Query Operators (inside `query` parameter)

| Operator | Syntax | Example |
|----------|--------|---------|
| Exact phrase | `"phrase"` | `"flood warning"` |
| Boolean OR | `(a OR b OR c)` | `(earthquake OR tsunami OR flood)` |
| Exclude | `-term` | `-sourcelang:spanish` |
| Domain | `domain:cnn.com` | `domain:bbc.co.uk` |
| Exact domain | `domainis:un.org` | `domainis:reuters.com` |
| GKG Theme | `theme:THEME` | `theme:NATURAL_DISASTER` |
| Source country | `sourcecountry:philippines` | `sourcecountry:philippines` (FIPS 2-char OK) |
| Source language | `sourcelang:english` | `sourcelang:arabic` |
| Tone filter | `tone<-3` | `tone<-3` (negative articles) |
| Proximity | `nearN:"word1 word2"` | `near20:"flood damage"` |
| Repeat count | `repeatN:"word"` | `repeat3:"earthquake"` |
| Image tag | `imagetag:"flood"` | `imagetag:"earthquake"` (from Cloud Vision) |
| Image web tag | `imagewebtag:"disaster"` | `imagewebtag:"flood"` |

### 3.4 ArtList JSON Response Fields

When using `mode=ArtList&format=JSON`:

```json
{
  "articles": [
    {
      "url": "https://...",
      "url_mobile": "https://...",
      "title": "Flooding hits Manila...",
      "seendate": "20260510T143000Z",
      "socialimage": "https://...",
      "domain": "rappler.com",
      "language": "English",
      "sourcecountry": "Philippines"
    }
  ]
}
```

---

## 4. GDELT 2.0 GEO API

### 4.1 Base URL

```
https://api.gdeltproject.org/api/v2/geo/geo
```

### 4.2 Key Parameters

| Parameter | Description | Values |
|-----------|-------------|--------|
| `query` | Search (same operators as DOC API) | Keywords, themes, image tags |
| `mode` | Map mode | `PointData`, `Country`, `ADM1`, `SourceCountry`, `PointHeatmap`, `ImagePointData`, `ImageCountry`, `ImageADM1`, `ImageSourceCountry` |
| `format` | Output | `HTML`, `ImageHTML`, `GeoJSON`, `ImageGeoJSON`, `CSV`, `RSS`, `JSONFeed` |
| `timespan` | Time window | 15–1440 minutes, `Nh`, `Nd`, `1w` |
| `maxpoints` | Max locations (point modes only) | 1–1000 (PointData), 1–25000 (PointHeatmap) |
| `geores` | Geographic resolution | 0=all, 1=no country, 2=landmark only |
| `sortby` | Sort | `Date`, `ToneDesc`, `ToneAsc` |

### 4.3 Query Operators Unique to GEO

| Operator | Description | Example |
|----------|-------------|---------|
| `location:"name"` | Location name match | `location:"manila"` |
| `locationcc:CC` | Country filter (FIPS or name) | `locationcc:philippines` |
| `locationadm1:CCXX` | ADM1 filter | `locationadm1:PH00` |
| `near:lat,lon,radius` | Radius search | `near:14.5995,120.9842,200` |
| `sourcecountry:country` | Source outlet country | `sourcecountry:philippines` |

---

## 5. GKG GeoJSON v1 API (Legacy but High-Value)

### 5.1 Base URL

```
https://api.gdeltproject.org/api/v1/gkg_geojson
```

### 5.2 Parameters

| Parameter | Description |
|-----------|-------------|
| `QUERY` | Comma-separated list of GKG themes, names, or operators. Searches `themes` + `names` fields only (NOT fulltext). Case-insensitive. |
| `OUTPUTFIELDS` | Comma-separated fields: `url`, `name`, `geores`, `sharingimage`, `lang`, `tone`, `wordcount`, `numcounts`, `themes`, `names`, `domain` |
| `TIMESPAN` | Minutes (1–1440) |
| `MAXROWS` | Max rows (default varies, up to 45000 for hourly) |
| `OUTPUTTYPE` | 0=article-level (default), 2=location+time collapsed (for animation) |

### 5.3 Query Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `domain:` | Filter by source domain | `domain:bbc.co.uk` |
| `domainlike:` | Substring domain match | `domainlike:postimees` |
| `geoname:` | Filter to country/ADM1 | `geoname:Syria`, `geoname:Philippines` |
| `excgeoname:` | Exclude country | `excgeoname:United States` |
| `lang:` | Language filter (3-char ISO) | `lang:ara`, `lang:tgl` |
| Comma-separated | AND logic | `NATURAL_DISASTER,geoname:Philippines` |

### 5.4 Key Fields for Disaster Monitoring

- **`mentionedthemes`**: All GKG themes matched to this location in the article (e.g., `NATURAL_DISASTER_EARTHQUAKE;KILL;WOUND;AFFECT`)
- **`urlnumamounts`**: Count of precise numeric amounts mentioned (proxy for article detail)
- **`urltone`**: Tone/sentiment score
- **`url`**: Link to source article
- **`name`**: Human-readable location name

---

## 6. Disaster-Relevant GKG Themes

The GKG Theme taxonomy is hierarchical (THEME, THEME_CHILD, THEME_GRANDCHILD). Below are the
themes relevant to disaster surveillance, drawn from the live lookup file:

### 6.1 Natural Disaster Themes

| Theme | Description | Article Count |
|-------|-------------|---------------|
| `NATURAL_DISASTER` | General natural disaster | 72,002,253 |
| `NATURAL_DISASTER_EARTHQUAKE` | Earthquakes | 7,086,203 |
| `NATURAL_DISASTER_EARTHQUAKES` | Earthquakes (plural) | 1,984,203 |
| `NATURAL_DISASTER_FLOOD` | Flood | 6,495,128 |
| `NATURAL_DISASTER_FLOODING` | Flooding | 6,207,184 |
| `NATURAL_DISASTER_FLOODS` | Floods | 4,820,227 |
| `NATURAL_DISASTER_FLOODED` | Flooded | 4,279,818 |
| `NATURAL_DISASTER_HURRICANE` | Hurricane damage | 5,336,512 |
| `NATURAL_DISASTER_HURRICANES` | Hurricanes | 1,364,149 |
| `NATURAL_DISASTER_DROUGHT` | Drought | 3,962,460 |
| `NATURAL_DISASTER_CYCLONE` | Cyclone | 1,336,767 |
| `NATURAL_DISASTER_TYPHOON` | Typhoon | 1,088,794 |
| `NATURAL_DISASTER_TSUNAMI` | Tsunami | 1,543,881 |
| `NATURAL_DISASTER_TROPICAL_STORM` | Tropical storm | 1,137,251 |
| `NATURAL_DISASTER_WILDFIRE` | Wildfire | 1,614,522 |
| `NATURAL_DISASTER_WILDFIRES` | Wildfires | 1,449,572 |
| `NATURAL_DISASTER_LANDSLIDE` | Landslide | 1,307,013 |
| `NATURAL_DISASTER_LANDSLIDES` | Landslides | 1,464,210 |
| `NATURAL_DISASTER_VOLCANO` | Volcano | 1,391,717 |
| `NATURAL_DISASTER_VOLCANIC` | Volcanic | 1,106,886 |
| `NATURAL_DISASTER_AVALANCHE` | Avalanche | 1,392,452 |
| `NATURAL_DISASTER_TORNADO` | Tornado | 1,203,283 |
| `NATURAL_DISASTER_HEAVY_RAIN` | Heavy rain | 2,539,450 |
| `NATURAL_DISASTER_HEAVY_RAINS` | Heavy rains | 1,309,653 |
| `NATURAL_DISASTER_ICE` | Ice/snow disaster | 11,025,516 |
| `NATURAL_DISASTER_DROWNED` | Drowned | 2,470,994 |
| `NATURAL_DISASTER_DROWNING` | Drowning | 1,527,800 |
| `NATURAL_DISASTER_EROSION` | Erosion | 1,980,096 |
| `NATURAL_DISASTER_CHILL` | Extreme cold | 1,088,271 |

### 6.2 Man-Made Disaster / Crisis Themes

| Theme | Description | Article Count |
|-------|-------------|---------------|
| `MANMADE_DISASTER` | General man-made disaster | 15,334,942 |
| `MANMADE_DISASTER_IMPLIED` | Implied man-made disaster | 221,229,073 |
| `DISASTER_FIRE` | Fire disaster | 18,136,739 |
| `MANMADE_DISASTER_TRAFFIC_ACCIDENT` | Traffic accident | 16,128,877 |
| `MANMADE_DISASTER_CAR_ACCIDENT` | Car accident | 1,000,507 |
| `ENV_OIL` | Oil-related environmental damage | 35,074,255 |
| `ENV_MINING` | Mining environmental damage | 12,677,919 |
| `ENV_CLIMATECHANGE` | Climate change | 12,505,779 |
| `INFRASTRUCTURE_BAD_ROADS` | Infrastructure damage | 2,828,633 |
| `POWER_OUTAGE` | Power outage | 2,934,922 |

### 6.3 Health / Disease Themes

| Theme | Description | Article Count |
|-------|-------------|---------------|
| `GENERAL_HEALTH` | General health | 262,433,948 |
| `HEALTH_PANDEMIC` | Pandemic | 28,064,635 |
| `TAX_DISEASE` | Disease taxonomy root | 174,585,309 |
| `TAX_DISEASE_OUTBREAK` | Disease outbreak | 11,435,619 |
| `TAX_DISEASE_EPIDEMIC` | Epidemic | 10,694,319 |
| `TAX_DISEASE_CORONAVIRUS` | Coronavirus | 20,736,261 |
| `TAX_DISEASE_COVID-19` | COVID-19 | 1,755,829 |
| `TAX_DISEASE_EBOLA` | Ebola | 1,001,638 |
| `TAX_DISEASE_CHOLERA` | Cholera (present) | — |
| `TAX_DISEASE_PLAGUE` | Plague | 1,781,440 |
| `TAX_DISEASE_INFLUENZA` | Influenza | 1,233,093 |
| `TAX_DISEASE_HIV` | HIV | 2,281,349 |
| `TAX_DISEASE_INFECTIOUS` | Infectious disease | 4,624,573 |
| `TAX_DISEASE_DIARRHEA` | Diarrhea | 1,103,236 |
| `TAX_DISEASE_FEVER` | Fever | 6,736,569 |
| `TAX_DISEASE_INFECTION` | Infection | 13,922,039 |
| `TAX_DISEASE_CONTAGIOUS` | Contagious | 1,909,148 |
| `TAX_DISEASE_PNEUMONIA` | Pneumonia | 3,997,847 |
| `TAX_DISEASE_POISONING` | Poisoning | 3,002,475 |
| `TAX_DISEASE_HEPATITIS` | Hepatitis | 999,056 |
| `WB_2167_PANDEMICS` | WB: Pandemics | 46,628,648 |
| `WB_2166_HEALTH_EMERGENCY_PREPAREDNESS` | WB: Health emergency preparedness | 46,628,648 |
| `WB_2165_HEALTH_EMERGENCIES` | WB: Health emergencies | 57,048,809 |
| `WB_1406_DISEASES` | WB: Diseases | 93,688,195 |

### 6.4 Humanitarian / Displacement Themes

| Theme | Description | Article Count |
|-------|-------------|---------------|
| `REFUGEES` | Refugees | 21,479,673 |
| `DISPLACED` | Displaced persons | 5,440,674 |
| `EVACUATION` | Evacuation | 12,346,729 |
| `SELF_IDENTIFIED_HUMANITARIAN_CRISIS` | Self-ID'd humanitarian crisis | 3,904,362 |
| `AID_HUMANITARIAN` | Humanitarian aid | 2,162,956 |
| `HUMAN_RIGHTS_ABUSES` | Human rights abuses | 9,125,562 |
| `CRISISLEX_T09_DISPLACEDRELOCATEDEVACUATED` | CRISISLEX: Displaced/Evacuated | 11,230,317 |
| `CRISISLEX_T08_MISSINGFOUNDTRAPPEDPEOPLE` | CRISISLEX: Missing/Trapped | 35,183,220 |
| `CRISISLEX_T02_INJURED` | CRISISLEX: Injured | 101,111,184 |
| `CRISISLEX_T03_DEAD` | CRISISLEX: Dead | 130,402,380 |
| `CRISISLEX_T04_INFRASTRUCTURE` | CRISISLEX: Infrastructure damage | 24,497,146 |
| `CRISISLEX_T06_SUPPLIES` | CRISISLEX: Supplies needed | 8,696,124 |
| `CRISISLEX_C05_NEED_OF_SHELTERS` | CRISISLEX: Shelter need | 8,997,281 |

### 6.5 Impact / Consequence Themes

| Theme | Description | Article Count |
|-------|-------------|---------------|
| `KILL` | Death toll | 183,899,676 |
| `WOUND` | Wounded/injured count | 59,774,495 |
| `AFFECT` | Affected people count | 136,248,467 |
| `SICKENED` | Sickened count | 1,252,049 |
| `TAX_DISEASE_WOUNDS` | Wounds | 4,671,378 |
| `FOOD_SECURITY` | Food security | 6,551,881 |
| `WATER_SECURITY` | Water security | 13,490,718 |

---

## 7. CAMEO+ Event Codes for Disasters (GDELT Cloud)

GDELT Cloud introduced CAMEO+ with non-conflict domains. Traditional CAMEO (codes 01–20) covers
political conflict only. The new GDELT Cloud domains add explicit disaster events:

| Code | Domain | Event | Example |
|------|--------|-------|---------|
| `EN01` | ENVIRONMENT | Geophysical Hazard | Earthquake, tsunami, volcanic eruption |
| `EN02` | ENVIRONMENT | Meteorological Hazard | Hurricane, tornado, severe flooding, wildfire |
| `EN03` | ENVIRONMENT | Climate Event | Record temperature, glacier collapse |
| `EN04` | ENVIRONMENT | Environmental Pollution | Oil spill, toxic release, air quality emergency |
| `HE01` | HEALTH | Disease Outbreak | Localized epidemic, novel pathogen |
| `HE02` | HEALTH | Pandemic / Global Health Emergency | WHO PHEIC declaration |
| `HE03` | HEALTH | Vaccine / Treatment Milestone | Vaccine approval, clinical trial |
| `HE04` | HEALTH | Public Health Policy | Lockdown, travel ban, vaccination mandate |
| `HE05` | HEALTH | Health System Crisis | Hospital failure, healthcare strike |
| `IN01` | INFRASTRUCTURE | Energy Infrastructure Event | Pipeline disruption, power outage |
| `IN02` | INFRASTRUCTURE | Transport Disruption | Port closure, rail strike, airport shutdown |
| `IN06` | INFRASTRUCTURE | Water Infrastructure | Dam failure, water scarcity, flood control failure |

**Note:** These are only available through the GDELT Cloud commercial API (`https://gdeltcloud.com`),
not the free GDELT 2.0 Event API. The free Event API uses traditional CAMEO (political conflict
focused, codes 01–20).

---

## 8. GDELT BigQuery Access

### 8.1 Available Tables

| Table | Description | Partitioned |
|-------|-------------|-------------|
| `gdelt-bq.gdeltv2.gkg` | GKG 2.0 (all time, full scan) | No |
| `gdelt-bq.gdeltv2.gkg_partitioned` | GKG 2.0 (partitioned by day) | Yes |
| `gdelt-bq.gdeltv2.events` | Events 2.0 (full scan) | No |
| `gdelt-bq.gdeltv2.events_partitioned` | Events 2.0 (partitioned) | Yes |
| `gdelt-bq.gdeltv2.eventmentions` | Event mentions | No |
| `gdelt-bq.gdeltv2.eventmentions_partitioned` | Event mentions (partitioned) | Yes |
| `gdelt-bq.full.events` | Full event history | No |

### 8.2 Sample Disaster Query (BigQuery SQL)

```sql
-- Find all city-level locations mentioning earthquakes in the last 24 hours
SELECT
  REGEXP_EXTRACT(location, r'^(?:[^#]*#){1}([^#]*)') AS location_name,
  REGEXP_EXTRACT(location, r'^(?:[^#]*#){5}([^#]*)') AS lat,
  REGEXP_EXTRACT(location, r'^(?:[^#]*#){6}([^#]*)') AS lon,
  COUNT(*) AS mentions
FROM
  `gdelt-bq.gdeltv2.gkg_partitioned`,
  UNNEST(SPLIT(V2Locations, ';')) AS location
WHERE
  _PARTITIONTIME >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND V2Themes LIKE '%NATURAL_DISASTER_EARTHQUAKE%'
  AND REGEXP_EXTRACT(location, r'^([^#]*)') IN ('3', '4')  -- US city or world city
GROUP BY location_name, lat, lon
ORDER BY mentions DESC
LIMIT 100
```

**BigQuery cost note:** Queries scan the partition. Setting `_PARTITIONTIME` boundaries limits scan
size. A 1-day GKG scan ≈ 15–20 GB of quota. Google provides 1 TB free quota per month.

---

## 9. Python Libraries

### 9.1 `gdeltdoc` (Recommended for DOC API)

- **PyPI:** `pip install gdeltdoc`
- **GitHub:** `alex9smith/gdelt-doc-api` (200+ stars)
- **Last release:** 1.12.0 (April 2025) — actively maintained
- **Python:** >=3.10
- **License:** MIT

**Key classes:**

```python
from gdeltdoc import GdeltDoc, Filters, near, repeat
from datetime import datetime

# Article search
f = Filters(
    keyword="earthquake",
    start_date=datetime(2026, 5, 10),
    end_date=datetime(2026, 5, 11),
    country=["RP", "ID"],     # Philippines, Indonesia (FIPS codes)
    theme="NATURAL_DISASTER",
    num_records=250,
    tone="<-2"                # Negative sentiment only
)
gd = GdeltDoc()
articles = gd.article_search(f)  # Returns pandas DataFrame

# Timeline search
timeline = gd.timeline_search("timelinevol", f)
```

**Filter fields:** `keyword`, `domain`, `domain_exact`, `country`, `language`, `theme`, `near`,
`repeat`, `tone`, `tone_absolute`, `start_date`, `end_date`, `timespan`, `num_records`

**Returns DataFrame columns:** `url`, `url_mobile`, `title`, `seendate`, `socialimage`,
`domain`, `language`, `sourcecountry`

### 9.2 `py-gdelt` (Broader Coverage)

- **GitHub:** `RBozydar/py-gdelt`
- Newer library, async-first design
- Supports: DOC API, GEO API, GKG GeoJSON API
- Pydantic models for typed responses

### 9.3 `gdeltr2` (R)

- Comprehensive R package by Alex Bresler
- Most mature GDELT client (covers all APIs)
- Not Python

---

## 10. Data Freshness

- **GDELT 2.0 Event/GKG raw files:** Updated every **15 minutes**
- **GDELT BigQuery tables:** Updated every 15 minutes
- **GDELT APIs:** Reflect the ElasticSearch indexes which update near-realtime
- **The 15-minute claim:** GDELT's processing pipeline ingests news articles, applies NLP/geocoding,
  and updates all products within a 15-minute window. In practice, depending on when the article was
  published vs. crawled, latency can be 15–60 minutes from publication to API availability.
- **GDELT Cloud:** Updated hourly (commercial product)

---

## 11. Rate Limits and Restrictions

### 11.1 Terms of Use

From `gdeltproject.org/about.html`:

> All datasets released by the GDELT Project are available for unlimited and unrestricted use for
> any academic, commercial, or governmental use of any kind without fee. You may redistribute,
> rehost, republish, and mirror any of the GDELT datasets in any form. Any use must include a
> citation to the GDELT Project and a link to `https://www.gdeltproject.org/`.

### 11.2 API Rate Limits

The free APIs (DOC, GEO, GKG GeoJSON) are **rate-limited** to protect the underlying ElasticSearch
clusters. Key points from blog posts:

- **No formal published rate limit.** The APIs apply dynamic throttling based on cluster load.
- **During peak global events** (wars, disasters), rate limiting intensifies.
- **Recommendation from GDELT:** For high-volume polling, use downloadable datasets (raw files or
  BigQuery) rather than hitting the search APIs.
- **BigQuery** is the recommended path for at-scale automated monitoring.
- The GKG GeoJSON v1 API (`gkg_geojson`) has a max timespan of **1440 minutes (24 hours)** and
  max rows of ~45,000.

### 11.3 Practical Guidance for Automated Polling

| Approach | Polling Frequency | Sustainability |
|----------|-------------------|----------------|
| DOC API `timespan=15min` every 15 min | 96 calls/day | May trigger throttling during crises |
| DOC API `timespan=1h` every hour | 24 calls/day | Safer, covers rolling window |
| GKG GeoJSON v1 every 60 min | 24 calls/day | Good for georeferenced disaster dashboards |
| BigQuery every 15–60 min | 24–96 queries/day | Best for production; costs quota |
| Raw file download every 15 min | 96 files/day | No rate limiting but 2.5 TB/year storage |

---

## 12. Suitability Analysis for Disaster Surveillance

### 12.1 Strengths

| Capability | Assessment |
|------------|------------|
| **Global coverage** | 100+ languages, nearly every country, including local outlets in Asia-Pacific + MENA |
| **Machine translation** | 65 languages translated to English, enabling cross-lingual search |
| **Real-time** | 15-minute updates, faster than most disaster databases (EM-DAT, ReliefWeb) |
| **Theme classification** | Rich GKG taxonomy with disaster-specific themes |
| **Geocoding** | Every article geocoded to city/landmark level with lat/lon |
| **Tone detection** | Sentiment analysis enables filtering for negative/urgent coverage |
| **Count extraction** | Auto-extracted casualty/affected counts (KILL, WOUND, AFFECT, SICKENED, DISPLACED) |
| **Cost** | Free, no API key needed |
| **Image intelligence** | Visual GKG can identify disaster imagery (flood damage, rubble, fire) |

### 12.2 Weaknesses / Gaps

| Limitation | Detail |
|------------|--------|
| **Theme false positives** | GDELT's NLP may tag articles as `NATURAL_DISASTER` even when disaster is only casually mentioned. UK ONS study found it "difficult to identify articles wholly or predominantly referring to a natural disaster." |
| **No article full-text in GKG** | The GKG only stores extracted metadata; DOC API provides full-text search but is rate-limited. |
| **Rate limiting** | Free APIs throttle under load; not designed for high-frequency automated polling. |
| **Error rate** | Geocoding errors (same-name confusion), mistranslations, theme misclassification. GDELT acknowledges this. |
| **No severity classification** | Unlike EM-DAT or GDACS, GDELT does not classify disaster severity. You get themes + counts, not a "magnitude 7.2 earthquake" label. |
| **CAMEO limitation** | Traditional CAMEO codes (01–20) do NOT cover natural disasters. You must use GKG themes. |
| **No structured fatality data** | Counts are extracted via regex, not validated. Same event reported by multiple outlets = duplicate counts. |
| **Coverage gaps** | Smaller regional outlets in remote areas may be under-represented. Some countries have thin media coverage. |
| **3-month API window** | DOC API only searches 3 months back by default (extendable to 1 year). |
| **No event deduplication** | Same disaster reported by 50 outlets = 50 separate GKG rows. Requires clustering. |

### 12.3 Can It Replace a General News Search API?

**Partial yes, but with caveats:**

- **For early detection:** Yes — GDELT detects breaking disaster news from local outlets faster than
  curated databases (ReliefWeb, EM-DAT) which have editorial delay.
- **For full article access:** No — you need the source URLs. GDELT provides them but doesn't host
  article text.
- **For verified casualty data:** No — use EM-DAT, GDACS, or ACAPS for validated figures.
- **For a news feed:** The DOC API in `ArtList` mode with `format=JSON` gives you article URLs,
  titles, dates, and source country — sufficient for a monitoring feed.

---

## 13. Code Example: Disaster Monitoring for Philippines

### 13.1 Using `gdeltdoc` (DOC API)

```python
from gdeltdoc import GdeltDoc, Filters
from datetime import datetime, timedelta

gd = GdeltDoc()

# Search for natural disasters in the Philippines in the last 24 hours
f = Filters(
    keyword="(earthquake OR typhoon OR flood OR volcano OR landslide OR tsunami)",
    start_date=datetime.utcnow() - timedelta(days=1),
    end_date=datetime.utcnow(),
    country="RP",          # Philippines FIPS code
    theme="NATURAL_DISASTER",
    num_records=250,
    sort="DateDesc"
)

articles = gd.article_search(f)
print(f"Found {len(articles)} articles")
print(articles[["title", "url", "seendate", "domain"]].head())
```

### 13.2 Direct DOC API Call with `requests`

```python
import requests
from urllib.parse import quote
from datetime import datetime, timedelta

# Build query
start = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d%H%M%S")
end = datetime.utcnow().strftime("%Y%m%d%H%M%S")

query = '(earthquake OR flood OR typhoon OR "volcanic eruption" OR landslide OR tsunami)'
query += ' theme:NATURAL_DISASTER sourcecountry:philippines'

url = "https://api.gdeltproject.org/api/v2/doc/doc"
params = {
    "query": query,
    "mode": "ArtList",
    "format": "JSON",
    "startdatetime": start,
    "enddatetime": end,
    "maxrecords": 250,
    "sort": "DateDesc"
}

r = requests.get(url, params=params, timeout=30)
data = r.json()

for article in data.get("articles", []):
    print(f"[{article['seendate']}] {article['title']}")
    print(f"  {article['url']}")
    print(f"  Source: {article['domain']} ({article['sourcecountry']})")
    print()
```

### 13.3 Using GKG GeoJSON v1 API for Real-Time Geo Feed

```python
import requests

# Real-time disaster locations in Philippines (last 60 minutes)
url = "https://api.gdeltproject.org/api/v1/gkg_geojson"
params = {
    "QUERY": "NATURAL_DISASTER,geoname:Philippines",
    "OUTPUTFIELDS": "name,url,domain,tone,themes,numcounts,sharingimage",
    "TIMESPAN": 60,
    "MAXROWS": 5000
}

r = requests.get(url, params=params, timeout=30)
geojson = r.json()

for feature in geojson.get("features", []):
    props = feature.get("properties", {})
    print(f"Location: {props.get('name')}")
    print(f"  Themes: {props.get('mentionedthemes', '')[:120]}")
    print(f"  Tone: {props.get('urltone')}")
    print(f"  URL: {props.get('url')}")
    print()
```

### 13.4 BigQuery: Real-Time Disaster Dashboard Query

```sql
SELECT
  REGEXP_EXTRACT(loc, r'^(?:[^#]*#){1}([^#]*)') AS location_name,
  REGEXP_EXTRACT(loc, r'^(?:[^#]*#){2}([^#]*)') AS country_code,
  REGEXP_EXTRACT(loc, r'^(?:[^#]*#){5}([^#]*)') AS lat,
  REGEXP_EXTRACT(loc, r'^(?:[^#]*#){6}([^#]*)') AS lon,
  COUNT(*) AS mentions,
  SUM(CASE WHEN theme LIKE '%KILL%' THEN 1 ELSE 0 END) AS kill_mentions,
  SUM(CASE WHEN theme LIKE '%WOUND%' THEN 1 ELSE 0 END) AS wound_mentions
FROM
  `gdelt-bq.gdeltv2.gkg_partitioned`,
  UNNEST(SPLIT(V2Locations, ';')) AS loc,
  UNNEST(SPLIT(V2Themes, ';')) AS theme
WHERE
  _PARTITIONTIME >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND (
    theme LIKE 'NATURAL_DISASTER_%'
    OR theme LIKE '%EPIDEMIC%'
    OR theme LIKE '%OUTBREAK%'
    OR theme LIKE '%PANDEMIC%'
  )
  AND REGEXP_EXTRACT(loc, r'^(?:[^#]*#){2}([^#]*)') IN (
    -- Asia-Pacific + MENA country codes (FIPS)
    'RP', 'ID', 'MY', 'TH', 'VM', 'BM', 'CB', 'LA', 'TW', 'HK', 'CH', 'JA', 'KS', 'KN',
    'PK', 'IN', 'BG', 'CE', 'MV', 'NP', 'BT', 'AF',
    'IZ', 'IR', 'SA', 'KU', 'QA', 'AE', 'MU', 'BA', 'YM', 'JO', 'LE', 'SY', 'IS', 'EG',
    'LY', 'TS', 'AG', 'MO', 'MR'
  )
GROUP BY location_name, country_code, lat, lon
ORDER BY mentions DESC
LIMIT 200
```

---

## 14. FIPS Country Codes for Asia-Pacific + MENA

### Asia-Pacific

| Country | FIPS | ISO |
|---------|------|-----|
| Philippines | RP | PH |
| Indonesia | ID | ID |
| Malaysia | MY | MY |
| Thailand | TH | TH |
| Vietnam | VM | VN |
| Myanmar | BM | MM |
| Cambodia | CB | KH |
| Laos | LA | LA |
| Taiwan | TW | TW |
| Hong Kong | HK | HK |
| China | CH | CN |
| Japan | JA | JP |
| South Korea | KS | KR |
| North Korea | KN | KP |
| India | IN | IN |
| Pakistan | PK | PK |
| Bangladesh | BG | BD |
| Sri Lanka | CE | LK |
| Nepal | NP | NP |
| Afghanistan | AF | AF |
| Australia | AS | AU |
| New Zealand | NZ | NZ |
| Papua New Guinea | PP | PG |
| Fiji | FJ | FJ |
| Singapore | SN | SG |

### MENA

| Country | FIPS | ISO |
|---------|------|-----|
| Iraq | IZ | IQ |
| Iran | IR | IR |
| Saudi Arabia | SA | SA |
| Kuwait | KU | KW |
| Qatar | QA | QA |
| UAE | AE | AE |
| Oman | MU | OM |
| Bahrain | BA | BH |
| Yemen | YM | YE |
| Jordan | JO | JO |
| Lebanon | LE | LB |
| Syria | SY | SY |
| Israel | IS | IL |
| Egypt | EG | EG |
| Libya | LY | LY |
| Tunisia | TS | TN |
| Algeria | AG | DZ |
| Morocco | MO | MA |
| Mauritania | MR | MR |
| Sudan | SU | SD |
| Palestine (West Bank) | WE | PS |
| Palestine (Gaza) | GZ | PS |

---

## 15. Recommendations for Implementation

### Architecture Recommendation: Multi-Layer Approach

```
Layer 1: GDELT DOC API (poll every 15-60 min)
  → Full-text search for disaster keywords + country/theme filters
  → Returns article URLs, titles, source, date
  → Lightweight, JSON, no storage needed

Layer 2: BigQuery GKG (poll every 1-6 hours)
  → Exhaustive theme + count + location queries
  → Extracts KILL/WOUND/AFFECT/DISPLACED counts per location
  → Georeferenced output for map layers

Layer 3: Source URLs
  → Fetch/scrape article URLs from Layer 1 results
  → Verify disaster relevance (reduce theme false positives)
  → Extract structured data if needed

Layer 4: Corroboration
  → Cross-reference with GDACS, EM-DAT, ReliefWeb, USGS earthquake feed
  → Deduplicate events
  → Assign severity classification
```

### Polling Pattern

```python
# Lightweight monitoring loop
import time
from gdeltdoc import GdeltDoc, Filters

gd = GdeltDoc()
COUNTRIES_OF_INTEREST = ["RP", "ID", "MY", "TH", "IN", "PK", "IZ", "IR", "SY", "YM", "EG", "LY"]
DISASTER_THEMES = [
    "NATURAL_DISASTER", "NATURAL_DISASTER_EARTHQUAKE", "NATURAL_DISASTER_FLOOD",
    "NATURAL_DISASTER_TYPHOON", "NATURAL_DISASTER_TSUNAMI", "NATURAL_DISASTER_VOLCANO",
    "NATURAL_DISASTER_WILDFIRE", "NATURAL_DISASTER_DROUGHT", "NATURAL_DISASTER_LANDSLIDE",
    "HEALTH_PANDEMIC", "TAX_DISEASE_OUTBREAK", "TAX_DISEASE_EPIDEMIC",
    "MANMADE_DISASTER", "SELF_IDENTIFIED_HUMANITARIAN_CRISIS", "REFUGEES"
]

while True:
    for theme in DISASTER_THEMES:
        try:
            f = Filters(
                theme=theme,
                country=COUNTRIES_OF_INTEREST,
                timespan="15min",
                num_records=100,
                sort="DateDesc"
            )
            articles = gd.article_search(f)
            if len(articles) > 0:
                print(f"[{theme}] {len(articles)} new articles")
                # Process articles...
        except Exception as e:
            print(f"Error: {e}")
    time.sleep(900)  # 15 minutes
```

### Key Design Decisions

1. **DOC API for alerting, BigQuery for analytics.**
2. **Use GKG themes as primary filter; keyword search as secondary.**
3. **Cache seen URLs to avoid duplicate processing.**
4. **Plan for rate limit backoff (exponential with jitter).**
5. **Accept that theme-based filtering has false positives; implement post-fetch validation.**

---

## 16. References

- GDELT Project: https://www.gdeltproject.org/
- GDELT DOC 2.0 API docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- GDELT GEO 2.0 API docs: https://blog.gdeltproject.org/gdelt-geo-2-0-api-debuts/
- GKG GeoJSON v1 API: https://blog.gdeltproject.org/announcing-our-first-api-gkg-geojson/
- GKG Themes lookup: http://data.gdeltproject.org/api/v2/guides/LOOKUP-GKGTHEMES.TXT
- Country lookup (FIPS): http://data.gdeltproject.org/api/v2/guides/LOOKUP-COUNTRIES.TXT
- CAMEO Event Codes: https://www.gdeltproject.org/data/lookups/CAMEO.eventcodes.txt
- BigQuery sample queries: https://blog.gdeltproject.org/google-bigquery-gkg-2-0-sample-queries/
- `gdeltdoc` Python library: https://github.com/alex9smith/gdelt-doc-api
- GDELT Cloud: https://gdeltcloud.com / https://docs.gdeltcloud.com
- UK ONS disaster study: https://www.ons.gov.uk/.../explorationoftheglobaldatabaseofeventslanguageandtonegdelt...
- Terms of Use: https://www.gdeltproject.org/about.html#termsofuse
