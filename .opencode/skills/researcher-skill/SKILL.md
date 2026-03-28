---
name: researcher-skill
description: Methodology and guidelines for conducting deep research on flagged incidents, source validation, and data enhancement
compatibility: "1.0.0+"
metadata:
  category: research
  difficulty: advanced
  type: incident-investigation
---

# Researcher Skill

Methodology and guidelines for conducting deep research on flagged incidents to validate, verify, and enhance incident data quality.

## Research Triggers

Research is triggered when storage-manager flags incidents for investigation:

| Trigger | Description | Priority |
|---------|-------------|----------|
| low_quality | Quality score < 0.85 | HIGH |
| limited_sources | Level 3-4 with < 2 sources | HIGH |
| humanitarian_crisis | Declared humanitarian crisis | HIGH |
| new_incident_type | First of this type in database | MEDIUM |
| escalation_potential | Likely to worsen significantly | HIGH |
| singapore_angle | Important for SRC response | MEDIUM |
| verification_needed | Data inconsistencies detected | MEDIUM |

## Research Methodology

### Phase 1: Source Identification

**Priority Order:**
1. Government agencies (highest authority)
2. UN/international organizations
3. Major international news agencies
4. Regional news (for local context)
5. NGO reports (for humanitarian angle)

**By Country - Primary Sources (Group A):**

| Country | Agency | Type | URL |
|---------|--------|------|-----|
| Indonesia | BNPB | Government | bnpb.go.id |
| Philippines | NDRRMC | Government | ndrrmc.gov.ph |
| Thailand | DDPM | Government | mjustice.go.th |
| Malaysia | NADMA | Government | nadma.gov.my |
| Vietnam | VDMA | Government | vdma.gov.vn |
| Myanmar | MNAF | Government | menafn.com |
| India | NDMA | Government | ndma.gov.in |
| Bangladesh | NDMRT | Government | modmr.gov.bd |
| Nepal | NDRRMA | Government | ndrrc.gov.np |
| Sri Lanka | DMC | Government | disastermin.gov.lk |

**International Sources:**

| Source | Type | Coverage |
|--------|------|----------|
| GDACS | Disaster DB | Natural disasters |
| WHO | Health | Disease outbreaks |
| ProMED | Health | Disease surveillance |
| ReliefWeb | Humanitarian | All disasters |
| UN OCHA | Humanitarian | All disasters |

**News Sources by Reliability:**

| Tier | Sources |
|------|---------|
| HIGH | Reuters, AP, AFP, BBC, Al Jazeera |
| MEDIUM | CNA, Straits Times, The Star, Bangkok Post |
| LOW | Social media, blogs |

### Phase 2: Data Extraction

**Required Information:**

```json
{
  "incident_id": "unique identifier",
  "location": {
    "country": "full name",
    "province": "state/region",
    "districts": ["list of affected areas"],
    "coordinates": {"lat": 0.0, "lon": 0.0}
  },
  "dates": {
    "onset": "ISO8601 - when disaster started",
    "latest_update": "ISO8601 - most recent update",
    "forecast_end": "ISO8601 or null",
    "timeline": [
      {"date": "ISO8601", "event": "description", "source": "source name"}
    ]
  },
  "impact": {
    "deaths": number,
    "missing": number,
    "injured": number,
    "affected": number,
    "displaced": number,
    "homeless": number,
    "confidence": {
      "deaths": "high|medium|low",
      "affected": "high|medium|low"
    }
  },
  "sources": [
    {
      "name": "source name",
      "url": "full URL",
      "type": "government|news|un|ngol",
      "reliability": "high|medium|low",
      "date": "publication date"
    }
  ]
}
```

### Phase 3: Cross-Reference Verification

**Verification Rules:**

1. **Numbers Verification**
   - Compare across 2-3 sources
   - Note discrepancies
   - Prefer authoritative sources
   - Document confidence level

2. **Date Verification**
   - Establish onset date (first impact)
   - Note updates timeline
   - Verify against multiple sources
   - Use earliest authoritative date

3. **Location Verification**
   - Confirm affected areas
   - Note geographic spread
   - Check coordinates if provided

### Phase 4: Enhancement

**Enhancement Checklist:**

- [ ] Complete all missing required fields
- [ ] Add multiple source citations
- [ ] Establish timeline of events
- [ ] Verify impact numbers
- [ ] Document confidence levels
- [ ] Add research metadata

**Enhancement Fields:**

```json
{
  "research_metadata": {
    "research_date": "ISO8601",
    "researcher": "researcher_agent",
    "research_reason": "trigger from storage-manager",
    "original_quality_score": 0.78,
    "enhanced_quality_score": 0.95,
    "sources_consulted": 5,
    "primary_source": "authoritative source name",
    "confidence_overall": "high|medium|low",
    "discrepancies_noted": "description if any",
    "research_notes": "methodology notes"
  }
}
```

## Quality Score Calculation

### Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Completeness | 40% | All required fields present |
| Source Quality | 30% | Authoritative sources used |
| Verification | 20% | Cross-referenced data |
| Consistency | 10% | Logical consistency |

### Score Calculation

```
quality_score = (completeness * 0.4) + (source_quality * 0.3) + (verification * 0.2) + (consistency * 0.1)
```

### Target Scores

| Stage | Target Score |
|-------|-------------|
| Before research | Report if < 0.85 |
| After research | Achieve ≥ 0.90 |
| Storage ready | Require ≥ 0.85 |

## Source Reliability Guide

### Government Sources

| Reliability | Indicators |
|-------------|------------|
| HIGH | Official agency, verified data, direct link |
| MEDIUM | Regional agency, some verification |
| LOW | Unconfirmed social media from officials |

### News Sources

| Reliability | Indicators |
|-------------|------------|
| HIGH | Reuters, AP, BBC, AFP with on-ground reporters |
| MEDIUM | Regional outlets, wire service republishing |
| LOW | Unverified social media, blogs |

### Special Cases

| Source Type | Best Use |
|-------------|----------|
| GDACS | Initial alerts, magnitude, coordinates |
| WHO | Official health statistics |
| ProMED | Disease surveillance, early detection |
| ReliefWeb | Humanitarian impact, response needs |

## Date Research Guidelines

### Date Types

1. **Onset Date** - When disaster started
   - First warning/forecast (if forecasted)
   - First impact/occurrence
   - First reported in media

2. **Update Date** - Most recent information
   - Latest official update
   - Latest media report
   - Current status

3. **Forecast Date** - Predicted events
   - Weather forecast end
   - Expected peak
   - Recovery timeline

### Date Extraction Rules

- Prefer official government dates
- Cross-reference with multiple sources
- Note if dates are approximate
- Document source for each date

## Impact Number Guidelines

### Definitions

| Metric | Definition | Source |
|--------|-----------|--------|
| Deaths | Confirmed fatalities | Government, WHO |
| Missing | Reported missing | Government, Police |
| Injured | Physical injuries | Hospital, Government |
| Affected | Direct impact | Varies by source |
| Displaced | In shelters | Government, UN |
| Homeless | Lost housing | Government, NGOs |

### Verification Rules

- Cross-reference at least 2 sources
- Prefer government numbers
- Note definitional differences
- Document confidence level

### Common Discrepancies

| Issue | Explanation |
|-------|------------|
| Deaths vary | Different cutoff times |
| Affected varies | Different definitions |
| Displaced vs homeless | Sheltered vs lost home |

## Output Standards

### Enhanced Incident JSON

Must include:
- All original fields preserved
- Enhanced fields clearly marked
- Research metadata added
- Sources array with 2+ entries

### Research Report

```json
{
  "research_status": "COMPLETE",
  "incident_id": "20250311-ID-FL",
  "original_quality_score": 0.78,
  "enhanced_quality_score": 0.95,
  "sources_consulted": [
    {"name": "BNPB", "type": "government", "reliability": "high"},
    {"name": "Reuters", "type": "news", "reliability": "high"}
  ],
  "data_enhanced": {
    "dates": "completed",
    "impact_numbers": "verified",
    "location": "expanded"
  },
  "ready_for_storage": true
}
```

## Error Handling

### Insufficient Sources

If cannot find enough sources:
- Note limitation in research metadata
- Set confidence to "low" for uncertain fields
- Flag for manual review
- Return whatever data found

### Conflicting Data

If sources conflict:
- Note discrepancies in research notes
- Prefer authoritative source
- Document reasoning
- Set appropriate confidence level

### No Information Found

If critical data not found:
- Mark field as null
- Note "not found" in research notes
- Set confidence to "low"
- Still return enhanced incident

## Interaction with Other Agents

### With storage-manager

**Receives:**
- Incident to research
- Flags/reasons for research
- Missing field list

**Returns:**
- Enhanced incident JSON
- Research report
- Quality improvement summary

### With data-engineer

**Receives:**
- Original incident (for reference)

**Returns:**
- Enhanced version for storage

## Success Criteria

- Quality score improved by ≥ 0.10
- At least 2 authoritative sources
- All critical dates established
- Impact numbers verified
- Ready for storage approval

This skill ensures consistent, thorough research methodology for all flagged incidents.
