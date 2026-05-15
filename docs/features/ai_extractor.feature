Feature: AI Extractor

  Batched AI extraction agent that processes IncidentBundles where country or disaster_type
  is still None after deterministic classification. Uses DSPy typed signatures to extract
  country, disaster_type, estimated_affected, and estimated_deaths from unstructured text
  across all raw records in each bundle, including supplementary DDG News results. Processes
  ~10 bundles per AI call. After extraction, the pipeline re-runs deterministic classification
  with the newly populated fields (country group, level derivation, priority matrix). Lives
  in ai/extractor.py.

  Rule: Extractor batches ten bundles per call

  Rule: Extractor uses all raw records for context

  Rule: Mid batch failure saves processed bundles

  Rule: Extractor runs before Classifier agent

  Rule: Re-classification preserves incident ID

  # Constraints:
  # - Reliability: AI extraction failure must not block storage — bundles stored with
  #   ai_enriched=False and enrichment_failed=True
  # - Performance: full batch with AI for 50 incidents completes in under 5 minutes
  #   (~90s estimated: ~6 AI calls × 15s rate limit)
