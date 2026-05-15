Feature: Storage Backends

  Persists complete IncidentBundles (all raw records + classification + enrichment) using
  two interchangeable backends implementing the StorageBackend protocol: JSONLStore
  (default, append-only, date-partitioned files) and SQLiteStore (alternative, atomic
  transactions). Queries return flattened Incident records filterable by date range,
  country group, disaster type, priority, should_report, and source name. Deduplication
  by incident_id prevents duplicate entries across pipeline runs.

  Rule: JSONL files are date partitioned
    JSONL files are stored at incidents/by-date/YYYY-MM-DD/incidents.jsonl. The
    partition date is classification_date — the earliest incident_date from the
    bundle's records at classification time, with fallback to fetched_at date if
    no incident_date is available.

  Rule: Dedup skips existing incident IDs
    store() checks exists(incident_id) before persisting each bundle. Bundles with
    incident IDs already present in storage are skipped. store() returns the count
    of genuinely new bundles stored, excluding duplicates.

  Rule: Query returns flattened Incident records
    query() returns list[Incident] — a flattened view of stored data, not raw
    IncidentBundle objects. query() output contains no raw_records field.

  Rule: Malformed JSONL lines skipped with warning
    When reading JSONL files during query(), any malformed or unparseable lines
    are logged as warnings and skipped. The remaining valid lines are processed.
    Partial data loss from corrupted lines is tolerated.

  Rule: Storage preserves complete IncidentBundles
    Storage persists the full IncidentBundle including all raw records,
    classification fields, enrichment fields, and metadata. Full fidelity
    persistence — no fields are discarded during store().

  Rule: SQLiteStore matches StorageBackend protocol
    SQLiteStore implements the same StorageBackend protocol as JSONLStore with
    identical store(), query(), and exists() method signatures. SQLiteStore uses
    atomic database transactions instead of the temp-file-and-rename strategy
    used by JSONLStore.

  Rule: Filter query by country group
    query(country_group="A") returns only incidents whose country_group field
    matches the specified value. Acceptable values are "A", "B", or "C".

  Rule: Filter query by disaster type
    query(disaster_type="EQ") returns only incidents whose disaster_type field
    matches the specified type string.

  Rule: Filter query by priority
    query(priority="HIGH") returns only incidents whose priority field matches
    the specified level. Acceptable values are "HIGH", "MED", or "LOW".

  Rule: Filter query by should report
    query(should_report=True) returns only incidents whose should_report field
    matches the specified boolean value.

  Rule: Filter query by source name
    query(source_name="GDACS") returns only incidents whose source_names list
    contains the specified source name string.

  Rule: Exists returns bool no side effects
    exists(incident_id) returns True if the given incident ID is already stored,
    False otherwise. No errors are raised and no side effects occur. This method
    is used for deduplication checks before calling store().

  Rule: Storage writes must be atomic
    JSONLStore writes to a temporary file first, then atomically renames it to
    the target path only on successful completion. SQLiteStore wraps writes in a
    database transaction with COMMIT on success and ROLLBACK on failure. If a
    write fails at any point, the original data remains intact and unchanged.

  Rule: Write failure isolates per bundle
    A storage write failure for one bundle MUST NOT prevent the storage of other
    bundles in the same batch. Each bundle write is independent and failures are
    isolated.

  Rule: Inverted date range returns empty list
    When date_from > date_to in a query call, return an empty list. No error is
    raised, no date swapping occurs, and no automatic correction is applied.

  Rule: Incident name from most reliable source
    incident_name is derived by using the title from the highest-reliability
    source's raw_fields, in order: GDACS, WHO, GDELT, DDG-NEWS. If no source
    provides a title, a synthetic name is generated as
    "{disaster_type} in {country} ({date})" using "Unknown disaster" and
    "Unknown location" placeholders for any missing fields.

  Rule: Source URLs collected per source
    source_urls is built by collecting URL fields from each record's raw_fields:
    WHO uses ItemDefaultUrl (prepend https://www.who.int), GDELT uses url,
    DDG-NEWS uses url, GDACS uses url.report from the url dict. The resulting
    list may be empty — an empty list is not an error.

  # Constraints:
  # - Performance: 50 incidents classified and stored without AI completes in under 5
  #   seconds (~65ms estimated, orders of magnitude faster than target)
  # - Testability: both JSONLStore and SQLiteStore must be tested against the same
  #   StorageBackend protocol with identical query semantics
