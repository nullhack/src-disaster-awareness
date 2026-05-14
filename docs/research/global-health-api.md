# Global.health API Research Report — Global.health Consortium, 2020–2026

## Citation

Global.health Consortium. (2020–2026). *Global.health: Open access to epidemiological data* [Platform and API]. https://global.health/. See also: Xu, B., Gutierrez, B., Mekaru, S., et al. (2020). Epidemiological data from the COVID-19 outbreak, real-time case information to inform public health response. *Scientific Data*, 7, 106. https://doi.org/10.1038/s41597-020-0448-0

## Source Type

Industry Standard

## Method

Review

## Verification Status

Needs Verification — API endpoints were tested as of May 2026; data portal status and API documentation availability may be intermittent (Swagger docs returned transport errors during assessment).

## Confidence

Moderate

## Key Insight

Global.health provides the richest publicly available line-list epidemiological data (76 fields per case record) under an open license, but its event-driven "first 100 days" mission model means it cannot serve as a continuous disease surveillance backbone for ongoing endemic diseases.

## Core Findings

1. **Global.health has two access mechanisms**: (A) a programmatic data download endpoint per disease at `https://data.<disease>.global.health/` returning paginated CSV/JSON, and (B) an underlying MongoDB-backed REST API with data service, curator service, and geocoding service microservices.
2. **Authentication requires a free API key** obtained by registering at the relevant data portal (e.g., `https://data.covid-19.global.health`) then navigating to Profile > Reset API Key. No account is needed to browse the website; the platform is free for research under CC-BY-4.0 license.
3. **Diseases tracked as of 2026 are all frozen/inactive**: COVID-19 (Jan 2020–Dec 2023, 142+ countries, 100M+ cases), Mpox 2022 (Apr–Sep 2022), Mpox 2024 (Jan–Dec 2024, Africa focus), Ebola (Aug–Nov 2022, Uganda), Marburg (Jan–Apr 2023, Equatorial Guinea), and Avian Influenza H5N1 (Feb 2024–Jul 2025, USA).
4. **No active data feeds exist as of May 2026**: all tracked outbreaks are archived. The platform activates for emergent outbreaks during the "first 100 days" response period, then freezes data.
5. **The platform does NOT track endemic diseases**: cholera, measles, dengue, malaria, and other ongoing diseases in Asia-Pacific and MENA are not covered. The platform is event-driven, not a continuous surveillance system.
6. **Each record contains 76 structured fields** organized into: metadata (6: source IDs, verification status), demographics (6: age range, gender, ethnicity, occupation), events (10: confirmation, symptoms onset, hospital/ICU admission, outcome), location (9: country, admin levels 1–3, geo-resolution, lat/lon), symptoms (2: status + values list), pre-existing conditions (2), transmission (3: linked cases, places, routes), travel history (12: dates, locations, methods), vaccines (16: up to 4 vaccines with batch/date/name/side effects), plus pathogens, variant, SGTF, and revision metadata.
7. **The official Python SDK (`gdh.py`)** is a standalone script (not pip-installable) located in the GitHub repository, depending on `requests` and `pandas`. It supports country filtering only (ISO 3166-1 two-letter codes), with no date range, disease, or field-level filtering. An R package also exists.
8. **Bulk downloads** are available as daily CSV exports from data portals, via the Humanitarian Data Exchange (5 datasets), and through the outbreak-data wiki (line list and timeseries datasets per outbreak).
9. **Rate limits are not explicitly documented**: the API paginates results in batches; caching is recommended and built into both Python and R libraries; no requests-per-second or daily limits are specified.
10. **Data is not real-time**: it is hand-curated from authoritative government sources with delays. During active outbreaks, daily refreshes occurred (refreshed at midnight UTC). After the 100-day mission completes, data is frozen.
11. **The CC-BY-4.0 open license** allows free use, redistribution, and modification with attribution, making it suitable for integration into open-source disaster monitoring systems.
12. **The peer-reviewed methodology** (published in Nature Scientific Data) and curation from authoritative government sources provide high data trustworthiness for the case records that are available.
13. **Asia-Pacific + MENA coverage exists primarily through COVID-19 data** (Jan 2020–Dec 2023, 142+ countries). Non-COVID outbreaks had narrow geographic scope (e.g., Ebola in Uganda only).
14. **Cannot query across multiple diseases simultaneously**: each outbreak has a separate data portal and dataset. There is no unified "all outbreaks" API endpoint.
15. **The platform would be most valuable during a new emergent outbreak** in the first 100 days if Global.health activates a response, or for historical COVID-19 pattern analysis in Asia-Pacific and MENA (2020–2023). The 76-field schema is also a strong reference model for designing a disease surveillance data schema.

## Mechanism

Global.health works by curating line-list case data (individual anonymized records) from authoritative government and public health sources during emergent outbreaks. Each outbreak gets its own data portal instance at `data.<disease>.global.health`. Case data is ingested through the curator service, validated against a standardized 76-field schema (covering demographics, events, location, symptoms, transmission, travel, and vaccination), geocoded, and stored in MongoDB. The data service exposes paginated download endpoints returning CSV or JSON. The platform's "first 100 days" mission model means it activates for specific emergent outbreaks where it can add value, curates intensively during the response period, then archives the dataset. This curated approach produces high-quality, structured data but limits coverage to specific outbreak windows rather than continuous surveillance.

## Relevance

Global.health is a supplementary (not primary) data source for the disaster surveillance system. Its value lies in providing detailed, structured epidemiological case records (76 fields including demographics, geocoded locations, symptoms, outcomes, and transmission chains) during emergent outbreaks. For the Asia-Pacific and MENA disaster monitoring use case, it would provide case-level detail when a new outbreak triggers a Global.health response. However, the absence of continuous endemic disease tracking (no cholera, dengue, measles, or malaria), the frozen state of all current datasets, and the lack of real-time updates mean it cannot serve as the surveillance backbone. The 76-field data schema is valuable as a reference model for designing the system's internal disease data model. Recommended complementary sources for continuous disease surveillance include WHO EIOS/EWARS, ProMED-mail, GPHIN, HealthMap, and HDX.

## Related Research

- **gdelt_api_technical_report.md** — GDELT provides the event detection layer (what disaster is happening, where, when) that would trigger the need for detailed case data. Global.health provides the case-level epidemiological detail (who is affected, symptoms, outcomes, transmission) for specific outbreaks that GDELT detects.
- **free-news-search-apis.md** — The broader API comparison that positions GDELT as the primary news/event source. Global.health fills a different niche: structured case records rather than news event detection.
