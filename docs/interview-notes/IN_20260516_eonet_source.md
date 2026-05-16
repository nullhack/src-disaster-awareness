# IN_20260516_eonet_source — EONET as Third Primary Data Source

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** eol
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | What data source replaces GDELT? | NASA EONET v3 — Earth Observatory Natural Event Tracker. Free, zero-auth REST API providing curated natural event metadata globally. |
| Q2 | Why EONET over alternatives? | GDELT `api.gdeltproject.org` is unreachable from our network (SSL timeout). GDELT Cloud requires API key + signup. ReliefWeb v2 requires pre-approved appname. EONET is the only zero-auth, globally-available, structured disaster API that works from this network. |
| Q3 | What disaster types does EONET cover? | 13 categories: earthquakes, floods, volcanoes, wildfires, severeStorms (cyclones/hurricanes), droughts, landslides, dustHaze, manmade, seaLakeIce, snow, tempExtremes, waterColor. Maps to our 7 disaster types: EQ, FL, VO, WF, TC, DR, LS. |
| Q4 | What data does each event provide? | `id` (EONET unique ID), `title` (human-readable), `categories[]` (type), `sources[]` (provenance), `geometry[]` (coordinates + date + magnitude), `closed` (active/ended status), `description` (optional). |
| Q5 | How is country determined? | Title parsing: EONET titles follow patterns like "Flood in **Bangladesh**", "Wildfire in **Mongolia**", "**Masaya** Volcano, **Nicaragua**". Parse country name, normalize via pycountry to ISO 3166-1 alpha-2. |
| Q6 | How does EONET overlap with GDACS? | EONET mirrors some GDACS events (source.id=="GDACS" with gdacs.org URLs). These are duplicates — the pipeline's source_fingerprint pre-filter handles them. Also: EONET adds US wildfire data not in GDACS API. |
| Q7 | What should be filtered out? | 1) Prescribed fires (title contains "Prescribed Fire" or "RX" — controlled burns, not disasters). 2) GDACS-sourced events (duplicate — our GDACS adapter already fetches these). 3) US-only small wildfires (<5000 acres from IRWIN) — low signal for global monitoring. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | API endpoint? | `GET https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=100` |
| Q9 | Auth required? | None. Zero auth, zero registration, zero API key. |
| Q10 | Rate limits? | None observed. NASA documents recommend 10-minute cache between API calls. |
| Q11 | Data format? | JSON. Root object has `title`, `description`, `link`, `events[]`. Each event is a dict with fields listed in Q4. |
| Q12 | Deterministic vs AI extraction split? | ~60% deterministic: disaster type (from categories), date (from geometry), title (verbatim), source fingerprint (from id), GDACS dedup (from source.id). ~40% needs AI: country (title parsing or reverse geocode), impact estimates (not in EONET raw data). |
| Q13 | Level derivation? | Default Level 2. Volcano (SIVolcano source) → Level 3. GDACS-sourced events → use GDACS alert level (same as current GDACS adapter logic). No tone/severity fields in EONET raw data for non-GDACS events. |

## Feature: eonet_adapter

| ID | Question | Answer |
|----|----------|--------|
| Q14 | Adapter name? | `EONETAdapter` in `disaster_surveillance_reporter/adapters/eonet.py`. Source name `"EONET"`. |
| Q15 | Failure behavior? | Never raises. Returns `[]` on HTTP errors (5xx, 429, timeout), network failures, malformed response, or empty events list. |
| Q16 | Prescribed fire filtering? | Filter events where title contains "Prescribed Fire" or "RX" — these are controlled burns. Pattern: most titles with "RX" prefix are managed burns, not disasters. |
| Q17 | GDACS dedup strategy? | Check `source.id`. If any source in `sources[]` has `id=="GDACS"`, skip that event from EONET — our GDACS adapter already provides higher-fidelity data for the same real-world event. |
| Q18 | Source fingerprint format? | `EONET:{id}` — e.g., `EONET:20104`. |
| Q19 | Country extraction approach? | Parse title for country name using pattern matching, normalize via `pycountry.countries.lookup()`. Fallback: leave country as `None` (AI Extractor handles it). |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reliability | EONET API returns 5xx or times out | Adapter returns `[]`, pipeline continues with other sources | Must |
| QA2 | Data Integrity | EONET event already fetched by GDACS adapter | Source fingerprint pre-filter deduplicates | Must |
| QA3 | Reproducibility | Same EONET API response | Same RawRecord list with identical raw_fields | Must |

---

## Pain Points Identified

- EONET is heavily US-wildfire-biased (~95% of open events). Non-US coverage exists but is sparse.
- Title-based country extraction is fragile — "Rincon de la Vieja Volcano, Costa Rica" requires backtracking "Costa Rica" from the end.
- Some coordinates in descriptions are truncated (e.g., `-[PHONE]` appears — likely a phone number suffix inadvertently matched by truncation).
- No impact estimates (deaths, affected, economic) in EONET data — these come from AI enrichment or remain unknown.

## Business Goals Identified

- Maintain 3-source coverage (GDACS + WHO + EONET) for pipeline resilience
- Zero-cost operation (all 3 sources free, no API keys)
- Global disaster monitoring with structured event data

## Terms to Define (for glossary)

- **EONET** — NASA Earth Observatory Natural Event Tracker v3
- **EONETAdapter** — Source adapter implementing `SourceAdapter` protocol for EONET API
- **Prescribed Fire** — Controlled/managed burn, not a disaster event

## Action Items

- [x] Create IN_20260516_eonet_source.md
- [ ] Update product_definition.md — add EONET to Phase 2 (delivery item after gdelt_adapter)
- [ ] Update domain_spec.md — add EONET source to Fetching context data shapes
- [ ] Update glossary.md — add EONET, EONETAdapter entries
- [ ] Create eonet_adapter.feature with Rule blocks
- [ ] Implement EONETAdapter in eonet.py
- [ ] Run pipeline simulation with EONET integrated
- [ ] Update pipeline/__init__.py to include EONETAdapter in adapter list
