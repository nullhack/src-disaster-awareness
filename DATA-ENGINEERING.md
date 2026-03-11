# Data Engineering System Documentation

Complete guide to the disaster incident data storage and processing system.

## System Overview

The Data Engineering system provides a professional-grade data pipeline for processing, validating, and organizing disaster incident information using the `@data-engineer` subagent.

### Architecture

```
Incident Data Sources
├── disaster-incident-reporter (GDACS/ProMED)
├── media-incident-reporter (News/Social Media)
└── Manual submissions (JSON)

        ↓

@data-engineer Agent
├── Validates against data-schema
├── Transforms/normalizes data
├── Generates incident IDs
├── Creates necessary directories
└── Writes to JSONL files

        ↓

Storage System
├── by-date/ (primary - YYYY-MM-DD)
├── by-country-group/ (secondary - monthly)
├── by-incident-type/ (tertiary)
├── by-country/ (country-specific)
├── media-coverage/ (media records)
├── escalations/ (escalation tracking)
├── archive/ (historical)
└── indices/ (fast lookups)

        ↓

Accessible Data
├── JSONL files (streaming)
├── Metadata (fast stats)
├── Indices (quick lookup)
└── Query tools (jq, Python)
```

---

## Components

### 1. data-schema Skill
**File:** `.opencode/skills/data-schema/SKILL.md`

**Purpose:** Defines complete JSON schema for all incident data

**Key Features:**
- Full incident record schema (60+ fields)
- Simplified incident schema (for quick storage)
- Media coverage record schema
- Query helper schema
- Validation rules and constraints
- Example records
- Data type specifications
- Backwards compatibility guidelines

**Schema Structure:**
```
- incident_id, incident_name, dates
- classification (level, priority, group, type)
- location (country, provinces, coordinates)
- impact (affected population, deaths, etc.)
- sources (with reliability tiers)
- disaster_details OR disease_details
- media_coverage (coverage articles)
- classification_metadata (rationale, confidence)
- src_involvement (SRC response tracking)
- escalation_tracking (level changes)
- metadata (quality score, tags)
```

**Validation Rules:**
- Required fields must be present
- Enums must match exact values
- Dates must be ISO 8601 format
- Impact numbers must be logical (deaths ≤ affected)
- Country codes must be valid
- Level and priority must align

---

### 2. data-storage Skill
**File:** `.opencode/skills/data-storage/SKILL.md`

**Purpose:** Defines folder organization and file structure

**Key Features:**
- Multi-level directory hierarchy
- Primary organization by date
- Secondary organization by region/type
- File naming conventions
- Index strategy for fast lookups
- Rotation and archival strategy
- Compression guidelines
- Access patterns (fast, analytical, historical)

**Directory Structure (At a Glance):**
```
incidents/
├── by-date/[YYYY-MM-DD]/               (PRIMARY - daily files)
├── by-country-group/[group]/[YYYY-MM]/ (SECONDARY - regional)
├── by-incident-type/[type]/[status]/   (TERTIARY - typed)
├── by-country/[country]/                (COUNTRY-SPECIFIC)
├── media-coverage/[YYYY-MM]/            (MEDIA RECORDS)
├── escalations/[YYYY-MM-DD]/            (ESCALATION TRACKING)
├── archive/[YYYY]/                      (HISTORICAL DATA)
└── indices/                             (FAST LOOKUPS)
```

**File Types:**
- `incidents.jsonl` - Incident records
- `media-coverage.jsonl` - Media records
- `metadata.json` - Daily/monthly statistics
- `[filtered].jsonl` - Pre-filtered subsets
- `[index].jsonl` - Index files for fast lookup

---

### 3. data-engineer Subagent
**File:** `.opencode/agents/data-engineer.md`

**Purpose:** Process, validate, and store incident data

**Key Responsibilities:**
1. Receive incident data from sources
2. Validate against data-schema
3. Check data quality and integrity
4. Transform/normalize as needed
5. Generate incident IDs
6. Create directories
7. Write to JSONL files
8. Update indices and metadata
9. Detect and flag escalations
10. Report processing status

**Six-Phase Workflow:**

**Phase 1: Reception & Validation (5 mins)**
- Receive JSON object(s)
- Load data-schema skill
- Validate all required fields
- Check data integrity constraints
- Generate quality score
- Determine if ready to store

**Phase 2: Data Transformation (3 mins)**
- Normalize dates to ISO 8601 UTC
- Standardize country names
- Fix enum values
- Generate incident ID if missing
- Populate missing metadata
- Ensure full record completeness

**Phase 3: Directory Organization (2 mins)**
- Determine all target directories
- Load data-storage skill
- Identify directory needs
- Create directories if missing

**Phase 4: JSONL File Writing (3 mins)**
- Append to `by-date/[YYYY-MM-DD]/incidents.jsonl`
- Append to `by-country-group/[group]/[YYYY-MM]/incidents.jsonl`
- Append to `by-incident-type/[type]/[status]/incidents.jsonl`
- Append to `by-country/[country]/incidents.jsonl`
- Append media coverage records to separate files

**Phase 5: Index Updates (2 mins)**
- Update `incident-index.jsonl`
- Update `country-index.jsonl`
- Update `date-index.jsonl`
- Enable fast lookups

**Phase 6: Metadata Updates (2 mins)**
- Update daily metadata (counts, statistics)
- Update monthly metadata
- Update type-specific metadata
- Generate summary statistics

**Temperature:** 0.1 (Focused, deterministic)

**Tools Used:**
- `skill` - Load data-schema and data-storage
- `write` - Create metadata and index files
- `bash` - Create directories, append to files
- `read` - Check for duplicates
- `grep` - Search for existing incident IDs

---

## Data Flow Example

### Scenario: New Earthquake Incident

```
1. disaster-incident-reporter detects GDACS alert
   → Sends structured incident JSON

2. @data-engineer receives incident:
{
  "incident_id": "20250311-ID-EQ",
  "incident_name": "Earthquake in Sumatra, Indonesia",
  "created_date": "2025-03-11T10:15:00Z",
  "country": "Indonesia",
  "country_group": "A",
  "incident_type": "Earthquake",
  "incident_level": 2,
  "priority": "MEDIUM",
  ...
}

3. Validation Phase:
   ✓ All required fields present
   ✓ Dates in ISO 8601 format
   ✓ Country in Group A list
   ✓ Incident level 1-4
   ✓ Priority HIGH/MEDIUM/LOW
   ✓ At least one source
   Quality Score: 0.95 → Ready to store

4. Transformation Phase:
   - Verify ID format: YYYYMMDD-CC-TTT ✓
   - Normalize dates to UTC ✓
   - Populate metadata fields ✓

5. Organization Phase:
   Create directories:
   - incidents/by-date/2025-03-11/
   - incidents/by-country-group/group-a/2025-03/
   - incidents/by-incident-type/earthquake/active/
   - incidents/by-country/indonesia/

6. Write Phase:
   Append to:
   - by-date/2025-03-11/incidents.jsonl
   - by-country-group/group-a/2025-03/incidents.jsonl
   - by-incident-type/earthquake/active/incidents.jsonl
   - by-country/indonesia/active-incidents.jsonl

7. Index Updates:
   Add to:
   - indices/incident-index.jsonl
   - indices/country-index.jsonl
   - indices/date-index.jsonl

8. Metadata Updates:
   Update:
   - by-date/2025-03-11/metadata.json
   - by-country-group/group-a/2025-03/metadata.json
   - by-incident-type/earthquake/metadata.json

9. Report Status:
   {
     "total_received": 1,
     "validated_successfully": 1,
     "stored": 1,
     "warnings": 0,
     "errors": 0,
     "storage_location": "incidents/by-date/2025-03-11/",
     "files_written": ["incidents.jsonl", "metadata.json"]
   }
```

---

## Usage Examples

### Using the data-engineer Agent

**Example 1: Store Single Incident**
```
@data-engineer Store this earthquake incident:
{
  "incident_name": "Earthquake in Sumatra, Indonesia",
  "country": "Indonesia",
  "incident_type": "Earthquake",
  "incident_level": 2,
  "priority": "MEDIUM",
  "affected_population": 75000,
  "deaths": 12,
  "sources": [{"name": "GDACS", "url": "https://www.gdacs.org/..."}]
}
```

**Example 2: Store Batch of Incidents**
```
@data-engineer Process these 5 incidents from today's monitoring:
[
  {incident 1},
  {incident 2},
  {incident 3},
  {incident 4},
  {incident 5}
]
```

**Example 3: Store with Media Coverage**
```
@data-engineer Store incident with media monitoring:
{
  "incident": {...},
  "media_coverage": [
    {
      "source": "Reuters",
      "url": "https://...",
      "singapore_mentioned": true,
      "src_mentioned": false
    }
  ]
}
```

### Querying Stored Data

**Using Command Line:**
```bash
# Read today's incidents
cat incidents/by-date/$(date +%Y-%m-%d)/incidents.jsonl

# Count incidents by level
jq '.classification.incident_level' incidents/by-date/2025-03-11/incidents.jsonl | sort | uniq -c

# Find Group A incidents
grep '"country_group": "A"' incidents/by-country-group/group-a/2025-03/incidents.jsonl

# Get Singapore mentions
wc -l incidents/media-coverage/2025-03/singapore-mentions.jsonl

# Search by incident ID
grep '"incident_id": "20250311-ID-EQ"' incidents/by-date/2025-03-11/incidents.jsonl
```

**Using Python:**
```python
import jsonlines
from datetime import datetime

# Read today's incidents
date = datetime.now().strftime('%Y-%m-%d')
with jsonlines.open(f'incidents/by-date/{date}/incidents.jsonl') as reader:
    for incident in reader:
        if incident['classification']['incident_level'] >= 3:
            print(f"PRIORITY: {incident['incident_name']}")

# Batch analysis
high_priority_count = 0
with jsonlines.open(f'incidents/by-date/{date}/incidents.jsonl') as reader:
    for incident in reader:
        if incident['classification']['priority'] == 'HIGH':
            high_priority_count += 1

print(f"High priority incidents today: {high_priority_count}")
```

---

## Data Quality & Validation

### Quality Scoring

Data quality is scored 0-1 based on:
- **1.0:** All required fields present and valid
- **0.95:** All required, some optional fields missing
- **0.85-0.94:** Some data gaps or uncertainties
- **0.75-0.84:** Significant missing data (warnings)
- **< 0.75:** Critical data missing (needs review)

### Validation Rules

**Must Pass:**
- All required fields present
- Valid schema conformance
- Unique incident ID
- Valid dates (ISO 8601)
- Impact numbers logical

**Should Pass:**
- Enum values correct
- Country in known list
- At least one credible source
- Level/Priority alignment

**Nice to Have:**
- All optional fields present
- Multiple sources
- SRC involvement data
- Complete media coverage

### Quality Thresholds

| Score | Action |
|-------|--------|
| ≥ 0.95 | Store immediately |
| 0.85-0.95 | Store with warnings logged |
| < 0.85 | Flag for manual review |

---

## Escalation Detection

The system automatically detects escalations:

**Detection Checks:**

1. **Level Change**
   - If previous incident exists
   - Compare incident_level to previous
   - If increased: Level escalation

2. **Humanitarian Crisis**
   - If special_flags contains "humanitarian-crisis"
   - Mark as HIGH priority
   - Flag for immediate action

3. **Geographic Spread**
   - If affected_provinces increased
   - If multi-regional spread detected
   - Elevate priority

**Escalation Actions:**

When detected:
- Create escalation record
- Store in `escalations/[YYYY-MM-DD]/escalations.jsonl`
- Update escalation metadata
- Flag for SRC alert
- Return escalation notification

**Example Escalation Alert:**
```json
{
  "action": "ESCALATION_ALERT",
  "priority": "CRITICAL",
  "incident_id": "20250311-ID-FL",
  "previous_level": 2,
  "new_level": 3,
  "reason": "Death toll increased from 5 to 25; widespread impact now confirmed",
  "src_notification": true
}
```

---

## Storage Capacity & Performance

### File Sizes
- Daily JSONL: 1-10 MB typical
- Monthly JSONL: 50-500 MB typical
- Archive JSONL: Compressed if > 100 MB

### Query Performance
- Metadata lookup: < 1 ms
- Date-based query: < 100 ms
- Country lookup: < 200 ms
- Index-based search: < 500 ms
- Full scan: 1-10 seconds

### Growth Projections
- Daily incidents: 5-20
- Daily growth: 5-50 KB
- Annual growth: 2-20 MB
- Long-term manageable with current structure

---

## Integration Points

### Input Sources
- **disaster-incident-reporter** - GDACS/ProMED incidents
- **media-incident-reporter** - Media coverage records
- **Manual API** - Direct JSON submission
- **Batch files** - Multiple incidents at once

### Output Destinations
- **by-date/** - Daily accessible records
- **by-country-group/** - Regional analysis
- **by-incident-type/** - Type-specific queries
- **indices/** - Fast lookup capability
- **archive/** - Historical reference

### Downstream Consumers
- **incident-summarizer** - Retrieves for report compilation
- **Analysis tools** - Query for patterns/trends
- **SRC operations** - Access for response coordination
- **Public reports** - Historical data for statistics

---

## Best Practices

### Writing Data
1. ✅ Always validate before storing
2. ✅ Use data-engineer agent (handles all steps)
3. ✅ Batch multiple incidents when possible
4. ✅ Include all available sources
5. ✅ Verify incident ID uniqueness

### Querying Data
1. ✅ Use by-date/ for recent data
2. ✅ Use indices/ for large lookups
3. ✅ Use metadata.json for statistics
4. ✅ Filter in memory (jq) for complex queries
5. ✅ Archive old data for performance

### Maintaining Data
1. ✅ Daily backups of by-date/
2. ✅ Weekly backups of by-country-group/
3. ✅ Monthly full backups
4. ✅ Monitor file sizes
5. ✅ Archive resolved incidents > 3 months

---

## Troubleshooting

### Issue: Validation Failure
**Error:** "Quality score < 0.85, needs review"
**Solution:** 
- Check required fields are present
- Verify data types match schema
- Ensure country is in known list
- Validate incident level 1-4

### Issue: Directory Not Created
**Error:** "Permission denied creating directory"
**Solution:**
- Check write permissions on incidents/
- Verify disk space available
- Check parent directories exist
- Retry operation

### Issue: Duplicate Incident ID
**Error:** "Incident ID already exists"
**Solution:**
- Check if updating existing incident (use updated_date)
- If different incident, generate new ID
- Append timestamp to differentiate
- Use incident-index.jsonl to check

### Issue: JSONL Write Failure
**Error:** "Write operation failed"
**Solution:**
- Verify file handle working
- Check disk space
- Validate JSON format
- Attempt append operation
- Check file permissions

### Issue: Corrupted JSONL File
**Error:** "Invalid JSON in file"
**Solution:**
- Read file line by line
- Skip corrupted lines
- Log error location
- Restore from backup
- Re-process incident

---

## Performance Metrics

### Operation Timing
- Validation: < 5 seconds per incident
- Transformation: < 2 seconds
- Directory creation: < 1 second
- JSONL writing: < 2 seconds
- Index update: < 2 seconds
- Metadata update: < 2 seconds
- **Total:** < 15 seconds per incident

### Query Performance
- By date: < 100 ms (single date file)
- By country: < 500 ms (one country file)
- By type: < 500 ms (one type file)
- Metadata stat: < 1 ms (JSON read)
- Full index search: < 1 second

### Storage Efficiency
- Compression ratio: ~70% (raw to gzip)
- Deduplication: Indices enable fast dupe checking
- Partitioning: Enables parallel processing
- Archival: 3+ year retention possible in << 1 GB

---

## Future Enhancements

1. **Database Backend**
   - Replace JSONL with PostgreSQL for transactions
   - Enable complex queries
   - Support concurrent access

2. **Real-time Streaming**
   - WebSocket integration
   - Live incident feeds
   - Immediate alerting

3. **Analytics Engine**
   - Pattern detection
   - Anomaly identification
   - Predictive modeling

4. **Visualization Dashboard**
   - Interactive maps
   - Time-series charts
   - Regional heatmaps

5. **API Layer**
   - REST API for queries
   - GraphQL support
   - Webhook notifications

---

## References

- **data-schema Skill:** `.opencode/skills/data-schema/SKILL.md`
- **data-storage Skill:** `.opencode/skills/data-storage/SKILL.md`
- **data-engineer Agent:** `.opencode/agents/data-engineer.md`
- **JSONL Format:** https://jsonlines.org/
- **ISO 8601 Dates:** https://en.wikipedia.org/wiki/ISO_8601
- **System Architecture:** `AGENTS.md`

---

## Quick Start

1. **Review Schema:** Understand incident structure
2. **Check Directory:** Look at `incidents/` structure
3. **Use Agent:** `@data-engineer Store incident [JSON]`
4. **Query Data:** `cat incidents/by-date/$(date +%Y-%m-%d)/incidents.jsonl`
5. **Analyze:** Use jq or Python for filtering

---

**Document Version:** 1.0  
**Last Updated:** 2025-03-11  
**Status:** Active  
**Maintained By:** Data Engineering Team
