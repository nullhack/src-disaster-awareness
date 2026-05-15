Feature: GDACS Adapter

  Fetches natural disaster alerts from the GDACS GeoJSON REST API and converts them
  into RawRecords. GDACS is the most reliable source for structured fields, providing
  ~90% deterministic field availability including alertlevel (Green/Orange/Red), eventtype,
  iso3 country code, and affectedcountries list. The url field is a dict containing
  geometry, report, and details URLs. The istemporary field is a string ("true"/"false"),
  not a boolean.

  Rule: Adapter Never Raises On HTTP Errors
    The adapter must return an empty list when the GDACS API returns HTTP 5xx,
    429 (rate limit), or times out, without raising any exception.

  Rule: Adapter Never Raises On Network Failure
    The adapter must return an empty list on connection refused, DNS resolution
    failure, or any other network-level error, without raising any exception.

  Rule: Adapter Skips Malformed Records
    The adapter must skip GeoJSON features that cannot be parsed, returning only
    successfully parsed records. A feed with some malformed entries must still
    produce valid RawRecords for the well-formed entries.

  Rule: Raw Fields Preserves Untouched GeoJSON Response
    Each RawRecord.raw_fields must contain the complete, untouched geometry
    properties from a single GeoJSON feature. No normalization, filtering,
    renaming, or transformation is applied — the API response is preserved
    verbatim.

  Rule: Source Name Is Exactly GDACS
    Every RawRecord produced by this adapter must have source_name equal to the
    string "GDACS" with exact casing, no abbreviations or variations.

  # Constraints:
  # - Reliability: GDACS API down must not affect WHO, GDELT, or DDG News adapters —
  #   each adapter returns empty list on failure and pipeline continues
