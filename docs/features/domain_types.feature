Feature: Domain Types

  Shared data structures (RawRecord, IncidentBundle, Incident) used across all
  five bounded contexts. These are the pipeline's internal language — RawRecord
  carries untouched source data, IncidentBundle groups records about one real-world
  incident and accumulates classification and enrichment state, and Incident provides
  a flattened view for storage queries. Defined in types.py as the shared kernel.

  Rule: raw_fields preserves the complete untouched API response
    # No normalization, no field removal — downstream contexts handle missing fields gracefully

  Rule: source_name must exactly match the adapter identity

  Rule: ai_enriched is False means all AI fields are None

  Rule: incident_id follows YYYYMMDD-CC-TTT format with UNX for unknown country and OTH for unknown type

  Rule: incident_id is stable identity that never changes after generation

  Rule: every RawRecord from the primary fetch is assigned to exactly one IncidentBundle

  Rule: an IncidentBundle must contain at least one RawRecord

  # Constraints:
  # - Testability: data shapes must support 100% rule coverage for all downstream
  #   classification, correlation, and storage rules
  # - Maintainability: adding a new source adapter requires zero changes to shared types
  #   — new adapters implement existing protocols without modifying types.py
