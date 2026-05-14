# IN_20260511_who_healthmap_research — WHO and HealthMap API Research

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** Stakeholder (domain expert)
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Why focus on WHO and HealthMap? | Both were identified as "no auth required" sources. The stakeholder wants to prioritize adapters that can be used immediately without registration or API keys. |
| Q2 | What did we find for WHO? | WHO Disease Outbreak News (DON) has a fully open OData REST API at `https://www.who.int/api/hubs/diseaseoutbreaknews`. No auth, no rate limits, JSON responses. ~3,179 records from 1990 to present. Updated within days of events. |
| Q3 | What did we find for HealthMap? | **Not viable.** No public API. ToS explicitly prohibits scraping. Internal AJAX endpoints are undocumented and unsupported. Would need a partnership agreement with Boston Children's Hospital. |
| Q4 | What's the decision? | Proceed with WHO DON adapter. Drop HealthMap. If a second disease source is needed, consider Global.health (free API key, takes minutes to register) or ProMED Bluesky feed (free, no auth). |
| Q5 | What can Python extract from WHO without AI? | `incident_name` from Title, `country` from Title (single-country cases, e.g. "Measles - Bangladesh"), `disaster_type` = "Disease" (all WHO DONs are disease outbreaks), `report_date` from PublicationDateAndTime, `source_url` from ItemDefaultUrl, dedup via DonId. |
| Q6 | What needs AI from WHO? | Country extraction when Title says "Multi-country" (parse Overview HTML). Summary generation from Summary/Overview. Case count extraction from Overview HTML. Standardized disease name from Title. Investigation status from Assessment. |

---

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q7 | What WHO API endpoints exist? | (A) Disease Outbreak News API: `https://www.who.int/api/hubs/diseaseoutbreaknews` — primary, real-time outbreaks. (B) Emergency Events API: `https://www.who.int/api/hubs/emergencyevents` — coarser-grained emergency records. (C) Global Health Observatory (GHO) API: `https://ghoapi.azureedge.net/api/` — annual statistical indicators, NOT real-time. Focus on DON API. |
| Q8 | What are the WHO DON fields? | DonId (unique), Title (e.g. "Measles - Bangladesh"), PublicationDateAndTime (ISO 8601), Summary (plain text), Overview (HTML — case counts, geography), Assessment (HTML — risk), Advice (HTML), Epidemiology (HTML), Response (HTML), UrlName, ItemDefaultUrl, DateCreated, LastModified. |
| Q9 | How to determine incident level from WHO? | No structured severity field. Two options: (A) Keyword scanning of Summary/Assessment for severity words (pandemic→4, epidemic→3, cluster→2, isolated→1). (B) Default all DONs to Level 2 — if WHO publishes a DON, it's at least notable. Recommend Option A with Level 2 fallback. |
| Q10 | How does WHO compare to GDACS for disease data? | WHO DON covers disease outbreaks only. GDACS covers earthquakes, cyclones, floods, volcanoes, droughts, wildfires. They are complementary, not competing. WHO is the authoritative source for disease emergencies; GDACS for natural disasters. |
| Q11 | What about the WHO Emergency Events API? | Less actively maintained than DON. Provides coarser "Cholera" as a named emergency rather than individual outbreak reports. Use DON as primary. |
| Q12 | What polling interval for WHO? | 6 hours. WHO publishes within days, not minutes. More frequent polling wastes resources. Query: `$top=20&$orderby=PublicationDateAndTime desc` gets the last 20 DONs. |

---

## Feature: who-adapter

| ID | Question | Answer |
|----|----------|--------|
| Q13 | Should we implement both WHO DON and Emergency Events? | No. Focus on DON API only. It's the real-time, structured, actively maintained source. Emergency Events is supplementary. |
| Q14 | How to handle "Multi-country" in WHO titles? | Python sets country to "Unknown". The AI enrich step parses Overview HTML for actual affected countries. Override O2 (Multi-Regional Impact) triggers automatically. |
| Q15 | What about WHO Regional RSS feeds? | WHO AFRO and EMRO have RSS feeds but they're limited and unstructured. The DON API is superior — JSON, filterable, paginated. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Zero-Auth Access | When adapter is deployed, no API key or registration needed | Works immediately with no configuration | Must |
| QA2 | Data Completeness | When WHO publishes a DON, the adapter captures it within one poll cycle | All DONs with DonId, Title, Date, Summary captured | Must |
| QA3 | HTML Tolerance | When WHO changes HTML structure in Overview/Assessment, the adapter doesn't crash | Graceful degradation — raw HTML stored in raw_fields | Should |
| QA4 | Dedup Reliability | When the same DON is fetched twice, it produces one incident | DonId used as dedup key | Must |

---

## Pain Points Identified

- HealthMap was in the original design but has no viable programmatic access
- WHO embeds country in Title text, not a separate field — requires parsing
- WHO content fields are HTML, not plain text — needs sanitization
- No standardized disease names — WHO uses free-text in titles
- No explicit severity/scale field — must infer from keywords

## Business Goals Identified

- Establish WHO DON as the primary disease outbreak source (zero auth, structured API)
- Drop HealthMap from the adapter list (no viable access path)
- Define clear Python-vs-AI split: Python extracts structured fields, AI handles HTML content parsing
- Document the WHO field mapping so the adapter implementation is straightforward

## Terms to Define

- `WHO DON` — Disease Outbreak News, WHO's official publication for disease events meeting IHR criteria
- `DonId` — Unique identifier for a WHO Disease Outbreak News report (e.g., "2026-DON600")
- `OData` — Open Data Protocol, REST API standard used by WHO's Sitefinity CMS
- `Global.health` — Open disease data platform with free API (potential HealthMap replacement)

## Action Items

- [x] Research WHO DON API — confirmed open OData API, no auth, structured JSON
- [x] Research HealthMap API — confirmed no public API, ToS prohibits scraping
- [ ] Implement WHOAdapter with DonId dedup, Title parsing, $top=20 polling
- [ ] Add WHO severity keyword mapping for incident_level derivation
- [ ] Add HTML sanitization for Overview/Assessment fields
- [ ] Drop HealthMapAdapter from codebase (replace with placeholder or remove)
- [ ] Evaluate Global.health as HealthMap replacement (requires free API key)
- [ ] Update adapter_specification.md with WHO and HealthMap findings
