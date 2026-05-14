# IN_20260511_gdelt_research — GDELT Project API Research

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** Stakeholder (domain expert)
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Why consider GDELT for news monitoring? | Stakeholder wanted a free, no-auth source for global news monitoring to detect disasters. GDELT is a purpose-built global event database (15+ years running) that processes news from 100+ languages, updated every 15 minutes. |
| Q2 | What is the GDELT Project? | Global Database of Events, Language, and Tone — a massive, open news monitoring database. Ingests global news, classifies articles with themes (300+ categories), assigns tone/sentiment scores, and provides multiple free APIs. |
| Q3 | What GDELT APIs are relevant for disaster surveillance? | (A) **DOC API** — keyword + theme search returning article metadata (URL, title, date, domain, language, tone, themes). Best for our adapter. (B) **GKG GeoJSON** — georeferenced news mentions with lat/lng. Good for mapping active disasters. (C) **BigQuery** — unlimited polling at Google infrastructure scale. Best for production. |
| Q4 | How does GDELT compare to DDGS? | GDELT is superior in almost every way for news monitoring: purpose-built database (not a scraper), theme classification (not keyword guessing), tone scoring (automated severity triage), 15+ year track record, BigQuery for production. DDGS remains useful as a lightweight alternative if BigQuery setup is too heavy. |
| Q5 | What Python library to use? | `gdeltdoc` (v1.12.0, `pip install gdeltdoc`). Wraps the DOC API. Returns pandas DataFrames. Supports keyword, theme, date, country, domain, and geographic proximity filters. |
| Q6 | What is the key insight about CAMEO codes? | Traditional CAMEO event codes (01-20) cover political conflict only — they do NOT cover natural disasters. You must use **GKG Themes** (e.g., `NATURAL_DISASTER_EARTHQUAKE`, `NATURAL_DISASTER_FLOOD`) for disaster filtering. CAMEO+ codes with environmental domains exist only in the commercial GDELT Cloud. |

---

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q7 | What natural disaster themes does GDELT provide? | `NATURAL_DISASTER_EARTHQUAKE`, `NATURAL_DISASTER_FLOOD`, `NATURAL_DISASTER_TROPICAL_CYCLONE`, `NATURAL_DISASTER_VOLCANO`, `NATURAL_DISASTER_TSUNAMI`, `NATURAL_DISASTER_WILDFIRE`, `NATURAL_DISASTER_DROUGHT`, `NATURAL_DISASTER_LANDSLIDE`, `NATURAL_DISASTER_EXTREME_WEATHER`, plus parent theme `NATURAL_DISASTER`. |
| Q8 | What disease/health themes? | `HEALTH_PANDEMIC`, `HEALTH_EPIDEMIC`, `HEALTH_OUTBREAK`, `HEALTH_DISEASE`, `WB_2284_DISASTER_RISK_MANAGEMENT`, `UNGP_EPIDEMIC_PREPAREDNESS`. |
| Q9 | What humanitarian themes? | `HUMANITARIAN_CRISIS`, `HUMANITARIAN_AID`, `REFUGEE`, `FOOD_SECURITY`, `WATER_CRISIS`. |
| Q10 | How does tone scoring work? | GDELT assigns tone scores per article: `tone = tone_positive - tone_negative`. Negative values indicate negative sentiment (disaster, crisis). Use tone as a severity triage signal: tone < -5.0 = likely severe disaster. |
| Q11 | What is the tone triage rule? | `< -5.0`: Strongly negative — likely severe disaster with high casualties or major damage. `-2.0 to -5.0`: Moderately negative — disaster with impacts. `> -2.0`: Mild or neutral — background reporting, political/response articles, recovery stories (filter out tone > 0). |
| Q12 | What fields does each DOC API article return? | `url`, `title`, `seendate` (YYYYMMDDHHMMSS), `domain` (e.g., "reuters.com"), `language`, `sourcecountry`, `tonepositive`, `tonenegative`, `tone`, `socialimage`, `themes` (list of GKG theme strings). |
| Q13 | How fresh is the data? | GDELT ingests news every 15 minutes. The `seendate` field records when GDELT first saw the article. DOC API queries with `timespan=15min` return only new articles. |
| Q14 | What are the DOC API rate limits? | Free REST API: ~100 requests/day (observed), no formal SLA. For production polling every 15 minutes, this is insufficient (96 queries/day minimum). Use BigQuery for sustained polling — 1 TB/month free tier, unlimited queries. |
| Q15 | How does BigQuery access work? | Table: `gdelt-bq.gdeltv2.gkg_partitioned`. Queries ~15-20 GB/day for recent data. Needs `google-cloud-bigquery` Python package + Google Cloud project. 1 TB/month free tier is ample for disaster surveillance. |

---

## Feature: gdelt-adapter

| ID | Question | Answer |
|----|----------|--------|
| Q16 | Should GDELT be primary or secondary? | **Secondary** for disaster alerts, **primary** for news monitoring. GDACS and WHO DON are authoritative for specific disaster/disease types. GDELT is the best general news monitor — it catches everything else. |
| Q17 | Should we use the DOC API or BigQuery? | **Both.** DOC API for lightweight development/testing. BigQuery for production. The adapter should support both backends with the same `SourceAdapter.fetch()` interface. |
| Q18 | How to filter by country? | `gdeltdoc` supports `country` filter with ISO alpha-2 codes. For the DOC API: append country filter to the query string. For BigQuery: use `REGEXP_CONTAINS(V2Locations, ...)` on location fields. |
| Q19 | How to dedup across cycles? | URL is the natural dedup key. The same URL never appears twice in GDELT's DOC API output for the same time window. Use URL hash + `seendate` for freshness. |
| Q20 | How to handle theme false positives? | GDELT theme assignment has false positives (ONS UK study confirmed). Mitigation: (1) Filter by tone < -2.0 to exclude non-crisis articles. (2) Validate article title against disaster keywords. (3) Cross-reference with GDACS/WHO DON for known events. (4) Prioritize disaster-focused source domains (reliefweb.int, reuters.com). |
| Q21 | How many queries per cycle? | **One query per cycle** with theme filter `NATURAL_DISASTER` catches all disaster types. No need to query per country or per disaster type — GDELT's theme taxonomy handles this server-side. Post-filter by country in Python. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Zero-Auth Access | When adapter is deployed, no API key or registration needed | Works immediately with no configuration | Must |
| QA2 | 15-Minute Freshness | When a disaster is reported in global news, GDELT captures it within one poll cycle | Article fetched within 15 minutes of GDELT ingestion | Must |
| QA3 | Disaster Type Coverage | When any natural disaster is reported, the adapter captures it regardless of type | All 10 disaster themes detected in one query | Must |
| QA4 | Tone Triage | When an article is strongly negative (tone < -5.0), it's flagged for urgent review | Escalation signal generated in the classify step | Should |
| QA5 | False Positive Filtering | When an article is tagged with a disaster theme but is not about an active disaster, it's filtered out | < 5% false positive rate in stored incidents | Should |
| QA6 | BigQuery Reliability | When the free DOC API is rate-limited, the BigQuery backend continues without interruption | No data loss during DOC API rate limiting | Should (for production) |

---

## Pain Points Identified

- Free DOC API has informal rate limits (~100 req/day) — not enough for 15-min polling
- CAMEO codes don't cover natural disasters — theme-based filtering is mandatory
- Theme classification has false positives — need post-filtering by tone and title validation
- Country is not a structured article field — must derive from query filter or title parsing
- No article body/snippet — only metadata (title + themes + tone). Need DDGS or `extract()` for content.
- BigQuery requires Google Cloud project setup — adds deployment complexity
- GDELT Cloud (CAMEO+ codes, better disaster classification) is commercial/paid

## Business Goals Identified

- Establish GDELT as the primary general news monitoring source for disaster surveillance
- Use theme-based filtering to catch all disaster types in a single query
- Use tone scoring for automated severity triage
- Deploy with BigQuery for reliable, unlimited production polling
- Cross-reference GDELT detections with GDACS/WHO DON for authoritative confirmation
- Where GDELT crosses DDGS: GDELT for structured news monitoring; DDGS for on-demand content retrieval

## Terms to Define

- `GDELT` — Global Database of Events, Language, and Tone, an open global news monitoring project
- `GKG` — Global Knowledge Graph, GDELT's classification taxonomy with 300+ themes
- `GKG Theme` — A classification tag assigned to each article (e.g., `NATURAL_DISASTER_EARTHQUAKE`)
- `CAMEO` — Conflict and Mediation Event Observations — event codes for political events (NOT natural disasters)
- `Tone` — GDELT's sentiment score per article (positive – negative)
- `DOC API` — GDELT's Document API for keyword/theme article search
- `gdeltdoc` — Python library wrapping the DOC API, returns pandas DataFrames
- `seendate` — Timestamp when GDELT first saw the article (YYYYMMDDHHMMSS format)

## Action Items

- [x] Research GDELT APIs — DOC, GKG GeoJSON, BigQuery confirmed viable
- [x] Document 10 natural disaster themes + 7 disease/health themes
- [x] Document tone scoring as severity triage signal
- [x] Document CAMEO vs GKG Theme distinction (critical finding)
- [x] Document `gdeltdoc` Python library API
- [x] Compare GDELT vs DDGS — GDELT recommended as primary news source
- [ ] Implement GDELTAdapter with DOC API backend (theme filter, 15-min window)
- [ ] Add tone-based severity triage logic
- [ ] Add GDELT BigQuery backend as production option
- [ ] Add domain-based false positive filtering
- [ ] Update adapter_specification.md with GDELT findings
- [ ] Update source lineup: GDACS (primary) + WHO DON (primary) + GDELT (secondary) + DDGS (content retrieval)
