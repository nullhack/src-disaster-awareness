Feature: AI Classifier

  Batched AI enrichment agent that processes IncidentBundles with should_report=True to
  generate summaries, rationales, and detect AI-assisted override conditions O1
  (Humanitarian Crisis), O3 (Likely Development), and O5 (Forecast/Early Warning). Uses
  DSPy typed signatures for structured output. Processes ~10 bundles per AI call.
  Override detection results flow back to ClassifyEngine for deterministic re-evaluation
  in pipeline step 6. Lives in ai/classifier.py.

  Rule: Process bundles in batches of ten

    The Classifier agent groups should_report=True bundles into batches of
    approximately 10 for each AI API call, minimizing the total number of calls
    (~6 calls per 50 incidents).

  Rule: AI receives all raw bundle records

    The Classifier agent operates on complete IncidentBundles, receiving ALL raw
    records in each bundle for full context during summary generation and
    override detection.

  Rule: Mid batch failure preserves processed bundles

    If the AIProvider fails mid-batch, all bundles already successfully enriched
    in the current batch are kept with their AI fields populated. All remaining
    unprocessed bundles in the batch are marked enrichment_failed=True and
    ai_enriched=False. All bundles proceed to storage — the pipeline does not
    abort.

  Rule: Generate bundle summary and rationale

    For each should_report=True bundle, the Classifier agent generates a human-
    readable summary and a rationale explaining the classification, stored in
    IncidentBundle.summary and IncidentBundle.rationale.

  Rule: Detect humanitarian crisis override flags

    The Classifier agent detects O1 (Humanitarian Crisis) conditions from
    bundle text content. Detected flags flow to ClassifyEngine for override
    re-evaluation in pipeline step 6.

  Rule: Detect likely development override flags

    The Classifier agent detects O3 (Likely Development) conditions from
    bundle text content. Detected flags flow to ClassifyEngine for override
    re-evaluation in pipeline step 6.

  Rule: Detect forecast early warning override flags

    The Classifier agent detects O5 (Forecast/Early Warning) conditions from
    bundle text content. Detected flags flow to ClassifyEngine for override
    re-evaluation in pipeline step 6.

  # Constraints:
  # - Reliability: AI classification failure must not block storage — bundles stored
  #   with ai_enriched=False and enrichment_failed=True
  # - Performance: full batch with AI for 50 incidents completes in under 5 minutes
