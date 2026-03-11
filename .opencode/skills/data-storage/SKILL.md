---
name: data-storage
description: Folder organization, directory structure, and file management conventions for disaster incident data storage
compatibility: "1.0.0+"
metadata:
  category: data-engineering
  difficulty: advanced
  type: data-storage
---

# Data Storage Skill

Comprehensive guide for organizing disaster and health incident data in a scalable, queryable directory structure.

## Directory Structure Overview

```
incidents/
├── README.md (overview and access guide)
├── staging/                          # STAGING - Reporters write raw data here
│   ├── incidents.jsonl              # Raw incidents from reporters
│   ├── media.jsonl                   # Raw media coverage
│   └── metadata.json                 # Staging metadata (counts, timestamps)
│
├── by-date/
│   ├── 2025-03-11/
│   │   ├── incidents.jsonl
│   │   ├── media-coverage.jsonl
│   │   └── metadata.json
│   ├── 2025-03-10/
│   │   ├── incidents.jsonl
│   │   ├── media-coverage.jsonl
│   │   └── metadata.json
│   └── [YYYY-MM-DD]/
│
├── by-country-group/
│   ├── group-a/
│   │   ├── 2025-03/
│   │   │   ├── incidents.jsonl
│   │   │   └── metadata.json
│   │   ├── 2025-02/
│   │   └── [YYYY-MM]/
│   ├── group-b/
│   │   ├── 2025-03/
│   │   └── [YYYY-MM]/
│   └── group-c/
│       └── [YYYY-MM]/
│
├── by-incident-type/
│   ├── earthquake/
│   │   ├── active/
│   │   │   └── incidents.jsonl
│   │   ├── resolved/
│   │   │   └── incidents.jsonl
│   │   └── metadata.json
│   ├── flood/
│   ├── cyclone/
│   ├── disease/
│   ├── wildfire/
│   └── [type]/
│
├── by-country/
│   ├── indonesia/
│   │   ├── active-incidents.jsonl
│   │   ├── resolved-incidents.jsonl
│   │   └── metadata.json
│   ├── philippines/
│   ├── malaysia/
│   └── [country]/
│
├── media-coverage/
│   ├── 2025-03/
│   │   ├── coverage.jsonl
│   │   ├── singapore-mentions.jsonl
│   │   ├── src-mentions.jsonl
│   │   └── misinformation.jsonl
│   └── [YYYY-MM]/
│
├── escalations/
│   ├── 2025-03-11/
│   │   └── escalations.jsonl
│   └── [YYYY-MM-DD]/
│
├── archive/
│   ├── 2024/
│   │   ├── resolved-incidents.jsonl
│   │   └── media-coverage.jsonl
│   └── [YYYY]/
│
└── indices/
    ├── incident-index.jsonl
    ├── country-index.jsonl
    ├── date-index.jsonl
    └── query-log.jsonl
```

## Staging Area (Workflow Separation)

The staging area separates data collection from data processing, allowing reporters and data engineers to work independently.

### Workflow Overview

```
┌─────────────────────────────────────────────────────────┐
│  STAGE 1: Reporters (disaster-incident-reporter,     │
│            media-incident-reporter)                    │
│  ↓                                                     │
│  Write raw data to staging/                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  STAGE 2: Data Engineer                                │
│  - Read from staging/                                  │
│  - Validate, deduplicate, transform                   │
│  - Write to by-date/, by-country-group/, etc.         │
│  - Update indices and metadata                         │
│  - Clear staging files after processing              │
└─────────────────────────────────────────────────────────┘
```

### Directory: `incidents/staging/`

**Purpose:** Raw incident data from reporters before validation and processing

### Files in Staging

#### 1. `incidents.jsonl`
**Purpose:** Raw incidents from reporters

**Content:** Unvalidated incident records
```
{"incident_name": "Flood in Aceh", "country": "Indonesia", ...}
{"incident_name": "Earthquake in Luzon", "country": "Philippines", ...}
```

**Notes:**
- May not conform to full data-schema
- May contain duplicates
- May have missing optional fields
- Reporters write here directly

#### 2. `media.jsonl`
**Purpose:** Raw media coverage from reporters

**Content:** Media articles without full normalization
```
{"source": "Reuters", "title": "...", "url": "...", ...}
```

**Notes:**
- May not have coverage_id assigned
- May need linking to existing incidents

#### 3. `metadata.json`
**Purpose:** Track what's in staging

**Content:**
```json
{
  "staging_date": "2025-03-11",
  "pending_incidents": 5,
  "pending_media": 12,
  "received_from": ["disaster-incident-reporter", "media-incident-reporter"],
  "received_at": "2025-03-11T08:00:00Z",
  "processed": false
}
```

### Write Operations: Reporters

**Step 1:** Append raw incident
```bash
echo '[raw incident JSON]' >> incidents/staging/incidents.jsonl
```

**Step 2:** Append raw media
```bash
echo '[raw media JSON]' >> incidents/staging/media.jsonl
```

### Process & Clear: Data Engineer

**Step 1:** Read staging
```bash
cat incidents/staging/incidents.jsonl
cat incidents/staging/media.jsonl
```

**Step 2:** Validate, deduplicate, transform

**Step 3:** Write to final locations
- Write to by-date/[YYYY-MM-DD]/
- Write to by-country-group/
- Write to by-incident-type/
- Write to by-country/

**Step 4:** Clear staging after successful processing
```bash
# Remove or truncate staging files after successful processing
rm incidents/staging/incidents.jsonl
rm incidents/staging/media.jsonl
# Update metadata.json to mark as processed
```

### Why Use Staging?

1. **Separation of Concerns:** Reporters don't need to know final storage structure
2. **Validation Gate:** Data engineer can catch issues before they reach main database
3. **Deduplication:** Can check against existing records before writing
4. **Error Recovery:** If processing fails, data remains in staging for retry

## Primary Structure: By Date (Most Important)

**Directory:** `incidents/by-date/[YYYY-MM-DD]/`

This is the primary working directory where all new incidents are written.

### Files in Each Date Directory

#### 1. `incidents.jsonl`
**Purpose:** All new incident records created/updated on this date

**Content:** One incident JSON object per line
```
{"incident_id": "20250311-ID-EQ", "incident_name": "...", ...}
{"incident_id": "20250311-PH-FL", "incident_name": "...", ...}
{"incident_id": "20250311-TH-DI", "incident_name": "...", ...}
```

**Naming:** `incidents.jsonl`
**Encoding:** UTF-8
**One record per line:** Yes
**Rotation:** Daily (new file each day)

#### 2. `media-coverage.jsonl`
**Purpose:** All media monitoring records for this date

**Content:** Media coverage records
```
{"coverage_id": "C001", "incident_id": "20250311-ID-EQ", "source": "Reuters", ...}
{"coverage_id": "C002", "incident_id": "20250311-PH-FL", "source": "AJazeera", ...}
```

**When to include:** All media monitoring results
**Rotation:** Daily

#### 3. `metadata.json`
**Purpose:** Summary statistics for the day

**Content:**
```json
{
  "date": "2025-03-11",
  "total_incidents": 5,
  "total_media_coverage": 12,
  "incidents_by_level": {
    "1": 1,
    "2": 2,
    "3": 1,
    "4": 1
  },
  "incidents_by_group": {
    "A": 4,
    "B": 1,
    "C": 0
  },
  "incidents_by_type": {
    "Earthquake": 1,
    "Flood": 2,
    "Disease": 1,
    "Cyclone": 1
  },
  "escalations": 1,
  "src_mentioned_count": 2,
  "singapore_mentioned_count": 3,
  "generated_timestamp": "2025-03-11T23:59:59Z"
}
```

**Update frequency:** Once per day (end of day)
**Purpose:** Quick stats without parsing JSONL files

## Secondary Structure: By Country Group (Monthly)

**Directory:** `incidents/by-country-group/[group-a|group-b|group-c]/[YYYY-MM]/`

Organized for efficient querying by geographic region.

### Files by Country Group
```
group-a/2025-03/
├── incidents.jsonl (all Group A incidents for March 2025)
├── active-incidents.jsonl (subset: status = Active)
├── escalations.jsonl (incidents that escalated)
└── metadata.json (monthly summary)

group-b/2025-03/
├── incidents.jsonl
├── metadata.json
└── [same structure]

group-c/2025-03/
├── incidents.jsonl
└── metadata.json
```

**Purpose:** 
- Quick filtering by region
- Regional analysis
- Group-specific reports
- Monthly aggregation

**Update frequency:** Updated when incidents added to by-date/
**File rotation:** Monthly (new file each month)

## Tertiary Structure: By Incident Type

**Directory:** `incidents/by-incident-type/[type]/[active|resolved]/`

For categorizing by disaster type.

### Files by Incident Type
```
earthquake/
├── active/
│   └── incidents.jsonl (active earthquakes)
├── resolved/
│   └── incidents.jsonl (resolved earthquakes)
└── metadata.json

flood/
├── active/incidents.jsonl
├── resolved/incidents.jsonl
└── metadata.json

cyclone/
disease/
wildfire/
volcano/
drought/
landslide/
tsunami/
conflict/
```

**Purpose:**
- Type-specific analysis
- Active vs. resolved filtering
- Incident type trends

**Update frequency:** Updated when incidents added

## Country-Specific Storage

**Directory:** `incidents/by-country/[country-name]/`

### Files by Country
```
indonesia/
├── active-incidents.jsonl
├── resolved-incidents.jsonl
├── media-coverage.jsonl
└── metadata.json

philippines/
├── active-incidents.jsonl
├── resolved-incidents.jsonl
└── metadata.json

[country]/
```

**Purpose:**
- Country-focused analysis
- SRC operations tracking
- Regional coordination
- Public reports

## Media Coverage Storage

**Directory:** `incidents/media-coverage/[YYYY-MM]/`

Separate organization for media monitoring results.

### Media Files
```
2025-03/
├── coverage.jsonl (all media coverage)
├── singapore-mentions.jsonl (filtered: singapore_mentioned = true)
├── src-mentions.jsonl (filtered: src_mentioned = true)
├── donation-concerns.jsonl (filtered: donation_concerns = true)
├── misinformation.jsonl (filtered: misinformation_detected = true)
└── metadata.json
```

**Purpose:**
- Media analysis and trends
- Singapore/SRC mention tracking
- Misinformation identification
- Public sentiment analysis

**Update frequency:** Updated daily

## Escalation Tracking

**Directory:** `incidents/escalations/[YYYY-MM-DD]/`

Tracks all incidents that escalated during the day.

### Files
```
2025-03-11/
├── escalations.jsonl
└── summary.json
```

**Content of escalations.jsonl:**
```json
{
  "incident_id": "20250311-ID-FL",
  "incident_name": "Floods in Aceh",
  "escalation_date": "2025-03-11T14:30:00Z",
  "previous_level": 2,
  "new_level": 3,
  "reason": "Death toll increased from 5 to 25",
  "src_notification": true
}
```

**Purpose:**
- Emergency response tracking
- SRC alert history
- Escalation analysis
- Pattern identification

## Archive Structure

**Directory:** `incidents/archive/[YYYY]/`

For resolved incidents older than 3 months.

### Files
```
2024/
├── resolved-incidents.jsonl (all resolved from 2024)
├── media-coverage.jsonl (all media coverage from 2024)
└── summary.json

2023/
├── resolved-incidents.jsonl
└── summary.json
```

**Purpose:**
- Historical analysis
- Long-term trends
- Reduced active working directory size
- Compliance/audit trail

**Archive strategy:**
- Move when incident status = Resolved for 3+ months
- Compress if file > 50MB
- Keep all data (never delete)
- Index for searchability

## Index Files

**Directory:** `incidents/indices/`

Fast lookup and query support.

### Index Files

#### 1. `incident-index.jsonl`
```json
{"incident_id": "20250311-ID-EQ", "location": "by-date/2025-03-11", "status": "Active"}
{"incident_id": "20250311-PH-FL", "location": "by-date/2025-03-11", "status": "Active"}
```

#### 2. `country-index.jsonl`
```json
{"country": "Indonesia", "country_group": "A", "file_count": 45, "last_updated": "2025-03-11T14:30:00Z"}
{"country": "Philippines", "country_group": "A", "file_count": 32, "last_updated": "2025-03-11T10:15:00Z"}
```

#### 3. `date-index.jsonl`
```json
{"date": "2025-03-11", "incident_count": 5, "last_updated": "2025-03-11T23:59:59Z"}
{"date": "2025-03-10", "incident_count": 8, "last_updated": "2025-03-10T23:59:59Z"}
```

#### 4. `query-log.jsonl`
```json
{"timestamp": "2025-03-11T14:30:00Z", "query": "country=Indonesia AND level>=3", "results": 12}
{"timestamp": "2025-03-11T14:25:00Z", "query": "date=2025-03-11", "results": 5}
```

**Purpose:**
- Fast lookups without scanning all files
- Query performance tracking
- Data discovery
- Change auditing

## File Naming Conventions

### JSONL Files
```
[scope]-[type].[status].jsonl
```

**Examples:**
- `incidents.jsonl` - All incidents for scope
- `active-incidents.jsonl` - Filtered by status
- `media-coverage.jsonl` - Media records
- `escalations.jsonl` - Escalated incidents
- `singapore-mentions.jsonl` - Filtered by relevance

### Metadata Files
```
metadata.json (always)
summary.json (for escalations/archives)
```

### Directory Naming
```
[YYYY-MM-DD] - for daily directories
[YYYY-MM] - for monthly directories
[YYYY] - for yearly directories
[group-a|group-b|group-c] - for geographic groups
[country-name] (lowercase, spaces as hyphens) - for countries
[incident-type] (lowercase) - for types
```

## Write Operations

### Adding New Incident

**Step 1:** Check date
- Get current date in UTC (YYYY-MM-DD)
- Create directory if doesn't exist: `incidents/by-date/[YYYY-MM-DD]/`

**Step 2:** Append to incidents.jsonl
```bash
echo '{...incident JSON...}' >> incidents/by-date/[YYYY-MM-DD]/incidents.jsonl
```

**Step 3:** Update related files
- Append to `by-country-group/[group]/[YYYY-MM]/incidents.jsonl`
- Append to `by-incident-type/[type]/[active|resolved]/incidents.jsonl`
- Append to `by-country/[country]/incidents.jsonl`
- Update indices in `indices/incident-index.jsonl`

**Step 4:** Update metadata
- Increment counters in `by-date/[YYYY-MM-DD]/metadata.json`
- Update `by-country-group/[group]/[YYYY-MM]/metadata.json`

### Updating Existing Incident

**Option A: In-place Update**
- Search incident ID in relevant files
- Replace entire JSON object line
- Update `metadata.json` if status changes

**Option B: Append New Version (Recommended)**
- Keep old entry for audit trail
- Append new entry with `updated_date`
- Use incident ID to deduplicate on query

### Adding Media Coverage

**Step 1:** Append to media storage
```
incidents/media-coverage/[YYYY-MM]/coverage.jsonl
```

**Step 2:** Append to filtered files
- If singapore_mentioned: append to `singapore-mentions.jsonl`
- If src_mentioned: append to `src-mentions.jsonl`
- If donation_concerns: append to `donation-concerns.jsonl`
- If misinformation: append to `misinformation.jsonl`

**Step 3:** Link to incident
- Add coverage_id to related incident's `media_coverage.coverage_articles[]`

## Read Operations

### Query: Find Incidents by Date
```
Read: incidents/by-date/[YYYY-MM-DD]/incidents.jsonl
Filter in memory or with jq
```

### Query: Find All Active Group A Incidents
```
Read: incidents/by-country-group/group-a/[YYYY-MM]/active-incidents.jsonl
No filtering needed
```

### Query: Find Earthquake by Country
```
Read: incidents/by-incident-type/earthquake/active/incidents.jsonl
Filter by country field
```

### Query: Find SRC Mentions This Month
```
Read: incidents/media-coverage/[YYYY-MM]/src-mentions.jsonl
No filtering needed
```

### Query: Quick Stats for Date
```
Read: incidents/by-date/[YYYY-MM-DD]/metadata.json
Instant results (no scanning needed)
```

## File Size Management

### Target File Sizes
- Daily JSONL files: 1-10 MB (typically)
- Monthly JSONL files: 50-500 MB
- Archive JSONL files: Compress if > 100 MB

### Compression Strategy
```
[File size tracking]
< 10 MB:   Keep as-is (JSONL)
10-50 MB:  Keep as-is (JSONL)
50-100 MB: Keep as-is, monitor
> 100 MB:  Compress with gzip
           Keep both .jsonl and .jsonl.gz
           Use .gz for archive access
```

### Rotation Strategy
- Daily: Create new file each day
- Monthly: Archive previous month to by-country-group/[group]/[YYYY-MM]/ and year archive
- Quarterly: Evaluate compression needs
- Annually: Move to archive/ directory

## Data Integrity

### Backup Strategy
- Daily backup of `by-date/` directories
- Weekly backup of `by-country-group/`
- Monthly backup of entire incidents/ tree
- Retain 3 months of daily backups
- Retain 1 year of monthly backups

### Validation on Write
- Validate JSON schema before writing
- Check required fields present
- Verify incident_id uniqueness in daily file
- Ensure valid timestamps
- Validate country codes

### Validation on Read
- Verify file format (JSONL)
- Check for corrupted records
- Log errors but continue processing
- Report data quality issues

## Access Patterns

### Fast Path (Recommended)
1. Check `indices/incident-index.jsonl` for location
2. Read specific date file
3. Filter in memory or with jq

### Analytical Path
1. Aggregate by-country-group monthly files
2. Use metadata.json for quick stats
3. Run batch queries across archived data

### Historical Path
1. Read from archive/ for past incidents
2. Decompress if .gz
3. Query as needed

## Performance Optimization

### Index Strategy
Keep indices fresh:
```
Update incident-index.jsonl daily
Update country-index.jsonl weekly
Update date-index.jsonl daily
Log all queries in query-log.jsonl
```

### Caching Strategy
- Cache metadata.json in memory (< 1 KB per date)
- Cache country lists in memory
- Pre-load incident types list
- Cache query results for common patterns

### Partitioning
- By date: 365 daily files per year
- By group + month: 36 files per year (3 groups × 12 months)
- By type: 10 files typically
- Total files manageable for fast lookup

## Tools for Data Access

### Command Line Tools
```bash
# Read today's incidents
tail -f incidents/by-date/$(date +%Y-%m-%d)/incidents.jsonl

# Count incidents by country group
grep '"country_group": "A"' incidents/by-country-group/group-a/*/incidents.jsonl | wc -l

# Filter by incident level
jq 'select(.classification.incident_level >= 3)' incidents/by-date/2025-03-11/incidents.jsonl

# Find specific incident
grep '"incident_id": "20250311-ID-EQ"' incidents/by-date/2025-03-11/incidents.jsonl
```

### Python Tools
```python
import jsonlines
import os
from datetime import datetime

# Read today's incidents
date = datetime.now().strftime('%Y-%m-%d')
with jsonlines.open(f'incidents/by-date/{date}/incidents.jsonl') as reader:
    for obj in reader:
        print(obj)

# Find by country
with jsonlines.open(f'incidents/by-date/{date}/incidents.jsonl') as reader:
    for obj in reader:
        if obj['location']['country'] == 'Indonesia':
            print(obj)
```

## Documentation Requirements

### In Each Directory
- Include `README.md` explaining contents
- Document file format and schema
- Include examples
- Note access patterns

### Main Index
- Create `incidents/README.md`
- Document overall structure
- Provide access examples
- List recent important incidents
