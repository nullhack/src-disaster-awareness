# IN_20260514_ai_strategy — DuckDuckGo AI, DSPy, and Batched Processing

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
| Q3 | Why does it exist — what problem does it solve? | AI extracts and enriches data from unstructured sources where deterministic rules cannot reach. |
| Q4 | When and where is it used? | After deterministic classification, as a batch enrichment step in the pipeline. |
| Q5 | Success — what does "done" look like? | AI extracts country, disaster type, and impact estimates from unstructured text. AI generates summaries and detects overrides. AI failure does not prevent storage. |
| Q6 | Failure — what must never happen? | AI must never be used for classification — only for extraction and enrichment. AI failure must not prevent incidents from being stored. |
| Q7 | Out-of-scope — what are we explicitly not building? | AI-based classification, AI model training, custom AI models. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | What AI provider is used? | DuckDuckGo AI via direct HTTP — free, no auth, no API key. No external AI client library. Calls DuckDuckGo's duckchat/v1 API directly via httpx. |
| Q9 | What models are available? | gpt-4o-mini, claude-3-haiku, llama-3.3-70b, o3-mini, mistral-small. Default is gpt-4o-mini. |
| Q10 | What is the rate limit? | ~1 request per 15 seconds. Auto-retry with backoff on rate limits (HTTP 429). |
| Q11 | How does the two-step DuckDuckGo AI protocol work? | Step 1: GET https://duckduckgo.com/duckchat/v1/status with header x-vqd-accept: 1 → returns x-vqd-4 token. Step 2: POST https://duckduckgo.com/duckchat/v1/chat with x-vqd-4 header + model + messages → SSE stream. The VQD token is cached for reuse. |
| Q12 | How is the SSE response parsed? | _parse_sse splits the response by lines, looks for lines starting with "data: " (excluding "data: [DONE]"), parses JSON from each, and concatenates all "message" values. |

## Feature: DuckAIProvider Implementation

| ID | Question | Answer |
|----|----------|--------|
| Q13 | What is the DuckAIProvider class structure? | Constructor takes httpx.Client. Has a private _vqd field (str or None) and a private _parse_sse method. The chat method lazy-initializes the VQD token on first call, then POSTs to the chat endpoint. |
| Q14 | Show the chat method flow? | If VQD is None, fetch it from /status endpoint. Then POST to /chat with x-vqd-4 header, model, and messages (role: "user", content: prompt). Parse SSE response via _parse_sse. Return concatenated message string. |

## Feature: DSPy Integration

| ID | Question | Answer |
|----|----------|--------|
| Q15 | Why DSPy? | DSPy provides structured LLM programming. Used alongside direct duck.ai calls for: typed output signatures (incident extraction, classification), prompt optimization over time, and composable AI modules. |
| Q16 | Where is DSPy used? | In the extractor agent (typed extraction signatures) and classifier agent (typed classification signatures). |

## Feature: Batched Processing

| ID | Question | Answer |
|----|----------|--------|
| Q17 | How does batched AI processing work? | AI operates on IncidentBundles — it receives ALL raw records in each bundle for full context. Two batches per pipeline run. |
| Q18 | What is the Extractor batch? | Bundles where country or disaster_type is still None after the deterministic pass. ~10 bundles per API call. DDG News results provide additional context when available. Output: extracted country, disaster_type, estimated_affected, estimated_deaths per bundle. |
| Q19 | What is the Classifier batch? | Bundles where should_report=True. ~10 bundles per API call. AI generates summaries and detects overrides O1 (Humanitarian Crisis), O3 (Likely Development), O5 (Forecast/Early Warning). Output: summary, humanitarian_crisis, likely_development, rationale per bundle. |
| Q20 | What is the total AI call budget? | ~6 calls × 15s = ~1.5 minutes per 50 incidents. Extractor batch and Classifier batch each process ~10 bundles per call. |

## Feature: AI Agent Modules

| ID | Question | Answer |
|----|----------|--------|
| Q21 | What does the Extractor agent do? | Input: list of IncidentBundles with raw text records. Output: extracted country, disaster_type, estimated_affected, estimated_deaths per bundle. Uses DSPy typed signatures. Lives in ai/extractor.py. |
| Q22 | What does the Classifier agent do? | Input: list of classified IncidentBundles with should_report=True. Output: summary, humanitarian_crisis, likely_development, rationale per bundle. Uses DSPy typed signatures. Lives in ai/classifier.py. |
| Q23 | How are AI responses handled in tests? | AI responses are mocked in tests. Prompt engineering is tested separately from the pipeline. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reliability | AI timeout/failure → incident stored without enrichment | Graceful degradation | Must |
| QA2 | Performance | Full batch with AI in < 5 minutes | < 5 minutes | Should |
| QA3 | Reproducibility | AI responses mocked in tests, deterministic rules tested independently | Test isolation | Must |

---

## Pain Points Identified

- DuckDuckGo AI rate limit (~1 req/15s) is the main pipeline bottleneck
- VQD token may expire mid-batch, requiring re-fetch
- SSE parsing must handle edge cases (empty messages, partial lines, [DONE] marker)
- AI extraction accuracy depends on prompt quality — needs iteration
- No guarantee of AI response structure — DSPy signatures help but aren't foolproof

## Business Goals Identified

- Use free AI with no API keys — zero cost
- Batched processing minimizes API calls while maximizing context per call
- AI only enriches — deterministic classification remains the source of truth
- Graceful degradation ensures incidents are never lost due to AI failures

## Terms to Define (for glossary)

- DuckAIProvider
- duckchat/v1 API
- VQD token (x-vqd-4)
- SSE (Server-Sent Events)
- DSPy
- Typed output signatures
- Extractor agent
- Classifier agent
- Batched processing
- Rate limit (HTTP 429)
- Auto-retry with backoff

## Action Items

- [ ] Test VQD token caching and expiration behavior
- [ ] Validate SSE parsing against real DuckDuckGo AI responses
- [ ] Benchmark actual batch processing time with real API
- [ ] Design DSPy signatures for extractor and classifier agents
- [ ] Test graceful degradation when AI is unavailable
