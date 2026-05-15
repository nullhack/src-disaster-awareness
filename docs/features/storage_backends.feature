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

    Example: Bundle stored in date partitioned JSONL
      Given an IncidentBundle with classification_date "2026-05-14"
      When the bundle is stored via JSONLStore
      Then the bundle is written to "incidents/by-date/2026-05-14/incidents.jsonl"

  Rule: Dedup skips existing incident IDs
    store() checks exists(incident_id) before persisting each bundle. Bundles with
    incident IDs already present in storage are skipped. store() returns the count
    of genuinely new bundles stored, excluding duplicates.

    Example: Existing incident ID is skipped
      Given a stored bundle with incident_id "20260514-JP-EQ"
      When storing a bundle with the same incident_id "20260514-JP-EQ"
      Then the store returns count 0

    Example: New incident ID bundle is stored
      Given a bundle with incident_id "20260514-JP-EQ" is not yet stored
      When the bundle is stored
      Then the store returns count 1

  Rule: Query returns flattened Incident records
    query() returns list[Incident] — a flattened view of stored data, not raw
    IncidentBundle objects. query() output contains no raw_records field.

    Example: Query returns Incident without raw records
      Given a stored bundle with incident_id "20260514-PH-EQ"
      When querying for all incidents
      Then the results contain no raw records

  Rule: Malformed JSONL lines skipped with warning
    When reading JSONL files during query(), any malformed or unparseable lines
    are logged as warnings and skipped. The remaining valid lines are processed.
    Partial data loss from corrupted lines is tolerated.

    Example: Malformed JSONL lines skipped with warning
      Given a JSONL file with one valid line and one malformed line
      When querying for incidents in the file date range
      Then only the valid line is returned as an Incident

  Rule: Storage preserves complete IncidentBundles
    Storage persists the full IncidentBundle including all raw records,
    classification fields, enrichment fields, and metadata. Full fidelity
    persistence — no fields are discarded during store().

    Example: Complete bundle preserved after storage
      Given a fully populated IncidentBundle with incident_id "20260514-JP-EQ"
      When the bundle is stored and queried by that incident_id
      Then the stored data matches every original field value

  Rule: SQLiteStore matches StorageBackend protocol
    SQLiteStore implements the same StorageBackend protocol as JSONLStore with
    identical store(), query(), and exists() method signatures. SQLiteStore uses
    atomic database transactions instead of the temp-file-and-rename strategy
    used by JSONLStore.

    Example: SQLiteStore implements storage backend protocol
      Given a SQLiteStore instance with a database file
      When a bundle is stored via SQLiteStore
      Then the stored bundle is retrievable via query

  Rule: Filter query by country group
    query(country_group="A") returns only incidents whose country_group field
    matches the specified value. Acceptable values are "A", "B", or "C".

    Example: Query filters by country group
      Given stored bundles with country_group "A" and country_group "B"
      When querying with country_group "A"
      Then only the Group A incident is returned

  Rule: Filter query by disaster type
    query(disaster_type="EQ") returns only incidents whose disaster_type field
    matches the specified type string.

    Example: Query filters by disaster type
      Given stored bundles with disaster_type "EQ" and disaster_type "FL"
      When querying with disaster_type "EQ"
      Then only the earthquake incident is returned

  Rule: Filter query by priority
    query(priority="HIGH") returns only incidents whose priority field matches
    the specified level. Acceptable values are "HIGH", "MED", or "LOW".

    Example: Query filters by priority
      Given stored bundles with priority "HIGH" and priority "LOW"
      When querying with priority "HIGH"
      Then only the high priority incident is returned

  Rule: Filter query by should report
    query(should_report=True) returns only incidents whose should_report field
    matches the specified boolean value.

    Example: Query filters by should report
      Given stored bundles with should_report true and should_report false
      When querying with should_report true
      Then only the reportable incident is returned

  Rule: Filter query by source name
    query(source_name="GDACS") returns only incidents whose source_names list
    contains the specified source name string.

    Example: Query filters by source name
      Given stored bundles where one has source_names containing "GDACS"
      When querying with source_name "GDACS"
      Then only incidents from GDACS are returned

  Rule: Exists returns bool no side effects
    exists(incident_id) returns True if the given incident ID is already stored,
    False otherwise. No errors are raised and no side effects occur. This method
    is used for deduplication checks before calling store().

    Example: Exists returns true for stored incident
      Given a stored bundle with incident_id "20260514-JP-EQ"
      When exists is called with incident_id "20260514-JP-EQ"
      Then the result is true

    Example: Exists returns false for unknown incident
      Given no bundle with incident_id "20260514-XX-UNK"
      When exists is called with incident_id "20260514-XX-UNK"
      Then the result is false

  Rule: Storage writes must be atomic
    JSONLStore writes to a temporary file first, then atomically renames it to
    the target path only on successful completion. SQLiteStore wraps writes in a
    database transaction with COMMIT on success and ROLLBACK on failure. If a
    write fails at any point, the original data remains intact and unchanged.

    Example: Failed write leaves original data intact
      Given a stored incident in a JSONL file
      When a new write is interrupted before completion
      Then the original file data remains unchanged

  Rule: Write failure isolates per bundle
    A storage write failure for one bundle MUST NOT prevent the storage of other
    bundles in the same batch. Each bundle write is independent and failures are
    isolated.

    Example: Single bundle failure isolates others
      Given three bundles with unique incident IDs
      When storing them and one write fails
      Then the other two bundles are stored successfully

  Rule: Inverted date range returns empty list
    When date_from > date_to in a query call, return an empty list. No error is
    raised, no date swapping occurs, and no automatic correction is applied.

    Example: Inverted date range returns empty list
      Given stored incidents with various dates
      When querying with date_from "2026-05-20" and date_to "2026-05-10"
      Then the result is an empty list

  Rule: Incident name from most reliable source
    incident_name is derived by using the title from the highest-reliability
    source's raw_fields, in order: GDACS, WHO, GDELT, DDG-NEWS. If no source
    provides a title, a synthetic name is generated as
    "{disaster_type} in {country} ({date})" using "Unknown disaster" and
    "Unknown location" placeholders for any missing fields.

    Example: Incident name uses highest reliability title
      Given a bundle with GDACS title "Quake in Japan" and WHO title "Tsunami alert"
      When the bundle is stored and queried
      Then the incident name is "Quake in Japan"

  Rule: Source URLs collected per source
    source_urls is built by collecting URL fields from each record's raw_fields:
    WHO uses ItemDefaultUrl (prepend https://www.who.int), GDELT uses url,
    DDG-NEWS uses url, GDACS uses url.report from the url dict. The resulting
    list may be empty — an empty list is not an error.

    Example: Source URLs collected for each source
      Given a bundle with records from GDACS WHO and GDELT
      When the bundle is stored and queried
      Then the source_urls contains URLs from all three sources

  # Constraints:
  # - Performance: 50 incidents classified and stored without AI completes in under 5
  #   seconds (~65ms estimated, orders of magnitude faster than target)
  # - Testability: both JSONLStore and SQLiteStore must be tested against the same
  #   StorageBackend protocol with identical query semantics
