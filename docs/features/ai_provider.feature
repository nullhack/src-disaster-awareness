Feature: AI Provider

  Pluggable AI chat interface with three backend implementations (OllamaProvider for
  local/free, GeminiProvider for Google free tier, OpenAIProvider for paid API) plus a
  disabled mode. Defines the AIProvider protocol: chat(prompt, *, model) -> str.
  Handles rate limiting with exponential backoff (15s initial, 2x multiplier, max 3
  retries) and distinguishes retryable from non-retryable failures. Configured via
  DSR_AI_PROVIDER environment variable. Uses DSPy for structured LLM programming.

  # Business rules:
  # - AIProvider uses pluggable backend selected at config time: Ollama, Gemini, OpenAI,
  #   or disabled (pipeline runs without AI)
  # - Rate limit (HTTP 429) triggers auto-retry with exponential backoff: initial delay
  #   15s, multiplier 2x, max 3 retries. Total max wait: 15+30+60=105s per call
  # - AIProvider raises exception immediately on auth failure (HTTP 401) — no retry
  # - AIProvider raises exception immediately on network failure (ConnectionError) — no
  #   retry. Distinct from HTTP 429 which gets retries

  # Constraints:
  # - Reliability: AI failure (timeout, auth, network) must not block storage — bundles
  #   are stored with ai_enriched=False and all AI fields as None
