---
name: data-schema
description: JSON schema definitions and data structures for storing disaster and health incident information in JSONL format
compatibility: "1.0.0+"
metadata:
  category: data-engineering
  difficulty: advanced
  type: data-schema
---

# Data Schema Skill

Comprehensive schema definitions for storing disaster and health incident data in standardized JSONL (JSON Lines) format.

## Overview

All incident data is stored in JSONL format (one JSON object per line) for:
- Efficient streaming and processing
- Easy appending of new records
- Compatibility with data analysis tools
- Compact storage and fast retrieval

## Core Incident Record Schema

Every incident record follows this comprehensive schema:

```json
{
  "incident_id": "string - unique identifier (YYYYMMDD-LOCATION-TYPE)",
  "incident_name": "string - human-readable incident name",
  "created_date": "string - ISO 8601 datetime when record created (YYYY-MM-DDTHH:MM:SSZ)",
  "updated_date": "string - ISO 8601 datetime of last update (YYYY-MM-DDTHH:MM:SSZ)",
  "status": "enum - Active | Forecasted | Updating | Resolved | Monitoring",
  
  "classification": {
    "country": "string - country name",
    "country_group": "enum - A | B | C",
    "region": "string - geographic region (South Asia, Southeast Asia, etc.)",
    "incident_type": "enum - Earthquake | Flood | Cyclone | Volcano | Wildfire | Drought | Landslide | Tsunami | Disease | Conflict | Other",
    "incident_level": "integer - 1-4 severity level",
    "priority": "enum - HIGH | MEDIUM | LOW",
    "should_report": "boolean - whether to include in distribution"
  },
  
  "location": {
    "country": "string - country name",
    "provinces": [
      {
        "name": "string - province/state/region name",
        "affected": "boolean - if impacted by incident"
      }
    ],
    "coordinates": {
      "latitude": "number - geographic latitude",
      "longitude": "number - geographic longitude"
    },
    "affected_area_description": "string - textual description of affected areas"
  },
  
  "impact": {
    "affected_population": "integer - estimated number of people affected",
    "deaths": "integer - confirmed deaths",
    "injuries": "integer - confirmed injuries",
    "displaced_persons": "integer - people displaced",
    "affected_provinces": "integer - number of provinces/states affected",
    "economic_damage_estimated": "number - estimated economic damage in USD",
    "impact_description": "string - detailed impact summary"
  },
  
  "sources": [
    {
      "name": "string - source name (GDACS, ProMED, Reuters, etc.)",
      "type": "enum - disaster-database | disease-database | news-agency | humanitarian-org | social-media | government | other",
      "url": "string - direct link to source",
      "accessed_date": "string - when source was accessed (YYYY-MM-DDTHH:MM:SSZ)",
      "reliability_tier": "enum - Tier1 | Tier2 | Tier3 | Unknown",
      "data_freshness": "enum - real-time | daily | weekly | archived"
    }
  ],
  
  "disaster_details": {
    "disaster_type": "string - specific disaster type",
    "magnitude_or_scale": "number - magnitude (earthquakes), wind speed (cyclones), etc.",
    "depth_or_altitude": "number - depth (earthquakes) or altitude (volcanoes)",
    "forecasted": "boolean - if this is a forecast vs. confirmed event",
    "forecast_confidence": "number - 0-1 confidence level if forecasted",
    "first_reported": "string - ISO 8601 datetime of first report",
    "latest_update": "string - ISO 8601 datetime of latest update"
  },
  
  "disease_details": {
    "disease_name": "string - name of disease",
    "confirmed_cases": "integer - confirmed cases",
    "suspected_cases": "integer - suspected cases",
    "deaths": "integer - deaths from disease",
    "investigation_status": "enum - Under Investigation | Confirmed | Contained | Spreading | Resolved",
    "spread_pattern": "enum - Localized | Regional | National | International | Unknown",
    "potential_pandemic": "boolean - if meets pandemic criteria"
  },
  
  "media_coverage": {
    "singapore_mentioned": "boolean - if Singapore mentioned",
    "src_mentioned": "boolean - if Singapore Red Cross mentioned",
    "donation_concerns": "boolean - if donation concerns flagged",
    "misinformation_detected": "boolean - if misinformation flagged",
    "public_sentiment": "enum - positive | neutral | negative | mixed | unknown",
    "coverage_articles": [
      {
        "title": "string - article title",
        "source": "string - news outlet",
        "url": "string - article link",
        "published_date": "string - publication date",
        "relevance": "enum - SRC-Involved | Singapore-Related | General | Other"
      }
    ]
  },
  
  "classification_metadata": {
    "classified_by": "string - agent or person who classified",
    "classified_date": "string - when classification was done",
    "classification_confidence": "number - 0-1 confidence in classification",
    "rationale": "string - explanation of why classified this way",
    "special_flags": [
      "string - humanitarian-crisis | multi-regional | escalation-risk | high-uncertainty"
    ]
  },
  
  "src_involvement": {
    "involved": "boolean - if SRC is involved",
    "involvement_type": "enum - None | Monitoring | Supporting | Leading | Coordinating",
    "donation_appeal_active": "boolean - active fundraising",
    "volunteer_deployment": "boolean - volunteers deployed",
    "estimated_response_value": "number - estimated donation/response value",
    "response_notes": "string - details of SRC response"
  },
  
  "escalation_tracking": {
    "initial_level": "integer - incident level when first reported",
    "current_level": "integer - current incident level",
    "escalation_potential": "boolean - if likely to escalate",
    "level_change_history": [
      {
        "level": "integer - severity level",
        "date": "string - when level changed",
        "reason": "string - why level changed"
      }
    ]
  },
  
  "metadata": {
    "data_quality": "enum - High | Medium | Low",
    "completeness_score": "number - 0-1 how complete record is",
    "last_verified": "string - when data was last verified",
    "related_incidents": ["string - IDs of related incidents"],
    "tags": ["string - searchable tags"],
    "notes": "string - additional notes or observations"
  }
}
```

## Simplified Record Schema (Minimal)

For quick storage when full details aren't yet available:

```json
{
  "incident_id": "string",
  "incident_name": "string",
  "created_date": "string - ISO 8601",
  "country": "string",
  "country_group": "enum - A | B | C",
  "incident_type": "enum",
  "incident_level": "integer - 1-4",
  "priority": "enum - HIGH | MEDIUM | LOW",
  "sources": [{"name": "string", "url": "string"}],
  "impact_summary": "string - brief description",
  "should_report": "boolean"
}
```

## Media Coverage Record Schema

For storing media monitoring data:

```json
{
  "coverage_id": "string - unique identifier",
  "incident_id": "string - related incident ID or null",
  "recorded_date": "string - ISO 8601 when recorded",
  "article_title": "string - title of article/post",
  "source": "string - news outlet, social media, etc.",
  "source_type": "enum - News | Social-Media | Government | Official-Statement | Other",
  "url": "string - link to content",
  "published_date": "string - ISO 8601 publication date",
  "content_type": "enum - News-Article | Blog-Post | Social-Media-Post | Video | Official-Statement | Other",
  
  "relevance_flags": {
    "singapore_mentioned": "boolean",
    "src_mentioned": "boolean",
    "donation_related": "boolean",
    "misinformation": "boolean",
    "scam_alert": "boolean",
    "urgent": "boolean"
  },
  
  "content_analysis": {
    "summary": "string - brief summary of content",
    "key_quotes": ["string"],
    "sentiment": "enum - positive | neutral | negative | mixed",
    "accuracy": "enum - verified | unverified | false | uncertain"
  },
  
  "metadata": {
    "country": "string",
    "disaster_type": "string",
    "recorded_by": "string - agent or person",
    "tags": ["string"]
  }
}
```

## Query Helper Schema

For tracking queries run against the data:

```json
{
  "query_id": "string - unique identifier",
  "query_type": "enum - incident-search | media-search | date-range | country-filter | type-filter",
  "query_date": "string - ISO 8601 when query was run",
  "parameters": {
    "country": "string - optional",
    "country_group": "string - optional",
    "date_from": "string - optional YYYY-MM-DD",
    "date_to": "string - optional YYYY-MM-DD",
    "incident_type": "string - optional",
    "incident_level": "integer - optional",
    "priority": "string - optional"
  },
  "results_count": "integer - number of results",
  "query_time_ms": "integer - query execution time"
}
```

## Schema Validation Rules

### Required Fields (Always)
- `incident_id` - Must be unique across all records
- `incident_name` - Human-readable name
- `created_date` - When record created
- `country` - Country name
- `country_group` - A, B, or C
- `incident_type` - Type of incident
- `incident_level` - 1-4
- `priority` - HIGH, MEDIUM, or LOW
- `sources` - At least one source

### ISO 8601 Format
All dates/times use ISO 8601 format:
- Datetime: `YYYY-MM-DDTHH:MM:SSZ` (UTC)
- Date only: `YYYY-MM-DD`
- Example: `2025-03-11T14:30:45Z`

### Incident ID Format
`YYYYMMDD-COUNTRYCODE-TYPECODE`
- Date: 8 digits (year, month, day)
- Country: 2-letter ISO code (ID, PH, TH, etc.)
- Type: 3-letter code (EQ=Earthquake, FL=Flood, CY=Cyclone, DI=Disease, etc.)
- Example: `20250311-ID-FL` (March 11, 2025 flood in Indonesia)

### Enum Constraints
- `country_group`: Must be A, B, or C
- `incident_type`: Fixed list of types (Earthquake, Flood, etc.)
- `priority`: Must be HIGH, MEDIUM, or LOW
- `incident_level`: Must be 1, 2, 3, or 4
- `status`: Active, Forecasted, Updating, Resolved, or Monitoring

## Data Integrity Rules

### Constraint 1: Level and Priority Alignment
- Level 4 → Priority MUST be HIGH
- Level 3 + Group A/B → Priority MUST be HIGH or MEDIUM
- Level 3 + Group C → Priority MAY be MEDIUM
- Level 2 + Group A → Priority MAY be MEDIUM
- Level 1 → Priority MAY be MEDIUM or LOW

### Constraint 2: Country Group Validation
- Must match country against known lists in Group A, B, or C
- Invalid countries not accepted

### Constraint 3: Date Consistency
- `created_date` ≤ `updated_date` (always)
- `updated_date` ≤ Current UTC time
- `disaster_details.first_reported` ≤ `created_date`

### Constraint 4: Impact Data Consistency
- `deaths` ≤ `affected_population` (logically)
- `injuries` ≤ `affected_population`
- `displaced_persons` ≤ `affected_population`
- All impact numbers ≥ 0

### Constraint 5: Source Reliability
- Tier 1 sources have highest weight in classification
- Multiple Tier 1 sources increase confidence
- Single Tier 3 source has lower confidence

## Data Type Specifications

### String Fields
- Max length: 2000 characters for descriptions, 500 for names
- UTF-8 encoding
- No null values (use empty string if needed)

### Number Fields
- Integers: Whole numbers only
- Decimals: Up to 2 decimal places for coordinates/measurements
- No negative values for counts
- No NaN or Infinity values

### Boolean Fields
- Only true or false (not 1/0 or "yes"/"no")

### Enum Fields
- Must match predefined options exactly
- Case-sensitive where specified
- No custom values allowed

### Array Fields
- Ordered lists of objects or strings
- Each element must match schema
- Empty arrays allowed
- No duplicate elements (when applicable)

## Backwards Compatibility

Schema version: 1.0

Future schema changes will be tracked with version numbers in metadata. Current implementation supports:
- Adding new optional fields (backwards compatible)
- Adding new enum values (notify users)
- Changing data types (breaking change - new version)
- Removing fields (breaking change - new version)

## Example Records

### Example 1: Earthquake Incident
```json
{
  "incident_id": "20250311-ID-EQ",
  "incident_name": "Earthquake in Sumatra, Indonesia",
  "created_date": "2025-03-11T10:15:00Z",
  "updated_date": "2025-03-11T14:30:00Z",
  "status": "Active",
  "classification": {
    "country": "Indonesia",
    "country_group": "A",
    "region": "Southeast Asia",
    "incident_type": "Earthquake",
    "incident_level": 2,
    "priority": "MEDIUM",
    "should_report": true
  },
  "location": {
    "country": "Indonesia",
    "provinces": [{"name": "Sumatra", "affected": true}],
    "coordinates": {"latitude": -0.89, "longitude": 100.74},
    "affected_area_description": "Sumatra region, centered near Padang"
  },
  "impact": {
    "affected_population": 75000,
    "deaths": 12,
    "injuries": 45,
    "displaced_persons": 5000,
    "affected_provinces": 1,
    "impact_description": "Moderate earthquake causing building damage and landslides"
  },
  "sources": [
    {
      "name": "GDACS",
      "type": "disaster-database",
      "url": "https://www.gdacs.org/incident/20250311",
      "accessed_date": "2025-03-11T10:20:00Z",
      "reliability_tier": "Tier1",
      "data_freshness": "real-time"
    }
  ],
  "disaster_details": {
    "disaster_type": "Tectonic Earthquake",
    "magnitude_or_scale": 6.1,
    "depth_or_altitude": 25,
    "forecasted": false,
    "first_reported": "2025-03-11T09:45:00Z",
    "latest_update": "2025-03-11T14:30:00Z"
  },
  "media_coverage": {
    "singapore_mentioned": false,
    "src_mentioned": false,
    "donation_concerns": false,
    "misinformation_detected": false,
    "public_sentiment": "neutral",
    "coverage_articles": []
  },
  "classification_metadata": {
    "classified_by": "disaster-incident-reporter",
    "classified_date": "2025-03-11T10:25:00Z",
    "classification_confidence": 0.95,
    "rationale": "6.1 magnitude earthquake in Group A country with 75K affected and multiple provinces, further development likely",
    "special_flags": ["escalation-risk"]
  },
  "src_involvement": {
    "involved": false,
    "involvement_type": "None"
  },
  "escalation_tracking": {
    "initial_level": 2,
    "current_level": 2,
    "escalation_potential": true,
    "level_change_history": []
  },
  "metadata": {
    "data_quality": "High",
    "completeness_score": 0.92,
    "tags": ["earthquake", "Indonesia", "Sumatra", "Group-A"],
    "notes": "Monitor for aftershocks and updated impact assessments"
  }
}
```

### Example 2: Disease Outbreak
```json
{
  "incident_id": "20250311-MY-DI",
  "incident_name": "Chikungunya Outbreak in Malaysia",
  "created_date": "2025-03-11T08:00:00Z",
  "updated_date": "2025-03-11T08:00:00Z",
  "status": "Active",
  "classification": {
    "country": "Malaysia",
    "country_group": "A",
    "region": "Southeast Asia",
    "incident_type": "Disease",
    "incident_level": 1,
    "priority": "MEDIUM",
    "should_report": true
  },
  "sources": [
    {
      "name": "ProMED-mail",
      "type": "disease-database",
      "url": "https://www.promedmail.org/post/12345678",
      "accessed_date": "2025-03-11T08:05:00Z",
      "reliability_tier": "Tier1",
      "data_freshness": "daily"
    }
  ],
  "disease_details": {
    "disease_name": "Chikungunya",
    "confirmed_cases": 50,
    "suspected_cases": 120,
    "deaths": 0,
    "investigation_status": "Under Investigation",
    "spread_pattern": "Localized",
    "potential_pandemic": false
  },
  "classification_metadata": {
    "rationale": "Early outbreak in Group A country, limited spread but Group A monitoring priority"
  }
}
```

## Performance Considerations

### Indexing Strategy (for future)
Index on:
- `incident_id` (primary key)
- `country_group` (common filter)
- `incident_type` (common filter)
- `created_date` (range queries)
- `priority` (filtering)

### Storage Optimization
- Use JSONL format (one object per line)
- Compress at rest if file size > 10MB
- Archive old records to dated files
- Partition by date and country_group

### Query Optimization
- Filter by date first (most selective)
- Filter by country_group second
- Full-text search on incident_name, impact_description

## Validation Checklist

When storing a record, verify:
- [ ] All required fields present
- [ ] Incident ID is unique
- [ ] All dates are valid ISO 8601
- [ ] Enum values match constraints
- [ ] Country is in known country lists
- [ ] Impact numbers are consistent
- [ ] Level and priority align correctly
- [ ] At least one source present and valid
- [ ] No future dates
- [ ] UTF-8 encoding correct
