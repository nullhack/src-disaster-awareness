Feature: GDACS Adapter

  Fetches natural disaster alerts from the GDACS GeoJSON REST API and converts them
  into RawRecords. GDACS is the most reliable source for structured fields, providing
  ~90% deterministic field availability including alertlevel (Green/Orange/Red), eventtype,
  iso3 country code, and affectedcountries list. The url field is a dict containing
  geometry, report, and details URLs. The istemporary field is a string ("true"/"false"),
  not a boolean.

  # Business rules:
  # - Adapter never raises on HTTP errors — HTTP 5xx, 429, and timeout all return empty
  #   list
  # - Adapter never raises on network failure — connection refused, DNS failure return
  #   empty list
  # - Adapter skips malformed records and returns successfully parsed valid ones —
  #   partial parse succeeds for well-formed entries
  # - raw_fields preserves the complete, untouched GeoJSON API response per record
  # - source_name is exactly "GDACS" for all records from this adapter

  # Constraints:
  # - Reliability: GDACS API down must not affect WHO, GDELT, or DDG News adapters —
  #   each adapter returns empty list on failure and pipeline continues
