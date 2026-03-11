# Disaster Awareness Agent System

Comprehensive documentation of the disaster and health emergency monitoring agent system for the Disaster Awareness Agent project.

## System Overview

The Disaster Awareness Agent system consists of **3 specialized subagents** and **3 supporting skills** working together to monitor, classify, and report on natural disasters and health emergencies with epidemic/pandemic potential.

### Architecture Diagram

```
Data Sources
├── GDACS (Natural Disasters)
├── ProMED (Disease Outbreaks)
├── News Outlets (Tier 1-3)
└── Social Media Platforms

        ↓

Monitoring Agents
├─ disaster-incident-reporter
│  └── Monitors: GDACS + ProMED
├─ media-incident-reporter
│  └── Monitors: News + Social Media
└─ [Both feed classified data]

        ↓

Supporting Skills (Classification & Formatting)
├─ incident-classifier
│  └── Rules for priority classification
├─ disaster-monitor
│  └── Incident formatting standards
└─ media-monitor
    └── Media monitoring guidelines

        ↓

Output Agent
└─ incident-summarizer
   └── Compiles into WhatsApp + Timeline reports

        ↓

Distribution
├─ WhatsApp "Incident updates" Group
└─ Disaster Event Timeline Document
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

### Agents
- `@disaster-incident-reporter` - GDACS/ProMED monitoring
- `@media-incident-reporter` - News/social media monitoring
- `@incident-summarizer` - Report compilation

### Skills
- `@skill incident-classifier` - Classification rules
- `@skill disaster-monitor` - Formatting standards
- `@skill media-monitor` - Media monitoring guidelines

### Data Sources
- GDACS: https://www.gdacs.org/
- ProMED: https://www.promedmail.org/
- ReliefWeb: https://reliefweb.int/
- HealthMap: https://www.healthmap.org/
- WHO: https://www.who.int/emergencies/

### Distribution Channels
- WhatsApp: https://chat.whatsapp.com/Iod50oeNYyM2eK6noZzVpr
- Disaster Event Timeline: [Document link]

---

## Document Information

**Created:** 2025-03-11  
**Last Updated:** 2025-03-11  
**Version:** 1.0  
**Status:** Active  
**Maintained By:** Disaster Awareness Agent Team

---

## Quick Start Guide

### For New Users

1. **Understand the System:**
   - Review this AGENTS.md file
   - Read each skill (incident-classifier, disaster-monitor, media-monitor)

2. **Use the Agents:**
   - Request disaster monitoring: `@disaster-incident-reporter`
   - Request media monitoring: `@media-incident-reporter`
   - Request report compilation: `@incident-summarizer`

3. **Check Reports:**
   - WhatsApp "Incident updates" group for daily summaries
   - Disaster Event Timeline for detailed documentation

4. **Report Issues:**
   - Escalate via WhatsApp immediate flag (🚨)
   - Contact system administrators for system issues

### For Operators

1. **Daily Operations:**
   - Ensure agents running on schedule
   - Monitor WhatsApp for escalations
   - Verify incident classifications
   - Update timeline as needed

2. **Quality Control:**
   - Cross-check reported incidents against sources
   - Verify classification accuracy
   - Ensure format compliance
   - Track false positive/negative rates

3. **Escalation Management:**
   - Respond to Level 4 incidents immediately
   - Coordinate with SRC if response needed
   - Update emergency timeline
   - Brief leadership on major incidents
