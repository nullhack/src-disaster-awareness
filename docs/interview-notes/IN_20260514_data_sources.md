# IN_20260514_data_sources — Data Sources and Uncertainty Principle

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** eol
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Who are the users? | Backend Developers, Ops Teams, Researchers. |
| Q2 | What does the product do at a high level? | Fetches incident data from free public APIs, correlates across sources, classifies deterministically, enriches with AI, stores locally. |
| Q3 | Why does it exist — what problem does it solve? | Automates multi-source disaster surveillance with deterministic classification. |
| Q4 | When and where is it used? | Scheduled CLI tool, backend batch processing. |
| Q5 | Success — what does "done" look like? | All sources fetched reliably, data correlated and classified, stored locally. |
| Q6 | Failure — what must never happen? | One source being down must not affect other sources or cause data loss. |
| Q7 | Out-of-scope — what are we explicitly not building? | Account-based API sources (ReliefWeb, HealthMap), real-time push notifications. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | How many primary data sources are there? | Three primary sources, all free, all zero-auth: GDACS, WHO DON, and GDELT. Plus one supplementary source: DuckDuckGo News. |
| Q9 | Tell me about GDACS — what does it provide? | GDACS provides GeoJSON via REST API. It's ~90% deterministic. It gives us alertlevel, iso3, eventtype, and coordinates — highly structured data. This is the most reliable source for structured fields. |
| Q10 | Tell me about WHO DON — what does it provide? | WHO Disease Outbreak News provides OData via REST API. It's only ~30% deterministic. It gives us title, date, url, and HTML content. The country, disaster type, and incident level all need extraction from the unstructured content. |
| Q11 | Tell me about GDELT — what does it provide? | GDELT provides a DOC API. It's ~20% deterministic. It gives us title, url, tone, themes, and seendate. Country and disaster type need extraction. It's the least structured primary source. |
| Q12 | What is the supplementary source and when is it used? | DuckDuckGo News via the `ddgs` package's `news()` function. It's used after the initial fetch to enrich incidents that need more context — specifically bundles where country is missing or that come from low-structure sources. DDG News returns per result: {date, title, body, url, source}. It supports multiple backends (bing, duckduckgo, yahoo) with automatic fallback. |
| Q13 | What is the determinism percentage breakdown? | GDACS is ~90% deterministic (most fields are directly available). WHO DON is ~30% (title, date, url are there but country/type/level need extraction from HTML). GDELT is ~20% (title, url, tone, themes are there but country/type need extraction). |
| Q14 | What is the "uncertainty principle"? | We can't be certain about exact field availability from any source until we call the APIs and inspect real responses. All raw data must be preserved verbatim in `RawRecord.raw_fields`. Classification and AI extraction work with whatever fields are available, falling back gracefully when fields are missing. Every adapter must capture the full raw response unmodified. |
| Q15 | How does the system handle missing or unreliable fields? | It falls back gracefully. The classification engine tries each source's raw_fields in order of reliability (GDACS > WHO > GDELT > DDG-NEWS). It extracts whatever is available and falls back to AI for missing fields. No normalization happens at the raw record layer. |

## Feature: Source-Specific Raw Fields

| ID | Question | Answer |
|----|----------|--------|
| Q16 | What does a GDACS raw_fields look like? | {title, description, alertlevel, eventtype, iso3, latitude, longitude, ...} — but this is subject to change after seeing real responses. |
| Q17 | What does a WHO raw_fields look like? | {title, url, date, content_html, ...} — subject to change after seeing real responses. |
| Q18 | What does a GDELT raw_fields look like? | {title, url, seendate, tone, themes, ...} — subject to change after seeing real responses. |
| Q19 | What does a DDG-NEWS raw_fields look like? | {date, title, body, url, source}. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reliability | Any source API down — other sources unaffected, no data loss | Graceful degradation per source | Must |
| QA2 | Reliability | AI timeout/failure — incident stored without enrichment | Partial data always stored | Must |

---

## Pain Points Identified

- Field availability varies wildly across sources (90% vs 30% vs 20% determinism)
- WHO and GDELT require extraction from unstructured text
- Cannot predict exact API response shapes until real calls are made
- Need to preserve raw data because field availability is uncertain

## Business Goals Identified

- Use only free, zero-auth sources to avoid vendor lock-in and cost
- Correlate across sources to compensate for individual source weaknesses
- Preserve all raw data for future reprocessing

## Terms to Define (for glossary)

- GDACS (Global Disaster Alert and Coordination System)
- WHO DON (Disease Outbreak News)
- GDELT (Global Database of Events, Language, and Tone)
- DDG News (DuckDuckGo News)
- Determinism percentage
- Uncertainty principle
- raw_fields
- Zero-auth API
- OData
- GeoJSON
- DOC API

## Action Items

- [ ] Run capture_fixtures.py against all APIs to validate assumed field shapes
- [ ] Confirm determinism percentages after inspecting real responses
- [ ] Verify DDG News fallback backends work as expected
