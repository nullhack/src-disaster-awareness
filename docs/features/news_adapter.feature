Feature: News Adapter

  Provides supplementary context search via DuckDuckGo News using the ddgs package's
  DDGS.news() function. Used after initial classification to find additional articles
  for bundles missing country or disaster type data. Implements the NewsSearcher
  protocol. Returns RawRecords with source_name="DDG-NEWS". Search query is generated
  from bundle fields: "{title} {country} {disaster_type} latest news" with fallbacks
  for unknown fields.

  # Business rules:
  # - NewsSearcher never raises on failure — network failure, empty results, and API
  #   errors all return empty list
  # - Supplementary search query uses worst-case template when nothing is known:
  #   "disaster incident disaster emergency latest news" is a valid query per spec
  # - Adapter never raises on HTTP errors — returns empty list on failure
  # - Adapter never raises on network failure — returns empty list on failure
  # - source_name is exactly "DDG-NEWS" for all records from this adapter

  # Constraints:
  # - Reliability: DDG News search failure must not block pipeline — bundles proceed
  #   to AI enrichment and storage with whatever context is available
