# WHO and HealthMap Source Specification

> **Status:** BASELINED (2026-05-11)
> API research, field mapping, and adapter design for WHO and HealthMap data sources.

---

## WHO Disease Outbreak News (DON) API

### API Details

| Item | Value |
|------|-------|
| Base URL | `https://www.who.int/api/hubs/diseaseoutbreaknews` |
| API Help | `https://www.who.int/api/hubs/diseaseoutbreaknews/sfhelp` |
| Type | Sitefinity OData REST API |
| Auth | **None** — fully open, no registration needed |
| Response format | JSON (OData) |
| Total records | ~3,179 (1990–present) |
| Rate limits | None observed |
| Update frequency | Within days of events |

### Endpoint

```
GET https://www.who.int/api/hubs/diseaseoutbreaknews?$top=20&$orderby=PublicationDateAndTime desc&$select=DonId,Title,PublicationDateAndTime,Summary,UrlName
```

### OData Parameters

| Parameter | Example | Purpose |
|-----------|---------|---------|
| `$top` | `$top=20` | Limit results |
| `$orderby` | `$orderby=PublicationDateAndTime desc` | Sort by date |
| `$select` | `$select=DonId,Title,PublicationDateAndTime,Summary` | Field selection |
| `$filter` | `$filter=Title eq 'Measles - Bangladesh'` | Filter |
| `$skip` | `$skip=20` | Pagination |
| `$count` | `$count=true` | Include total count |

### Response Structure

```json
{
  "value": [
    {
      "DonId": "2026-DON600",
      "Title": "Hantavirus cluster linked to cruise ship travel, Multi-country",
      "PublicationDateAndTime": "2026-05-08T00:00:00Z",
      "FormattedDate": "8 May 2026",
      "Summary": "Plain-text summary of the event...",
      "Overview": "<p>Full HTML description with case counts, geography...</p>",
      "Assessment": "<p>WHO risk assessment...</p>",
      "Advice": "<p>Public health recommendations...</p>",
      "Epidemiology": "<p>Disease background...</p>",
      "Response": "<p>Public health response actions...</p>",
      "FurtherInformation": "<p>Links to resources...</p>",
      "UrlName": "hantavirus-cluster-linked-to-cruise-ship-travel-multi-country",
      "ItemDefaultUrl": "/emergencies/disease-outbreak-news/...",
      "Id": "guid-uuid",
      "DateCreated": "2026-05-08T...",
      "LastModified": "2026-05-08T..."
    }
  ]
}
```

### Field Mapping to RawIncidentData

| RawIncidentData Field | WHO Source | Parsing Logic |
|-----------------------|-----------|---------------|
| `source_name` | Hardcoded `"WHO"` | — |
| `incident_name` | `Title` | Direct: "Measles - Bangladesh" |
| `country` | `Title` | Parse after " - " or last comma. E.g., "Measles - Bangladesh" → "Bangladesh". "Multi-country" → "Unknown" (use Overview for actual countries). |
| `disaster_type` | `Title` | Parse before " - ". E.g., "Measles - Bangladesh" → "Measles". Map to incident type enum: disease names → `"Disease"`. |
| `report_date` | `PublicationDateAndTime` | Direct ISO 8601 |
| `source_url` | `ItemDefaultUrl` | Prefix with `https://www.who.int` |
| `raw_fields` | Curated subset | See below |

### raw_fields for WHO

```json
{
  "don_id": "2026-DON600",
  "summary": "Plain-text summary...",
  "overview_html": "<p>Full HTML...</p>",
  "assessment_html": "<p>Risk assessment...</p>",
  "advice_html": "<p>Recommendations...</p>",
  "formatted_date": "8 May 2026",
  "url_name": "hantavirus-cluster-linked-to-cruise-ship-travel-multi-country",
  "who_internal_id": "guid-uuid",
  "date_created": "2026-05-08T...",
  "last_modified": "2026-05-08T..."
}
```

### Polling Strategy

| Setting | Value | Rationale |
|---------|-------|-----------|
| Poll interval | 6 hours | WHO publishes within days, not minutes |
| Query | `$top=20&$orderby=PublicationDateAndTime desc` | Last 20 DONs |
| Dedup key | `DonId` | Unique per report |
| Caching | In-memory, 4-hour TTL | Avoid redundant calls |

### Country Extraction Logic

WHO titles follow predictable patterns:
- `"Measles - Bangladesh"` → single country: `Bangladesh`
- `"Hantavirus cluster linked to cruise ship travel, Multi-country"` → multi-country: parse `Overview` HTML
- `"Cholera - Democratic Republic of the Congo"` → single country: `Democratic Republic of the Congo`
- `"Avian Influenza - France, Germany, Netherlands"` → multiple countries: split by comma

Python extraction:
```python
def extract_country_from_who_title(title: str) -> str:
    if " - " not in title:
        return "Unknown"
    parts = title.split(" - ", 1)
    country_part = parts[1].strip()
    if country_part.lower() == "multi-country":
        return "Unknown"  # Will need AI to extract from Overview
    if "," in country_part:
        return country_part.split(",")[0].strip()  # First country
    return country_part
```

### Limitations

1. **Country not a separate field** — must parse from Title or Overview HTML
2. **No explicit severity enum** — risk described in prose within Assessment/Summary
3. **HTML content** — Overview, Assessment, etc. contain HTML requiring sanitization
4. **Not exhaustive** — WHO only publishes events meeting IHR (2005) Article 11.4 criteria
5. **Disease names not standardized** — "Measles", "Avian Influenza", "Hantavirus" etc. in free text

### What Python Can Extract (No AI Needed)

- `incident_name` from `Title`
- `country` from `Title` (single-country cases)
- `disaster_type` = `"Disease"` (all WHO DON records are disease outbreaks)
- `report_date` from `PublicationDateAndTime`
- `source_url` from `ItemDefaultUrl`
- Dedup via `DonId`
- Date filtering/freshness checks

### What AI Needs to Extract

- `country` when Title says "Multi-country" (parse Overview HTML)
- `summary` — concise human-readable summary from Summary/Overview
- `estimated_affected` and `estimated_deaths` from Overview HTML (case counts in prose)
- `disease_details.disease_name` — standardized disease name from Title
- `disease_details.investigation_status` from Assessment
- Risk level from Assessment prose

---

## HealthMap

### Access Assessment

| Item | Value |
|------|-------|
| Public API | **None** — no documented API endpoint |
| Auth | N/A |
| Terms of Service | **Scraping explicitly prohibited** without written permission |
| Contact | info@healthmap.org |
| Viability | **Not viable** for programmatic access |

### Why HealthMap Is Not Viable

1. **No public API** — `healthmap.org/api` returns 404
2. **ToS prohibits scraping** — "Systematic retrieval of Content from the Site to create or compile a collection, compilation, database or directory is strictly prohibited"
3. **No documented data feeds** — internal AJAX/PHP endpoints are unsupported
4. **Partnership required** — 2012 precedent shows they may accommodate research projects case-by-case

### HealthMap Data Fields (For Reference)

These fields exist in HealthMap's internal system but are NOT programmatically accessible:

| Field | Description |
|-------|-------------|
| Source | ProMED, WHO, Google News, etc. |
| Date | Alert date |
| Summary | Headline/description |
| Disease | Classified disease name |
| Location | Country and sub-national location |
| Species | Human, animal, or plant |
| Cases | Case counts |
| Deaths | Death counts |
| Significance | 1-5 noteworthiness score |
| Disease Category | 12 categories (Respiratory, Gastrointestinal, etc.) |
| Alert Level | Color-coded noteworthiness |
| Activity Index | Heat rating based on alert volume |

### Recommendation: Drop HealthMap, Use Global.health Instead

**Global.health** (`global.health`) is the recommended replacement:

| Item | Value |
|------|-------|
| API | **Yes, fully documented** |
| Base URL | `https://data.covid-19.global.health/api-docs/` |
| Auth | API key required (free, via registration) |
| Data | De-identified line-list case data |
| Formats | JSON API, CSV/JSON daily exports on GitHub |
| License | MIT (code); data free for research |
| Libraries | Official Python and R packages (`globaldothealth`) |

However, Global.health requires an API key (registration), so it doesn't meet the "no auth" criterion.

### HealthMap Decision

**Drop HealthMap from the adapter list.** Replace with one of:
- **Global.health** (if API key registration is acceptable — free, takes minutes)
- **WHO DON API only** (already covers WHO disease outbreaks, no auth needed)
- **ProMED Bluesky feed** via AT Protocol API (free, no auth, JSON — but unstructured)

For now, WHO DON provides sufficient disease outbreak coverage with zero auth overhead.

---

## Adapter Comparison: WHO vs HealthMap

| Criterion | WHO DON | HealthMap |
|-----------|---------|-----------|
| API | Full OData REST | None |
| Auth | None | N/A |
| Disaster types | Disease outbreaks only | Disease outbreaks |
| Country data | Parse from Title | Structured (inaccessible) |
| Severity | Prose in Assessment | 1-5 score (inaccessible) |
| Case counts | In Overview HTML | Structured (inaccessible) |
| Update frequency | Days | Continuous |
| Historical data | 1990–present | ~30 days visible |
| Dedup key | DonId | Alert ID (inaccessible) |
| Programmatic access | **Full** | **None** |

---

## Pipeline Integration

### WHO Adapter in Pipeline

```
WHO DON API (single GET, $top=20, desc by date)
    │
    ▼  WHOAdapter._parse_response()
    │  Parse Title for country and disease name
    │  Map disaster_type = "Disease" for all records
    │
list[RawIncidentData]
    │  raw_fields = {don_id, summary, overview_html, assessment_html, ...}
    │
    ▼  Python classify()
    │  country → country_group lookup
    │  Level from WHO severity keywords (or default to 2 for DONs)
    │  Priority from PRIORITY_MATRIX
    │
ClassifiedIncident
    │
    ▼  AI enrich (summaries only)
    │  Extract case counts from Overview HTML
    │  Generate summary from Summary field
    │  Extract disease_details from Overview/Assessment
    │
EnrichedIncident → Store
```

### WHO Incident Level Mapping

WHO DON does not have a structured severity field. Mapping options:

**Option A (Python, keyword-based):**
```python
WHO_SEVERITY_KEYWORDS = {
    4: ["pandemic", "public health emergency of international concern", "international emergency"],
    3: ["epidemic", "widespread", "outbreak", "rapidly spreading"],
    2: ["cluster", "cases reported", "limited transmission"],
    1: ["isolated case", "suspected case", "under investigation"],
}
```

Scan `Summary` and `Assessment` for keywords → derive level. Deterministic, no AI.

**Option B (Default):** All WHO DONs start at Level 2 (SIGNIFICANT) — if WHO publishes a DON, it's at least notable. Override based on keyword detection or country group.

---

## Changes

| Date | Source | Change | Reason |
|------|--------|--------|--------|
| 2026-05-11 | API research | Created from live API testing | Document WHO and HealthMap findings |
