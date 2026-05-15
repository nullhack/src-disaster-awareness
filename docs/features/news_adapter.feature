Feature: News Adapter

  Provides supplementary context search via DuckDuckGo News using the ddgs package's
  DDGS.news() function. Used after initial classification to find additional articles
  for bundles missing country or disaster type data. Implements the NewsSearcher
  protocol. Returns RawRecords with source_name="DDG-NEWS". Search query is generated
  from bundle fields: "{title} {country} {disaster_type} latest news" with fallbacks
  for unknown fields.

  Rule: Failure returns empty list

    Scenario Outline: DDG News search failure returns empty list
      Given a DDG News search request
      When the search encounters "<failure_kind>"
      Then the search returns an empty list

      Examples:
        | failure_kind            |
        | "network error"         |
        | "HTTP server error"     |
        | "unexpected exception"  |

  Rule: Worst case query uses default template

    Example: DDG News worst case query default template
      Given a bundle with no title and no country and no disaster type
      When the supplementary search query is generated
      Then the query is "disaster incident disaster emergency latest news"

    Example: DDG News partial info query includes fallbacks
      Given a bundle with title "Earthquake detected" and no country and no disaster type
      When the supplementary search query is generated
      Then the query is "Earthquake detected disaster emergency latest news"

  Rule: Records have source name DDG-NEWS

    Example: DDG News records source name verified
      Given a successful DDG News search returning multiple articles
      When the search results are processed
      Then every record has source name "DDG-NEWS"

  # Constraints:
  # - Reliability: DDG News search failure must not block pipeline — bundles proceed
  #   to AI enrichment and storage with whatever context is available
