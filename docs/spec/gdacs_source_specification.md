# GDACS Source Specification

> **Status:** BASELINED (2026-05-11)
> API research, field mapping, and adapter design for GDACS data source.

---

## API Details

| Item | Value |
|------|-------|
| Base URL | `https://www.gdacs.org/gdacsapi/api/` |
| Swagger Docs | `https://www.gdacs.org/gdacsapi/swagger/index.html` |
| Quick Start PDF | `https://www.gdacs.org/Documents/2025/GDACS_API_quickstart_v1.pdf` |
| Feed Reference | `https://www.gdacs.org/feed_reference.aspx` |
| Auth | **None** — no API key or registration needed |
| Response format | GeoJSON (REST API), XML (RSS feeds) |
| Rate limits | None enforced |
| Update frequency | Every ~6 minutes |

---

## Endpoints

### Primary: All Current Events (Recommended)

```
GET https://www.gdacs.org/gdacsapi/api/events/geteventlist/events4app
```

Returns GeoJSON FeatureCollection with ALL active events across ALL disaster types. ~140KB, 50-80 features. Single call gets everything.

### Search: Targeted Query

```
GET https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=EQ;TC;FL;VO;DR;WF&fromdate=2026-05-04&alertlevel=red;orange&pagenumber=1&pagesize=100
```

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `eventlist` | `EQ;TC;FL;VO;TS;DR;WF` (semicolon-separated) | Filter by disaster type |
| `fromdate` | `2026-05-04` or `2026-05-04+00:00` | Start date |
| `todate` | Same format | End date |
| `alertlevel` | `red;orange;green` (semicolon-separated) | Filter by alert level |
| `pagenumber` | Integer | Pagination |
| `pagesize` | Integer (max 100) | Results per page |

### Per-Event Details

```
GET https://www.gdacs.org/gdacsapi/api/events/geteventdata?eventtype=EQ&eventid=1539988
```

Returns full details for a single event. Use for enrichment of Level 3-4 incidents.

### Geospatial Polygon

```
GET https://www.gdacs.org/gdacsapi/api/polygons/getgeometry?eventtype=EQ&eventid=1539988&episodeid=...
```

### RSS Feeds (Alternative, XML)

| Feed | URL |
|------|-----|
| All events | `https://www.gdacs.org/xml/rss.xml` |
| Last 24h | `https://www.gdacs.org/xml/rss_24h.xml` |
| Last 7 days | `https://www.gdacs.org/xml/rss_7d.xml` |
| Earthquakes 24h | `https://www.gdacs.org/xml/rss_eq_24h.xml` |
| Earthquakes 48h (M>=4.5) | `https://www.gdacs.org/xml/rss_eq_48h_low.xml` |
| Earthquakes 48h (M>=5.5) | `https://www.gdacs.org/xml/rss_eq_48h_med.xml` |
| Earthquakes 3mo (Orange/Red) | `https://www.gdacs.org/xml/rss_eq_3M.xml` |
| Cyclones 7d | `https://www.gdacs.org/xml/rss_tc_7d.xml` |
| Cyclones 3mo | `https://www.gdacs.org/xml/rss_tc_3m.xml` |
| Floods 7d | `https://www.gdacs.org/xml/rss_fl_7d.xml` |
| Floods 3mo | `https://www.gdacs.org/xml/rss_fl_3m.xml` |

**Recommendation:** Use the REST API (GeoJSON) for primary fetch. RSS is a fallback if the API is unavailable.

---

## Disaster Types

| Code | Type | Asia Pacific + MENA Relevance |
|------|------|-------------------------------|
| `EQ` | Earthquake | Critical: Ring of Fire (Japan, Indonesia, Philippines) |
| `TC` | Tropical Cyclone | Critical: Philippines, Vietnam, Bangladesh, Myanmar |
| `FL` | Flood | Critical: Monsoon across South/Southeast Asia |
| `VO` | Volcano | Critical: Indonesia, Philippines, Japan |
| `TS` | Tsunami | Critical: Pacific and Indian Ocean rim |
| `DR` | Drought | Critical: MENA, South Asia, Australia |
| `WF` | Wildfire | Relevant: Australia, Indonesia |

---

## Response Structure (GeoJSON)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [122.5, 12.3]
      },
      "bbox": [121.0, 124.0, 11.0, 13.0],
      "properties": {
        "eventtype": "EQ",
        "eventid": 1539988,
        "episodeid": 1539989,
        "eventname": "Sumatra",
        "name": "Earthquake M6.1 in Sumatra, Indonesia",
        "description": "...",
        "htmldescription": "<p>...</p>",
        "alertlevel": "Orange",
        "alertscore": 1.5,
        "episodealertlevel": "Orange",
        "episodealertscore": 1.5,
        "istemporary": "false",
        "iscurrent": "true",
        "country": "Indonesia",
        "iso3": "IDN",
        "fromdate": "2026-05-11T05:35:52",
        "todate": "2026-05-11T05:35:52",
        "datemodified": "2026-05-11T06:12:00",
        "source": "GDO",
        "glide": "EQ-2026-000123-IDN",
        "icon": "https://.../EQ_Orange.png",
        "iconoverall": "https://.../EQ_Orange.png",
        "url": {
          "geometry": "https://www.gdacs.org/gdacsapi/api/polygons/getgeometry?...",
          "report": "https://www.gdacs.org/report.aspx?eventid=1539988&eventtype=EQ",
          "details": "https://www.gdacs.org/gdacsapi/api/events/geteventdata?..."
        },
        "affectedcountries": [
          {"iso2": "ID", "iso3": "IDN", "countryname": "Indonesia"}
        ],
        "severitydata": {
          "severity": 6.1,
          "severitytext": "Magnitude 6.1M, Depth:34.3km",
          "severityunit": "M"
        }
      }
    }
  ]
}
```

### RSS Additional Fields (XML with GeoRSS)

```xml
<gdacs:severity unit="M" value="6.5">Magnitude 6.5M, Depth:10km</gdacs:severity>
<gdacs:population unit="in MMI V" value="3873">4 thousand in MMI V</gdacs:population>
<gdacs:vulnerability value="1.3145341380124" />
<gdacs:bbox>120.5 122.0 10.0 12.0</gdacs:bbox>
<gdacs:version>2</gdacs:version>
<gdacs:calculationtype>earthquakeonly</gdacs:calculationtype>
<gdacs:cap>https://www.gdacs.org/contentdata/resources/EQ/.../cap_....xml</gdacs:cap>
```

---

## Field Mapping to RawIncidentData

| RawIncidentData Field | GDACS Source | Parsing Logic |
|-----------------------|-------------|---------------|
| `source_name` | Hardcoded `"GDACS"` | — |
| `incident_name` | `properties.name` | Direct: "Earthquake M6.1 in Sumatra, Indonesia" |
| `country` | `properties.country` | First country if comma-separated. Use `properties.iso3` for ISO lookup. |
| `disaster_type` | `properties.eventtype` via `GDACS_TYPE_MAP` | `"EQ"` → `"Earthquake"`, `"TC"` → `"Cyclone"`, etc. |
| `report_date` | `properties.fromdate` | Parse ISO format, add UTC timezone |
| `source_url` | `properties.url.report` | Direct GDACS report URL |
| `raw_fields` | Curated subset | See below |

### GDACS Type Map

```python
GDACS_TYPE_MAP: dict[str, str] = {
    "EQ": "Earthquake",
    "TC": "Cyclone",
    "FL": "Flood",
    "VO": "Volcano",
    "TS": "Tsunami",
    "DR": "Drought",
    "WF": "Wildfire",
}
```

### raw_fields for GDACS

```json
{
  "eventtype": "EQ",
  "eventid": 1539988,
  "episodeid": 1539989,
  "eventname": "Sumatra",
  "alertlevel": "Orange",
  "alertscore": 1.5,
  "episodealertlevel": "Orange",
  "episodealertscore": 1.5,
  "istemporary": false,
  "iscurrent": true,
  "iso3": "IDN",
  "fromdate": "2026-05-11T05:35:52",
  "todate": "2026-05-11T05:35:52",
  "datemodified": "2026-05-11T06:12:00",
  "source": "GDO",
  "glide": "EQ-2026-000123-IDN",
  "severitydata": {
    "severity": 6.1,
    "severitytext": "Magnitude 6.1M, Depth:34.3km",
    "severityunit": "M"
  },
  "affectedcountries": [
    {"iso2": "ID", "iso3": "IDN", "countryname": "Indonesia"}
  ],
  "coordinates": [122.5, 12.3],
  "bbox": [121.0, 124.0, 11.0, 13.0]
}
```

---

## Alert Level to Incident Level Mapping

| GDACS alertlevel | Incident Level | Rationale |
|------------------|---------------|-----------|
| `Green` | 1 (MINOR) | Low severity |
| `Orange` | 3 (MAJOR) | Significant event |
| `Red` | 4 (CRITICAL) | Major disaster |

GDACS has no Yellow level. Level 2 (SIGNIFICANT) is derived from `severitydata`:

```python
def derive_level(alertlevel: str, severitydata: dict, country_group: str) -> int:
    base = {"Green": 1, "Orange": 3, "Red": 4}.get(alertlevel, 1)
    if base == 1 and country_group == "A":
        severity = severitydata.get("severity", 0) if severitydata else 0
        if severity >= 5.0:
            return 2
    return base
```

---

## What Python Can Extract (No AI Needed)

| Field | Source | Logic |
|-------|--------|-------|
| `incident_name` | `properties.name` | Direct |
| `country` | `properties.country` | First if comma-separated |
| `country_group` | Country lookup | `COUNTRY_GROUPS` dict |
| `disaster_type` | `properties.eventtype` | Via `GDACS_TYPE_MAP` |
| `incident_level` | `properties.alertlevel` | Via `GDACS_ALERT_LEVEL_MAP` + severitydata |
| `priority` | Level + Group | Via `PRIORITY_MATRIX` |
| `should_report` | Level + Group | Via `PRIORITY_MATRIX` |
| `report_date` | `properties.fromdate` | Parse, add UTC |
| `source_url` | `properties.url.report` | Direct |
| `incident_id` | Date + ISO3 + type code | `YYYYMMDD-CC-TTT` format |
| `coordinates` | `geometry.coordinates` | Direct |
| Dedup | `eventid` + `episodeid` | Unique per event |
| Multi-country | `affectedcountries.length > 1` | Override O2 |
| Freshness filter | `fromdate` vs cutoff | Per-source window (7 days) |

### What AI Needs to Extract

- `summary` — human-readable summary from `name` + `description`
- `impact.impact_description` — from severitydata + alertscore context
- `classification_metadata.rationale` — why classified at this level
- `estimated_affected` / `estimated_deaths` — when not in severitydata (rare)

---

## Polling Strategy

| Setting | Value | Rationale |
|---------|-------|-----------|
| Endpoint | `events4app` | Single call, all types, ~140KB |
| Poll interval | 6 minutes | Matches GDACS update cycle |
| Cache TTL | 5 minutes | Prevent duplicate calls within a cycle |
| Timeout | 10 seconds | Response is small |
| Retry | 1 retry, 2s backoff | Transient failures only |
| Search fallback | For backfill only | `SEARCH?fromdate=...&eventlist=EQ;TC;FL` |

---

## Country Normalization

GDACS provides both `country` (text) and `iso3` (ISO code). Use ISO3 for reliable lookup:

```python
def normalize_country(country_text: str, iso3: str) -> str:
    if "," in country_text:
        return country_text.split(",")[0].strip()
    return country_text if country_text else "Unknown"
```

For multi-country events, store full `affectedcountries` array in `raw_fields` and take the first country as primary. The multi-regional override (O2) triggers automatically.

---

## Comparison: Old (USGS) vs New (GDACS API)

| Criterion | Old (USGS fallback) | New (GDACS API) |
|-----------|-------------------|-----------------|
| Disaster types | Earthquakes only | EQ, TC, FL, VO, TS, DR, WF |
| Alert levels | None (magnitude only) | Green, Orange, Red + alertscore |
| Country data | Fragile place string parsing | Structured iso3 + affectedcountries |
| Severity | Magnitude only | severitydata with units |
| Multi-country | Not supported | affectedcountries array |
| Event tracking | None | eventid + episodeid |
| Population impact | None | In RSS (population field) |
| GLIDE IDs | None | Standard disaster identifier |
| API auth | None | None |
| Response format | GeoJSON | GeoJSON |

---

## Changes

| Date | Source | Change | Reason |
|------|--------|--------|--------|
| 2026-05-11 | API research | Created from live API testing and Swagger docs | Replace USGS fallback with real GDACS API |
