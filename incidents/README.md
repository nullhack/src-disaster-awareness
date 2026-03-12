# Disaster Incident Data Store - Efficient Storage v2.0

This directory contains all stored disaster and health incident data using an efficient, zero-duplication storage system with reference tracking.

## 🚀 New Efficient Storage System

**Core Philosophy:** Store each incident exactly **once** in date folders. Use lightweight reference files and tags for categorization instead of duplicating data.

### Primary Storage (Single Source of Truth)
- **Location:** `by-date/[YYYY-MM-DD]/incidents.jsonl`
- **Use Case:** All incident data stored here ONCE
- **Files:**
  - `incidents.jsonl` - Single source of truth for all incidents
  - `media-coverage.jsonl` - Media coverage records
  - `metadata.json` - Summary statistics

### Reference Tracking (Lightweight Pointers)
- **Location:** `references/`
- **Use Case:** Fast categorization and status tracking without data duplication
- **Structure:**
  - `active/` - Pointers to currently active incidents
  - `inactive/` - Pointers to resolved/monitoring incidents
  - `all-incidents-index.jsonl` - Master index of all incidents

### Tag-Based Categorization
**Location:** Within each incident's `tags` array in primary storage
**Use Case:** Flexible categorization replacing rigid folder hierarchies
**Tags:**
  - **Required:** status (active/resolved), type (flood/earthquake), country-group (group-a/b/c), severity (level-1/2/3/4), priority
  - **Optional:** escalation-risk, src-involved, singapore-mentioned, etc.
- **Files:** `active-incidents.jsonl`, `resolved-incidents.jsonl`

### Media Coverage
- **Location:** `media-coverage/[YYYY-MM]/`
- **Use Case:** Track news coverage and public discussion
- **Files:**
  - `coverage.jsonl` - All media coverage
  - `singapore-mentions.jsonl` - Singapore-related
  - `src-mentions.jsonl` - Singapore Red Cross mentions
  - `donation-concerns.jsonl` - Donation-related coverage
  - `misinformation.jsonl` - Flagged misinformation

### Escalations
- **Location:** `escalations/[YYYY-MM-DD]/`
- **Use Case:** Track incidents that escalated during the day
- **Files:** `escalations.jsonl` - Escalation records

### Historical Data
- **Location:** `archive/[YYYY]/`
- **Use Case:** Access resolved incidents from past years
- **Files:** `resolved-incidents.jsonl`, `media-coverage.jsonl`

### Fast Lookups
- **Location:** `indices/`
- **Files:**
  - `incident-index.jsonl` - Quick lookup by incident ID
  - `country-index.jsonl` - Countries and status
  - `date-index.jsonl` - Daily summaries
  - `query-log.jsonl` - Query history for optimization

## File Format

All incident files use **JSONL (JSON Lines)** format:
- One JSON object per line
- UTF-8 encoding
- No line breaks within objects
- Fast streaming and processing

**Example:**
```
{"incident_id": "20250311-ID-EQ", "incident_name": "Earthquake in Sumatra", ...}
{"incident_id": "20250311-PH-FL", "incident_name": "Floods in Luzon", ...}
{"incident_id": "20250311-TH-DI", "incident_name": "Disease Outbreak", ...}
```

## Data Schema

See `.opencode/skills/data-schema/SKILL.md` for complete schema documentation.

**Key Fields:**
- `incident_id` - Unique identifier (format: YYYYMMDD-COUNTRYCODE-TYPECODE)
- `incident_name` - Human-readable name
- `created_date` - ISO 8601 datetime (UTC)
- `country` - Country name
- `country_group` - A, B, or C
- `incident_type` - Earthquake, Flood, Disease, etc.
- `incident_level` - 1-4 severity
- `priority` - HIGH, MEDIUM, LOW
- `sources` - Data sources with links

## Common Queries

### Find All Incidents from Today
```bash
cat by-date/$(date +%Y-%m-%d)/incidents.jsonl | wc -l
```

### Find Active Earthquakes in Group A
```bash
cat by-country-group/group-a/2025-03/incidents.jsonl | \
  grep -E '"incident_type": "Earthquake".*"status": "Active"' | \
  wc -l
```

### Get Singapore Mentions This Month
```bash
cat media-coverage/2025-03/singapore-mentions.jsonl | wc -l
```

### Find Specific Incident by ID
```bash
grep '"incident_id": "20250311-ID-EQ"' by-date/2025-03-11/incidents.jsonl
```

### List All Countries with Active Incidents
```bash
jq -s 'group_by(.location.country) | map({country: .[0].location.country, count: length})' \
  by-date/2025-03-11/incidents.jsonl
```

### Count Incidents by Level
```bash
jq '.classification.incident_level' by-date/2025-03-11/incidents.jsonl | sort | uniq -c
```

## Storage Statistics

Current structure supports:
- **Daily files:** 1-10 MB typical
- **Monthly files:** 50-500 MB typical
- **Archive files:** Compressed if > 100 MB
- **Indices:** < 10 MB (fast lookups)

## Data Quality

All stored incidents are validated against the data schema:
- ✅ Required fields present
- ✅ Valid enums and data types
- ✅ Date consistency checks
- ✅ Impact number validation
- ✅ Unique incident IDs
- ✅ Source verification

Quality scores stored in metadata indicate data completeness.

## Backup & Retention

- **Daily backups** of by-date/ directory
- **Weekly backups** of by-country-group/
- **Monthly full backups** of entire incidents/ tree
- **Retention:** 
  - 3 months of daily backups
  - 1 year of monthly backups
  - Archive indefinitely

## Access Tools

### Command Line
```bash
# View today's incidents
tail incidents/by-date/$(date +%Y-%m-%d)/incidents.jsonl

# Filter by country
jq 'select(.location.country == "Indonesia")' incidents/by-date/2025-03-11/incidents.jsonl

# Get metadata
cat by-date/2025-03-11/metadata.json
```

### Python
```python
import jsonlines
from datetime import datetime

# Read today's incidents
date = datetime.now().strftime('%Y-%m-%d')
with jsonlines.open(f'by-date/{date}/incidents.jsonl') as reader:
    for incident in reader:
        print(f"{incident['incident_name']}: Level {incident['classification']['incident_level']}")
```

### Data Analysis
```bash
# Get all high-priority incidents this week
grep '"priority": "HIGH"' by-date/*/incidents.jsonl

# Count incidents by group
grep '"country_group": "A"' by-date/*/incidents.jsonl | wc -l

# Get escalations summary
cat escalations/2025-03-*/summary.json | jq .
```

## Management

### Adding New Incidents
- Use `@data-engineer` agent to process and store
- Incidents automatically placed in correct directories
- Indices and metadata updated automatically

### Querying Incidents
- Use indices/ for fast lookups
- Use by-date/ for time-based queries
- Use by-country-group/ for regional analysis
- Use by-incident-type/ for type-based filtering

### Archiving Old Data
- Resolved incidents > 3 months old moved to archive/
- Archive/ maintains searchability
- Compression applied if > 100 MB
- All historical data retained permanently

## Performance Notes

**Fastest queries:**
1. Metadata.json (instant)
2. Filtered by date (one file read)
3. Filtered by country group (one file read)
4. Using indices (index lookup + one file)

**Slower queries:**
1. Full scan of all dates
2. Cross-group analysis
3. Complex filters (use jq for in-memory filtering)

**Optimization:**
- Use by-date/ for recent data
- Use indices/ for large-scale lookups
- Use metadata.json for statistics
- Aggregate by-country-group monthly files for regional analysis

## Documentation

For detailed information:
- **Data Schema:** `.opencode/skills/data-schema/SKILL.md`
- **Storage Organization:** `.opencode/skills/data-storage/SKILL.md`
- **Data Engineer Agent:** `.opencode/agents/data-engineer.md`
- **System Overview:** `AGENTS.md`

## Getting Started

1. **Review schema:** Understand incident data structure
2. **Check today's data:** `cat by-date/$(date +%Y-%m-%d)/incidents.jsonl`
3. **Run sample query:** Filter by priority or country
4. **Explore metadata:** Check statistics in metadata.json
5. **Use tools:** Try Python/jq for advanced queries

## Questions?

- Check `.opencode/skills/` for detailed documentation
- Review example records in `.opencode/skills/data-schema/SKILL.md`
- Consult `@data-engineer` agent for data storage issues
- See `AGENTS.md` for system architecture overview
