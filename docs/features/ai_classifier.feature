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

  Scenario Outline: AI Classifier batch size processing
    Given <bundle_count> bundles with should_report set to True
    When the Classifier agent processes the bundles in batches
    Then the bundles are processed in <batch_count> AI calls of at most "10" bundles each

    Examples:
      | bundle_count | batch_count |
      | 0            | 0           |
      | 10           | 1           |
      | 23           | 3           |
      | 11           | 2           |

  Rule: AI receives all raw bundle records

    The Classifier agent operates on complete IncidentBundles, receiving ALL raw
    records in each bundle for full context during summary generation and
    override detection.

  Example: AI Classifier full record context provided
    Given an IncidentBundle with should_report True containing "3" raw records
    When the Classifier agent enriches the bundle
    Then all "3" raw records are provided to the AI for text analysis

  Rule: Mid batch failure preserves processed bundles

    If the AIProvider fails mid-batch, all bundles already successfully enriched
    in the current batch are kept with their AI fields populated. All remaining
    unprocessed bundles in the batch are marked enrichment_failed=True and
    ai_enriched=False. All bundles proceed to storage — the pipeline does not
    abort.

  Scenario Outline: AI Classifier mid batch failure recovery
    Given a batch of "10" bundles being processed by the Classifier agent
    When the AI fails after <processed_count> bundles succeed
    Then the <processed_count> successful bundles retain their enrichment while the rest are marked failed

    Examples:
      | processed_count |
      | 4               |
      | 7               |
      | 0               |
      | 9               |

  Rule: Generate bundle summary and rationale

    For each should_report=True bundle, the Classifier agent generates a human-
    readable summary and a rationale explaining the classification, stored in
    IncidentBundle.summary and     IncidentBundle.rationale.

  Example: AI Classifier generates summary and rationale
    Given a should_report IncidentBundle with text content describing a disaster event
    When the Classifier agent enriches the bundle
    Then the bundle summary and rationale fields are populated by the AI

  Rule: Detect humanitarian crisis override flags

    The Classifier agent detects O1 (Humanitarian Crisis) conditions from
    bundle text content. Detected flags flow to ClassifyEngine for override
    re-evaluation in pipeline step 6.

  Example: AI Classifier detects humanitarian crisis
    Given a should_report IncidentBundle with text describing "mass displacement and food shortage"
    When the Classifier agent processes the bundle
    Then the humanitarian crisis override flag is set to True

  Rule: Detect likely development override flags

    The Classifier agent detects O3 (Likely Development) conditions from
    bundle text content. Detected flags flow to ClassifyEngine for override
    re-evaluation in pipeline step 6.

  Example: AI Classifier detects likely development
    Given a should_report IncidentBundle with text describing "situation expected to deteriorate rapidly"
    When the Classifier agent processes the bundle
    Then the likely development override flag is set to True

  Rule: Detect forecast early warning override flags

    The Classifier agent detects O5 (Forecast/Early Warning) conditions from
    bundle text content. Detected flags flow to ClassifyEngine for override
    re-evaluation in pipeline step 6.

  Example: AI Classifier detects forecast warning
    Given a should_report IncidentBundle with text describing "early warning of approaching tropical cyclone"
    When the Classifier agent processes the bundle
    Then the forecast warning override flag is set to True

  # Constraints:
  # - Reliability: AI classification failure must not block storage — bundles stored
  #   with ai_enriched=False and enrichment_failed=True
  # - Performance: full batch with AI for 50 incidents completes in under 5 minutes
