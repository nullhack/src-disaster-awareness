Feature: Incident Monitoring

  Lifecycle gating for incident bundles across pipeline-flow v4: source
  pre-filter deduplication discards seen records before correlation (step B),
  deterministic classification (step D) runs before the active-status check,
  so non-reportable bundles exit early to store. Only reportable bundles
  continue through active-status checks (step E: bundles classified as
  NEW/ACTIVE/STALE with staleness evaluated after classification), DDG News
  search gating (step F), AI enrichment with post-extract re-classification
  (step G), override re-evaluation (step H), and upsert storage (step I)
  with insert/update/no-op semantics. This feature spans the Pipeline,
  Storage, and Fetching contexts. The not-reportable shortcut saves
  processing cost on classification, search, and AI enrichment for bundles
  that should not be reported. Key entities: StorageBackend.upsert,
  get_last_updated, exists_by_source_fingerprint; IncidentBundle.last_updated.

  Rule: Seven Day Active Window
    The active monitoring window is 7 days from last_updated. Bundles with
    now - last_updated ≤ 7 days are ACTIVE and proceed through the full
    pipeline. Bundles with now - last_updated > 7 days are STALE and are
    removed from the pipeline after classification (step D) and before search
    updates (step E, active-status check) — they receive classification but
    are not re-searched via DDG and not re-enriched by AI.

    Example: bundle within 7 days is active
      Given a bundle in storage with last_updated 3 days ago
      When the active-status check evaluates the bundle
      Then the bundle is ACTIVE

  Rule: Source Filter Discard
    For each RawRecord fetched from primary sources (step A), compute its
    source_fingerprint in the format {SOURCE_NAME}:{native_id}. In the source
    pre-filter (step B), if storage.exists_by_source_fingerprint(fp) returns
    True, the record has already been processed in a prior pipeline run and
    is discarded. Only records with fingerprints not in storage pass through
    to the correlator (step C).

    Example: seen fingerprint is discarded
      Given a RawRecord with source_fingerprint "GDACS:12345" already in storage
      When the source pre-filter evaluates the record
      Then the record is discarded from the pipeline

    Example: new fingerprint passes prefilter
      Given a RawRecord with source_fingerprint "GDACS:99999" not in storage
      When the source prefilter evaluates the record
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
    than 7 days ago are STALE. In v4, classification (step D) precedes the
    active-status check (step E), so stale bundles receive classification
    but are removed at step E before supplementary search, AI enrichment,
    and storage update.

    Example: stale bundle removed from pipeline
      Given a bundle in storage with incident_id "20260514-PH-EQ" and last_updated 10 days ago
      When the active-status check evaluates the bundle
      Then the bundle is removed from the pipeline

  Rule: DDG Search Gate
    Supplementary DDG News search (step F) is triggered only when the bundle's
    should_report is True AND either the bundle is ACTIVE (within the 7-day
    window) OR the bundle has missing fields (country is None or disaster_type
    is None). In practice, should_report is always True at this stage in v4
    because non-reportable bundles exit the pipeline at step D before reaching
    this gate. Stale bundles are removed at step E and also never reach this
    gate. Fully-known, active bundles skip DDG search to avoid unnecessary
    API calls.

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
      Then the status is "inserted"

  Rule: Upsert Update Active
    When upsert() receives a bundle whose incident_id is in storage and new
    source_fingerprints are found (not already present in the stored bundle),
    the existing record is updated: fingerprints are merged, bundle fields
    are refreshed, and last_updated is reset to the current time. Returns
    "updated".

    Example: upsert merges bundle with new fingerprints
      Given a bundle in storage with incident_id "20260514-JP-EQ" and fingerprints ["GDACS:12345"]
      When upsert is called with the same incident_id and new fingerprint "WHO:abc-def"
      Then the status is "updated"

  Rule: Upsert Noop Unchanged
    When upsert() receives a bundle whose incident_id is in storage but no
    new source_fingerprints are found (all fingerprints already present in
    the stored bundle), the operation is a noop. last_updated is NOT reset,
    preserving the monitoring window. Returns "noop".

    Example: upsert noops when no new fingerprints
      Given a bundle in storage with incident_id "20260514-JP-EQ" and last_updated 3 days ago
      When upsert is called with the same incident_id and no new fingerprints
      Then the status is "noop"

  # Constraints:
  # - Efficiency: source pre-filter discards all stale/seen records; pipeline with no
  #   new data completes all steps in under 5s
  # - Data Integrity: upsert merges rather than duplicates; source fingerprint dedup
  #   via exists_by_source_fingerprint prevents the same source record from being
  #   stored in two different bundles
  # - Reliability: pipeline continues when any single source API is down; pre-filter
  #   and active-status check operate on available data without blocking
