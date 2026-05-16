Feature: Pipeline Orchestration

  Seven-step sequential pipeline that orchestrates the full disaster surveillance flow:
  Fetch → Correlate → Initial Classify → Supplementary Search → AI Enrich → Override
  Re-evaluation → Store. The pipeline orchestrator coordinates all bounded contexts,
  manages supplementary search query generation for bundles needing context, handles
  post-extraction re-classification, and ensures failure isolation between steps. Runs
  as the dsr-pipeline CLI command. Single-process, single-threaded, idempotent.

  Rule: AI failure does not block storage
    When AI enrichment times out or fails completely, the bundle is stored with
    ai_enriched=False and all AI-extracted fields set to None. The pipeline
    continues with the next bundle or step.

    Example: Pipeline AI failure stores unenriched
      Given incident bundles pending AI enrichment
      When the AI enrichment step fails completely
      Then the bundle stores without AI enrichment

    Example: Pipeline mid batch failure preserves results
      Given a batch of three incident bundles needing AI enrichment
      When AI enrichment fails after the first bundle processes
      Then successfully enriched bundles are preserved despite batch failure

  Rule: Extractor runs before Classifier
    Within the AI Enrich step, the Extractor agent processes bundles with missing
    fields before the Classifier agent generates summaries for reportable bundles.
    Post-extraction re-classification runs between the two agents.

    Example: Pipeline extraction precedes classification
      Given incident bundles needing both extraction and classification
      When the AI enrichment step runs
      Then the Extractor agent processes before the Classifier agent

  Rule: Supplementary search triggers on missing fields
    After initial classification, bundles where country is None or disaster_type
    is None trigger a supplementary DDG News search. Pipeline step 4 evaluates
    the trigger condition using bundle fields.

    Scenario Outline: Pipeline missing field triggers search
      Given a bundle missing "<field>" after initial classification
      When the supplementary search trigger is evaluated
      Then supplementary search is triggered

      Examples:
        | field                 |
        | country               |
        | disaster_type         |
        | country and type      |

  Rule: Pipeline executes nine sequential steps
    The pipeline orchestrates nine sequential steps: (1) Fetch, (2) Source
    Pre-filter, (3) Correlate, (4) Active-Status Check, (5) Classify,
    (6) Supplementary DDG Search, (7) AI Enrich, (8) Override Re-evaluation,
    (9) Store with upsert.

    Example: Pipeline completes all nine steps
      Given raw records from all primary sources GDACS WHO and EONET
      When the pipeline orchestrator runs
      Then nine pipeline steps execute in specified order

  Rule: Source filter discards seen records
    Before correlation, the pipeline computes a source fingerprint for each
    fetched RawRecord and checks exists_by_source_fingerprint() in storage.
    Records with known fingerprints are discarded, preventing re-processing
    of already-ingested source data.

  Rule: Active status check gates bundles
    After correlation, the pipeline checks each IncidentBundle's last_updated
    and incident_id against storage. NEW bundles always proceed. ACTIVE
    bundles (now - last_updated <= 7 days) proceed with existing fingerprints
    merged. STALE bundles (now - last_updated > 7 days) are removed from
    the pipeline.

  Rule: DDG search gated on activity
    Supplementary DDG News search is triggered only when all of the following
    hold: the bundle's should_report is True, AND the bundle is either ACTIVE
    (updated within 7 days) or has missing fields (country is None or
    disaster_type is None). STALE bundles with fully known fields are excluded.

  Rule: Search queries use templated fields
    Supplementary search queries use the template "{title} {country} {disaster_type}
    latest news". Unknown country is omitted from the query. Unknown disaster type
    is substituted with "disaster emergency".

    Scenario Outline: Pipeline search query matches template
      Given a bundle with title "<title>", country "<country>", and type "<disaster_type>"
      When the supplementary search query is generated
      Then the search query is "<expected_query>"

      Examples:
        | title                       | country       | disaster_type | expected_query                                                |
        | "Magnitude 7.2 earthquake"  | "Philippines" | "Earthquake"  | "Magnitude 7.2 earthquake Philippines Earthquake latest news" |
        | "Disease outbreak report"   | ""            | "Flood"       | "Disease outbreak report Flood latest news"                   |
        | "Flood warning issued"      | ""            | ""            | "Flood warning issued disaster emergency latest news"         |
        | "disaster incident"         | "Japan"       | "Earthquake"  | "disaster incident Japan Earthquake latest news"              |

  # Constraints:
  # - Reproducibility: pipeline is idempotent — duplicate runs produce no duplicate
  #   storage entries (dedup by incident_id)
  # - Reliability (source): any single source API down must not affect other sources —
  #   each adapter returns empty list on failure, pipeline continues
  # - Reliability (AI): AI timeout or failure stores bundles without enrichment —
  #   ai_enriched=False, all AI fields None, bundle persisted to storage
  # - Performance: pure Python path (Steps 2–3, 6–7) completes in < 5s for 50 bundles
  #   (~65ms estimated)
  # - Performance: full batch with AI completes in < 5 minutes (~90s estimated)
  # - Observability: every pipeline run produces structured JSON log (via structlog) of
  #   step outcomes, timing, source fetch counts, classification distribution, and
  #   storage count to stderr at INFO level
  # - Efficiency: with no new data across any source, source_fingerprint dedup at Step 2
  #   discards all records, pipeline returns zero stored in < 5 seconds — fast exit
  #   without redundant AI or DDG search for stale incidents
