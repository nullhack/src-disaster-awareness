# Data Schema Specification: Disaster Surveillance Reporter

> **Status:** BASELINED (2026-05-11)
> Source of truth for all JSON/JSONL data structures used in the pipeline.
> Recovered and refined from deleted `data-schema` skill.

---

## Overview

All incident data flows through three schema stages:

1. **RawIncidentData** — minimal, flat record from source adapters
2. **ClassifiedIncident** — enriched, validated record after classification
3. **MediaCoverage** — separate record for media monitoring data

Storage format is JSONL (one JSON object per line). All datetimes are ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).

---

## Stage 1: RawIncidentData (Adapter Output)

The minimal record that every adapter MUST produce. Flat structure — no nesting.

```json
{
  "source_name": "GDACS",
  "incident_name": "M6.1 Earthquake Sumatra, Indonesia",
  "country": "Indonesia",
  "disaster_type": "Earthquake",
  "report_date": "2025-03-11T10:15:00Z",
  "source_url": "https://earthquake.usgs.gov/...",
  "raw_fields": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_name` | string | YES | Adapter identifier (GDACS, ProMED, ReliefWeb, HealthMap, WHO) |
| `incident_name` | string | YES | Human-readable incident name, max 500 chars |
| `country` | string | YES | Country name, must match a known country in groups A/B/C |
| `disaster_type` | string | YES | One of the defined incident type enums |
| `report_date` | string | YES | ISO 8601 datetime, when the source reported this |
| `source_url` | string | YES | Direct link to the source report |
| `raw_fields` | object | YES | Source-specific extra data (can be empty `{}`) |

---

## Stage 2: ClassifiedIncident (Pipeline Output)

The full record after AI enhancement and classification. This is what gets stored.

### 2.1 Classification Block

```json
{
  "country": "Indonesia",
  "country_group": "A",
  "region": "Southeast Asia",
  "incident_type": "Earthquake",
  "incident_level": 2,
  "priority": "MEDIUM",
  "should_report": true
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `country` | string | Must match known country list |
| `country_group` | enum | `A` \| `B` \| `C` |
| `region` | string | Geographic region (e.g., "South Asia", "Southeast Asia") |
| `incident_type` | enum | See Incident Types below |
| `incident_level` | integer | 1–4 |
| `priority` | enum | `HIGH` \| `MEDIUM` \| `LOW` |
| `should_report` | boolean | Whether to include in distribution |

### 2.2 Location Block

```json
{
  "country": "Indonesia",
  "provinces": [
    {"name": "Sumatra", "affected": true}
  ],
  "coordinates": {"latitude": -0.89, "longitude": 100.74},
  "affected_area_description": "Sumatra region, centered near Padang"
}
```

### 2.3 Impact Block

```json
{
  "affected_population": 75000,
  "deaths": 12,
  "injuries": 45,
  "displaced_persons": 5000,
  "affected_provinces": 1,
  "economic_damage_estimated": null,
  "impact_description": "Moderate earthquake causing building damage and landslides"
}
```

All numeric fields ≥ 0. `deaths` ≤ `affected_population`. `injuries` ≤ `affected_population`.

### 2.4 Sources Block

```json
[
  {
    "name": "GDACS",
    "type": "disaster-database",
    "url": "https://www.gdacs.org/incident/20250311",
    "accessed_date": "2025-03-11T10:20:00Z",
    "reliability_tier": "Tier1",
    "data_freshness": "real-time"
  }
]
```

Source types: `disaster-database` \| `disease-database` \| `news-agency` \| `humanitarian-org` \| `social-media` \| `government` \| `other`

Reliability tiers: `Tier1` (highest) \| `Tier2` \| `Tier3` \| `Unknown`

Data freshness: `real-time` \| `daily` \| `weekly` \| `archived`

### 2.5 Disaster Details Block

Conditionally present when `incident_type` is geophysical/meteorological/hydrological/climatological.

```json
{
  "disaster_type": "Tectonic Earthquake",
  "magnitude_or_scale": 6.1,
  "depth_or_altitude": 25,
  "forecasted": false,
  "forecast_confidence": null,
  "first_reported": "2025-03-11T09:45:00Z",
  "latest_update": "2025-03-11T14:30:00Z"
}
```

### 2.6 Disease Details Block

Conditionally present when `incident_type` is `Disease`.

```json
{
  "disease_name": "Chikungunya",
  "confirmed_cases": 50,
  "suspected_cases": 120,
  "deaths": 0,
  "investigation_status": "Under Investigation",
  "spread_pattern": "Localized",
  "potential_pandemic": false
}
```

Investigation status: `Under Investigation` \| `Confirmed` \| `Contained` \| `Spreading` \| `Resolved`

Spread pattern: `Localized` \| `Regional` \| `National` \| `International` \| `Unknown`

### 2.7 Media Coverage Block (Embedded in Incident)

```json
{
  "singapore_mentioned": false,
  "src_mentioned": false,
  "donation_concerns": false,
  "misinformation_detected": false,
  "public_sentiment": "neutral",
  "coverage_articles": [
    {
      "title": "...",
      "source": "Channel NewsAsia",
      "url": "...",
      "published_date": "2025-03-11T12:00:00Z",
      "relevance": "General"
    }
  ]
}
```

Sentiment: `positive` \| `neutral` \| `negative` \| `mixed` \| `unknown`

Article relevance: `SRC-Involved` \| `Singapore-Related` \| `General` \| `Other`

### 2.8 Classification Metadata Block

```json
{
  "classified_by": "pipeline",
  "classified_date": "2025-03-11T10:25:00Z",
  "classification_confidence": 0.95,
  "rationale": "6.1 magnitude earthquake in Group A country...",
  "special_flags": ["escalation-risk"]
}
```

Special flags (only when applicable): `humanitarian-crisis` \| `multi-regional` \| `escalation-risk` \| `high-uncertainty`

### 2.9 SRC Involvement Block

```json
{
  "involved": false,
  "involvement_type": "None",
  "donation_appeal_active": false,
  "volunteer_deployment": false,
  "estimated_response_value": null,
  "response_notes": ""
}
```

Involvement type: `None` \| `Monitoring` \| `Supporting` \| `Leading` \| `Coordinating`

### 2.10 Escalation Tracking Block

```json
{
  "initial_level": 2,
  "current_level": 2,
  "escalation_potential": true,
  "level_change_history": [
    {"level": 2, "date": "2025-03-11T10:25:00Z", "reason": "Initial classification"}
  ]
}
```

### 2.11 Metadata Block

```json
{
  "data_quality": "High",
  "completeness_score": 0.92,
  "last_verified": "2025-03-11T14:30:00Z",
  "related_incidents": [],
  "tags": ["earthquake", "Indonesia", "Sumatra"],
  "notes": "Monitor for aftershocks"
}
```

Data quality: `High` \| `Medium` \| `Low`

### Full ClassifiedIncident Record

```json
{
  "incident_id": "20250311-ID-EQ",
  "incident_name": "Earthquake in Sumatra, Indonesia",
  "created_date": "2025-03-11T10:15:00Z",
  "updated_date": "2025-03-11T14:30:00Z",
  "status": "Active",
  "summary": "M6.1 earthquake struck Sumatra, Indonesia causing building damage...",
  "classification": {},
  "location": {},
  "impact": {},
  "sources": [],
  "disaster_details": {},
  "disease_details": null,
  "media_coverage": {},
  "classification_metadata": {},
  "src_involvement": {},
  "escalation_tracking": {},
  "metadata": {}
}
```

Top-level required fields: `incident_id`, `incident_name`, `created_date`, `updated_date`, `status`, `classification`, `sources`.

Status enum: `Active` \| `Forecasted` \| `Updating` \| `Resolved` \| `Monitoring`

---

## Stage 3: MediaCoverage Record (Standalone)

For independent media monitoring, not tied to a specific classified incident:

```json
{
  "coverage_id": "20250311-MED-001",
  "incident_id": null,
  "recorded_date": "2025-03-11T12:00:00Z",
  "article_title": "Singapore Red Cross deploys team to Indonesia",
  "source": "Channel NewsAsia",
  "source_type": "News",
  "url": "https://...",
  "published_date": "2025-03-11T11:30:00Z",
  "content_type": "News-Article",
  "relevance_flags": {
    "singapore_mentioned": true,
    "src_mentioned": true,
    "donation_related": false,
    "misinformation": false,
    "scam_alert": false,
    "urgent": false
  },
  "content_analysis": {
    "summary": "...",
    "key_quotes": [],
    "sentiment": "positive",
    "accuracy": "verified"
  },
  "metadata": {
    "country": "Indonesia",
    "disaster_type": "Earthquake",
    "tags": ["src-response"]
  }
}
```

Source type: `News` \| `Social-Media` \| `Government` \| `Official-Statement` \| `Other`

Content type: `News-Article` \| `Blog-Post` \| `Social-Media-Post` \| `Video` \| `Official-Statement` \| `Other`

Accuracy: `verified` \| `unverified` \| `false` \| `uncertain`

---

## Incident Types (Enum)

| Category | Types |
|----------|-------|
| Geophysical | Earthquake, Volcano, Tsunami |
| Meteorological | Cyclone, Hurricane, Typhoon, Tornado, Dust Storm, Severe Weather |
| Hydrological | Flood, Flash Flood, Landslide, Avalanche |
| Climatological | Drought, Extreme Temperature, Wildfire |
| Biological | Disease |
| Technological | Industrial Accident, Infrastructure Failure |
| Conflict | Armed Conflict, Civil Unrest, Mass Displacement |
| Environmental | Air Pollution, Water Contamination |
| Other | Other |

---

## Incident ID Format

`YYYYMMDD-COUNTRYCODE-TYPECODE`

- Date: 8 digits
- Country: 2-letter ISO 3166-1 alpha-2 (e.g., `ID`, `PH`, `TH`)
- Type: 3-letter code

Common type codes:

| Code | Type |
|------|------|
| `EQ` | Earthquake |
| `FL` | Flood |
| `CY` | Cyclone |
| `VO` | Volcano |
| `WF` | Wildfire |
| `DR` | Drought |
| `LS` | Landslide |
| `TS` | Tsunami |
| `DI` | Disease |
| `CF` | Conflict |
| `OT` | Other |

Example: `20250311-ID-EQ` = March 11, 2025 earthquake in Indonesia

---

## Validation Rules

### R1: Required Fields

Every ClassifiedIncident MUST have: `incident_id`, `incident_name`, `created_date`, `updated_date`, `status`, `classification`, `sources` (at least 1).

### R2: Level-Priority Alignment

| Level | Group A | Group B | Group C |
|-------|---------|---------|---------|
| 4 | HIGH | HIGH | HIGH |
| 3 | HIGH | MEDIUM | MEDIUM |
| 2 | MEDIUM | MEDIUM | LOW |
| 1 | MEDIUM | LOW | LOW |

### R3: Date Consistency

- `created_date` ≤ `updated_date` ≤ current UTC time
- `disaster_details.first_reported` ≤ `created_date`

### R4: Impact Data Consistency

- All impact numbers ≥ 0
- `deaths` ≤ `affected_population`
- `injuries` ≤ `affected_population`

### R5: Source Reliability

- At least one source required
- Tier 1 sources increase classification confidence
- Single Tier 3 source → flag `high-uncertainty`

### R6: Enum Constraints

- `country_group`: `A` \| `B` \| `C`
- `incident_level`: 1 \| 2 \| 3 \| 4
- `priority`: `HIGH` \| `MEDIUM` \| `LOW`
- `status`: `Active` \| `Forecasted` \| `Updating` \| `Resolved` \| `Monitoring`

---

## Changes

| Date | Source | Change | Reason |
|------|--------|--------|--------|
| 2026-05-11 | Specification recovery | Created from deleted data-schema skill | Domain knowledge at risk of loss |
