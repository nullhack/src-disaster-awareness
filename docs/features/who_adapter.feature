Feature: WHO Adapter

  Fetches disease outbreak reports from the WHO Disease Outbreak News OData REST API and
  converts them into RawRecords. WHO has ~30% deterministic field availability — there
  is NO structured country or disaster type field. Country and disaster type must be
  extracted from Title/Overview text via AI or regex. The ItemDefaultUrl field is a
  relative path requiring "https://www.who.int" prefix for a full URL.

  Rule: HTTP errors return empty list
    The adapter never raises on HTTP errors. HTTP 5xx, 429, and timeout all return
    an empty list.

  Rule: Network failure returns empty list
    The adapter never raises on network failure. Connection refused and DNS failure
    return an empty list.

  Rule: Partial parse succeeds for valid records
    The adapter skips malformed records and returns successfully parsed valid ones.
    A partially malformed OData response still produces records for well-formed
    entries.

  Rule: Raw fields preserve complete API response
    raw_fields preserves the complete, untouched OData API response per record with
    no normalization or field removal.

  Rule: Source name is exactly WHO
    source_name is exactly "WHO" for all records produced by this adapter.

  # Constraints:
  # - Reliability: WHO API down must not affect GDACS, GDELT, or DDG News adapters —
  #   each adapter returns empty list on failure and pipeline continues
