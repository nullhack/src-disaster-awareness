# ADR_20260514_pluggable_ai_provider

## Status

Accepted

## Context

DSR uses AI for two purposes: (1) extracting structured fields (country, disaster type, casualties) from unstructured text in WHO, GDELT, and DDG News records, and (2) generating summaries and detecting override conditions (O1, O3, O5) for reportable bundles. Quality attribute #3 (Reliability) requires that AI failure never blocks storage — the pipeline must run fully without AI. Different deployment environments have different AI capabilities: some users run local Ollama, some use Google Gemini's free tier, some have OpenAI API keys, and some run fully offline.

The forces at play are: (1) AI must be optional and failure-safe, (2) different users have different AI backends available, (3) the Extractor and Classifier agents need structured output (typed fields, not free text), (4) prompt engineering must be testable and optimisable independently of the AI provider, (5) the same agent code must work across all providers.

## Interview

| Question | Answer |
|---|---|
| Should AI providers share a common interface? | Yes — all providers must implement the same `AIProvider` protocol (`chat(prompt, *, model) -> str`) |
| Is DSPy adding unnecessary abstraction? | No — DSPy provides typed signatures, output parsing, and retry logic that raw prompt engineering would require manual implementation of |
| Should we support multiple AI providers simultaneously? | No — one provider per pipeline run, configured via `DSR_AI_PROVIDER` env var |

## Decision

Use DSPy for structured LLM programming with a pluggable `AIProvider` protocol. DSPy handles typed output signatures, prompt engineering, and retry logic. The underlying LM is configured via `dspy.configure(lm=dspy.LM("provider/model"))`. Four implementations are supported: OllamaProvider (local, free, recommended), GeminiProvider (free tier), OpenAIProvider (paid), and None (AI disabled — pipeline runs deterministically only).

## Reason

DSPy decouples the AI agent logic (what to extract, what to classify) from the AI provider (where to send prompts), enabling provider-agnostic agent code with typed output guarantees, while the pluggable protocol allows zero-code provider switching via environment variables.

## Alternatives Considered

- **Raw prompt engineering (manual `httpx` calls to AI API)**: No typed output structure; manual JSON parsing; fragile prompt templates; no retry logic; provider-specific code in each agent. Rejected because Extractor and Classifier would need duplicate boilerplate for API calls, response parsing, and error handling.
- **LangChain**: Heavier framework with many abstraction layers (chains, agents, tools, memory). DSR needs only two simple agents (Extractor, Classifier) with batched processing. LangChain's complexity is disproportionate. Rejected.
- **Instructor**: Good for structured output via Pydantic models, but doesn't provide DSPy's prompt optimization, typed signatures, or composable module system. Would require separate prompt management. Rejected as less capable for DSR's needs.
- **Fixed provider (Ollama only)**: Simplifies implementation but excludes users without local Ollama. Conflicts with Quality Attribute #3 (reliability requires AI to be optional). Rejected.

## Consequences

- (+) Provider-agnostic agents: Extractor and Classifier work with any DSPy-supported LM
- (+) Zero-code provider switching via `DSR_AI_PROVIDER` environment variable
- (+) AI disabled mode (`none`) guarantees the pipeline runs without any AI dependency
- (+) Typed signatures ensure output structure is validated at runtime
- (+) DSPy's prompt optimization can improve extraction quality over time without code changes
- (+) Batched processing (~10 bundles per call) minimises API calls and respects rate limits
- (-) DSPy is an additional dependency with its own abstraction layer to learn
- (-) DSPy's typed signatures may lag behind the latest model capabilities
- (-) Testing requires mocking the DSPy LM layer, which adds test complexity

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Accepted? |
|------|------------|--------|------------|-----------|
| DSPy breaks backward compatibility in a major version update | Low | Medium | Pin DSPy version in requirements; test upgrades in CI before deploying | Yes |
| AI provider rate limits cause pipeline runs to exceed 5-minute target | Medium | Low | Exponential backoff (15s initial, 2× multiplier, 3 max retries); AI failure does not block storage | Yes |
| DSPy typed signature output parsing fails on unexpected model responses | Medium | Medium | Mid-batch failure handling: keep successful bundles, mark remaining as `enrichment_failed=True`, store everything | Yes |
| Local Ollama not running when pipeline executes | High | Low | Pipeline detects Ollama unavailable, logs warning, proceeds with `ai_enriched=False` | Yes |
