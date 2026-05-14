Feature: AI Classifier

  Batched AI enrichment agent that processes IncidentBundles with should_report=True to
  generate summaries, rationales, and detect AI-assisted override conditions O1
  (Humanitarian Crisis), O3 (Likely Development), and O5 (Forecast/Early Warning). Uses
  DSPy typed signatures for structured output. Processes ~10 bundles per AI call.
  Override detection results flow back to ClassifyEngine for deterministic re-evaluation
  in pipeline step 6. Lives in ai/classifier.py.

  # Business rules:
  # - Batched processing at approximately 10 bundles per AI call
  # - AI operates on IncidentBundle receiving all raw records for full context
  # - Mid-batch failure keeps already-processed bundles enriched and marks remaining as
  #   enrichment_failed=True and ai_enriched=False
  # - Generates summary and rationale text for reportable bundles
  # - Detects override flags: humanitarian_crisis (O1), likely_development (O3),
  #   forecast_warning (O5) — these flow to ClassifyEngine for override re-evaluation

  # Constraints:
  # - Reliability: AI classification failure must not block storage — bundles stored
  #   with ai_enriched=False and enrichment_failed=True
  # - Performance: full batch with AI for 50 incidents completes in under 5 minutes
