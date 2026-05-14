# Global.health API Research Report

**Date:** 2026-05-11
**Sources:** global.health, GitHub (globaldothealth), web searches

---

## 1. API Base URL & Access

Global.health has **two distinct access mechanisms**:

### A. Programmatic Data Download (Python/R SDK)
- **Base URL pattern:** `https://data.<disease>.global.health/`
  - COVID-19: `https://data.covid-19.global.health/`
  - Mpox (archived 2022): `https://data.monkeypox.global.health/` (was `https://www.monkeypox.global.health`)
  - Avian Influenza 2024: `https://data.influenza-2024.global.health/` (linked as `https://data.global.health/`)
  - Each pathogen/outbreak gets its own data portal instance
- **API docs (Swagger):** `https://data.covid-19.global.health/api-docs/` (currently returning transport errors; may be intermittent)
- **Download endpoint:** Returns paginated case data (CSV or JSON)

### B. Underlying REST API (Curator/Data Services)
- MongoDB-backed microservices architecture
- **Data service:** CRUD operations on case data (Node.js/TypeScript)
- **Curator service:** Backend for the curator portal, manages sources and ingestion
- **Geocoding service:** Location geocoding
- API docs available for curator service and data service (linked from repo dev docs)

### C. Bulk Downloads
- Daily CSV exports available from data portals
- Mpox CSV: `https://7rydd2v2ra.execute-api.eu-central-1.amazonaws.com/web/url?folder=&file_name=latest.csv`
- HDX (Humanitarian Data Exchange): 5 datasets published at https://data.humdata.org/organization/e9b9990b-d955-4895-a568-dc14e7939b76
- Outbreak-data wiki: links to line list and timeseries datasets per outbreak

---

## 2. Authentication

- **API Key required** for programmatic access
- **Free to obtain:** Register an account at the relevant data portal (e.g., `https://data.covid-19.global.health`), then go to Profile > Reset API Key
- The key is unique per user and tied to your account
- Key is passed in requests (likely as a header or query parameter)
- **No account needed** to browse the website, explore outbreak data, or use tools
- **Account needed** to access the curator portal (100M+ COVID-19 records)
- Platform is free for research purposes under CC-BY-4.0 license

---

## 3. Data Provided

### Disease Types Tracked (as of 2026)
| Disease | Period | Status | Geographic Scope |
|---------|--------|--------|-----------------|
| COVID-19 | Jan 2020 - Dec 2023 | Inactive (completed) | Global (142+ countries, 100M+ cases) |
| Mpox (2022) | Apr 2022 - Sep 2022 | Inactive | Global |
| Mpox (2024) | Jan 2024 - Dec 2024 | Inactive | Multicountry (Africa focus) |
| Ebola | Aug 2022 - Nov 2022 | Inactive | Uganda |
| Marburg | Jan 2023 - Apr 2023 | Inactive | Equatorial Guinea |
| Avian Influenza (H5N1) | Feb 2024 - Jul 2025 | Inactive (last human case Feb 2025) | USA |

### Geographic Coverage
- COVID-19: 142+ countries globally
- Other outbreaks: specific to the outbreak region
- **Asia Pacific + MENA coverage exists primarily through COVID-19 data** (Jan 2020 - Dec 2023)

### Date Ranges
- COVID-19: January 2020 through December 2023 (no longer updated)
- Other outbreaks: limited to specific outbreak periods
- Data is **not continuously updated** for all diseases - only during active outbreak responses

### Data Types
- **Line-list data:** Individual anonymized case records (primary product)
- **Timeseries data:** Available for some outbreaks via wiki
- **Aggregate data:** Used when line-list is unavailable
- **Maps and visualizations:** Interactive maps with data overlays

---

## 4. Rate Limits

- **Not explicitly documented** in publicly available materials
- The programmatic access endpoint paginates results (batches)
- Large country datasets can take considerable time to download
- Caching is recommended and built into both Python and R libraries
- No mention of specific requests-per-second or daily limits in documentation

---

## 5. Outbreaks/Diseases Tracked

### Current approach: "First 100 Days" Mission
Global.health focuses on **early-phase outbreak response** (first 100 days). Their stated mission: *"enable rapid sharing of trusted and open public health data to advance the response to infectious disease during the early phase of an outbreak, for the first 100 days, when the chance for containment is highest."*

### What they DO track:
- Active emergent outbreaks where they can add value
- Line-list case data curated from official sources
- They track specific outbreaks, not continuous surveillance of all diseases

### What they DO NOT track (as of May 2026):
- **Cholera** - not tracked
- **Measles** - not tracked
- **Dengue** - not tracked (though DART tool focuses on dengue climate analysis)
- **Malaria** - not tracked
- **Routine/endemic diseases** - not tracked
- **Continuous real-time surveillance** - not provided

The platform is **event-driven** (responds to specific outbreaks) rather than providing ongoing surveillance of known endemic diseases.

---

## 6. Data Currency / Freshness

| Outbreak | Update Frequency | Current Status |
|----------|-----------------|----------------|
| COVID-19 | Was daily, now frozen | Last updated Dec 2023 |
| Mpox 2024 | Was daily (refreshed at midnight UTC) | Frozen as of Dec 2024 |
| Avian Influenza | Was actively curated | Frozen Jul 2025 |

- Data is **NOT real-time**. It is curated with delays.
- Active outbreaks get daily refreshes during the response period
- After the "100 day mission" completes, data is frozen and archived
- **As of May 2026, no outbreak data is being actively updated**
- The DART tool for dengue analysis uses external data sources, not G.h line-list data

---

## 7. Python SDK/Library

### Official Python Access: `gdh.py`
- **Location:** `https://github.com/globaldothealth/list/tree/main/api/` (Python subdirectory, file may have been reorganized)
- **Not a pip-installable package** - it's a standalone script
- **Dependencies:** `requests`, `pandas`
- **Installation:** Download the `gdh.py` file manually

### Usage:
```python
from gdh import GlobalDotHealth

key = "YOUR_API_KEY"
# Initialize with disease name
covid = GlobalDotHealth(key, 'covid-19')

# Get cases by country (ISO 3166-1 two-letter codes)
cases_nz = covid.get_cases(country="NZ")

# With caching (recommended for large datasets)
cases_cached = covid.get_cached_cases(country="NZ")
cases_refreshed = covid.get_cached_cases(country="NZ", refresh=True)
```

### Filtering
- Currently supports **country filtering only** (ISO 3166-1 two-letter codes)
- No date range, disease, or field-level filtering in the SDK

### R Package
```r
devtools::install_github("globaldothealth/list/api/R")
library(globaldothealth)
key <- "API_KEY"
cases <- get_cases(key, country = "NZ")
```

### Other Tools
- **InsightBoard** (`pip install InsightBoard`): Dashboard for uploading, managing, and visualizing data
- **adtl** (`pip install adtl`): Schema-based data transformation library
- **DART**: Pipeline for dengue climate analysis (separate tool, not API access)

---

## 8. Data Format

- **Primary format: CSV** (`.csv`, `.csv.gz` for compressed)
- **Also available: JSON** (download or API)
- Line-list data downloads are CSV by default
- API responses are JSON
- Mpox 2022 had both JSON and CSV archives in timestamped files

---

## 9. Structured Fields Per Record (76 fields from Data Dictionary)

### Metadata (6 fields)
| Field | Description |
|-------|-------------|
| `_id` | Internal database ID (not stable) |
| `caseReference.sourceId` | Unique source ID |
| `caseReference.sourceUrl` | URL of data source |
| `caseReference.uploadIds` | Upload IDs that updated this case |
| `caseReference.verificationStatus` | VERIFIED / UNVERIFIED / EXCLUDED |
| `caseReference.additionalSources` | Additional source URLs |

### Demographics (6 fields)
| Field | Description |
|-------|-------------|
| `demographics.ageRange.start` | Lower age (0-120) |
| `demographics.ageRange.end` | Upper age (0-120) |
| `demographics.gender` | Male / Female / Non-binary / Other |
| `demographics.ethnicity` | Ethnicity |
| `demographics.nationalities` | Nationalities |
| `demographics.occupation` | Occupation |

### Events (10 fields)
| Field | Description |
|-------|-------------|
| `events.confirmed.date` | Confirmation date (YYYY-MM-DD) |
| `events.confirmed.value` | Confirmation method |
| `events.onsetSymptoms.date` | Symptom onset date |
| `events.hospitalAdmission.date` | Hospital admission date |
| `events.hospitalAdmission.value` | Yes / No |
| `events.icuAdmission.date` | ICU admission date |
| `events.icuAdmission.value` | Yes / No |
| `events.outcome.date` | Outcome date |
| `events.outcome.value` | Death / Recovered / Unknown |
| `events.firstClinicalConsultation.date` | First clinical consult |

### Location (9 fields)
| Field | Description |
|-------|-------------|
| `location.country` | Country (required) |
| `location.administrativeAreaLevel1` | State/province |
| `location.administrativeAreaLevel2` | District |
| `location.administrativeAreaLevel3` | City |
| `location.geoResolution` | Country / Admin1 / Admin2 / Admin3 / Point |
| `location.geometry.latitude` | Latitude |
| `location.geometry.longitude` | Longitude |
| `location.name` | Full location name |
| `location.place` | Place name (e.g., hospital) |

### Symptoms (2 fields)
- `symptoms.status`: Asymptomatic / Symptomatic / Presymptomatic
- `symptoms.values[]`: List of symptoms

### Pre-existing Conditions (2 fields)
- `preexistingConditions.hasPreexistingConditions`: Boolean
- `preexistingConditions.values[]`: List of conditions

### Transmission (3 fields)
- `transmission.linkedCaseIds[]`: Related case UUIDs
- `transmission.places[]`: Transmission locations
- `transmission.routes[]`: Transmission routes

### Travel History (12 fields)
- Travel dates, locations (admin levels 1-3), country, coordinates, methods, purpose
- `travelHistory.traveledPrior30Days`: Boolean

### Vaccines (16 fields)
- Up to 4 vaccines tracked: batch, date, name, side effects

### Other
- `pathogens[]`: Other pathogens
- `variantOfConcern`: Pango lineage (COVID-19)
- `SGTF`: S-Gene Target Failure (COVID-19)
- `revisionMetadata`: Creation/edit dates, notes, revision number

---

## 10. Suitability Assessment for Disaster Monitoring (Asia Pacific + MENA)

### Overall Rating: **POOR to MODERATE** (with significant caveats)

### Strengths
- **Rich case-level data schema:** 76 fields per record with demographics, location (geocoded), symptoms, outcomes, transmission, travel history, and vaccination status
- **Open and free:** CC-BY-4.0 license, free API key, no subscription costs
- **Well-structured data:** Standardized schema across diseases, geocoded locations
- **Open-source tools:** Python/R access, InsightBoard, DART pipeline
- **Trusted data:** Peer-reviewed methodology (published in Nature Scientific Data), curated from authoritative government sources
- **Proven track record:** COVID-19 data for 142+ countries used by major research institutions

### Critical Weaknesses for Disaster Monitoring

1. **No ongoing surveillance of endemic diseases:**
   - Does NOT track cholera, measles, dengue, malaria, or other endemic diseases
   - Focused on emergent outbreaks during the "first 100 days"
   - Asia Pacific and MENA have ongoing cholera, dengue, and measles outbreaks that G.h does not cover

2. **No current active data feeds (as of May 2026):**
   - All tracked outbreaks are frozen/inactive
   - COVID-19 frozen since Dec 2023
   - Avian influenza frozen since Jul 2025
   - No guarantee of rapid activation for future outbreaks

3. **Not real-time:**
   - Data is curated with delays (hand-curated)
   - Daily refresh at best during active outbreaks
   - Not suitable for real-time disaster monitoring dashboards

4. **Limited geographic filtering for non-COVID diseases:**
   - Non-COVID outbreaks have narrow geographic scope (e.g., Ebola in Uganda only)
   - COVID-19 has global coverage but is frozen

5. **No multi-disease surveillance:**
   - Cannot query across multiple diseases simultaneously
   - Each outbreak has a separate data portal and dataset
   - No unified "all outbreaks" API endpoint

6. **No predictive or alerting capabilities:**
   - Historical/curated data only
   - No alerting, threshold monitoring, or anomaly detection

### When It WOULD Be Useful
- **During a new emergent outbreak** in the first 100 days, if G.h activates a response
- **Historical analysis** of COVID-19 patterns in Asia Pacific and MENA (2020-2023)
- **As a supplementary source** alongside WHO, ProMED, GPHIN, or HealthMap for line-list detail
- **Schema reference** for designing a disease surveillance data model (the 76-field schema is well-designed)

### Recommended Complementary Sources for Asia Pacific + MENA
| Source | What It Covers | Why Needed |
|--------|---------------|------------|
| WHO EIOS / EWARS | All notifiable diseases, real-time | Continuous surveillance |
| ProMED-mail | Emerging infectious diseases | Event-based surveillance |
| GPHIN (Global Public Health Intelligence Network) | Disease events worldwide | Early warning |
| HealthMap | Real-time disease surveillance | Multi-disease monitoring |
| WHO WER (Weekly Epidemiological Record) | Cholera, measles, dengue weekly | Endemic disease trends |
| ECDC Surveillance Atlas | Cholera, dengue, measles | European perspective on global diseases |
| HDX (Humanitarian Data Exchange) | Multiple disease datasets | Humanitarian crisis context |
| GDDOCs (WHO) | Disease outbreak news | Official WHO reports |

---

## Summary

Global.health is an excellent source for **detailed, structured line-list case data** during the early phase of specific outbreaks. It provides rich epidemiological metadata (76 fields) under an open license with Python/R programmatic access. However, it is fundamentally an **event-driven outbreak response platform**, not a continuous disease surveillance system. For a disaster monitoring system covering Asia Pacific and MENA, it would be a **valuable supplementary data source** during active emergent outbreaks but **cannot serve as the primary surveillance backbone** due to its lack of ongoing endemic disease tracking, real-time updates, and multi-disease coverage.
