Feature: AI Extractor

  Batched AI extraction agent that processes IncidentBundles where country or disaster_type
  is still None after deterministic classification. Uses DSPy typed signatures to extract
  country, disaster_type, estimated_affected, and estimated_deaths from unstructured text
  across all raw records in each bundle, including supplementary DDG News results. Processes
  ~10 bundles per AI call. After extraction, the pipeline re-runs deterministic classification
  with the newly populated fields (country group, level derivation, priority matrix). Lives
  in ai/extractor.py.

  # Business rules:
  # - Batched processing at approximately 10 bundles per AI call — 23 bundles split into
  #   3 calls (10+10+3)
  # - AI operates on IncidentBundle receiving all raw records for full context — including
  #   supplementary DDG News results
  # - Mid-batch failure keeps already-processed bundles enriched and marks remaining as
  #   enrichment_failed=True and ai_enriched=False
  # - Extractor runs before Classifier — missing fields extracted first, then post-
  #   extraction re-classification runs, then summaries generated for reportable bundles
  # - Post-extraction re-classification may upgrade level, change priority, or add O4
  #   without regenerating incident_id

  # Constraints:
  # - Reliability: AI extraction failure must not block storage — bundles stored with
  #   ai_enriched=False and enrichment_failed=True
  # - Performance: full batch with AI for 50 incidents completes in under 5 minutes
  #   (~90s estimated: ~6 AI calls × 15s rate limit)
