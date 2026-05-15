Feature: AI Provider

  Pluggable AI chat interface with three backend implementations (OllamaProvider for
  local/free, GeminiProvider for Google free tier, OpenAIProvider for paid API) plus a
  disabled mode. Defines the AIProvider protocol: chat(prompt, *, model) -> str.
  Handles rate limiting with exponential backoff (15s initial, 2x multiplier, max 3
  retries) and distinguishes retryable from non-retryable failures. Configured via
  DSR_AI_PROVIDER environment variable. Uses DSPy for structured LLM programming.

  Rule: Provider backend is pluggable
    AIProvider selects from Ollama Gemini OpenAI or disabled mode at initialization
    via the DSR_AI_PROVIDER environment variable

  Rule: Rate limit triggers exponential backoff
    HTTP 429 responses trigger automatic retries with exponential backoff starting
    at 15 seconds doubling each attempt up to 3 total retries

  Rule: Auth failure raises immediately
    HTTP 401 responses raise an exception immediately with no retries

  Rule: Network failure raises immediately
    Connection errors raise an exception immediately with no retries distinct from
    retryable HTTP 429 responses

  # Constraints:
  # - Reliability: AI failure (timeout, auth, network) must not block storage — bundles
  #   are stored with ai_enriched=False and all AI fields as None
