# Fixture Validation Report

Date: 2026-05-14
Purpose: Validate protocol assumptions in behavioral_spec.md against real API responses

## Summary

| Source | Status | Critical Mismatches | Minor Issues |
|--------|--------|-------------------|--------------|
| GDACS | ✅ Working | 1 | 1 |
| WHO DON | ✅ Working | 2 | 1 |
| GDELT DOC | ⚠️ Partial | 2 | 1 |
| DDG News | ✅ Working | 0 | 0 |
| DuckDuckGo AI | ❌ Blocked | 1 | 0 |

## Source-by-Source Analysis

### GDACS GeoJSON API

**Endpoint**: `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH`
**Auth**: None required
**Rate limit**: No explicit limit observed
**Format**: GeoJSON FeatureCollection

**Protocol Status**: All assumed fields confirmed present.

**⚠️ Critical Mismatch #1: `url` field is a dict, not a string**

Spec assumed: `url: str` (single URL)
Reality: `url: dict` with keys `{geometry, report, details}`

The spec says GDACS has no URL for source_urls. This is WRONG — `url.report` provides a human-readable event page. This resolves STO-4 (Incident.source_urls for GDACS-only bundles).

Fix: Update behavioral_spec Fetching context data shape to show `url` as dict. Collect `url.report` as the source_url for GDACS records.

**Minor Issue: `istemporary` is string "false"/"true", not boolean**

Spec assumed: `istemporary: bool`
Reality: `istemporary: str` ("false" or "true")

Fix: Parse string to bool in adapter.

**Confirmed Fields** (28 properties per feature):
- alertlevel (Green/Orange/Red) ✅
- eventtype (EQ/TC/FL/VO/TS/DR/WF) ✅
- name, description, htmldescription ✅
- country (name), iso3 (ISO alpha-3) ✅
- fromdate, todate, datemodified ✅
- eventid, episodeid ✅
- istemporary ✅ (string)
- affectedcountries (list of {iso2, iso3, countryname}) ✅
- severitydata ({severity, severitytext, severityunit}) ✅
- url (dict with geometry/report/details) ✅
- geometry (Point coordinates) ✅

### WHO Disease Outbreak News API

**Endpoint**: `https://www.who.int/api/hubs/diseaseoutbreaknews`
**Auth**: None required
**Format**: OData JSON with `@odata.context`, `value` array, `@odata.nextLink`

**Protocol Status**: Fields confirmed, BUT no structured country or disaster type.

**⚠️ Critical Mismatch #2: No structured country field**

Spec assumed: Country would be available as a structured field.
Reality: `regionscountries` is either null or a GUID reference to a related entity. No direct country name/code.

Impact: Confirms the spec's claim that WHO is ~30% deterministic. Country must be extracted from Title/Overview text via AI or regex. Example title: "Avian influenza – situation in Egypt" → country = Egypt.

**⚠️ Critical Mismatch #3: No structured disaster type field**

Spec assumed: Disaster type would be derivable.
Reality: No structured type field. Type must be extracted from Title text (e.g., "Avian influenza" → disease type, "Marburg virus" → disease type).

**Minor Issue: `ItemDefaultUrl` is a relative path, not full URL**

Spec assumed: Full URL available.
Reality: `ItemDefaultUrl` = "/2006_03_20-en" (relative). Must prepend "https://www.who.int" for full URL.

**Confirmed Fields** (22 fields per article):
- Title ✅
- Overview (full HTML body) ✅
- Summary ✅ (often empty)
- PublicationDateAndTime ✅
- PublicationDate ✅
- ItemDefaultUrl ✅ (relative path)
- DonId ✅ (often empty string)
- Id (UUID) ✅
- Assessment, Advice, Epidemiology, FurtherInformation, Response ✅ (often empty)

### GDELT DOC API

**Endpoint**: `https://api.gdeltproject.org/api/v2/doc/doc`
**Auth**: None required
**Rate limit**: 1 request per 5 seconds (strictly enforced, returns 429)
**Format**: JSON with `articles` array
**Query syntax**: OR'd terms must be parenthesized: `(earthquake OR flood)`

**Protocol Status**: ArtList mode lacks critical fields assumed in spec.

**⚠️ Critical Mismatch #4: No `tone` field in ArtList mode**

Spec assumed: `tone` field available for severity classification (tone < -5 → Level 4, etc.).
Reality: ArtList mode returns only `{url, title, seendate, domain, language, sourcecountry, socialimage, url_mobile}`. No tone.

Impact: GDELT level derivation via tone is NOT possible in ArtList mode. Must either:
1. Use a different GDELT API mode (ToneChart) — but this changes the response structure entirely
2. Derive level from title sentiment analysis (AI)
3. Default to Level 2 for GDELT records without tone data

**⚠️ Critical Mismatch #5: `sourcecountry` is news source country, not incident location**

Spec assumed: Country of the incident.
Reality: `sourcecountry` is the country where the news source is located (e.g., "China" for chinese news sites).

Impact: Incident country must be extracted from title text, not from a structured field.

**Minor Issue: `seendate` format is not ISO 8601**

Format: `20260512T053000Z` (YYYYMMDDTHHMMSSz)
Must parse to extract date for correlation.

**Confirmed Fields** (8 fields per article):
- url ✅
- title ✅
- seendate ✅ (non-ISO format)
- domain ✅
- language ✅
- sourcecountry ✅ (source country, not incident country)
- socialimage ✅
- url_mobile ✅

### DDG News (ddgs package)

**Method**: `ddgs.DDGS().news(query, max_results=N)`
**Auth**: None required
**Rate limit**: Not observed (works reliably)

**Protocol Status**: All assumed fields confirmed. No mismatches.

**Confirmed Fields** (6 fields per result):
- title ✅
- url ✅
- body ✅ (snippet text)
- date ✅ (ISO 8601)
- source ✅ (source name)
- image ✅

### DuckDuckGo AI (duckchat/v1)

**Endpoint**: `https://duckduckgo.com/duckchat/v1/chat`
**Protocol**: Was GET /status → VQD token → POST /chat with SSE

**❌ Critical Mismatch #6: VQD protocol is dead, anti-bot challenge active**

Spec assumed: Two-step protocol (GET VQD → POST chat with SSE).
Reality: As of 2026-05:
- GET /duckchat/v1/status returns `x-vqd-hash-1` (JavaScript challenge, NOT VQD token)
- No `x-vqd-4` header returned
- POST /duckchat/v1/chat returns 418 `ERR_CHALLENGE` without valid VQD
- /duckchat/chat page returns 410 Gone
- /duckchat/v1/getvqd returns 410 Gone

**Impact**: DuckDuckGo AI is NOT usable as the AI enrichment backend. The entire AI strategy in the contract is blocked.

**Resolution Options**:
1. **Ollama with local models** (no API key, runs locally, fully free)
2. **Google Gemini free tier** (free API key, generous limits)
3. **Make AI enrichment fully optional** — pipeline works without AI, classification is deterministic
4. **DSPy + any API-key provider** (user provides key)

## Impact on behavioral_spec.md

### Required Changes

1. **Fetching/GDACS data shape**: Change `url` from "not available" to `dict {geometry, report, details}`. Note that `url.report` resolves the source_urls issue for GDACS.

2. **Fetching/WHO data shape**: Add note that `regionscountries` is a GUID (or null), not a structured country field. Country extraction requires text parsing. `ItemDefaultUrl` is relative path.

3. **Fetching/GDELT data shape**: Remove `tone` from ArtList response fields. Note that tone requires ToneChart mode (different API call). Change `sourcecountry` description to "news source country, not incident location". `seendate` format is YYYYMMDDTHHMMSSz.

4. **Classification/Level Derivation/GDELT**: The tone-based level derivation (tone < -5 → L4, etc.) is NOT available with ArtList mode. Must either use a separate ToneChart call or derive level differently.

5. **Enrichment/AI Provider**: DuckDuckGo AI protocol is blocked. The AIProvider protocol abstraction is correct (allows swapping implementation), but the DuckAIProvider implementation is not viable. Need alternative:
   - Option A: Ollama + local model (preferred, no API key)
   - Option B: Google Gemini free tier
   - Option C: Make AI enrichment optional (pipeline runs without AI)
   - Option D: User provides API key for any provider

6. **Storage/source_urls**: GDACS bundles CAN have source_urls via `url.report`. STO-4 is still valid (source_urls is Optional) but GDACS is no longer the "no URL" source.

## Fixture Files

| File | Source | Records |
|------|--------|---------|
| `fixtures/gdacs/raw_response.json` | GDACS SEARCH API | 1 GeoJSON feature |
| `fixtures/who/raw_response.json` | WHO DON API | 50 OData items |
| `fixtures/gdelt/raw_response.json` | GDELT DOC ArtList | 5 articles |
| `fixtures/ddg_news/raw_response.json` | DDG News (ddgs) | 5 results |
| `fixtures/duckai/protocol_analysis.json` | DuckDuckGo AI | Protocol blocked |
