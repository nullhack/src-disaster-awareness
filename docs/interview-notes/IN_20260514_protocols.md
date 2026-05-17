# IN_20260514_protocols — SourceAdapter, NewsSearcher, AIProvider, StorageBackend

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** eol
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Who are the users? | Backend Developers, Ops Teams, Researchers. |
| Q2 | What does the product do at a high level? | Backend pipeline: fetch → correlate → classify → enrich → store. |
| Q3 | Why does it exist — what problem does it solve? | Automates disaster surveillance with deterministic classification. |
| Q4 | When and where is it used? | Scheduled CLI tool, backend batch processing. |
| Q5 | Success — what does "done" look like? | All protocols defined, all adapters implement them, testable with fixtures. |
| Q6 | Failure — what must never happen? | Adapters must never raise exceptions on API failure — they return empty lists. AI provider must raise on unrecoverable failure but auto-retry on rate limits. |
| Q7 | Out-of-scope — what are we explicitly not building? | Base class hierarchy, caching, TTL logic, account-based sources. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | How many protocols are there? | Four: SourceAdapter, NewsSearcher, AIProvider, and StorageBackend. All use Python's Protocol (structural typing), not abstract base classes. |

## Feature: SourceAdapter

| ID | Question | Answer |
|----|----------|--------|
| Q9 | What is SourceAdapter? | A Protocol for primary API fetchers. Each adapter wraps a single API. No base class, no caching, no TTL — just httpx calls returning raw records. |
| Q10 | What attributes does SourceAdapter have? | source_name (str) — identifies which source this adapter handles. |
| Q11 | What is the fetch method signature? | `fetch(self, client: httpx.Client) -> list[RawRecord]`. Fetches current incidents from one API. |
| Q12 | What is the error handling contract for fetch? | Returns empty list on failure, never raises. Each RawRecord.raw_fields contains the complete, unmodified API response. |
| Q13 | Which adapters implement this? | Four: gdacs.py (GDACS GeoJSON), who.py (WHO OData), gdelt.py (GDELT DOC API), and news.py (DDG News search — though this also implements NewsSearcher). |

## Feature: NewsSearcher

| ID | Question | Answer |
|----|----------|--------|
| Q14 | What is NewsSearcher? | A Protocol for supplementary news search. Wraps `ddgs.DDGS.news()`. Used to find additional articles about an incident when primary sources don't provide enough context. |
| Q15 | What is the search method signature? | `search(self, query: str, *, region: str = "wt-wt", timelimit: str or None = None, max_results: int = 5) -> list[RawRecord]`. |
| Q16 | What are the search parameters? | query (str — search term), region (str, default "wt-wt" for worldwide), timelimit (optional str — time filter), max_results (int, default 5). |
| Q17 | What is the error handling contract for search? | Returns empty list on failure, never raises. Each RawRecord has source_name="DDG-NEWS". |

## Feature: AIProvider

| ID | Question | Answer |
|----|----------|--------|
| Q18 | What is AIProvider? | A Protocol for abstract AI chat. The concrete implementation is DuckAIProvider which calls DuckDuckGo's duckchat/v1 API directly via httpx — no external AI client library. |
| Q19 | What is the chat method signature? | `chat(self, prompt: str, *, model: str = "gpt-4o-mini") -> str`. Sends a prompt, gets a text response. |
| Q20 | What is the error handling contract for chat? | Raises on unrecoverable failure (auth, network). Auto-retries on rate limits (HTTP 429). |
| Q21 | How does the DuckAIProvider two-step protocol work? | Step 1: GET https://duckduckgo.com/duckchat/v1/status with header x-vqd-accept: 1 → returns x-vqd-4 token. Step 2: POST https://duckduckgo.com/duckchat/v1/chat with x-vqd-4 header + model + messages → SSE stream response. The provider caches the VQD token for reuse. |
| Q22 | How is SSE parsed? | The _parse_sse method splits the response by lines, looks for lines starting with "data: " (excluding "data: [DONE]"), parses JSON, and concatenates all "message" values. |
| Q23 | What models are available? | gpt-4o-mini, claude-3-haiku, llama-3.3-70b, o3-mini, mistral-small. All free, no auth needed. Default is gpt-4o-mini. |
| Q24 | What is the rate limit? | ~1 request per 15 seconds. Auto-retry with backoff on HTTP 429. |

## Feature: StorageBackend

| ID | Question | Answer |
|----|----------|--------|
| Q25 | What is StorageBackend? | A Protocol for persistent storage. Two backends: JSONL (default, append-only, date-partitioned) and SQLite (alternative, same query interface). Both store the complete IncidentBundle including all raw records. |
| Q26 | What is the store method signature? | `store(self, bundles: list[IncidentBundle]) -> int`. Stores bundles, returns count of new bundles stored (skips existing IDs). |
| Q27 | What is the query method signature? | `query(self, *, date_from: date, date_to: date, **filters: Any) -> list[Incident]`. Queries stored incidents by date range and optional filters. Filters: country_group, disaster_type, priority, should_report, source_name. Returns Incident (flattened view), not raw bundles. |
| Q28 | What is the exists method signature? | `exists(self, incident_id: str) -> bool`. Checks if an incident already exists — used for dedup. |
| Q29 | How does dedup work? | Dedup by incident_id across both backends. The store method skips existing IDs. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reliability | Any source API down — adapter returns empty list, other sources unaffected | Graceful degradation | Must |
| QA2 | Reliability | AI timeout/failure — incident stored without enrichment | Partial storage | Must |
| QA3 | Testability | Every adapter tested against saved fixtures | Fixture-first | Must |

---

## Pain Points Identified

- DuckDuckGo AI rate limit (~1 req/15s) is the pipeline bottleneck
- No caching in adapters means every pipeline run fetches fresh data
- SSE parsing for DuckDuckGo AI requires careful implementation
- VQD token management needs to handle expiration

## Business Goals Identified

- Use Protocol (structural typing) instead of base classes for loose coupling
- Zero-auth for all sources — no API keys, no accounts
- Every adapter must capture full raw response unmodified
- Storage must preserve complete bundles for future reprocessing

## Terms to Define (for glossary)

- Protocol (Python structural typing)
- SourceAdapter
- NewsSearcher
- AIProvider
- StorageBackend
- DuckAIProvider
- VQD token
- SSE (Server-Sent Events)
- httpx.Client
- ddgs package
- Dedup by incident_id

## Action Items

- [ ] Validate VQD token caching and expiration behavior
- [ ] Confirm SSE parsing handles all edge cases (empty messages, partial lines)
- [ ] Test DuckAIProvider against real DuckDuckGo AI endpoint
- [ ] Validate StorageBackend query filters cover all researcher use cases
