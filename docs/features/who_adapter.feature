Feature: WHO Adapter

  Fetches disease outbreak reports from the WHO Disease Outbreak News OData REST API and
  converts them into RawRecords. WHO has ~30% deterministic field availability — there
  is NO structured country or disaster type field. Country and disaster type must be
  extracted from Title/Overview text via AI or regex. The ItemDefaultUrl field is a
  relative path requiring "https://www.who.int" prefix for a full URL.

  Rule: HTTP errors return empty list
    The adapter never raises on HTTP errors. HTTP 5xx, 429, and timeout all return
    an empty list.

    Scenario Outline: Server error produces empty list
      Given the WHO API responds with HTTP status <status_code>
      When the adapter fetches records
      Then the adapter returns an empty list

      Examples:
        | status_code |
        | 500         |
        | 503         |
        | 429         |

    Example: Request timeout yields empty list
      Given the WHO API times out
      When the adapter fetches records
      Then the adapter returns an empty list

  Rule: Network failure returns empty list
    The adapter never raises on network failure. Connection refused and DNS failure
    return an empty list.

    Scenario Outline: Connection failure produces empty list
      Given the WHO API connection fails with <error_type>
      When the adapter fetches records
      Then the adapter returns an empty list

      Examples:
        | error_type          |
        | connection refused  |
        | DNS failure         |
        | network unreachable |

  Rule: Partial parse succeeds for valid records
    The adapter skips malformed records and returns successfully parsed valid ones.
    A partially malformed OData response still produces records for well-formed
    entries.

    Example: Malformed records are silently skipped
      Given the WHO API response contains one valid and one malformed record
      When the adapter fetches records
      Then the adapter returns one record

    Example: All malformed yields empty list
      Given the WHO API response contains only malformed records
      When the adapter fetches records
      Then the adapter returns an empty list

  Rule: Raw fields preserve complete API response
    raw_fields preserves the complete, untouched OData API response per record with
    no normalization or field removal.

    Example: Complete API response is preserved
      Given the WHO API returns a disease outbreak record
      When the adapter parses the response
      Then raw fields contains all API response fields

  Rule: Source name is exactly WHO
    source_name is exactly "WHO" for all records produced by this adapter.

    Example: Source name is always WHO
      Given the WHO adapter fetches from the API
      When a raw record is produced
      Then the source name is "WHO"

  # Constraints:
  # - Reliability: WHO API down must not affect GDACS, GDELT, or DDG News adapters —
  #   each adapter returns empty list on failure and pipeline continues
