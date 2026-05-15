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

  Rule: Extractor runs before Classifier
    Within the AI Enrich step, the Extractor agent processes bundles with missing
    fields before the Classifier agent generates summaries for reportable bundles.
    Post-extraction re-classification runs between the two agents.

  Rule: Supplementary search triggers on missing fields
    After initial classification, bundles where country is None or disaster_type
    is None trigger a supplementary DDG News search. Pipeline step 4 evaluates
    the trigger condition using bundle fields.

  Rule: Pipeline executes seven sequential steps
    The pipeline orchestrates seven sequential steps: (1) Fetch all 3 primary
    sources, (2) Correlate records into bundles, (3) Classify deterministically,
    (4) Supplementary DDG News search for bundles needing context, (5) AI enrich
    in batches, (6) Override re-evaluation, (7) Store complete bundles.

  Rule: Search queries use templated fields
    Supplementary search queries use the template "{title} {country} {disaster_type}
    latest news". Unknown country is omitted from the query. Unknown disaster type
    is substituted with "disaster emergency".

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
