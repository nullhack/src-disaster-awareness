Feature: Domain Types

  Shared data structures (RawRecord, IncidentBundle, Incident) used across all
  five bounded contexts. These are the pipeline's internal language — RawRecord
  carries untouched source data, IncidentBundle groups records about one real-world
  incident and accumulates classification and enrichment state, and Incident provides
  a flattened view for storage queries. Defined in types.py as the shared kernel.

  # Business rules:
  # - raw_fields preserves the complete, untouched API response with no normalization
  #   or field removal, enabling downstream contexts to handle missing fields gracefully
  # - source_name in each record must exactly match the adapter's identity: "GDACS",
  #   "WHO", "GDELT", or "DDG-NEWS"
  # - ai_enriched=False means all AI fields (summary, rationale, estimated_affected,
  #   estimated_deaths) are None
  # - IncidentBundle.incident_id follows YYYYMMDD-CC-TTT format with "UNX" for unknown
  #   country and "OTH" for unknown disaster type
  # - incident_id is stable identity — once generated, it must not change even if AI
  #   enrichment fills in missing fields
  # - Every RawRecord from the primary fetch must be assigned to exactly one
  #   IncidentBundle
  # - An IncidentBundle must contain at least one RawRecord

  # Constraints:
  # - Testability: data shapes must support 100% rule coverage for all downstream
  #   classification, correlation, and storage rules
  # - Maintainability: adding a new source adapter requires zero changes to shared types
  #   — new adapters implement existing protocols without modifying types.py
