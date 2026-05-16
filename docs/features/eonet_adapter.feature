Feature: EONET Adapter

  Fetches curated natural event metadata from the NASA EONET v3 REST API and converts
  them into RawRecords. EONET provides structured event data with ~60% deterministic
  field availability: disaster type from categories array, date from geometry array,
  title verbatim. Country and impact estimates must be extracted via AI. Events with
  GDACS-sourced data (source.id == "GDACS") are duplicates of the GDACS adapter and
  are filtered out. Events with "Prescribed Fire" or "RX" in the title are controlled
  burns and are filtered out. Replaces the unreachable GDELT DOC API as the third
  primary data source.

  Rule: HTTP errors return empty list

    The adapter handles HTTP 5xx responses, HTTP 429 rate limiting, and request timeouts
    by returning an empty list of RawRecords without raising exceptions.

    Scenario Outline: EONET server error produces empty list
      Given the EONET API responds with HTTP status <status_code>
      When the adapter fetches records
      Then the adapter returns an empty list

      Examples:
        | status_code |
        | 500         |
        | 503         |
        | 429         |

    Example: EONET request timeout yields empty list
      Given the EONET API times out
      When the adapter fetches records
      Then the adapter returns an empty list

  Rule: Network failures return no records

    The adapter handles network-level failures including connection refused and DNS
    resolution failures by returning an empty list of RawRecords without raising
    exceptions.

    Scenario Outline: EONET connection failure produces empty list
      Given the EONET API connection fails with <error_type>
      When the adapter fetches records
      Then the adapter returns an empty list

      Examples:
        | error_type          |
        | connection refused  |
        | DNS failure         |
        | network unreachable |

  Rule: Partial parse returns valid records

    When the EONET API response contains a mix of well-formed and malformed event
    records, the adapter skips the malformed entries and returns the successfully
    parsed valid records. A response with no parseable records returns an empty list.

    Example: EONET malformed records are silently skipped
      Given the EONET API response contains one valid and one malformed event
      When the adapter fetches records
      Then the adapter returns one record

    Example: EONET all malformed yields empty list
      Given the EONET API response contains only malformed events
      When the adapter fetches records
      Then the adapter returns an empty list

  Rule: raw_fields preserves untouched API response

    Each RawRecord's raw_fields dict contains the complete, unmodified EONET v3 API
    event object. No normalization, field removal, or transformation is applied.

    Example: EONET API response is preserved verbatim
      Given the EONET API returns an event record
      When the adapter parses the response
      Then raw fields contains all API response fields including id title categories sources geometry

  Rule: source_name is exactly EONET

    Every RawRecord produced by this adapter has its source_name field set to the exact
    string "EONET".

    Example: Source name is always EONET
      Given the EONET adapter fetches from the API
      When a raw record is produced
      Then the source name is "EONET"

  Rule: GDACS sourced events excluded as duplicates

    Events where any entry in the sources array has id equal to "GDACS" are filtered
    out and not returned as RawRecords. The GDACS adapter provides higher-fidelity
    structured data for the same real-world event. This deduplication is applied at the
    adapter level before records enter correlation.

    Example: EONET event with GDACS source is skipped
      Given the EONET API returns an event with source id GDACS
      When the adapter fetches records
      Then the event is not in the returned records

    Example: EONET event without GDACS source returns normally
      Given the EONET API returns an event with only source id EO
      When the adapter fetches records
      Then the event is in the returned records

  Rule: Prescribed fires filtered as controlled burns

    Events where the title contains "Prescribed Fire" or "RX" (case-insensitive) are
    filtered out and not returned as RawRecords. These are controlled managed burns,
    not disaster events.

    Scenario Outline: Prescribed fire event is filtered
      Given the EONET API returns an event with title containing <fire_pattern>
      When the adapter fetches records
      Then the event is not in the returned records

      Examples:
        | fire_pattern      |
        | Prescribed Fire   |
        | RX Burn Project   |

    Example: Wildfire event without prescribed fire keywords returns normally
      Given the EONET API returns an event with title "Wildfire in California"
      When the adapter fetches records
      Then the event is in the returned records

  Rule: Source fingerprint is EONET colon id

    The source fingerprint for each EONET record uses the format EONET:{id} where id
    is the EONET event ID string (e.g., EONET:EONET_20104). The ID is extracted from
    the id field of the EONET event.

    Example: EONET record fingerprint format
      Given an EONET event with id EONET_20104
      When the source fingerprint is computed
      Then the fingerprint is "EONET:EONET_20104"

  Rule: Disaster type is derived from categories

    The disaster type for each EONET event is derived from the categories array.
    Mapping: earthquakes→EQ, floods→FL, volcanoes→VO, wildfires→WF,
    severeStorms→TC, droughts→DR, landslides→LS. Unrecognized categories are
    treated as unknown disaster type.

    Scenario Outline: EONET category maps to disaster type code
      Given an EONET event with category <category_title>
      When the disaster type is derived
      Then the type code is <type_code>

      Examples:
        | category_title | type_code |
        | Earthquakes    | EQ        |
        | Floods         | FL        |
        | Volcanoes      | VO        |
        | Wildfires      | WF        |
        | Severe Storms  | TC        |
        | Drought        | DR        |
        | Landslides     | LS        |

  # Constraints:
  # - Reliability: EONET API down must not affect GDACS, WHO, or DDG News adapters —
  #   each adapter returns empty list on failure and pipeline continues
  # - Data Integrity: GDACS-sourced EONET events are deduplicated via source.id check
  #   at the adapter level, preventing duplicate entries in correlation
  # - Maintainability: EONETAdapter implements the same SourceAdapter protocol as all
  #   other adapters, requiring zero changes to core pipeline
