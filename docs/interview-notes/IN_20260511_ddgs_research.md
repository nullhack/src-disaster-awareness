# IN_20260511_ddgs_research — DDGS (Metasearch) API Research

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** Stakeholder (domain expert)
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Why consider DDGS for news monitoring? | Stakeholder wanted a free, no-auth Python alternative for general web/news search to check for disaster events not covered by official APIs (GDACS, WHO). DDGS emerged as a viable metasearch library. |
| Q2 | What is DDGS? | `ddgs` (PyPI, v9.14.2) is a Python metasearch aggregator that scrapes Bing, Yahoo, DuckDuckGo, and other search engines. It has a dedicated `news()` method that returns article headlines, snippets, dates, URLs, and sources. MIT licensed, actively maintained (weekly releases, 2.6k GitHub stars). |
| Q3 | What are the key DDGS methods for surveillance? | `news()` — primary, returns news articles with metadata. `text()` — web search fallback (no date/source fields). `extract()` — fetches full URL content for a specific article. |
| Q4 | What does `news()` return? | Six fields per result: `date` (ISO 8601, may be empty), `title` (headline), `body` (snippet, ~300 chars), `url` (canonical), `image` (may be empty), `source` (publisher name). |
| Q5 | How to filter by recency? | `timelimit="d"` for past 24 hours, `"w"` for past week, `"m"` for past month. For 15-minute cycles, use `timelimit="d"` and dedup by URL. |
| Q6 | How to filter by region/country? | `region` parameter uses `{country}-{language}` codes. 50+ regions available including Philippines (`ph-en`), Indonesia (`id-id`), Japan (`jp-jp`), India (`in-en`), Thailand (`th-th`), Vietnam (`vn-vi`), Turkey (`tr-tr`), Middle East (`xa-ar`, `xa-en`). |
| Q7 | Which countries lack region codes? | Myanmar, Nepal, Sri Lanka, Iran, Egypt, Iraq, Saudi Arabia, Afghanistan, Pacific Island nations. Workaround: use `wt-wt` (global) region and include country name in the query string. |
| Q8 | What are the rate limits? | ~10-20 requests/minute without proxy. ~30-60 req/min with Tor (`proxy="tb"`). Library has `RatelimitException` for HTTP 202/429 responses. Exponential backoff recommended. |

---

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q9 | What backends does `news()` use? | Bing, Yahoo, and DuckDuckGo. `backend="auto"` tries all. For disaster surveillance, use `backend="bing,yahoo"` explicitly — Bing has best metadata and region filtering. |
| Q10 | How to build effective disaster queries? | Combine disaster term + country name: `"earthquake Philippines"`, `"flood Bangladesh"`. Use `+` operator to require terms: `cyclone +warning`. Use `-` to exclude false positives: `earthquake -movie`. |
| Q11 | What disaster types can DDGS detect? | Keyword-dependent. Effective for: earthquake, flood, cyclone/typhoon, tsunami, volcano, landslide, outbreak, epidemic, drought, heatwave, wildfire, storm. Not pre-classified — must parse titles. |
| Q12 | How to dedup across cycles? | MD5 hash of the `url` field. URL is the most stable dedup anchor. Titles/body text can change on article updates. |
| Q13 | Is DDGS reliable for production? | **Moderate.** It's a scraper (unofficial), not an API. Backends can change HTML, causing empty results. Library is actively maintained (weekly releases) but legal gray area — disclaimer says "for educational purposes only." |
| Q14 | What's the plan for production? | For polling every 15 minutes: 1-2 queries per cycle is safe without proxy. With Tor/proxy rotation: 5-10 queries. Use 3-retry exponential backoff on rate limits. Fall back to `text()` if `news()` returns empty for critical regions. |

---

## Feature: ddgs-adapter

| ID | Question | Answer |
|----|----------|--------|
| Q15 | Should DDGS be a primary or secondary source? | **Secondary.** DDGS is a supplementary news monitor. Official APIs (GDACS, WHO DON, ReliefWeb) are primary sources. DDGS catches breaking news that official feeds miss or delay — especially for disaster types with no global monitoring API (floods, landslides, heatwaves). |
| Q16 | How many regions should we query per cycle? | Rotate through Group A countries: 5-8 regions per 15-minute cycle, 2-3 disaster terms per region. Covers all Group A countries over 3 cycles (45 minutes). |
| Q17 | What Python dedup logic? | Hash `url` field. Store seen URLs in an in-memory set with 24-hour expiry window. If `date` field is empty, use `retrieved_at` for freshness. |
| Q18 | What's the country extraction strategy? | Primary: `region` parameter maps to a country name. Secondary: parse `title` for country mentions when region is global (`wt-wt`). AI enrichment (not Python) handles country disambiguation from title text. |
| Q19 | How to handle non-English results? | Asia-Pacific regions (`id-id`, `vn-vi`, `cn-zh`, `th-th`, `jp-jp`) return local-language results. Store them in `raw_fields` for AI translation. The adapter doesn't translate — that's the AI enrich step. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Zero-Auth Access | When adapter is deployed, no API key or registration needed | Works immediately with no configuration | Must |
| QA2 | Graceful Degradation | When a backend (Bing/Yahoo) returns empty, the adapter falls back to the next backend | Never crashes, never returns empty for a known-populated region | Must |
| QA3 | Rate-Limit Resilience | When backends rate-limit, the adapter retries and eventually succeeds or returns partial results | 3 retries with exponential backoff; never blocks the pipeline | Must |
| QA4 | Dedup Accuracy | When the same article appears in two polling cycles, it produces one incident | URL-based dedup with 24-hour retention | Must |
| QA5 | Freshness | When a disaster occurs, DDGS detects news within 1-2 polling cycles | Article captured within 30 minutes | Should |

---

## Pain Points Identified

- DDGS is a scraper, not an official API — risk of breaking if search engine HTML changes
- No geolocation/coordinates in results — can't map disaster locations
- No severity classification — must parse title/body text for magnitude/intensity
- `date` field can be empty — must fall back to `retrieved_at` timestamp
- Countries without region codes (Iran, Myanmar, Nepal, etc.) have poor coverage
- Library disclaimer says "educational purposes only" — legal gray area for production
- Rate limiting varies by backend and is not documented
- Non-English results in regional queries need translation

## Business Goals Identified

- Provide a free, zero-auth news monitoring capability for disaster surveillance
- Catch breaking disaster news that official APIs miss or delay
- Cover disaster types with no dedicated monitoring API (floods, landslides, heatwaves)
- Enable language-specific monitoring for Asia-Pacific local media
- Keep the adapter simple — DDGS handles the complexity of scraping multiple backends

## Terms to Define

- `DDGS` — Dux Distributed Global Search, a Python metasearch library (PyPI package `ddgs`)
- `Metasearch` — Search that aggregates results from multiple search engines
- `Region code` — `{country}-{language}` code used by search engines for geographic filtering
- `RatelimitException` — DDGS exception raised when backends return HTTP 202/429
- `Backend` — The underlying search engine DDGS scrapes (Bing, Yahoo, DuckDuckGo, etc.)

## Action Items

- [x] Research DDGS library — confirmed v9.14.2, actively maintained, `news()` method works
- [x] Document region codes for Asia Pacific + MENA
- [x] Document rate limit patterns and retry strategy
- [ ] Implement DDGSAdapter with region rotation, news polling, URL dedup
- [ ] Add 3-retry exponential backoff with `RatelimitException` handling
- [ ] Add country-to-region-code mapping for all Group A/B countries
- [ ] Add MD5 URL dedup with 24-hour in-memory retention
- [ ] Add `text()` fallback for regions where `news()` returns empty
- [ ] Evaluate whether GDELT (purpose-built news database) is a better primary news source
- [ ] Update adapter_specification.md with DDGS findings
