Feature: WHO Adapter

  Fetches disease outbreak reports from the WHO Disease Outbreak News OData REST API and
  converts them into RawRecords. WHO has ~30% deterministic field availability — there
  is NO structured country or disaster type field. Country and disaster type must be
  extracted from Title/Overview text via AI or regex. The ItemDefaultUrl field is a
  relative path requiring "https://www.who.int" prefix for a full URL.

  # Business rules:
  # - Adapter never raises on HTTP errors — HTTP 5xx, 429, and timeout all return empty
  #   list
  # - Adapter never raises on network failure — connection refused, DNS failure return
  #   empty list
  # - Adapter skips malformed records and returns successfully parsed valid ones —
  #   partial parse succeeds for well-formed entries
  # - raw_fields preserves the complete, untouched OData API response per record
  # - source_name is exactly "WHO" for all records from this adapter

  # Constraints:
  # - Reliability: WHO API down must not affect GDACS, GDELT, or DDG News adapters —
  #   each adapter returns empty list on failure and pipeline continues
