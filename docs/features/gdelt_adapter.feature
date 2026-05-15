Feature: GDELT Adapter

  Fetches global news articles from the GDELT DOC API (ArtList mode) and converts them
  into RawRecords. GDELT has ~20% deterministic field availability. ArtList mode has no
  tone field — level derivation uses title keyword scan instead of tone scores. The
  sourcecountry field is where the news source is located, NOT where the incident
  occurred. Incident country must be extracted from title text.

  Rule: HTTP errors return empty list

    The adapter handles HTTP 5xx responses, HTTP 429 rate limiting, and request timeouts
    by returning an empty list of RawRecords without raising exceptions.

    Scenario Outline: Server error produces empty list
      Given the GDELT API responds with HTTP status <status_code>
      When the adapter fetches records
      Then the adapter returns an empty list

      Examples:
        | status_code |
        | 500         |
        | 503         |
        | 429         |

    Example: Request timeout yields empty list
      Given the GDELT API times out
      When the adapter fetches records
      Then the adapter returns an empty list

  Rule: Network failures return no records

    The adapter handles network-level failures including connection refused and DNS
    resolution failures by returning an empty list of RawRecords without raising
    exceptions.

    Scenario Outline: Connection failure produces empty list
      Given the GDELT API connection fails with <error_type>
      When the adapter fetches records
      Then the adapter returns an empty list

      Examples:
        | error_type          |
        | connection refused  |
        | DNS failure         |
        | network unreachable |

  Rule: Partial parse returns valid records

    When the GDELT DOC API response contains a mix of well-formed and malformed records,
    the adapter skips the malformed entries and returns the successfully parsed valid
    records. A response with no parseable records returns an empty list.

    Example: Malformed records are silently skipped
      Given the GDELT API response contains one valid and one malformed record
      When the adapter fetches records
      Then the adapter returns one record

    Example: All malformed yields empty list
      Given the GDELT API response contains only malformed records
      When the adapter fetches records
      Then the adapter returns an empty list

  Rule: raw_fields preserves untouched API response

    Each RawRecord's raw_fields dict contains the complete, unmodified GDELT DOC API
    response for that article. No normalization, field removal, or transformation is
    applied.

    Example: Complete API response is preserved
      Given the GDELT API returns a news article record
      When the adapter parses the response
      Then raw fields contains all API response fields

  Rule: source_name is exactly GDELT

    Every RawRecord produced by this adapter has its source_name field set to the exact
    string "GDELT".

    Example: Source name is always GDELT
      Given the GDELT adapter fetches from the API
      When a raw record is produced
      Then the source name is "GDELT"

  # Constraints:
  # - Reliability: GDELT API down must not affect GDACS, WHO, or DDG News adapters —
  #   each adapter returns empty list on failure and pipeline continues
