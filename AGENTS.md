# Disaster Awareness Agent System

Comprehensive documentation of the complete disaster awareness system consisting of monitoring and data engineering subsystems for the Disaster Awareness Agent project.

## System Overview

The Disaster Awareness Agent system is composed of **TWO INTEGRATED SUBSYSTEMS**:

1. **Monitoring Subsystem:** 3 subagents + 3 supporting skills for detecting, classifying, and reporting disasters
2. **Data Engineering Subsystem:** 1 subagent + 2 supporting skills for processing, validating, and storing incident data

Together they create a complete pipeline from data source → monitoring → analysis → storage → querying.

### Complete Architecture Diagram

```
DATA SOURCES (5 platforms)
├── GDACS (Natural Disasters, real-time)
├── ProMED-mail (Disease Outbreaks, daily)
├── Reuters/AP/BBC (Tier 1 news)
├── Regional News (Tier 2-3)
└── WHO (Official verification)

        ↓

MONITORING SUBSYSTEM
├─ disaster-incident-reporter (GDACS + ProMED)
├─ media-incident-reporter (News + Social Media)
└─ incident-summarizer (Report compilation)

        ↓

CLASSIFICATION & FORMATTING (Skills)
├─ incident-classifier (Priority classification)
├─ disaster-monitor (Formatting standards)
└─ media-monitor (Media monitoring guidelines)

        ↓

OUTPUT
├─ WhatsApp "Incident updates" Group
└─ Disaster Event Timeline Document

        ↓

DATA ENGINEERING SUBSYSTEM
└─ data-engineer (Validate, transform, store)

        ↓

SUPPORTING SKILLS (Schema & Storage)
├─ data-schema (JSON schema with validation)
└─ data-storage (Folder organization)

        ↓

JSONL INCIDENT DATABASE
├─ incidents/by-date/[YYYY-MM-DD]/           (PRIMARY)
├─ incidents/by-country-group/[A|B|C]/[MM]/  (SECONDARY)
├─ incidents/by-incident-type/[type]/        (TERTIARY)
├─ incidents/by-country/[country]/            (COUNTRY-SPECIFIC)
├─ incidents/media-coverage/[YYYY-MM]/       (MEDIA)
├─ incidents/escalations/[YYYY-MM-DD]/       (ESCALATIONS)
├─ incidents/archive/[YYYY]/                 (HISTORICAL)
└─ incidents/indices/                        (FAST LOOKUPS)
```

---

## System Components

### 1. Skills (Supporting Knowledge)

#### Skill: incident-classifier
**File:** `.opencode/skills/incident-classifier/SKILL.md`

**Purpose:** Defines rules and methodology for classifying disaster incidents by:
- Country group (A: Asia Pacific 1, B: Asia Pacific 2 + MENA, C: Other)
- Severity level (1: Minor, 2: Significant, 3: Major, 4: Critical)
- Reporting priority (HIGH, MEDIUM, LOW)

**Key Content:**
- Priority matrix for all country groups and levels
- Level 1-4 defining indicators
- Special case overrides (humanitarian crisis, multi-regional, forecasts)
- Decision tree for quick classification
- Data structure for storing classifications

**Used By:**
- disaster-incident-reporter (when classifying GDACS/ProMED incidents)
- media-incident-reporter (when determining reporting threshold)

---

#### Skill: disaster-monitor
**File:** `.opencode/skills/disaster-monitor/SKILL.md`

**Purpose:** Standardized formats and incident grouping rules for consistent disaster reporting.

**Key Content:**
- 3 main reporting formats (Active, Forecasted, Update)
- Geographic grouping definitions (Groups A, B, C with full country lists)
- Incident priority classification (Levels 1-4 with indicators)
- Inclusion/exclusion criteria for reports
- Incident type definitions
- Decision tree for reporting determination

**Used By:**
- disaster-incident-reporter (when formatting GDACS incidents)
- incident-summarizer (when compiling final reports)

---

#### Skill: media-monitor
**File:** `.opencode/skills/media-monitor/SKILL.md`

**Purpose:** Guidelines for monitoring news and social media for Singapore/SRC-relevant content.

**Key Content:**
- General monitoring overview and scope
- Credible news sources (Tier 1-3 rating)
- Content inclusion criteria (SRC mentions, donation concerns, misinformation)
- Content exclusion criteria
- Report formats for WhatsApp and Timeline
- Peacetime vs. emergency monitoring schedules
- Escalation protocols for urgent issues
- Best practices and data recording

**Used By:**
- media-incident-reporter (when monitoring news sources)
- incident-summarizer (when documenting media coverage)

---

### 2. Subagents (Monitoring & Analysis)

#### Subagent: disaster-incident-reporter
**File:** `.opencode/agents/disaster-incident-reporter.md`

**Purpose:** Monitor GDACS and ProMED for disaster and disease incidents, classify them, and generate formatted reports.

**Responsibilities:**
1. Monitor GDACS for real-time natural disaster alerts
2. Monitor ProMED-mail for emerging disease outbreaks
3. Classify incidents using incident-classifier skill rules
4. Format reports using disaster-monitor skill standards
5. Determine reporting priority
6. Output formatted incidents for incident-summarizer

**Data Sources:**
- **GDACS** (https://www.gdacs.org/) - Real-time natural disasters
- **ProMED-mail** (https://www.promedmail.org/) - Disease outbreak intelligence

**Workflow:**
1. Retrieve latest data from GDACS and ProMED (5-10 mins)
2. Apply incident-classifier rules (5-10 mins)
3. Format using disaster-monitor standards (5-10 mins)
4. Quality checks (2-5 mins)
5. Generate structured incident reports (2-5 mins)

**Output:**
Structured incident data with:
- Disaster type and location
- Country group and severity level
- Priority classification
- Formatted report text
- Source URLs
- Classification rationale
- Reporting action (INCLUDE/MONITOR/EXCLUDE)

**Tools Used:**
- `webfetch` - Retrieve GDACS/ProMED data
- `grep` - Search incident databases
- `skill` - Load incident-classifier and disaster-monitor

**Temperature:** 0.2 (Focused, analytical)

**Key Operating Principles:**
- Accuracy over speed
- Group A incidents elevated priority
- Level 4 always reported
- Humanitarian crises override all rules
- Track potential escalation

---

#### Subagent: media-incident-reporter
**File:** `.opencode/agents/media-incident-reporter.md`

**Purpose:** Monitor news sources and social media for Singapore/SRC-relevant disaster coverage.

**Responsibilities:**
1. Scan Tier 1-3 news sources for disaster coverage
2. Monitor social media for Singapore/SRC mentions
3. Identify donation concerns and misinformation
4. Flag urgent escalations (scams, major concerns, crisis growth)
5. Generate media monitoring reports
6. Document coverage in disaster timelines

**Data Sources:**
- **Tier 1 Agencies:** Reuters, AP, BBC, AFP, Al Jazeera
- **Tier 2 Regional:** Channel NewsAsia, Straits Times, The Star, Antara, Bangkok Post
- **Tier 3 Humanitarian:** ReliefWeb, Devex
- **Social Media:** Twitter/X, Facebook, Reddit, WhatsApp, TikTok

**Monitoring Schedule:**
- **Peacetime:** 2-3 scans per week (30-45 mins each)
- **Emergency:** Daily scans (30-60 mins)

**Workflow:**
1. News aggregator discovery (10-15 mins)
2. Content evaluation (10-15 mins)
3. Formatting & reporting (5-10 mins)
4. Quality checks (2-5 mins)
5. Distribution & escalation (2-5 mins)

**Output:**
- WhatsApp reports (general monitoring)
- Disaster Event Timeline entries (SRC involvement)
- Escalation alerts (scams, crises, major concerns)

**Report Formats:**
- General: `[Country/Disaster] [Link] [Optional flags]`
- Detailed: Country, Date, Province, Details, SRC Mention, Donation Concern

**Tools Used:**
- `webfetch` - Retrieve news articles
- `grep` - Search news archives
- `skill` - Load media-monitor

**Temperature:** 0.3 (Analytical with context)

**Key Operating Principles:**
- Singapore/SRC focus
- Tier 1-2 source priority
- Misinformation detection
- Scam identification
- Public concern tracking

---

#### Subagent: incident-summarizer
**File:** `.opencode/agents/incident-summarizer.md`

**Purpose:** Compile and format incident reports into standardized WhatsApp and timeline documentation.

**Responsibilities:**
1. Receive classified incidents from reporters
2. Consolidate and deduplicate incidents
3. Organize by priority and geography
4. Format for WhatsApp distribution
5. Document in disaster timelines
6. Identify and flag escalations
7. Ensure quality and consistency

**Input Data:**
Structured incidents from:
- disaster-incident-reporter (GDACS/ProMED classification)
- media-incident-reporter (media monitoring)

**Workflow:**
1. Report consolidation (5-10 mins)
2. Deduplication (2-5 mins)
3. Format selection (3-5 mins)
4. Report compilation (5-10 mins)
5. Timeline documentation (5-10 mins)
6. Quality assurance (3-5 mins)
7. Distribution preparation (2-3 mins)

**Output Formats:**

**WhatsApp Distribution:**
```
🔴 CRITICAL INCIDENTS (HIGH priority)
[Organized by severity, with Group A first]

🟠 SIGNIFICANT INCIDENTS (MEDIUM priority)
[Regional incidents]

🟡 MONITORING UPDATES (LOW priority)
[Early warnings, emerging situations]
```

**Timeline Documentation:**
```json
{
  "incident_record": {
    "id": "unique ID",
    "name": "disaster name",
    "country": "country",
    "locations": ["regions"],
    "country_group": "A/B/C",
    "disaster_type": "classification",
    "severity": "Level 1-4",
    "affected": number,
    "deaths": number,
    "src_involvement": {...},
    "sources": [{...}],
    "media_monitoring": {...},
    "next_actions": [...]
  }
}
```

**Tools Used:**
- `skill` - Load disaster-monitor, media-monitor
- `write` - Document in structured format

**Temperature:** 0.3 (Consistent, organized)

**Key Operating Principles:**
- Accuracy over speed
- Consistent formatting
- Priority-based organization
- Complete documentation
- Escalation identification

---

## 3. Data Engineering Subagent

#### Subagent: data-engineer
**File:** `.opencode/agents/data-engineer.md`

**Purpose:** Process incident data from monitoring agents, validate against schema, organize into folder structure, and store in JSONL format.

**Responsibilities:**
1. Receive incident data from monitoring agents
2. Validate against complete data schema
3. Transform and normalize data
4. Generate unique incident IDs
5. Create necessary directory structure
6. Write data to JSONL files in appropriate locations
7. Update indices for fast lookups
8. Generate metadata and statistics
9. Detect and flag escalations
10. Handle errors and ensure data quality

**Supporting Skills:**
- `@skill data-schema` - JSON schema definitions and validation rules
- `@skill data-storage` - Folder organization and file naming conventions

**Workflow (6 Phases):**
1. **Reception & Validation** (5 mins)
   - Receive incident JSON
   - Load data-schema skill
   - Validate all required fields
   - Check data integrity constraints
   - Generate quality score (0-1)

2. **Data Transformation** (3 mins)
   - Normalize dates to ISO 8601 UTC
   - Standardize country names
   - Fix enum values
   - Generate incident ID if missing
   - Populate metadata fields

3. **Directory Organization** (2 mins)
   - Load data-storage skill
   - Determine target directories
   - Create directories as needed
   - Plan file writes

4. **JSONL File Writing** (3 mins)
   - Append to `by-date/[YYYY-MM-DD]/incidents.jsonl`
   - Append to `by-country-group/[group]/[YYYY-MM]/incidents.jsonl`
   - Append to `by-incident-type/[type]/[status]/incidents.jsonl`
   - Append to `by-country/[country]/incidents.jsonl`
   - Store media coverage records separately

5. **Index Updates** (2 mins)
   - Update incident-index.jsonl
   - Update country-index.jsonl
   - Update date-index.jsonl
   - Enable fast lookups

6. **Metadata Updates** (2 mins)
   - Update daily metadata (counts, statistics)
   - Update monthly metadata
   - Update type-specific metadata
   - Generate summary statistics

**Input Format:**
Structured incident JSON from monitoring agents with:
- incident_id, incident_name, created_date
- country, country_group, incident_type
- incident_level, priority, status
- location, impact, sources
- disaster_details or disease_details
- media_coverage, escalation_tracking

**Output:**
- JSONL files in organized directory structure
- Updated indices for fast querying
- Metadata files with statistics
- Escalation notifications (if detected)
- Processing status report

**Data Quality:**
- Quality scoring (0-1 scale)
- ≥ 0.95: Store immediately
- 0.85-0.95: Store with warnings
- < 0.85: Flag for manual review
- Average quality target: ≥ 0.90

**Performance:**
- Validation: < 5 seconds per incident
- Transformation: < 2 seconds
- Storage: < 5 seconds
- Total: < 15 seconds per incident (end-to-end)

**Escalation Detection:**
- Level changes detected automatically
- Humanitarian crisis flagged
- Multi-regional spread identified
- Creates escalation records
- Returns escalation alerts

**Tools Used:**
- `skill` - Load data-schema and data-storage
- `write` - Create metadata and index files
- `bash` - Create directories, append to files
- `read` - Check for duplicates
- `grep` - Search for existing incident IDs

**Temperature:** 0.1 (Focused, deterministic)

**Key Operating Principles:**
- Accuracy over speed
- Data quality critical
- Validation always
- No invalid data stored
- Complete audit trail
- Error handling and recovery

---

## Supporting Skills for Data Engineering

#### Skill: data-schema
**File:** `.opencode/skills/data-schema/SKILL.md`

**Purpose:** Defines complete JSON schema for incident data storage and validation.

**Key Content:**
- Full incident record schema (60+ fields)
- Simplified incident schema (for quick entry)
- Media coverage record schema
- Schema validation rules and constraints
- Data type specifications
- Integrity constraint rules
- Example records (earthquake, disease outbreak)
- Backwards compatibility guidelines

**Used By:**
- data-engineer (when validating incidents)
- Developers (when creating new incident data)

---

#### Skill: data-storage
**File:** `.opencode/skills/data-storage/SKILL.md`

**Purpose:** Defines folder organization, directory structure, and file management conventions.

**Key Content:**
- Complete directory hierarchy
- Primary organization: by-date (YYYY-MM-DD)
- Secondary organization: by-country-group ([A|B|C]/[YYYY-MM])
- Tertiary organization: by-incident-type
- Country-specific storage
- Media coverage segregation
- Escalation tracking
- Archive strategy
- Index maintenance
- File naming conventions
- Rotation and compression strategy
- Access patterns and performance optimization

**Used By:**
- data-engineer (when organizing data)
- Query tools (when accessing data)

---

## Data Engineering Workflows

### Workflow 5: Storing Incident Data

```
Monitoring agents produce incident JSON
        ↓
@data-engineer receives incident
        ↓
Step 1: Validate against @skill data-schema
        ├─ Check required fields
        ├─ Validate data types
        ├─ Check constraints
        └─ Generate quality score
        ↓
Step 2: Transform and normalize
        ├─ Convert dates to ISO 8601
        ├─ Standardize country names
        ├─ Fix enum values
        └─ Generate incident ID
        ↓
Step 3: Load @skill data-storage
        ├─ Determine target directories
        ├─ Create directories
        └─ Plan file structure
        ↓
Step 4: Write to JSONL files
        ├─ by-date/2025-03-11/incidents.jsonl
        ├─ by-country-group/group-a/2025-03/incidents.jsonl
        ├─ by-incident-type/earthquake/active/incidents.jsonl
        └─ by-country/indonesia/active-incidents.jsonl
        ↓
Step 5: Update indices
        ├─ incident-index.jsonl
        ├─ country-index.jsonl
        └─ date-index.jsonl
        ↓
Step 6: Update metadata
        ├─ by-date/2025-03-11/metadata.json
        ├─ by-country-group/group-a/2025-03/metadata.json
        └─ Aggregate statistics
        ↓
Success Report
        ├─ Incident stored: YES
        ├─ Location: incidents/by-date/2025-03-11/
        ├─ Quality score: 0.95
        └─ Escalation detected: NO
```

### Workflow 6: Batch Processing Multiple Incidents

```
Daily monitoring produces 5-10 incidents
        ↓
@data-engineer receives batch
        ↓
Step 1: Validate all incidents
        ├─ Check each independently
        ├─ Collect validation results
        └─ Separate by quality tier
        ↓
Step 2: Organize by quality
        ├─ Ready to store (quality ≥ 0.95) → 8 incidents
        ├─ Store with warnings (0.85-0.95) → 1 incident
        └─ Needs review (< 0.85) → 1 incident
        ↓
Step 3: Batch directory creation
        ├─ Create all needed directories once
        └─ More efficient than individual creation
        ↓
Step 4: Batch write operations
        ├─ Write all validated incidents to same date files
        ├─ Single metadata.json update per date
        └─ Bulk index updates
        ↓
Step 5: Report status
        {
          "total_received": 10,
          "validated": 9,
          "stored": 9,
          "warnings": 1,
          "needs_review": 1,
          "storage_location": "incidents/by-date/2025-03-11/",
          "files_updated": ["incidents.jsonl", "metadata.json", "indices"]
        }
```

### Workflow 7: Escalation Detection During Storage

```
Updated incident arrives: Flood in Aceh, Indonesia
        ↓
Previous record exists (Level 2)
        ↓
@data-engineer detects level change
        ├─ Previous: Level 2 (5K affected)
        ├─ Current: Level 3 (25K affected, 5 deaths)
        └─ Escalation detected: YES
        ↓
Creates escalation record
        {
          "incident_id": "20250311-ID-FL",
          "previous_level": 2,
          "new_level": 3,
          "reason": "Death toll increased; affected population tripled",
          "escalation_date": "2025-03-11T14:30:00Z"
        }
        ↓
Step 1: Store incident update to by-date files
Step 2: Write escalation record to escalations/2025-03-11/escalations.jsonl
Step 3: Update escalation metadata/summary
Step 4: Flag for SRC alert
Step 5: Return escalation notification
        ↓
Result:
        ├─ Escalation alert generated
        ├─ Sent to SRC monitoring
        └─ Flagged for immediate action
```

---

## Data Organization & Access Patterns

### Storage Structure

```
incidents/
├── by-date/[YYYY-MM-DD]/              (PRIMARY - Most used)
│   ├── incidents.jsonl
│   ├── media-coverage.jsonl
│   └── metadata.json
├── by-country-group/[A|B|C]/[YYYY-MM]/(SECONDARY - Regional analysis)
│   ├── incidents.jsonl
│   └── metadata.json
├── by-incident-type/[type]/[status]/ (TERTIARY - Type-based)
│   ├── incidents.jsonl
│   └── metadata.json
├── by-country/[country]/              (COUNTRY-SPECIFIC)
│   ├── active-incidents.jsonl
│   ├── resolved-incidents.jsonl
│   └── metadata.json
├── media-coverage/[YYYY-MM]/          (MEDIA RECORDS)
│   ├── coverage.jsonl
│   ├── singapore-mentions.jsonl
│   ├── src-mentions.jsonl
│   ├── donation-concerns.jsonl
│   └── misinformation.jsonl
├── escalations/[YYYY-MM-DD]/          (ESCALATION TRACKING)
│   ├── escalations.jsonl
│   └── summary.json
├── archive/[YYYY]/                    (HISTORICAL)
│   ├── resolved-incidents.jsonl
│   └── media-coverage.jsonl
└── indices/                           (FAST LOOKUPS)
    ├── incident-index.jsonl
    ├── country-index.jsonl
    ├── date-index.jsonl
    └── query-log.jsonl
```

### Data File Format

**Format:** JSONL (JSON Lines)
- One JSON object per line
- UTF-8 encoding
- No newlines within objects
- Streaming and processing friendly

**Example:**
```
{"incident_id": "20250311-ID-EQ", "incident_name": "Earthquake in Sumatra, Indonesia", ...}
{"incident_id": "20250311-PH-FL", "incident_name": "Floods in Luzon, Philippines", ...}
{"incident_id": "20250311-TH-DI", "incident_name": "Chikungunya Outbreak in Thailand", ...}
```

### Quick Access Examples

**Find today's incidents:**
```bash
cat incidents/by-date/$(date +%Y-%m-%d)/incidents.jsonl
```

**Find high-priority incidents:**
```bash
jq 'select(.priority=="HIGH")' incidents/by-date/2025-03-11/incidents.jsonl
```

**Count incidents by severity:**
```bash
jq '.classification.incident_level' incidents/by-date/2025-03-11/incidents.jsonl | sort | uniq -c
```

**Get Singapore mentions:**
```bash
wc -l incidents/media-coverage/2025-03/singapore-mentions.jsonl
```

---

## Data Flow & Workflows

### Workflow 1: Natural Disaster Monitoring (GDACS)

```
User Request: "Monitor for earthquakes in Asia"
        ↓
@disaster-incident-reporter
        ↓
Step 1: Fetch GDACS latest alerts
        ↓
Step 2: Extract earthquake data
        ├─ Location: Indonesia
        ├─ Impact: 5,000 affected
        └─ Magnitude: 6.1
        ↓
Step 3: Load @skill incident-classifier
        ├─ Country group: A (Indonesia)
        ├─ Level: 2 (< 100k affected, updates expected)
        └─ Priority: MEDIUM
        ↓
Step 4: Load @skill disaster-monitor
        ├─ Format: "Earthquake in [region], Indonesia"
        ├─ Link: https://...
        └─ Action: INCLUDE
        ↓
Step 5: Output structured incident
        ├─ disaster_type: Earthquake
        ├─ country_group: A
        ├─ incident_level: 2
        ├─ priority: MEDIUM
        ├─ action: INCLUDE
        └─ formatted_text: "[Earthquake] in [region], Indonesia"
        ↓
@incident-summarizer
        ├─ Receives incident
        ├─ Groups with other MEDIUM priority incidents
        ├─ Formats for WhatsApp
        └─ Outputs to chat
```

### Workflow 2: Disease Outbreak Monitoring (ProMED)

```
User Request: "Check for disease outbreaks"
        ↓
@disaster-incident-reporter
        ↓
Step 1: Fetch ProMED latest posts
        ↓
Step 2: Extract disease data
        ├─ Disease: Chikungunya
        ├─ Location: Malaysia
        ├─ Cases: 50 confirmed
        └─ Risk: Spread potential
        ↓
Step 3: Load @skill incident-classifier
        ├─ Country group: A (Malaysia)
        ├─ Level: 1 (Local outbreak, few cases)
        ├─ But: Track for escalation
        └─ Priority: MEDIUM (Group A special rule)
        ↓
Step 4: Load @skill disaster-monitor
        ├─ Format: "Disease outbreak: Chikungunya in Malaysia"
        ├─ Link: https://promedmail.org/...
        └─ Action: INCLUDE (for Group A monitoring)
        ↓
Step 5: Output structured incident
        ├─ disaster_type: Disease Outbreak
        ├─ country_group: A
        ├─ incident_level: 1
        ├─ priority: MEDIUM
        └─ action: INCLUDE
        ↓
@incident-summarizer
        └─ Includes in monitoring updates
```

### Workflow 3: Media Coverage Monitoring

```
User Request: "Monitor news for Singapore/SRC mentions"
        ↓
@media-incident-reporter
        ↓
Step 1: Scan news sources (10-15 mins)
        ├─ Reuters: [Disaster article]
        ├─ Straits Times: [Relief article]
        └─ Facebook SRC page: [Comments about donations]
        ↓
Step 2: Evaluate content (10-15 mins)
        ├─ Article 1: Singapore citizens affected → INCLUDE
        ├─ Article 2: SRC donation announcement → INCLUDE
        └─ Article 3: No Singapore angle → EXCLUDE
        ↓
Step 3: Load @skill media-monitor
        ├─ Format check: Standard WhatsApp format
        ├─ Flags: [SRC mentioned], [Singapore aid]
        └─ Action: REPORT
        ↓
Step 4: Format for output
        ├─ Format 1: "Sri Lanka – floods"
        ├─ Format 2: "[SRC mentioned]"
        └─ Link: https://...
        ↓
Step 5: Output media reports
        ├─ WhatsApp "media updates" chat
        ├─ Timeline documentation (if SRC involved)
        └─ Escalation alert (if urgent)
        ↓
@incident-summarizer
        └─ Consolidates with disaster reports
```

### Workflow 4: Emergency Escalation

```
Condition: "Humanitarian crisis declared in Philippines"
        ↓
@disaster-incident-reporter detects escalation
        ├─ GDACS: International aid requested
        ├─ Level changes from 2 → 4
        └─ Priority: HIGH (override rule)
        ↓
OR
        ↓
@media-incident-reporter detects escalation
        ├─ Major news: "Humanitarian crisis declared"
        ├─ SRC considering large response
        └─ Public concern rising
        ↓
Both feed to @incident-summarizer
        ↓
Escalation Alert Generated
        ├─ 🚨 ESCALATION ALERT
        ├─ Previous Level: 2
        ├─ Current Level: 4
        ├─ Reason: International assistance requested
        ├─ Action: Immediate reporting
        └─ Distributed immediately to WhatsApp
        ↓
Timeline Updated
        ├─ SRC involvement status updated
        ├─ Donation appeal activated
        └─ Daily monitoring initiated
```

---

## Integration Points

### With GDACS
- **URL:** https://www.gdacs.org/
- **Data Type:** Real-time disaster alerts
- **Update Frequency:** Minutes to hours
- **Access:** Web scraping, RSS feeds
- **Key Data:** Disaster type, location, impact estimates, alerts

### With ProMED
- **URL:** https://www.promedmail.org/
- **Data Type:** Disease outbreak surveillance
- **Update Frequency:** Daily (5-20 events)
- **Access:** Website posts, archive search
- **Key Data:** Disease, location, cases, spread pattern

### With News Sources
- **Tier 1:** Reuters, AP, BBC, AFP, Al Jazeera
- **Tier 2:** Channel NewsAsia, Straits Times, The Star, Antara, Bangkok Post
- **Tier 3:** ReliefWeb, Devex
- **Access:** Website browsing, news aggregators
- **Key Data:** Coverage, Singapore angle, SRC involvement

### With Social Media
- **Twitter/X:** Disaster hashtags, real-time discussions
- **Facebook:** SRC official page, community groups
- **Reddit:** r/Singapore, regional subreddits
- **TikTok:** Trending disaster content
- **WhatsApp:** SRC official channels
- **Access:** Platform APIs, public monitoring
- **Key Data:** Public sentiment, scams, misinformation

### With Distribution Channels
- **WhatsApp Group:** "Incident updates" (https://chat.whatsapp.com/Iod50oeNYyM2eK6noZzVpr)
- **Disaster Event Timeline Document:** Shared spreadsheet/document
- **Email:** Optional alerts for critical escalations
- **Dashboard:** Real-time incident tracking (future enhancement)

---

## Geographic Coverage

### Group A: Asia Pacific 1 (PRIMARY - 25 Countries)
Highest monitoring priority. All incidents tracked.

**South Asia:** Afghanistan, Bangladesh, Bhutan, India, Maldives, Nepal, Pakistan, Sri Lanka

**Southeast Asia:** Brunei, Cambodia, Indonesia, Laos, Malaysia, Myanmar, Philippines, Singapore, Thailand, Timor Leste, Vietnam

**East Asia:** China, Japan, North Korea, South Korea, Taiwan

### Group B: Asia Pacific 2 + MENA (SECONDARY)
Medium monitoring priority. Level 3-4 incidents reported.

**Asia Pacific 2:** Australia, Fiji, New Zealand, Papua New Guinea, and 20+ Pacific island nations

**Middle East:** Iran, Iraq, Israel/Palestine, Saudi Arabia, Syria, Turkey, UAE, Yemen, and others

**North Africa:** Algeria, Egypt, Morocco, Tunisia

### Group C: Rest of Africa, Europe, Americas (TERTIARY)
Selective monitoring. Only Level 4 incidents or exceptional cases reported.

---

## Reporting Standards

### Priority Matrix Quick Reference

| Level | Group A | Group B | Group C | Criteria |
|-------|---------|---------|---------|----------|
| 4 | HIGH | HIGH | HIGH | 300k+ affected / 50+ deaths / International aid / Multi-state |
| 3 | HIGH | MEDIUM | MEDIUM | 100k+ affected / Daily coverage / Major impact |
| 2 | MEDIUM | MEDIUM | LOW | 50-100k affected / Multiple updates |
| 1 | MEDIUM | LOW | LOW | <50k affected / Early warning |

**Special Rules:**
- Humanitarian crisis declaration → Always HIGH
- Forecasted events → Include for awareness
- Multi-regional impact → Elevate one level
- Likely further development → Elevate one level

### Reporting Formats

**Format 1 - Active Incident:**
```
[Disaster type] in [regions/provinces/states], [country]
[Link]
```

**Format 2 - Forecasted Event:**
```
Forecasted [disaster type] in [regions/provinces/states], [country]
[Link]
```

**Format 3 - Update:**
```
Update on [disaster event/name/type] in [country]
[Link]
```

**Format 4 - Media Coverage:**
```
[Country / Disaster Type]
[Link]
[Optional flags: SRC mentioned / Singapore aid / Donation concerns / Misinformation]
```

---

## Operational Schedules

### Peacetime Mode

**Disaster Monitoring:**
- Frequency: Continuous
- GDACS checks: Every 4-6 hours
- ProMED checks: Daily
- Schedule: Flexible (whenever available)

**Media Monitoring:**
- Frequency: 2-3 scans per week
- Duration: 30-45 minutes per scan
- Geographic focus: Asia Pacific
- Best times: Morning or evening

**Reporting:**
- WhatsApp updates: Posted 2-3 times per week
- Timeline: Updated continuously
- Escalations: Immediate upon detection

### Emergency Mode

**Triggered By:**
- Level 4 incident reported
- Humanitarian crisis declared
- SRC deciding to support disaster
- Major global crisis receiving daily coverage

**Disaster Monitoring:**
- Frequency: Continuous
- GDACS checks: Every 2-4 hours
- ProMED checks: Daily
- Schedule: Daily shift coverage

**Media Monitoring:**
- Frequency: Daily
- Duration: 30-60 minutes per scan
- Geographic focus: Global (for incident context)
- Best times: Multiple throughout day

**Reporting:**
- WhatsApp updates: Daily
- Timeline: Daily updates
- Escalations: Immediate
- Duration: Until crisis stabilizes

---

## Success Metrics

### Coverage Metrics
- Report 95%+ of Group A Level 3-4 incidents
- Capture 90%+ of Group B Level 4 incidents
- Minimal false positives (exclude criteria violations <5%)

### Timeliness Metrics
- Report GDACS incidents within 2 hours
- Report ProMED incidents within 24 hours
- Report media coverage within 4 hours
- Escalate Level 4 within 1 hour

### Accuracy Metrics
- 100% data accuracy (vs. source verification)
- 95%+ correct classification
- 100% link accuracy
- 0% scam reporting (100% identification)

### Reporting Metrics
- 100% format compliance
- 0% duplicate reports
- 100% appropriate priority assignment
- 100% escalation capture

---

## Troubleshooting

### Issue: Duplicate Reports
**Solution:** incident-summarizer deduplication step consolidates same incidents

### Issue: Incorrect Classification
**Solution:** Always refer to incident-classifier skill decision tree

### Issue: Missing Incidents
**Solution:** Ensure GDACS and ProMED monitored daily, cross-check news

### Issue: Escalation Missed
**Solution:** Flag any Level 3→4 change immediately, use escalation alert format

### Issue: Format Inconsistency
**Solution:** Always use disaster-monitor or media-monitor skill formats

---

## Future Enhancements

1. **API Integration**
   - Direct GDACS API integration
   - ProMED-mail API access
   - News aggregator APIs

2. **Real-time Dashboard**
   - Live incident tracking
   - Interactive maps
   - Priority visualization

3. **Automated Alerts**
   - SMS alerts for Level 4
   - Email summaries
   - Slack/Teams integration

4. **Sentiment Analysis**
   - Public opinion tracking
   - Donor sentiment
   - Misinformation spread analysis

5. **Predictive Analytics**
   - Escalation prediction
   - Humanitarian crisis forecasting
   - Geographic hotspot identification

6. **Multi-language Support**
   - Translate incident summaries
   - Monitor non-English sources
   - Global coverage expansion

---

## References

### Monitoring Agents
- `@disaster-incident-reporter` - GDACS/ProMED monitoring
- `@media-incident-reporter` - News/social media monitoring
- `@incident-summarizer` - Report compilation

### Data Engineering Agent
- `@data-engineer` - Incident data processing and storage

### Monitoring Skills
- `@skill incident-classifier` - Classification rules
- `@skill disaster-monitor` - Formatting standards
- `@skill media-monitor` - Media monitoring guidelines

### Data Engineering Skills
- `@skill data-schema` - JSON schema and validation
- `@skill data-storage` - Folder organization and file structure

### Data Sources (Top 5)
- GDACS: https://www.gdacs.org/ (Natural disasters)
- ProMED: https://www.promedmail.org/ (Disease outbreaks)
- Reuters/AP/BBC: Tier 1 news agencies
- Regional News: Tier 2-3 local/regional outlets
- WHO: https://www.who.int/emergencies/ (Official verification)

### Distribution Channels
- WhatsApp Group: https://chat.whatsapp.com/Iod50oeNYyM2eK6noZzVpr
- Disaster Event Timeline: Shared spreadsheet/document
- JSONL Database: incidents/ directory

### Documentation Files
- AGENTS.md - This file (monitoring system)
- docs/DATA-ENGINEERING.md - Data storage and processing guide
- docs/SYSTEM-COMPLETE.md - System completion summary
- incidents/README.md - Data access and query guide

---

## Document Information

**Created:** 2025-03-11  
**Last Updated:** 2025-03-11  
**Version:** 2.0  
**Status:** Active  
**Maintained By:** Disaster Awareness Agent Team

**Changes in Version 2.0:**
- Added complete Data Engineering Subsystem
- Integrated data-engineer subagent
- Added data-schema and data-storage skills
- Documented JSONL storage format
- Added data workflows and storage structure
- Updated architecture to show complete system pipeline

---

## Quick Start Guide

### For New Users

1. **Understand the System:**
   - Review this AGENTS.md file (complete system overview)
   - Read docs/DATA-ENGINEERING.md for data storage details
   - Read each skill file for detailed rules

2. **Monitor Incidents (Subsystem 1):**
   - Request disaster monitoring: `@disaster-incident-reporter Check GDACS and ProMED`
   - Request media monitoring: `@media-incident-reporter Scan news for Singapore/SRC mentions`
   - Request report compilation: `@incident-summarizer Compile daily reports`

3. **Store Incidents (Subsystem 2):**
   - Request storage: `@data-engineer Store this incident [JSON]`
   - Incidents automatically organized in incidents/ directory
   - Stored in JSONL format with indices

4. **Check Reports:**
   - WhatsApp "Incident updates" group for daily summaries
   - Disaster Event Timeline for detailed documentation
   - Query incidents: `cat incidents/by-date/$(date +%Y-%m-%d)/incidents.jsonl`

5. **Report Issues:**
   - Escalate via WhatsApp immediate flag (🚨)
   - Contact system administrators for system issues

### For Operators

1. **Daily Operations:**
   - Ensure monitoring agents running on schedule
   - Ensure data-engineer ready for storage
   - Monitor WhatsApp for escalations
   - Verify incident classifications
   - Update timeline as needed

2. **Quality Control:**
   - Cross-check reported incidents against sources
   - Verify classification accuracy
   - Ensure format compliance
   - Monitor data quality scores (target ≥ 0.90)
   - Track false positive/negative rates

3. **Data Management:**
   - Monitor incidents/ directory size
   - Verify metadata.json files updated
   - Check indices for accuracy
   - Archive old incidents (> 3 months)
   - Backup incidents/ directory daily

4. **Escalation Management:**
   - Respond to Level 4 incidents immediately
   - Coordinate with SRC if response needed
   - Update emergency timeline
   - Check for detected escalations in data-engineer output
   - Brief leadership on major incidents
