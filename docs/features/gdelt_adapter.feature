Feature: GDELT Adapter

  Fetches global news articles from the GDELT DOC API (ArtList mode) and converts them
  into RawRecords. GDELT has ~20% deterministic field availability. ArtList mode has no
  tone field — level derivation uses title keyword scan instead of tone scores. The
  sourcecountry field is where the news source is located, NOT where the incident
  occurred. Incident country must be extracted from title text.

  Rule: HTTP errors return empty list

    The adapter handles HTTP 5xx responses, HTTP 429 rate limiting, and request timeouts
    by returning an empty list of RawRecords without raising exceptions.

  Rule: Network failures return no records

    The adapter handles network-level failures including connection refused and DNS
    resolution failures by returning an empty list of RawRecords without raising
    exceptions.

  Rule: Partial parse returns valid records

    When the GDELT DOC API response contains a mix of well-formed and malformed records,
    the adapter skips the malformed entries and returns the successfully parsed valid
    records. A response with no parseable records returns an empty list.

  Rule: raw_fields preserves untouched API response

    Each RawRecord's raw_fields dict contains the complete, unmodified GDELT DOC API
    response for that article. No normalization, field removal, or transformation is
    applied.

  Rule: source_name is exactly GDELT

    Every RawRecord produced by this adapter has its source_name field set to the exact
    string "GDELT".

  # Constraints:
  # - Reliability: GDELT API down must not affect GDACS, WHO, or DDG News adapters —
  #   each adapter returns empty list on failure and pipeline continues
