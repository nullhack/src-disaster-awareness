Feature: Domain Types

  Shared data structures (RawRecord, IncidentBundle, Incident) used across all
  five bounded contexts. These are the pipeline's internal language — RawRecord
  carries untouched source data, IncidentBundle groups records about one real-world
  incident and accumulates classification and enrichment state, and Incident provides
  a flattened view for storage queries. Defined in types.py as the shared kernel.

  Rule: raw_fields preserves the complete untouched API response
    # No normalization, no field removal — downstream contexts handle missing fields gracefully

    Example: GDACS adapter response stored without modification
      Given a GDACS adapter has fetched an earthquake alert with fields eventtype, alertlevel, name, country, iso3, fromdate, url, and severitydata
      When the adapter creates a RawRecord from the API response
      Then the raw_fields dict contains every field exactly as returned by the API including nested dicts

  Rule: source_name must exactly match the adapter identity

    Example: GDACS adapter assigns source_name GDACS
      Given a GDACS adapter has fetched data from the GDACS API
      When the adapter creates a RawRecord
      Then the source_name is "GDACS"

  Rule: ai_enriched is False means all AI fields are None

    Example: unenriched bundle has no AI generated values
      Given an IncidentBundle where ai_enriched is False
      Then summary is None and rationale is None and estimated_affected is None and estimated_deaths is None

  Rule: incident_id uses date country type format with UNX for unknown country and OTH for unknown type

    Scenario Outline: incident_id format varies by country and type
      Given an IncidentBundle whose earliest record date is 2026-05-14 with country <country> and disaster_type <disaster_type>
      When the incident_id is generated
      Then the incident_id is "<expected_id>"

      Examples:
        | country     | disaster_type | expected_id     |
        | Philippines | Earthquake    | 20260514-PH-EQ  |
        | unknown     | Flood         | 20260514-UNX-FL |
        | Indonesia   | unknown       | 20260514-ID-OTH |

  Rule: incident_id is stable identity that never changes after generation

    Example: incident_id unchanged after AI enrichment fills missing country and type
      Given an IncidentBundle with incident_id "20260514-UNX-OTH"
      When AI enrichment fills in country as Japan and disaster_type as Earthquake
      Then the incident_id remains "20260514-UNX-OTH"

  Rule: every RawRecord from the primary fetch is assigned to exactly one IncidentBundle

    Example: all fetched records appear in bundles with no duplicates or orphans
      Given a primary fetch returns 5 RawRecords from GDACS, WHO, and GDELT
      When the correlator groups the records into IncidentBundles
      Then each of the 5 RawRecords appears in exactly one IncidentBundle

  Rule: an IncidentBundle must contain at least one RawRecord

    Example: singleton bundle created from a single uncorrelated record
      Given a single RawRecord from GDELT with no matching records from other sources
      When the correlator processes the record
      Then an IncidentBundle is created containing that one RawRecord

  # Constraints:
  # - Testability: data shapes must support 100% rule coverage for all downstream
  #   classification, correlation, and storage rules
  # - Maintainability: adding a new source adapter requires zero changes to shared types
  #   — new adapters implement existing protocols without modifying types.py
