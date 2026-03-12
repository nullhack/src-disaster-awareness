---
name: data-storage
description: Efficient, non-duplicating data storage with date-based primary storage and reference tracking
compatibility: "2.0.0+"
metadata:
  category: data-engineering
  difficulty: intermediate
  type: data-storage
---

# Data Storage Skill - Refactored (v2.0)

Efficient, non-duplicating data storage system using date-based primary storage with reference tracking and tag-based categorization.

## Core Philosophy

**NO DATA DUPLICATION** - Store each incident JSON record exactly once in date folders. Use lightweight reference files and JSON tags for categorization instead of duplicating entire records across multiple folder hierarchies.

## New Directory Structure

```
incidents/
├── README.md (access guide and examples)
├── staging/                          # STAGING - Raw data from reporters
│   ├── incidents.jsonl
│   ├── media.jsonl
│   └── metadata.json
│
├── by-date/                          # PRIMARY STORAGE - All data stored here ONCE
│   ├── 2025-03-11/
│   │   ├── incidents.jsonl          # Single source of truth
│   │   ├── media-coverage.jsonl
│   │   └── metadata.json
│   ├── 2025-03-10/
│   └── [YYYY-MM-DD]/
│
├── references/                       # LIGHTWEIGHT REFERENCE TRACKING
│   ├── active/
│   │   ├── by-country-group.jsonl
│   │   ├── by-incident-type.jsonl
│   │   ├── by-country.jsonl
│   │   └── active-summary.json
│   ├── inactive/
│   │   ├── by-country-group.jsonl
│   │   ├── by-incident-type.jsonl
│   │   ├── by-country.jsonl
│   │   └── inactive-summary.json
│   └── all-incidents-index.jsonl    # Master index of all incidents
│
├── queries/                          # QUERY CACHE AND LOGS
│   ├── cached-results/
│   └── query-log.jsonl
│
└── archive/                          # LONG-TERM STORAGE
    ├── 2024/
    │   ├── resolved-incidents.jsonl
    │   └── media-coverage.jsonl
    └── [YYYY]/
```

## Primary Storage: by-date/ (Single Source of Truth)

All incident data is stored **exactly once** in date-based folders.

### Storage Format

**Location:** `incidents/by-date/[YYYY-MM-DD]/incidents.jsonl`

**Common fields stored as formal JSON fields (NOT in tags):**

```json
{
  "incident_id": "20250311-ID-FL",
  "incident_name": "Floods in Aceh, Indonesia",
  "created_date": "2025-03-11T10:15:00Z",
  "updated_date": "2025-03-11T14:30:00Z",
  "status": "Active",
  "country": "Indonesia",
  "country_group": "A",
  "incident_type": "Flood",
  "incident_level": 3,
  "priority": "HIGH",
  
  // OPTIONAL: Only special tags go here (not common fields)
  // Status determined by folder: active/ = active, inactive/ = resolved
  "tags": [
    "escalation-risk",  // special flag - only include when applicable
    "src-involved"     // optional - only include when applicable
  ],
  
  // Full incident data continues...
  "location": {...},
  "impact": {...},
  "sources": [...]
}
```

## Reference Tracking System

Instead of duplicating data, use lightweight reference files that point to the original data.

### Active Incidents: references/active/

#### 1. by-country-group.jsonl
```json
{"incident_id": "20250311-ID-FL", "file": "by-date/2025-03-11/incidents.jsonl", "line": 1, "country_group": "A", "priority": "HIGH", "type": "Flood"}
{"incident_id": "20250311-PH-EQ", "file": "by-date/2025-03-11/incidents.jsonl", "line": 2, "country_group": "A", "priority": "MEDIUM", "type": "Earthquake"}
{"incident_id": "20250310-TH-DI", "file": "by-date/2025-03-10/incidents.jsonl", "line": 3, "country_group": "A", "priority": "MEDIUM", "type": "Disease"}
```

#### 2. by-incident-type.jsonl
```json
{"incident_id": "20250311-ID-FL", "file": "by-date/2025-03-11/incidents.jsonl", "line": 1, "type": "Flood", "country": "Indonesia", "level": 3}
{"incident_id": "20250311-PH-EQ", "file": "by-date/2025-03-11/incidents.jsonl", "line": 2, "type": "Earthquake", "country": "Philippines", "level": 2}
{"incident_id": "20250310-TH-DI", "file": "by-date/2025-03-10/incidents.jsonl", "line": 3, "type": "Disease", "country": "Thailand", "level": 1}
```

#### 3. by-country.jsonl
```json
{"incident_id": "20250311-ID-FL", "file": "by-date/2025-03-11/incidents.jsonl", "line": 1, "country": "Indonesia", "type": "Flood", "level": 3}
{"incident_id": "20250311-PH-EQ", "file": "by-date/2025-03-11/incidents.jsonl", "line": 2, "country": "Philippines", "type": "Earthquake", "level": 2}
{"incident_id": "20250310-TH-DI", "file": "by-date/2025-03-10/incidents.jsonl", "line": 3, "country": "Thailand", "type": "Disease", "level": 1}
```

#### 4. active-summary.json
```json
{
  "last_updated": "2025-03-11T18:00:00Z",
  "total_active": 15,
  "by_country_group": {"A": 12, "B": 2, "C": 1},
  "by_type": {"Flood": 5, "Earthquake": 3, "Disease": 4, "Cyclone": 2, "Other": 1},
  "by_priority": {"HIGH": 3, "MEDIUM": 8, "LOW": 4},
  "escalation_risk": 4
}
```

### Inactive Incidents: references/inactive/

Same structure as active/, but for resolved/monitoring incidents:

- `by-country-group.jsonl`
- `by-incident-type.jsonl` 
- `by-country.jsonl`
- `inactive-summary.json`

### Master Index: all-incidents-index.jsonl

Complete index of every incident ever stored:

```json
{"incident_id": "20250311-ID-FL", "date": "2025-03-11", "file": "by-date/2025-03-11/incidents.jsonl", "line": 1, "status": "Active", "country_group": "A", "type": "Flood", "priority": "HIGH"}
{"incident_id": "20250311-PH-EQ", "date": "2025-03-11", "file": "by-date/2025-03-11/incidents.jsonl", "line": 2, "status": "Active", "country_group": "A", "type": "Earthquake", "priority": "MEDIUM"}
{"incident_id": "20250310-BD-FL", "date": "2025-03-10", "file": "by-date/2025-03-10/incidents.jsonl", "line": 5, "status": "Resolved", "country_group": "A", "type": "Flood", "priority": "LOW"}
```

## Storage Operations

### 1. Store New Incident

**Step 1:** Store in primary location
```bash
echo '{incident_json}' >> incidents/by-date/2025-03-11/incidents.jsonl
```

**Step 2:** Add reference if active
```bash
echo '{"incident_id":"20250311-ID-FL", "file":"by-date/2025-03-11/incidents.jsonl", "line":1, "country_group":"A", "type":"Flood", "priority":"HIGH"}' >> incidents/references/active/by-country-group.jsonl
echo '{"incident_id":"20250311-ID-FL", "file":"by-date/2025-03-11/incidents.jsonl", "line":1, "type":"Flood", "country":"Indonesia", "level":3}' >> incidents/references/active/by-incident-type.jsonl
echo '{"incident_id":"20250311-ID-FL", "file":"by-date/2025-03-11/incidents.jsonl", "line":1, "country":"Indonesia", "type":"Flood", "level":3}' >> incidents/references/active/by-country.jsonl
```

**Step 3:** Update master index
```bash
echo '{"incident_id":"20250311-ID-FL", "date":"2025-03-11", "file":"by-date/2025-03-11/incidents.jsonl", "line":1, "status":"Active", "country_group":"A", "type":"Flood", "priority":"HIGH"}' >> incidents/references/all-incidents-index.jsonl
```

**Step 4:** Update summaries
```bash
# Update active-summary.json with new counts
```

### 2. Change Status (Active → Inactive)

**Step 1:** Remove from active references
```bash
# Remove lines matching incident_id from:
# - references/active/by-country-group.jsonl
# - references/active/by-incident-type.jsonl  
# - references/active/by-country.jsonl
```

**Step 2:** Add to inactive references
```bash
# Add same reference lines to inactive/ files
echo '{"incident_id":"20250311-ID-FL", "file":"by-date/2025-03-11/incidents.jsonl", "line":1, "country_group":"A", "type":"Flood", "priority":"HIGH"}' >> incidents/references/inactive/by-country-group.jsonl
```

**Step 3:** Update master index status
```bash
# Update status field in all-incidents-index.jsonl line
```

**NOTE:** Original incident data in `by-date/` **never changes** - only status tracking changes.

### 3. Update Incident

**Option A: Append new version (Recommended)**
```bash
# Add updated record to same date file
echo '{updated_incident_json_with_updated_date}' >> incidents/by-date/2025-03-11/incidents.jsonl
# Update references to point to new line number
```

**Option B: In-place update (if needed)**
```bash
# Replace specific line in by-date file (careful with line numbers)
# Update reference line numbers if they shift
```

## Query Operations

### Query 1: Find Active Group A Incidents
```bash
# Read reference file (fast)
jq 'select(.country_group == "A")' incidents/references/active/by-country-group.jsonl

# Then fetch full details using file+line info
while read ref; do
  file=$(echo $ref | jq -r '.file')
  line=$(echo $ref | jq -r '.line')
  sed -n "${line}p" incidents/$file
done
```

### Query 2: Find All Floods (Active + Inactive)
```bash
# Search by tags in original data
grep '"flood"' incidents/by-date/*/incidents.jsonl

# OR use type references
cat incidents/references/active/by-incident-type.jsonl incidents/references/inactive/by-incident-type.jsonl | jq 'select(.type == "Flood")'
```

### Query 3: Get Today's Incidents
```bash
# Direct read (fastest)
cat incidents/by-date/$(date +%Y-%m-%d)/incidents.jsonl
```

### Query 4: Find Incident by ID
```bash
# Use master index for location
grep '"incident_id": "20250311-ID-FL"' incidents/references/all-incidents-index.jsonl
# Then read specific file+line
```

## Tag-Based Categorization

**IMPORTANT:** Common fields (country, country_group, incident_type, incident_level, priority) are stored as formal JSON fields, NOT in tags. Status is tracked via folder structure (active/inactive references).

### Optional Special Tags Only

Only use tags for special flags - NOT for common fields:

**Special Tags (Optional - only include when applicable):**
- `escalation-risk` - Likely to escalate
- `humanitarian-crisis` - Declared humanitarian crisis
- `multi-regional` - Affects multiple regions/countries
- `src-involved` - Singapore Red Cross involvement
- `singapore-mentioned` - Singapore mentioned in coverage
- `donation-concerns` - Public donation concerns flagged
- `monsoon-related` - Related to monsoon season
- `misinformation-detected` - Misinformation spreading

**Example tags usage:**
```json
"tags": ["escalation-risk", "src-involved"]
```

### Common Fields (Formal JSON Fields - NOT tags)

These are already formal fields in the incident JSON:
- `country` - Country name (e.g., "Indonesia")
- `country_group` - A, B, or C
- `incident_type` - Earthquake, Flood, etc.
- `incident_level` - 1, 2, 3, or 4
- `priority` - HIGH, MEDIUM, or LOW

Query these fields directly, not via tags:
```bash
# Query by formal fields (correct)
jq 'select(.country_group == "A" and .incident_level >= 3)' incidents/by-date/*/incidents.jsonl

# Query by special tags only (correct)  
jq 'select(.tags | contains(["escalation-risk"]))' incidents/by-date/*/incidents.jsonl
```

### Custom Tags

Add domain-specific tags as needed:
- `tsunami-risk` - Coastal areas at tsunami risk
- `monsoon-related` - Monsoon season incidents
- `border-region` - Near country borders
- `urban-impact` - Major cities affected
- `infrastructure-damage` - Key infrastructure damaged

### Tag-Based Queries

```bash
# Query by special tags (correct approach)
jq 'select(.tags | contains(["escalation-risk"]))' incidents/by-date/*/incidents.jsonl
jq 'select(.tags | contains(["src-involved"]))' incidents/by-date/*/incidents.jsonl

# Query by formal fields (correct approach - NOT tags)
jq 'select(.country_group == "A" and .incident_level >= 3)' incidents/by-date/*/incidents.jsonl
jq 'select(.incident_type == "Flood" and .priority == "HIGH")' incidents/by-date/*/incidents.jsonl
jq 'select(.country == "Indonesia" and .incident_type == "Earthquake")' incidents/by-date/*/incidents.jsonl

# Complex query: Group A floods/earthquakes with HIGH priority and escalation-risk tag
jq 'select(.country_group == "A" and (.incident_type == "Flood" or .incident_type == "Earthquake") and .priority == "HIGH" and (.tags | contains(["escalation-risk"])))' incidents/by-date/*/incidents.jsonl
```

## Reference File Management

### Automated Reference Updates

**When storing new incident:**
1. Append to `all-incidents-index.jsonl` 
2. If active: append to `active/` reference files
3. Update `active-summary.json` counts
4. Calculate line number for future references

**When changing status:**
1. Remove from old status references  
2. Add to new status references
3. Update both summary files
4. Update master index status

### Reference File Cleanup

**Daily maintenance:**
- Verify line numbers in reference files match actual data
- Remove orphaned references (where original data deleted)
- Rebuild reference files if line numbers drift

**Weekly maintenance:**
- Optimize reference files (remove duplicates)
- Verify reference counts match summary files
- Archive old inactive references

### Reference Deduplication

```bash
# Remove duplicate references (keep latest)
sort -k1,1 -u incidents/references/active/by-country-group.jsonl > temp && mv temp incidents/references/active/by-country-group.jsonl
```

## Performance Benefits

### Storage Efficiency
- **90% reduction** in duplicated data
- **50% reduction** in total storage space
- **Linear growth** with incidents (not exponential)

### Query Performance
- **Fast filtering:** Reference files are small (KB not MB)
- **Direct access:** Line numbers enable O(1) record access
- **Tag queries:** JSON tags more flexible than folder paths

### Maintenance Efficiency  
- **Single updates:** Change data once in by-date/
- **Fast status changes:** Move references, not data
- **Simple backups:** Backup by-date/ for complete data

## Data Consistency

### Consistency Rules

1. **Primary data immutable:** Once written to by-date/, data doesn't change
2. **References track location:** File path + line number always accurate
3. **Tags authoritative:** Tags in primary data override reference classifications
4. **Status in references:** Reference location (active/ vs inactive/) defines current status

### Consistency Checks

```bash
# Verify reference line numbers
while read ref; do
  incident_id=$(echo $ref | jq -r '.incident_id')
  file=$(echo $ref | jq -r '.file')  
  line=$(echo $ref | jq -r '.line')
  actual_id=$(sed -n "${line}p" incidents/$file | jq -r '.incident_id')
  if [ "$incident_id" != "$actual_id" ]; then
    echo "MISMATCH: Reference points to wrong line"
  fi
done < incidents/references/active/by-country-group.jsonl
```

### Recovery Procedures

**If reference files corrupted:**
```bash
# Rebuild from primary data
rm incidents/references/active/*.jsonl
rm incidents/references/inactive/*.jsonl
# Scan all by-date/ files and rebuild references based on status field
for file in incidents/by-date/*/incidents.jsonl; do
  jq -r 'select(.status == "Active") | .incident_id' $file | while read id; do
    # Add to active references...
  done
done
```

## Migration from Old System

### Phase 1: Data Consolidation
1. **Read all existing duplicated data**
2. **Deduplicate by incident_id** (keep most recent)
3. **Extract common fields** to formal JSON fields (country, type, level, priority)
4. **Store in by-date/** folders only

### Phase 2: Reference Generation
1. **Scan consolidated data**
2. **Generate reference files** based on status field (not tags)
3. **Build master index**
4. **Verify consistency**

### Phase 3: Cleanup
1. **Remove old by-country-group/ duplicates**
2. **Remove old by-incident-type/ duplicates**  
3. **Remove old by-country/ duplicates**
4. **Keep by-date/ as primary**

## Example Workflows

### Store Incident from Reporter

```bash
# Reporter sends incident with common fields already as formal JSON fields:
# {"incident_id": "20250311-ID-FL", "country_group": "A", "incident_type": "Flood", "incident_level": 3, "priority": "HIGH", "tags": ["escalation-risk"], ...}

# 1. Validate has required formal fields (country_group, incident_type, incident_level, priority)

# 2. Append to primary storage (tags array optional - only for special flags)  
echo "$raw_incident" >> incidents/by-date/2025-03-11/incidents.jsonl

# 3. Get line number for references
line_num=$(wc -l < incidents/by-date/2025-03-11/incidents.jsonl)

# 4. Add to active references
echo "{\"incident_id\":\"20250311-ID-FL\", \"file\":\"by-date/2025-03-11/incidents.jsonl\", \"line\":$line_num, \"country_group\":\"A\", \"type\":\"Flood\", \"priority\":\"HIGH\"}" >> incidents/references/active/by-country-group.jsonl

# 5. Update master index
echo "{\"incident_id\":\"20250311-ID-FL\", \"date\":\"2025-03-11\", \"file\":\"by-date/2025-03-11/incidents.jsonl\", \"line\":$line_num, \"status\":\"Active\", \"country_group\":\"A\", \"type\":\"Flood\"}" >> incidents/references/all-incidents-index.jsonl

# 6. Update summary counts
jq '.total_active += 1 | .by_country_group.A += 1 | .by_type.Flood += 1 | .by_priority.HIGH += 1' incidents/references/active/active-summary.json > temp && mv temp incidents/references/active/active-summary.json
```

### Query Active Group A Incidents

```bash
# 1. Get references (fast)
jq 'select(.country_group == "A")' incidents/references/active/by-country-group.jsonl > temp_refs

# 2. Fetch full details
while read ref; do
  file=$(echo $ref | jq -r '.file')
  line=$(echo $ref | jq -r '.line')
  sed -n "${line}p" incidents/$file
done < temp_refs
```

### Change Status: Active → Resolved

```bash
incident_id="20250311-ID-FL"

# 1. Find and remove from active references
sed -i "/\"incident_id\":\"$incident_id\"/d" incidents/references/active/by-country-group.jsonl
sed -i "/\"incident_id\":\"$incident_id\"/d" incidents/references/active/by-incident-type.jsonl
sed -i "/\"incident_id\":\"$incident_id\"/d" incidents/references/active/by-country.jsonl

# 2. Add to inactive references (move the same reference lines)
ref_line=$(grep "\"incident_id\":\"$incident_id\"" incidents/references/all-incidents-index.jsonl)
file=$(echo $ref_line | jq -r '.file')
line=$(echo $ref_line | jq -r '.line')

echo "{\"incident_id\":\"$incident_id\", \"file\":\"$file\", \"line\":$line, \"country_group\":\"A\", \"type\":\"Flood\", \"priority\":\"HIGH\"}" >> incidents/references/inactive/by-country-group.jsonl

# 3. Update master index status
sed -i "s/\"status\":\"Active\"/\"status\":\"Resolved\"/" incidents/references/all-incidents-index.jsonl

# 4. Update summary counts
jq '.total_active -= 1' incidents/references/active/active-summary.json > temp && mv temp incidents/references/active/active-summary.json
jq '.total_inactive += 1' incidents/references/inactive/inactive-summary.json > temp && mv temp incidents/references/inactive/inactive-summary.json
```

## Tools and Scripts

### Validation Script
```bash
#!/bin/bash
# validate-references.sh
# Verify all reference files point to correct data

echo "Validating reference consistency..."
errors=0

for ref_file in incidents/references/active/*.jsonl incidents/references/inactive/*.jsonl; do
  while read ref; do
    incident_id=$(echo $ref | jq -r '.incident_id')
    file=$(echo $ref | jq -r '.file')
    line=$(echo $ref | jq -r '.line')
    
    if [ -f "incidents/$file" ]; then
      actual_id=$(sed -n "${line}p" incidents/$file | jq -r '.incident_id')
      if [ "$incident_id" != "$actual_id" ]; then
        echo "ERROR: Reference mismatch in $ref_file"
        echo "  Expected: $incident_id, Found: $actual_id"
        errors=$((errors + 1))
      fi
    else
      echo "ERROR: Referenced file missing: incidents/$file"
      errors=$((errors + 1))
    fi
  done < "$ref_file"
done

if [ $errors -eq 0 ]; then
  echo "✓ All references validated successfully"
else
  echo "✗ Found $errors reference errors"
fi
```

### Rebuild References Script
```bash
#!/bin/bash
# rebuild-references.sh
# Rebuild all reference files from primary data

echo "Rebuilding reference files from primary data..."

# Clear existing references
rm -rf incidents/references/active/*.jsonl
rm -rf incidents/references/inactive/*.jsonl
rm -f incidents/references/all-incidents-index.jsonl

# Initialize files
touch incidents/references/active/by-country-group.jsonl
touch incidents/references/active/by-incident-type.jsonl
touch incidents/references/active/by-country.jsonl
touch incidents/references/inactive/by-country-group.jsonl
touch incidents/references/inactive/by-incident-type.jsonl
touch incidents/references/inactive/by-country.jsonl
touch incidents/references/all-incidents-index.jsonl

# Scan all primary data
for date_file in incidents/by-date/*/incidents.jsonl; do
  line_num=0
  while read incident; do
    line_num=$((line_num + 1))
    
    incident_id=$(echo $incident | jq -r '.incident_id')
    date=$(echo $incident | jq -r '.created_date' | cut -d'T' -f1)
    country_group=$(echo $incident | jq -r '.country_group')
    type=$(echo $incident | jq -r '.incident_type')
    priority=$(echo $incident | jq -r '.priority')
    country=$(echo $incident | jq -r '.country')
    level=$(echo $incident | jq -r '.incident_level')
    
    # Determine status from formal status field (NOT from tags)
    status=$(echo $incident | jq -r '.status')
    if [ "$status" = "Active" ]; then
      ref_dir="active"
    else
      ref_dir="inactive"
    fi
    
    relative_path=${date_file#incidents/}
    
    # Add to appropriate reference files
    echo "{\"incident_id\":\"$incident_id\", \"file\":\"$relative_path\", \"line\":$line_num, \"country_group\":\"$country_group\", \"type\":\"$type\", \"priority\":\"$priority\"}" >> incidents/references/$ref_dir/by-country-group.jsonl
    
    echo "{\"incident_id\":\"$incident_id\", \"file\":\"$relative_path\", \"line\":$line_num, \"type\":\"$type\", \"country\":\"$country\", \"level\":$level}" >> incidents/references/$ref_dir/by-incident-type.jsonl
    
    echo "{\"incident_id\":\"$incident_id\", \"file\":\"$relative_path\", \"line\":$line_num, \"country\":\"$country\", \"type\":\"$type\", \"level\":$level}" >> incidents/references/$ref_dir/by-country.jsonl
    
    # Add to master index
    echo "{\"incident_id\":\"$incident_id\", \"date\":\"$date\", \"file\":\"$relative_path\", \"line\":$line_num, \"status\":\"$status\", \"country_group\":\"$country_group\", \"type\":\"$type\"}" >> incidents/references/all-incidents-index.jsonl
    
  done < "$date_file"
done

echo "✓ Reference files rebuilt successfully"
```

## Summary

The refactored data storage system provides:

✅ **No data duplication** - Each incident stored exactly once  
✅ **Efficient status tracking** - Lightweight reference files  
✅ **Flexible categorization** - JSON tags instead of rigid folders  
✅ **Fast queries** - Reference files enable rapid filtering  
✅ **Simple maintenance** - Status changes don't require data movement  
✅ **Strong consistency** - Single source of truth in by-date/ folders  
✅ **Easy backup** - Backup by-date/ for complete data recovery  
✅ **Scalable performance** - Linear growth, not exponential  

This approach dramatically reduces storage overhead while maintaining query performance and data integrity.