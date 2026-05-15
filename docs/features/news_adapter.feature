Feature: News Adapter

  Provides supplementary context search via DuckDuckGo News using the ddgs package's
  DDGS.news() function. Used after initial classification to find additional articles
  for bundles missing country or disaster type data. Implements the NewsSearcher
  protocol. Returns RawRecords with source_name="DDG-NEWS". Search query is generated
  from bundle fields: "{title} {country} {disaster_type} latest news" with fallbacks
  for unknown fields.

  Rule: Failure returns empty list

  Rule: Worst case query uses default template

  Rule: Records have source name DDG-NEWS

  # Constraints:
  # - Reliability: DDG News search failure must not block pipeline — bundles proceed
  #   to AI enrichment and storage with whatever context is available
