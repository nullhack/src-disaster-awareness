---
name: storage-manager-skill
description: Rules and methodology for overseeing storage operations, ensuring data integrity, preventing duplicates, and maintaining reference accuracy
compatibility: "1.0.0+"
metadata:
  category: data-engineering
  difficulty: advanced
  type: storage-management
---

# Storage Manager Skill

Rules and operational guidelines for overseeing incident data storage operations, ensuring standards compliance, and maintaining data integrity.

## Core Responsibilities

The storage-manager skill provides the operational framework for:
1. Pre-storage validation
2. Duplicate detection
3. Quality scoring
4. Reference integrity verification
5. Active/inactive status management
6. Storage auditing
7. Research flagging

## Validation Rules

### Required Fields (per data-schema)

Every incident MUST have these fields before storage:

| Field | Type | Description |
|-------|------|-------------|
| incident_id | string | Unique ID (YYYYMMDD-CC-TT format) |
| incident_name | string | Human-readable name |
| created_date | ISO8601 | Creation timestamp |
| country | string | Country name |
| country_group | A\|B\|C | Geographic grouping |
| incident_type | string | Disaster classification |
| incident_level | 1-4 | Severity level |
| priority | HIGH\|MEDIUM\|LOW | Reporting priority |
| status | Active\|Resolved\|Monitoring | Current status |
| sources | array | Source objects with url |

### Quality Thresholds

| Quality Score | Decision | Action |
|--------------|----------|--------|
| ≥ 0.95 | APPROVE | Proceed to storage |
| 0.85-0.95 | CONDITIONAL | Proceed with warnings |
| < 0.85 | DENY/DEEP_RESEARCH | Reject or flag for research |

### Critical Validation Rules

1. **Level-Priority Alignment**
   - Level 4 MUST have HIGH priority
   - Level 3 should have HIGH or MEDIUM
   - Level 1-2 typically MEDIUM or LOW

2. **Impact Consistency**
   - deaths ≤ affected (always)
   - missing should be documented separately
   - displaced ≤ affected

3. **Date Validity**
   - created_date ≤ updated_date (if updated_date exists)
   - All dates in ISO 8601 format
   - No future dates for onset (except forecasted)

4. **Source Requirements**
   - At least 1 source with URL
   - Sources should be authoritative (government, UN, major news)
   - Source URLs should be valid format

## Duplicate Detection Rules

### Detection Priority

1. **Exact ID Match** (highest priority)
   - Same incident_id exists in all-incidents-index
   - Check if it's an update or true duplicate

2. **Composite Match** (medium priority)
   - Same country + incident_type + date within 7 days
   - Cross-reference with source URLs

3. **Source URL Match** (lower priority)
   - Same URL found in existing incidents
   - May indicate duplicate reporting

### Duplicate Resolution

| Scenario | Resolution |
|----------|-----------|
| Exact ID + older timestamp | DENY |
| Exact ID + newer timestamp | APPROVE_AS_UPDATE |
| Composite match + different sources | Flag for review |
| Same URL | DENY |

## Reference Integrity Rules

### Active Incidents

Active incidents MUST have references in:
- `references/active/by-country-group.jsonl`
- `references/active/by-incident-type.jsonl`
- `references/active/by-country.jsonl`

### Inactive Incidents

Inactive incidents MUST have references in:
- `references/inactive/by-country-group.jsonl`
- `references/inactive/by-incident-type.jsonl`
- `references/inactive/by-country.jsonl`

### Master Index

ALL incidents MUST have entry in:
- `references/all-incidents-index.jsonl`

### Reference Structure

Each reference entry MUST contain:
```json
{
  "incident_id": "20250311-ID-FL",
  "file": "by-date/2025-03-11/incidents.jsonl",
  "line": 1,
  "country_group": "A",
  "type": "Flood",
  "priority": "HIGH"
}
```

## Research Flagging Rules

Flag for deep research when ANY of:

1. **Quality Issues**
   - Quality score < 0.85
   - Missing any required field
   - Inconsistent data (deaths > affected)

2. **Severity + Source Issues**
   - Level 3-4 with only 1 source
   - No authoritative source (government/UN)

3. **Special Categories**
   - Humanitarian crisis flagged
   - Singapore/SRC mentioned
   - Escalation potential high

4. **New Types**
   - First incident of this type in database
   - Unusual disaster type for region

## Active/Inactive Status Rules

### Status Definitions

| Status | Definition | Reference Location |
|--------|------------|-------------------|
| Active | Ongoing incident, response active | references/active/ |
| Resolved | Incident closed, no more updates | references/inactive/ |
| Monitoring | Watch list, may escalate | references/inactive/ |
| Forecasted | Predicted event, not yet occurred | references/inactive/ |

### Status Change Triggers

**Active → Inactive (Resolved):**
- Official declaration of resolution
- No updates for 7+ days
- Response concluded
- All affected resolved

**Active → Inactive (Monitoring):**
- Intensity decreased
- No immediate response needed
- Continue watching for changes

### Status Change Process

1. Verify status field changed in by-date/ data
2. Remove from active references
3. Add to inactive references
4. Update all-incidents-index status
5. Document in audit log

## Storage Audit Rules

### Daily Checks

1. Verify reference integrity (all refs point to valid data)
2. Check for orphaned references
3. Verify line numbers match
4. Review new incidents added

### Weekly Checks

1. Full reference file rebuild verification
2. Duplicate scan across all dates
3. Storage statistics compilation
4. Quality trend analysis

### Monthly Checks

1. Archive old inactive incidents
2. Compression of old date folders
3. Backup verification
4. Performance metrics review

## Error Handling

### Storage Failures

| Error | Action |
|-------|--------|
| File not writable | Report permission issue |
| Directory creation failed | Check filesystem |
| JSON parse error | Reject with details |
| Reference update failed | Rollback, report |

### Data Quality Issues

| Issue | Severity | Action |
|-------|----------|--------|
| Missing non-critical field | WARNING | Allow with note |
| Missing critical field | ERROR | Reject |
| Invalid enum value | ERROR | Reject |
| Date format wrong | ERROR | Reject |

## Reporting Formats

### Storage Approval

```json
{
  "type": "storage_approval",
  "approved": true,
  "incident_id": "20250311-ID-FL",
  "quality_score": 0.95,
  "duplicate_check": "passed",
  "issues": [],
  "warnings": [],
  "next_steps": ["store_incident"]
}
```

### Research Flag

```json
{
  "type": "research_flag",
  "incident_id": "20250311-ID-FL",
  "reason": "low_quality",
  "quality_score": 0.78,
  "missing": ["deaths", "dates"],
  "research_required": true,
  "instructions": "Find authoritative sources, verify numbers, establish dates"
}
```

### Audit Report

```json
{
  "type": "audit_report",
  "date": "2025-03-11",
  "total_incidents": 150,
  "active": 25,
  "inactive": 125,
  "reference_errors": 0,
  "duplicates_found": 0,
  "storage_health": "good"
}
```

## Operational Procedures

### Pre-Storage Validation

1. Load storage-manager-skill
2. Load data-schema
3. Parse incident JSON
4. Check required fields
5. Calculate quality score
6. Check for duplicates
7. Generate approval/denial

### Post-Storage Validation

1. Verify written to by-date/
2. Verify references updated
3. Check line number accuracy
4. Run integrity check
5. Log to audit

### Status Change Procedure

1. Verify status field changed
2. Move references (active↔inactive)
3. Update master index
4. Update summary counts
5. Log change

## Interaction Standards

### With data-engineer

- data-engineer submits incidents for approval
- storage-manager validates and responds
- storage-manager validates post-storage

### With researcher

- storage-manager flags incidents
- researcher investigates and enhances
- researcher returns enhanced data
- storage-manager re-validates

### With incident-summarizer

- Summarizer submits compiled incidents
- storage-manager validates before storage

## Success Metrics

- Zero duplicates in database
- 100% reference accuracy
- Quality threshold: 90% of incidents ≥ 0.90
- Daily audits completed
- Research flagged appropriately

This skill ensures consistent, high-quality storage operations with proper oversight and validation.
