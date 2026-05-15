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

    Scenario Outline: Provider initializes from env var
      Given DSR_AI_PROVIDER is set to "<provider>"
      When the AIProvider is initialized
      Then the AIProvider is configured as <provider> backend

      Examples:
        | provider |
        | ollama   |
        | gemini   |
        | openai   |
        | none     |

    Example: Invalid provider raises error
      Given DSR_AI_PROVIDER is set to "claude"
      When the AIProvider is initialized
      Then the initialization raises a ValueError

    Example: Missing API key raises error
      Given DSR_AI_PROVIDER is set to "openai"
      And DSR_AI_API_KEY is not set
      When the AIProvider is initialized
      Then the initialization raises a configuration error

  Rule: Rate limit triggers exponential backoff
    HTTP 429 responses trigger automatic retries with exponential backoff starting
    at 15 seconds doubling each attempt up to 3 total retries

    Scenario Outline: Rate limit retry succeeds
      Given the AIProvider receives <failures> HTTP 429 responses
      When the chat call is made
      Then the chat call returns a response

      Examples:
        | failures |
        | 1        |
        | 2        |
        | 3        |

    Example: Rate limit retries exhausted
      Given the AIProvider receives 4 consecutive HTTP 429 responses
      When the chat call is made
      Then the chat call raises a rate limit error

  Rule: Auth failure raises immediately
    HTTP 401 responses raise an exception immediately with no retries

    Example: Auth failure raises without retry
      Given the AIProvider receives an HTTP 401 response
      When the chat call is made
      Then the chat call raises an authentication error

  Rule: Network failure raises immediately
    Connection errors raise an exception immediately with no retries distinct from
    retryable HTTP 429 responses

    Scenario Outline: Network failure raises without retry
      Given the AIProvider encounters a <network_error>
      When the chat call is made
      Then the chat call raises a network error immediately

      Examples:
        | network_error       |
        | connection refused  |
        | DNS failure         |
        | connection timeout  |

  # Constraints:
  # - Reliability: AI failure (timeout, auth, network) must not block storage — bundles
  #   are stored with ai_enriched=False and all AI fields as None
