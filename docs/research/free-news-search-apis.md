# Free News Search APIs for Disaster Surveillance

**Date:** 2026-05-11
**Purpose:** Evaluate free Python-accessible web search/news APIs for automated disaster news monitoring

---

## Executive Summary

For a disaster surveillance system that needs **automated, free, Python-accessible news monitoring**, the recommended stack is:

1. **GDELT Project** (primary) — purpose-built for global event monitoring, completely free, structured event data with disaster themes, country/date filtering. No API key required.
2. **Google News RSS** (secondary) — free, no API key, real-time news search via RSS feeds. Complements GDELT with broader media coverage.
3. **DDGS (duckduckgo_search)** (tertiary) — free metasearch with news endpoint, no API key. Good fallback but rate-limited.

---

## Comprehensive Comparison Table

| API | Python Package | Auth | News-Specific | Free Tier Limits | Rate Limits | Data Fields | Disaster Suitability |
|-----|---------------|------|--------------|-----------------|-------------|-------------|---------------------|
| **GDELT** | `gdelt`, `gdeltdoc`, `gdelt-client` | None (free, no key) | Yes (event-focused) | Unlimited (public API) | ~1-2 req/sec (soft) | title, url, date, source, country, language, theme, tone, entities | **Excellent** — purpose-built |
| **Google News RSS** | `feedparser` + stdlib | None | Yes (RSS) | No hard limit | Polite use (~60 req/min) | title, link, published, source, summary | **Very Good** — broad coverage |
| **DDGS** | `ddgs` (was `duckduckgo_search`) | None | Yes (`news()`) | Unlimited (scraping) | Aggressive rate limiting (202 errors) | title, url, date, snippet, source, image | **Good** — but fragile |
| **Brave Search** | `requests` (REST) | API key required | Yes (news endpoint) | ~1,000 req/mo ($5 credit) | 50 req/sec | title, url, date, snippet, source | **Good** — but needs CC |
| **SearXNG** | `searxng_search` or `requests` | None (self-hosted) | Yes (news category) | Unlimited (self-hosted) | Self-imposed | title, url, date, snippet, engine | **Good** — requires hosting |
| **Tavily** | `tavily-python` | API key required | No (web search) | 1,000 credits/mo | 100 req/min | title, url, content, score | Moderate — no news filter |
| **NewsAPI.org** | `newsapi-python` | API key required | Yes | 100 req/day (dev only) | N/A | title, url, date, source, description | **Poor** — dev-only, no prod |
| **SerpAPI** | `google-search-results` | API key required | Yes (Google News) | 100 req/mo | N/A | title, url, date, snippet, source | **Poor** — tiny free tier |
| **NewsData.io** | `newsdata` | API key required | Yes | 200 credits/day | N/A | title, url, date, source, description | Moderate — 200/day free |

---

## 1. GDELT Project (RECOMMENDED — Primary)

### Overview
The GDELT Project monitors global news media in 100+ languages across every country, updating every 15 minutes. It is **100% free and open** — no API key, no subscription, no credit card. Created by Google Jigsaw, it is the largest open database of global events ever created.

### Python Packages

| Package | PyPI Name | Description | Status |
|---------|-----------|-------------|--------|
| `gdeltdoc` | `gdeltdoc` v1.12 | GDELT 2.0 Doc API client — article search & timelines | Active (2025) |
| `gdelt-client` | `gdelt-client` v0.2.1 | GDELT 2.0 API client — articles, timelines, raw events/mentions/GKG | Active (2026) |
| `gdelt` (gdeltPyR) | `gdelt` | GDELT 1.0/2.0 data via parallel HTTP GET + Pandas | Alpha |
| `py-gdelt` | `py-gdelt` | Comprehensive async client, all 6 REST APIs, Pydantic models | New (2026) |

### GDELT Cloud API v2 (NEW — Highly Relevant)

A newer REST API at `docs.gdeltcloud.com` provides structured event data with:

- **Filters:** `country`, `region`, `continent`, `category`, `subcategory`, `domain`
- **Disaster-relevant domains:** `ENVIRONMENT`, `HEALTH`, `INFRASTRUCTURE`
- **Categories:** Conflict events, with fatality tracking (`has_fatalities`)
- **Semantic search:** Free-text search with cosine similarity ranking
- **Story clustering:** Articles grouped into narratives
- **Pagination:** Cursor-based

Example query for disaster events:
```python
import requests

resp = requests.get(
    "https://api.gdeltcloud.com/api/v2/events",
    params={
        "domain": "ENVIRONMENT,HEALTH,INFRASTRUCTURE",
        "date_start": "2026-05-10",
        "date_end": "2026-05-11",
        "sort": "recent",
        "has_fatalities": "true",
        "limit": 50,
    }
)
```

### GDELT DOC API (article search via `gdeltdoc`)

```python
from gdeltdoc import GdeltDoc, Filters

f = Filters(
    keyword="earthquake OR flood OR tsunami",
    start_date="2026-05-10",
    end_date="2026-05-11",
    country=["US", "JP"],           # FIPS country codes
    theme="NATURAL_DISASTER",        # GKG Theme
    tone="<-5",                      # Negative tone threshold
    num_records=250,
)

gd = GdeltDoc()
articles = gd.article_search(f)
# Returns DataFrame: url, url_mobile, title, seendate, socialimage, domain, language, sourcecountry
```

### Key Capabilities for Disaster Monitoring

| Feature | Details |
|---------|---------|
| **Disaster themes** | `NATURAL_DISASTER`, `ENVIRONMENT`, `EPIDEMIC`, `MANMADE_DISASTER` and 100+ more GKG themes |
| **Country filter** | FIPS 2-letter codes (e.g., US, JP, PH) |
| **Language filter** | ISO 639 codes (100+ languages monitored) |
| **Tone filter** | Sentiment scoring; negative tone (< -5) catches disasters |
| **Date range** | Rolling 3 months via DOC API; 1979+ via raw data files |
| **Update frequency** | Every 15 minutes |
| **Data sources** | Print, broadcast, web news media worldwide |
| **Structured events** | 300+ CAMEO event categories (protests, conflict, aid, etc.) |
| **Mentions tracking** | How events propagate across media over time |
| **GKG** | Entities, themes, tone, quotations, image analysis |
| **TV monitoring** | Closed caption analysis from TV broadcasts (Jul 2009+) |

### Rate Limits
- Soft rate limit; no published hard cap
- Blog post from GDELT mentions fleet-wide QPS precision matters
- Practical guidance: 1-2 requests per second is safe for sustained use
- Use timespan-based queries to minimize request count

### Data Returned
- **Articles:** url, title, seendate, domain, language, sourcecountry, socialimage
- **Events:** date, actor1/actor2, event code, Goldstein scale, avg tone, geo coordinates, source URLs
- **Mentions:** event mentions over time across media outlets
- **GKG:** themes, entities (persons/orgs/locations), tone scores, quotation text

---

## 2. Google News RSS (RECOMMENDED — Secondary)

### Overview
Google discontinued its News API in 2011, but the **RSS feed interface remains free, public, and key-free**. It provides real-time access to Google's news aggregation — the broadest news index available.

### Access

```python
import feedparser

# Search for disaster news
feed = feedparser.parse(
    "https://news.google.com/rss/search"
    "?q=earthquake+OR+flood+OR+tsunami"
    "&hl=en&gl=US&ceid=US:en"
)

for entry in feed.entries:
    print(entry.title, entry.link, entry.published, entry.source)
```

### RSS Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/rss/search?q=<query>` | Search news by keyword |
| `/rss/headlines/section/topic/<TOPIC>` | Topic feed (WORLD, NATION, SCIENCE, HEALTH) |
| `/rss?hl=en&gl=US&ceid=US:en` | Top stories |

### Parameters
- `q`: Search query (supports OR, AND, quotes)
- `hl`: Language (e.g., `en`)
- `gl`: Country (e.g., `US`)
- `ceid`: Country:language code

### Python Packages
- `feedparser` — standard RSS parsing library (pip install feedparser)
- `gnews` — higher-level Google News client (pip install gnews)
- `google-news-feed` — async RSS client (pip install google-news-feed)
- `google-news-api` — sync/async client with rate limiting (pip install google-news-api)

### Rate Limits
- No hard published limit
- RSS feeds are designed for programmatic access
- ~60 requests/minute is safe; no proxy needed for RSS
- Google may block aggressive access patterns

### Data Fields
- `title`, `link` (redirect URL), `published`, `source` (publisher name), `summary`

### Disaster Suitability
- **Pros:** Free, no API key, broadest coverage, real-time, supports keyword search, ToS-compliant
- **Cons:** Only headlines/snippets (no full text), links are Google redirect URLs, no structured filtering by event type

---

## 3. DDGS / duckduckgo_search (Tertiary)

### Overview
`ddgs` (formerly `duckduckgo_search`) is a metasearch library that aggregates results from multiple search engines. It has a dedicated `news()` function. **No API key required** — it works by scraping search engines.

### Installation
```bash
pip install ddgs
```

### Usage
```python
from ddgs import DDGS

with DDGS() as ddgs:
    results = ddgs.news(
        query="earthquake OR flood disaster",
        region="us-en",
        timelimit="d",       # d=day, w=week, m=month
        max_results=20,
        backend="auto",      # tries bing, duckduckgo, yahoo
    )
    for r in results:
        print(r["title"], r["url"], r["date"], r["source"])
```

### News Backends
The `news()` function supports backends: `bing`, `duckduckgo`, `yahoo`, `auto`

### Rate Limits
- **Major pain point.** DDGS scrapes search engines and is frequently rate-limited (HTTP 202)
- Rate limits are imposed by the underlying search engines, not the library
- DHT peer-to-peer cache network (beta) helps reduce rate limits for repeated queries
- Requires 1-3 second delays between requests in practice
- Proxy rotation recommended for sustained use

### Data Fields
- `title`, `url`, `date`, `snippet/body`, `source`, `image`

### Disaster Suitability
- **Pros:** Free, no API key, news-specific endpoint, multi-backend, time filtering
- **Cons:** Fragile (breaks when search engines change), rate-limited, not designed for production monitoring, results quality varies by backend

---

## 4. Brave Search API

### Overview
Brave Search has its own independent web index (not Google/Bing dependent). Offers a dedicated `/news/search` endpoint. **Credit card required** even for free tier.

### Access
```python
import requests

resp = requests.get(
    "https://api.search.brave.com/res/v1/news/search",
    headers={"X-Subscription-Token": "<API_KEY>"},
    params={"q": "earthquake disaster", "count": 10, "country": "us"},
)
```

### Free Tier
- **$5/month free credit** (~1,000 queries/month at $5/1K requests)
- Requires credit card (anti-fraud); card charged for overages with no cap
- Attribution required to maintain free credit
- Former 5,000 free queries/month plan removed Feb 2026

### Data Fields
- title, url, date, snippet, source, thumbnail

### Disaster Suitability
- **Pros:** Independent index, dedicated news endpoint, good coverage, fast
- **Cons:** Requires CC, volatile pricing (recently changed), ~1K free queries/month may not be enough for continuous monitoring

---

## 5. SearXNG (Self-Hosted)

### Overview
Open-source metasearch engine (AGPL-3.0) aggregating 249 search services. Self-hosted via Docker. Full control, no rate limits, no API keys.

### Access
```python
import requests

resp = requests.get(
    "http://localhost:8080/search",
    params={
        "q": "earthquake disaster news",
        "format": "json",
        "categories": "news",
        "time_range": "day",
        "language": "en",
    }
)
results = resp.json()
```

### Python Package
- `searxng_search` — dedicated client library
- Or use `requests` directly against your instance

### Setup
```bash
docker pull searxng/searxng
docker run -d -p 8080:8080 searxng/searxng
```

### Rate Limits
- None (self-hosted); limited only by underlying engines SearXNG queries
- JSON output format must be enabled in `settings.yml`

### Disaster Suitability
- **Pros:** Free, unlimited, private, news category support, multi-engine aggregation
- **Cons:** Requires hosting infrastructure, maintenance, JSON format must be manually enabled, underlying engine rate limits may still apply

---

## 6. Tavily

### Overview
AI-native search API designed for LLM/RAG applications. Returns cleaned, relevance-scored results. Python SDK available.

### Installation
```bash
pip install tavily-python
```

### Free Tier
- 1,000 credits/month (no CC required)
- 1 credit per basic search, 2 per advanced search
- So effectively 500-1,000 searches/month

### Limitations for Disaster Monitoring
- **No dedicated news endpoint** — it does general web search
- `topic="news"` parameter exists but is web search filtered, not a news API
- `time_range` supports day/week/month/year
- `max_results` capped at 20 per query
- Returns: title, url, content, score

### Disaster Suitability
- **Moderate.** Good for AI-optimized results but no news-specific functionality. Free tier (1K/month) is modest for continuous monitoring.

---

## 7. NewsAPI.org

### Overview
Aggregates 80,000+ sources across 54 countries. Has dedicated news endpoints.

### Free Tier (Developer Plan)
- 100 requests/day
- 24-hour article delay
- **Production use explicitly prohibited** — development/testing only
- 1-month article history

### Python Package
```bash
pip install newsapi-python
```

### Disaster Suitability
- **Poor for production.** The developer plan cannot be used in staging or production environments. Paid plan starts at $449/month. Not viable for a free disaster monitoring system.

---

## 8. SerpAPI

### Overview
Scrapes Google (and other engines) returning structured JSON. Covers Google News.

### Free Tier
- 100 searches/month (very limited)
- Paid plans start at $50/month for 5,000 searches

### Disaster Suitability
- **Poor.** Tiny free tier, expensive paid plans. Also facing legal risk from Google's Dec 2025 DMCA lawsuit.

---

## 9. NewsData.io

### Overview
News aggregation API with commercial use allowed on free tier.

### Free Tier
- 200 credits/day (~6,000/month)
- 10 results per request
- Commercial use allowed
- 2 languages, 5 countries on free tier

### Disaster Suitability
- **Moderate.** Reasonable free tier with commercial use allowed, but limited language/country coverage on free tier.

---

## 10. GNews

### Overview
Python library wrapping Google News. Provides search, topic feeds, and location-based feeds.

### Installation
```bash
pip install gnews
```

### Usage
```python
from gnews import GNews

google_news = GNews()
google_news.period = '1d'
google_news.max_results = 10

results = google_news.get_news("earthquake disaster")
# Returns: title, description, url, publisher, published date
```

### Free Tier
- No API key needed (wraps Google News RSS/HTML)
- Rate limited by Google (~60-100 req/min)

### Disaster Suitability
- **Good.** Simple wrapper, free, no API key. But subject to Google rate limiting and ToS concerns for non-RSS access.

---

## Recommendation for Disaster Surveillance

### Architecture: Layered Approach

```
┌─────────────────────────────────────────────────┐
│              Disaster Surveillance               │
├─────────────────────────────────────────────────┤
│                                                  │
│  Layer 1: GDELT (Primary)                       │
│  - Structured event detection                   │
│  - Theme filtering (NATURAL_DISASTER, etc.)     │
│  - Tone/sentiment scoring                       │
│  - Country/date/geographic filtering            │
│  - 15-minute update cycle                       │
│  - No API key, no cost                          │
│                                                  │
│  Layer 2: Google News RSS (Secondary)           │
│  - Broad media coverage                         │
│  - Keyword-based monitoring                     │
│  - Real-time RSS feeds                          │
│  - No API key, no cost                          │
│                                                  │
│  Layer 3: DDGS (Tertiary Fallback)              │
│  - Metasearch when other sources are down       │
│  - Multi-backend news aggregation               │
│  - No API key, no cost                          │
│  - Handle rate limits with backoff              │
│                                                  │
│  Optional: SearXNG (Self-Hosted)                │
│  - If infrastructure available                  │
│  - Unlimited queries, full control              │
│  - Aggregates multiple search engines           │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Why GDELT is the Clear Winner

1. **Purpose-built for this exact use case** — global event monitoring from news media
2. **Completely free** — no API key, no credit card, no rate limit concerns for reasonable use
3. **Structured data** — events have categories, actors, locations, tone, themes
4. **Disaster-specific themes** — `NATURAL_DISASTER`, `EPIDEMIC`, `ENVIRONMENT`, `MANMADE_DISASTER`
5. **Geographic filtering** — country, region, continent, admin1
6. **Sentiment/tone** — negative tone scores correlate with disaster reporting
7. **Multiple access methods** — REST API, raw data files (S3), BigQuery
8. **Historical data** — back to 1979 for trend analysis
9. **15-minute updates** — near real-time for current events
10. **100+ languages** — global coverage, not just English

### Polling Strategy

```python
# Suggested polling interval: every 15 minutes (matching GDELT's update cycle)
# GDELT DOC API: ~96 queries/day at 15-min intervals
# Google News RSS: ~96 queries/day at 15-min intervals
# Total: ~192 queries/day — well within all free limits
```

### Avoid These for Production Monitoring
- **NewsAPI.org** — Developer plan prohibits production use
- **SerpAPI** — Only 100 queries/month free; legal risk from Google lawsuit
- **Tavily** — No news-specific endpoint; limited to 1K/month
