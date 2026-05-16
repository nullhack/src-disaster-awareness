Feature: Incident Monitoring

  Lifecycle gating for incident bundles across the nine-step pipeline: a 7-day
  active monitoring window, source pre-filter deduplication that discards seen
  records, active-status checks that classify bundles as NEW/ACTIVE/STALE,
  DDG News search gating, and upsert storage with insert/update/no-op semantics.
  This feature spans the Pipeline, Storage, and Fetching contexts, ensuring stale
  incidents are skipped to save processing cost. Key entities: StorageBackend.upsert,
  get_last_updated, exists_by_source_fingerprint; IncidentBundle.last_updated.

  Rule: Seven Day Active Window
    The active monitoring window is 7 days from last_updated. Bundles with
    now - last_updated ≤ 7 days are ACTIVE and proceed through the full
    pipeline. Bundles with now - last_updated > 7 days are STALE and are
    removed from the pipeline before classification — they are not re-classified,
    not re-searched via DDG, and not re-enriched by AI.

    Example: bundle within 7 days is active
      Given a bundle in storage with last_updated 3 days ago
      When the active-status check evaluates the bundle
      Then the bundle is ACTIVE

    Example: bundle older than 7 days is stale
      Given a bundle in storage with last_updated 10 days ago
      When the active-status check evaluates the bundle
      Then the bundle is STALE and removed from the pipeline

  Rule: Source Filter Discard
    For each RawRecord fetched from primary sources, compute its
    source_fingerprint in the format {SOURCE_NAME}:{native_id}. If
    storage.exists_by_source_fingerprint(fp) returns True, the record has
    already been processed in a prior pipeline run and is discarded. Only
    records with fingerprints not in storage pass through to the correlator.

    Example: seen fingerprint is discarded
      Given a RawRecord with source_fingerprint "GDACS:12345" already in storage
      When the source pre-filter evaluates the record
      Then the record is discarded and does not reach the correlator

    Example: new fingerprint passes pre-filter
      Given a RawRecord with source_fingerprint "GDACS:99999" not in storage
      When the source pre-filter evaluates the record
      Then the record passes through to the correlator

  Rule: New Bundles Proceed
    Bundles whose incident_id is not found in storage are NEW. New bundles
    proceed through the full pipeline: classification, supplementary search,
    AI enrichment, and storage insertion.

    Example: new bundle proceeds through pipeline
      Given an IncidentBundle with incident_id "20260514-PH-EQ" not in storage
      When the active-status check evaluates the bundle
      Then the bundle proceeds to classification

  Rule: Active Bundles Merge Fingerprints
    Bundles whose incident_id is in storage and whose last_updated is within
    the 7-day window are ACTIVE. Active bundles proceed through the pipeline
    and merge their existing source_fingerprints from storage with any new
    fingerprints from the current run.

    Example: active bundle merges fingerprints
      Given a bundle in storage with incident_id "20260514-PH-EQ" and last_updated 3 days ago
      When the active-status check evaluates the bundle
      Then the bundle proceeds with merged source fingerprints

  Rule: Stale Bundles Skipped
    Bundles whose incident_id is in storage and whose last_updated is more
    than 7 days ago are STALE. Stale bundles are removed from the pipeline
    entirely — they receive no classification, no supplementary search, no
    AI enrichment, and no storage update.

    Example: stale bundle removed from pipeline
      Given a bundle in storage with incident_id "20260514-PH-EQ" and last_updated 10 days ago
      When the active-status check evaluates the bundle
      Then the bundle is removed and does not proceed

  Rule: DDG Search Gate
    Supplementary DDG News search is triggered only when the bundle's
    should_report is True AND either the bundle is ACTIVE (within the 7-day
    window) OR the bundle has missing fields (country is None or disaster_type
    is None). Stale, fully-known incidents skip DDG search entirely to avoid
    unnecessary API calls.

    Scenario Outline: DDG search triggered by gate condition
      Given a bundle with should_report "<should_report>" active "<active>" and missing_fields "<missing_fields>"
      When the DDG search gate is evaluated
      Then supplementary search is "<triggered>"

      Examples:
        | should_report | active | missing_fields | triggered  |
        | true          | true   | false          | triggered  |
        | true          | false  | true           | triggered  |
        | true          | true   | true           | triggered  |
        | false         | true   | false          | not triggered |
        | true          | false  | false          | not triggered |
        | false         | false  | true           | not triggered |

  Rule: Upsert Insert New
    When upsert() receives a bundle whose incident_id is not in storage, the
    bundle is inserted as a new record. last_updated is set to the bundle's
    correlation time. Returns "inserted".

    Example: upsert inserts new bundle
      Given a bundle with incident_id "20260514-JP-EQ" not in storage
      When the bundle is upserted
      Then the status is "inserted" and last_updated is set

  Rule: Upsert Update Active
    When upsert() receives a bundle whose incident_id is in storage and new
    source_fingerprints are found (not already present in the stored bundle),
    the existing record is updated: fingerprints are merged, bundle fields
    are refreshed, and last_updated is reset to the current time. Returns
    "updated".

    Example: upsert updates active bundle with new fingerprints
      Given a bundle in storage with incident_id "20260514-JP-EQ" and fingerprints ["GDACS:12345"]
      When upsert is called with the same incident_id and new fingerprint "WHO:abc-def"
      Then the status is "updated" and last_updated is reset

  Rule: Upsert No-op Unchanged
    When upsert() receives a bundle whose incident_id is in storage but no
    new source_fingerprints are found (all fingerprints already present in
    the stored bundle), the operation is a no-op. last_updated is NOT reset,
    preserving the monitoring window. Returns "noop".

    Example: upsert no-ops when no new fingerprints
      Given a bundle in storage with incident_id "20260514-JP-EQ" and last_updated 3 days ago
      When upsert is called with the same incident_id and no new fingerprints
      Then the status is "noop" and last_updated is unchanged

  # Constraints:
  # - Efficiency: source pre-filter discards all stale/seen records; pipeline with no
  #   new data completes all steps in under 5s
  # - Data Integrity: upsert merges rather than duplicates; source fingerprint dedup
  #   via exists_by_source_fingerprint prevents the same source record from being
  #   stored in two different bundles
  # - Reliability: pipeline continues when any single source API is down; pre-filter
  #   and active-status check operate on available data without blocking
