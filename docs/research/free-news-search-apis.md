# Free News Search APIs for Disaster Surveillance — Project Team, 2026

## Citation

Project Team. (2026). *Free news search APIs for disaster surveillance: Comparative evaluation of Python-accessible web search and news APIs for automated disaster news monitoring*. Internal research report.

## Source Type

Synthesis

## Method

Review

## Verification Status

Needs Verification — API pricing, rate limits, and feature availability were current as of May 2026 and may change.

## Confidence

Moderate

## Key Insight

GDELT, Google News RSS, and DDGS form a free, no-API-key-required layered monitoring stack purpose-fit for automated disaster surveillance.

## Core Findings

1. **GDELT is the strongest primary source** for disaster monitoring: purpose-built for global event monitoring, completely free, no API key required, with structured event data, disaster-specific GKG themes (e.g., `NATURAL_DISASTER`, `EPIDEMIC`), country/date/geographic filtering, tone scoring, and 15-minute update cycles.
2. **Google News RSS** is the best free secondary source: broad media coverage, real-time RSS feeds with keyword search, no API key, ~60 requests/minute safe rate, accessed via `feedparser` with endpoints for search, topic feeds, and top stories.
3. **DDGS (duckduckgo_search)** is a viable tertiary fallback: free metasearch with `news()` endpoint, no API key, multi-backend (Bing, DuckDuckGo, Yahoo), but suffers from aggressive rate limiting (HTTP 202 errors) and fragility from scraping-based architecture.
4. **Brave Search API** has good coverage with an independent index and dedicated news endpoint but requires a credit card even for the free tier (~1,000 queries/month at $5 credit), with volatile pricing (former 5,000/month plan removed Feb 2026).
5. **SearXNG** offers unlimited self-hosted metasearch with news category support but requires Docker hosting and manual JSON format enablement; underlying engine rate limits may still apply.
6. **Tavily** is AI-native with relevance scoring but lacks a dedicated news endpoint (general web search only) and is limited to ~500–1,000 searches/month on the free tier.
7. **NewsAPI.org** is unsuitable for production: the developer plan (100 requests/day) explicitly prohibits production use; paid plans start at $449/month.
8. **SerpAPI** has an impractically tiny free tier (100 searches/month) and faces legal risk from Google's Dec 2025 DMCA lawsuit.
9. **NewsData.io** offers a moderate free tier (200 credits/day, commercial use allowed) but with limited language/country coverage on the free tier.
10. **GNews** is a simple free Python wrapper around Google News but subject to Google rate limiting and ToS concerns for non-RSS access.
11. **The recommended polling strategy** is 15-minute intervals matching GDELT's update cycle, yielding ~192 queries/day across GDELT and Google News RSS — well within all free limits.
12. **Multiple Python packages exist for GDELT access**: `gdeltdoc` (active, MIT, 200+ GitHub stars), `gdelt-client`, `gdelt` (gdeltPyR, alpha), and `py-gdelt` (new async client with Pydantic models).
13. **GDELT Cloud API v2** (commercial, newer) provides structured event data with disaster-relevant domains (ENVIRONMENT, HEALTH, INFRASTRUCTURE), fatality tracking, semantic search, and story clustering.

## Mechanism

The layered architecture works by using each API's strengths while compensating for weaknesses: GDELT provides structured, theme-filtered event detection with geographic and tone metadata from 100+ language sources; Google News RSS provides broad, real-time media coverage via keyword search; DDGS provides metasearch fallback when primary sources are unavailable. The 15-minute polling interval matches GDELT's data refresh cycle, and the combined query volume (~192/day) stays within free tier limits for all services.

## Relevance

Directly informs the disaster surveillance system's data ingestion layer. GDELT should be the primary source for structured disaster event detection (earthquakes, floods, typhoons, epidemics) in Asia-Pacific and MENA regions, with Google News RSS as a complementary broad-coverage source and DDGS as a fallback. The comparison table, API parameters, Python code examples, and rate limit guidance provide actionable implementation specifications. The recommendation to avoid NewsAPI.org and SerpAPI for production use prevents architectural dead ends.

## Related Research

- **gdelt_api_technical_report.md** — Deep technical assessment of the GDELT API surface, data model, query operators, GKG themes, CAMEO+ event codes, BigQuery access, and Python library details. Provides the implementation-level detail behind the GDELT recommendation in this document.
- **global-health-api.md** — Assessment of Global.health API for disease outbreak line-list data. Complementary to GDELT's event-level detection with detailed epidemiological case records, though limited to specific emergent outbreaks rather than continuous surveillance.
