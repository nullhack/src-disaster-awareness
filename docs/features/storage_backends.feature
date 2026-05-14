Feature: Storage Backends

  Persists complete IncidentBundles (all raw records + classification + enrichment) using
  two interchangeable backends implementing the StorageBackend protocol: JSONLStore
  (default, append-only, date-partitioned files) and SQLiteStore (alternative, atomic
  transactions). Queries return flattened Incident records filterable by date range,
  country group, disaster type, priority, should_report, and source name. Deduplication
  by incident_id prevents duplicate entries across pipeline runs.

  # Business rules:
  # - JSONL files are date-partitioned at incidents/by-date/YYYY-MM-DD/ using
  #   classification_date (earliest incident_date from bundle records, fallback to
  #   fetched_at date)
  # - Dedup by incident_id: store() skips bundles with existing IDs and returns count
  #   of new bundles only
  # - Query returns flattened Incident records, not raw IncidentBundles — no raw_records
  #   in output
  # - Malformed JSONL lines are skipped with a warning — partial data loss is tolerated
  # - Storage preserves complete IncidentBundles including all raw records — full
  #   fidelity persistence
  # - SQLiteStore implements the same StorageBackend protocol as JSONLStore with atomic
  #   transactions instead of temp file + rename
  # - Query filter by country_group returns only incidents in the specified group
  # - Query filter by disaster_type returns only incidents matching the type
  # - Query filter by priority returns only incidents at the specified priority level
  # - Query filter by should_report returns only reportable or non-reportable incidents
  # - Query filter by source_name matches incidents containing that source in the
  #   source_names list
  # - exists() returns bool with no errors and no side effects — used for dedup check
  #   before store
  # - Storage writes must be atomic: JSONLStore uses temp file + rename, SQLiteStore
  #   uses transactions. If write fails, original data remains intact
  # - Storage write failure on one bundle must not prevent storage of other bundles
  # - Inverted date range (date_from > date_to) returns empty list, not an error
  # - incident_name derived from highest-reliability source title, with fallback to
  #   "{disaster_type} in {country} ({date})" using "Unknown" placeholders
  # - source_urls collected from raw_fields: WHO uses ItemDefaultUrl (prepend
  #   https://www.who.int), GDELT uses url, DDG-NEWS uses url, GDACS uses
  #   url.report from url dict. May be empty — not an error

  # Constraints:
  # - Performance: 50 incidents classified and stored without AI completes in under 5
  #   seconds (~65ms estimated, orders of magnitude faster than target)
  # - Testability: both JSONLStore and SQLiteStore must be tested against the same
  #   StorageBackend protocol with identical query semantics
