Feature: Incident Identity

  Source-stable incident identifiers that remain consistent across pipeline runs,
  source fingerprint deduplication that prevents the same record from being
  processed twice, and lifecycle modification timestamps for active monitoring.
  These identity and dedup mechanisms span the shared kernel (IncidentBundle data
  shape) and Correlation contexts, providing the foundation for incident lifecycle
  management. Key entities: IncidentBundle.incident_id, source_fingerprints, last_updated.

  Rule: Incident ID Uses Source Dates
    The incident_id date component (YYYYMMDD) uses the earliest source-provided
    date from any record in the bundle. Source date fields: GDACS fromdate,
    WHO PublicationDate, GDELT seendate, DDG-NEWS date. If no source-provided
    date is available from any record, fall back to fetched_at (the pipeline
    run time). Using source dates makes IDs stable across pipeline runs — the
    same source article produces the same ID regardless of when it was fetched.

    Scenario Outline: source date field recognized
      Given a record from "<source>" with source date "<raw_date>"
      When the incident id date component is computed
      Then the date component is "<date_component>"

      Examples:
        | source    | raw_date            | date_component |
        | GDACS     | 2026-05-14          | 20260514      |
        | WHO       | 2026-05-13          | 20260513      |
        | GDELT     | 20260512T120000z    | 20260512      |
        | DDG-NEWS  | 2026-05-11          | 20260511      |

    Example: earliest source date wins
      Given a bundle with GDACS fromdate "2026-05-14" ; WHO PublicationDate "2026-05-13"
      When the incident id date component is computed
      Then the date component is "20260513"

    Example: no source date falls back
      Given a bundle with no source provided dates and fetched at "2026-05-15"
      When the incident id date component is computed
      Then the date component is "20260515"

  Rule: Incident ID Format Stable
    incident_id follows the format YYYYMMDD-CC-TTT where CC is the ISO 3166-1
    alpha-2 country code and TTT is the 3-character disaster type code. When
    country is unknown, use "UNX". When disaster type is unknown, use "OTH".

    Scenario Outline: incident id format stable
      Given a bundle with earliest source date "<source_date>"; country code "<country_code>"; disaster type "<type_code>"
      When the incident_id is generated
      Then the incident_id is "<expected_id>"

      Examples:
        | source_date | country_code | type_code | expected_id       |
        | 2026-05-14  | PH           | EQ        | 20260514-PH-EQ    |
        | 2026-05-14  | UNX          | FL        | 20260514-UNX-FL   |
        | 2026-05-14  | ID           | OTH       | 20260514-ID-OTH   |

  Rule: Incident ID Never Changes
    incident_id is stable identity — once generated at correlation time, it must
    not change even if later pipeline steps fill in missing fields. AI enrichment
    that discovers a country or disaster type previously unknown does not trigger
    incident_id regeneration. The original UNX or OTH placeholders remain.

    Example: incident_id unchanged after AI enrichment
      Given an IncidentBundle with incident_id "20260514-UNX-OTH"
      When AI enrichment fills country as "Japan" and disaster_type as "Earthquake"
      Then the incident_id remains "20260514-UNX-OTH"

  Rule: Source Fingerprint Format
    Each source fingerprint is a globally unique identifier for a single source
    record, formatted as {SOURCE_NAME}:{native_id}. SOURCE_NAME is one of
    "GDACS", "WHO", "GDELT", or "DDG-NEWS". native_id is source-specific:
    GDACS uses eventid, WHO uses Id or DonId, GDELT uses url, DDG-NEWS uses url.
    The source_fingerprints list on IncidentBundle contains one fingerprint per
    record in the bundle.

    Scenario Outline: source fingerprint is formatted correctly
      Given a RawRecord from "<source>" with native identifier "<native_id>"
      When the source fingerprint is computed
      Then the fingerprint is "<fingerprint>"

      Examples:
        | source    | native_id                                    | fingerprint                                    |
        | GDACS     | 12345                                        | GDACS:12345                                    |
        | WHO       | abc-def-456                                  | WHO:abc-def-456                                |
        | GDELT     | https://reuters.com/article/xyz              | GDELT:https://reuters.com/article/xyz          |
        | DDG-NEWS  | https://news.example.com/article/abc         | DDG-NEWS:https://news.example.com/article/abc  |

  Rule: Last Updated Timestamp
    last_updated records the most recent modification time of the bundle. It is
    set at bundle creation (correlation time). It is reset only when new data is
    added to the bundle — new DDG News articles, new primary source records, or
    any new source fingerprints. It is NOT reset when the pipeline processes a
    bundle but finds no new fingerprints. This field drives the active monitoring
    window: bundles with now - last_updated ≤ 7 days are ACTIVE, bundles with
    now - last_updated > 7 days are STALE.

    Example: last updated set at creation
      Given a new IncidentBundle at correlation time "2026-05-15T10:00:00Z"
      When the bundle is created
      Then the last_updated is "2026-05-15T10:00:00Z"

    Example: last updated reset on new data
      Given a bundle in storage with last_updated "2026-05-14T00:00:00Z"
      When new source fingerprints are added at "2026-05-15T10:00:00Z"
      Then the last_updated is "2026-05-15T10:00:00Z"

    Example: last_updated unchanged when no new fingerprints
      Given a bundle in storage with last_updated set to "2026-05-14"
      When the pipeline processes the bundle and finds no new source fingerprints
      Then the last_updated remains "2026-05-14"

    Example: active status within seven day boundary
      Given a bundle in storage with last_updated set to "2026-05-09" and current date "2026-05-15"
      When the active status is checked
      Then the bundle is active

    Example: stale status beyond seven day boundary
      Given a bundle in storage with last_updated set to "2026-05-07" and current date "2026-05-15"
      When the active status is checked
      Then the bundle is stale

    Example: unparseable source date falls back
      Given a record from GDACS with corrupt fromdate "unknown"
      When the incident id date component is computed
      Then the fallback date is used

  # Constraints:
  # - Reproducibility: source-stable IDs ensure same source article always produces
  #   same incident_id across repeated pipeline runs, enabling byte-identical output
  #   from identical input fixtures
  # - Data Integrity: source fingerprints uniquely identify each record, preventing
  #   the same source record from being stored in two different bundles
  # - Testability: incident_id generation and source fingerprint computation must have
  #   dedicated test coverage including boundary cases (unknown country, unknown type,
  #   missing source date)
