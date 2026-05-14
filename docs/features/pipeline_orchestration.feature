Feature: Pipeline Orchestration

  Seven-step sequential pipeline that orchestrates the full disaster surveillance flow:
  Fetch → Correlate → Initial Classify → Supplementary Search → AI Enrich → Override
  Re-evaluation → Store. The pipeline orchestrator coordinates all bounded contexts,
  manages supplementary search query generation for bundles needing context, handles
  post-extraction re-classification, and ensures failure isolation between steps. Runs
  as the dsr-pipeline CLI command. Single-process, single-threaded, idempotent.

  # Business rules:
  # - AI failure does not block storage — the bundle is stored with ai_enriched=False
  #   when AI times out or fails completely
  # - Extractor runs before Classifier with post-extraction re-classification between
  #   them: Fetch → Correlate → Classify → Search → Extract → Re-classify → Enrich →
  #   Re-evaluate → Store
  # - Correlation result triggers supplementary search when country or type is missing
  #   after initial classification — pipeline step 4 checks bundle fields
  # - Full pipeline flow is: (1) Fetch all 3 primary sources, (2) Correlate records
  #   into bundles, (3) Classify deterministically, (4) Supplementary DDG News search
  #   for bundles needing context, (5) AI enrich in batches, (6) Override re-evaluation,
  #   (7) Store complete bundles
  # - Full batch with AI for 50 incidents completes in approximately 90 seconds (~6 AI
  #   calls × 15s rate limit), well within the 5-minute target
  # - Supplementary search query generation: "{title} {country} {disaster_type} latest
  #   news". Omit unknown country. Substitute "disaster emergency" for unknown type

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
