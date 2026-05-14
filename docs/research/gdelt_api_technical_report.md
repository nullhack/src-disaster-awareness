# GDELT API Technical Assessment for Disaster Surveillance — Leetaru, 1979–2026

## Citation

Leetaru, K. H., & Schrodt, P. A. (2013). GDELT: Global data on events, location, and tone. *International Studies Association Annual Convention*, 1–54. See also: GDELT Project. (2013–2026). *GDELT 2.0 API documentation* [Software documentation]. https://blog.gdeltproject.org/

## Source Type

Industry Standard

## Method

Observational

## Verification Status

Verified — GDELT is a publicly accessible, well-documented platform maintained by Google Jigsaw. API endpoints, data schemas, and theme taxonomies were tested and confirmed as of May 2026.

## Confidence

High

## Key Insight

GDELT computes structured metadata (themes, entities, locations, tone, casualty counts) from global news in 100+ languages every 15 minutes, making it the most capable free data source for automated disaster event detection — but theme-based filtering produces false positives that require post-fetch validation.

## Core Findings

1. **GDELT monitors global news in 100+ languages** across broadcast, print, and online media, processing them through machine translation (65 languages), geocoding, entity extraction, theme classification, and tone analysis.
2. **Core data products include** the Event DB (CAMEO-coded events, 1979–present), GKG (Global Knowledge Graph — entities, themes, tone, locations), Visual GKG (deep-learning image cataloging), Global Frontpage Graph, and Global Difference Graph (stealth-edit detection).
3. **The GKG data model** stores each row as a "nameset" — a unique combination of entities, themes, and locations — with fields: DATE, NUMARTS, COUNTS, THEMES, LOCATIONS, PERSONS, ORGANIZATIONS, TONE, CAMEOEVENTIDS, SOURCES, SOURCEURLS.
4. **The DOC 2.0 API** (`api.gdeltproject.org/api/v2/doc/doc`) is the primary interface for disaster monitoring: supports full-text search with Boolean operators, GKG theme filtering, source country/language filtering, tone thresholds, proximity and repeat operators, domain filtering, and image tag search. Returns up to 250 articles in JSON with fields: url, title, seendate, domain, language, sourcecountry.
5. **The GEO 2.0 API** provides geographic mapping of keywords/themes with modes for point data, country/ADM1 aggregation, heatmaps, and GeoJSON export. Supports location-based queries including radius search (`near:lat,lon,radius`) and administrative area filtering.
6. **The GKG GeoJSON v1 API** (legacy but high-value) returns real-time georeferenced data for disaster themes with lat/lon, counts (KILL/WOUND/AFFECT), tone scores, and source URLs. Limited to a 24-hour window and ~45,000 max rows.
7. **GDELT Cloud API** (commercial, Jan 2025+) introduced CAMEO+ event codes with non-conflict domains: ENVIRONMENT (EN01–EN04: geophysical hazards, meteorological hazards, climate events, pollution), HEALTH (HE01–HE05: outbreaks, pandemics, vaccines, policy, system crises), INFRASTRUCTURE (IN01–IN06: energy, transport, water). These codes are only available through the paid Cloud API, not the free Event API.
8. **Disaster-relevant GKG themes** are extensive and hierarchical: `NATURAL_DISASTER` (72M+ articles), with child themes for earthquakes (7M), floods (6.5M), hurricanes (5.3M), drought (4M), wildfire (1.6M), tsunami (1.5M), typhoon (1.1M), and many more. Health themes include `HEALTH_PANDEMIC` (28M), `TAX_DISEASE_OUTBREAK` (11.4M), `TAX_DISEASE_EPIDEMIC` (10.7M). Humanitarian themes include `REFUGEES` (21.5M), `EVACUATION` (12.3M), `DISPLACED` (5.4M). Impact themes include `KILL` (184M), `AFFECT` (136M), `WOUND` (60M).
9. **Count extraction** auto-extracts casualty/affected counts via regex: KILL, WOUND, AFFECT, SICKENED, DISPLACED counts are embedded in the COUNTS field with geo-coordinates. These are not validated and may duplicate across outlets.
10. **BigQuery access** provides the most powerful querying capability against partitioned GKG and events tables, with SQL access to all fields. A 1-day GKG scan costs ~15–20 GB of quota; Google provides 1 TB free per month.
11. **The `gdeltdoc` Python library** (MIT, 200+ GitHub stars, actively maintained) is the recommended client for the DOC API, providing `Filters` class with keyword, domain, country, language, theme, tone, proximity, and repeat filtering, returning pandas DataFrames.
12. **Rate limits are dynamic and unpublished**: the free APIs throttle based on ElasticSearch cluster load, especially during peak global events. Practical guidance: 1–2 requests/second for sustained use; use timespan-based queries to minimize request count; BigQuery or raw file downloads are recommended for high-volume automated monitoring.
13. **Key weaknesses include**: theme false positives (UK ONS found GDELT "difficult to identify articles wholly or predominantly referring to a natural disaster"), no article full-text in GKG, rate limiting under load, geocoding errors, no severity classification, no event deduplication (same disaster reported by 50 outlets = 50 GKG rows), and a 3-month default DOC API window (extendable to 1 year).
14. **The recommended implementation architecture** is multi-layered: DOC API for alerting (poll every 15–60 min), BigQuery GKG for analytics (poll every 1–6 hours), source URL fetching for verification, and cross-referencing with GDACS, EM-DAT, ReliefWeb, and USGS for corroboration and deduplication.
15. **FIPS country codes** (not ISO) are used by GDELT for country filtering: Philippines=RP, Indonesia=ID, Japan=JA, China=CH, India=IN, Iraq=IZ, Iran=IR, etc. A full mapping for Asia-Pacific and MENA countries is documented.

## Mechanism

GDELT works by continuously crawling global news sources (print, broadcast, web) in 100+ languages, running each article through NLP pipelines (machine translation for 65 languages, geocoding to city/landmark level with lat/lon, entity extraction for persons/organizations/locations, theme classification using a hierarchical taxonomy including GKG, World Bank, CRISISLEX, UNGP, and CAMEO vocabularies, tone/sentiment scoring on a -10 to +10 scale, and numeric count extraction for casualties). The processed metadata is stored in the GKG (updated every 15 minutes) and event databases (CAMEO-coded). The free DOC/GEO/GKG APIs query ElasticSearch indexes built from this metadata. The DOC API provides full-text search against article content plus structured filtering by theme, country, language, and tone. The GKG GeoJSON API returns georeferenced theme data. BigQuery provides SQL access to the full historical dataset.

## Relevance

GDELT is the recommended primary data source for the disaster surveillance system's event detection layer. Its 15-minute update cycle, disaster-specific theme taxonomy, geographic filtering with FIPS codes for Asia-Pacific and MENA countries, tone-based urgency detection (negative tone < -5 correlates with disaster reporting), and auto-extracted casualty counts provide the core event detection capability. The DOC API's `ArtList` JSON mode with theme + country filters is the primary query interface. The GKG GeoJSON API supports real-time map overlays. The `gdeltdoc` Python library provides the integration path. Key design decisions informed by this research: use GKG themes as primary filter (not keywords alone), implement post-fetch validation to reduce false positives, cache seen URLs for deduplication, plan for rate limit backoff, and cross-reference with curated databases (EM-DAT, GDACS) for severity classification.

## Related Research

- **free-news-search-apis.md** — Broader comparison of free news/search APIs that led to the GDELT recommendation. Includes Google News RSS and DDGS as complementary secondary and tertiary sources.
- **global-health-api.md** — Assessment of Global.health for detailed epidemiological line-list data. Complementary to GDELT's event-level detection: GDELT detects the event; Global.health provides case-level detail (76 fields per record) for specific outbreaks, though only during active emergent responses.
