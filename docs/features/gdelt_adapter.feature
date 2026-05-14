Feature: GDELT Adapter

  Fetches global news articles from the GDELT DOC API (ArtList mode) and converts them
  into RawRecords. GDELT has ~20% deterministic field availability. ArtList mode has no
  tone field — level derivation uses title keyword scan instead of tone scores. The
  sourcecountry field is where the news source is located, NOT where the incident
  occurred. Incident country must be extracted from title text.

  # Business rules:
  # - Adapter never raises on HTTP errors — HTTP 5xx, 429, and timeout all return empty
  #   list
  # - Adapter never raises on network failure — connection refused, DNS failure return
  #   empty list
  # - Adapter skips malformed records and returns successfully parsed valid ones —
  #   partial parse succeeds for well-formed entries
  # - raw_fields preserves the complete, untouched DOC API response per record
  # - source_name is exactly "GDELT" for all records from this adapter

  # Constraints:
  # - Reliability: GDELT API down must not affect GDACS, WHO, or DDG News adapters —
  #   each adapter returns empty list on failure and pipeline continues
