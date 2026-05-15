Feature: AI Extractor

  Batched AI extraction agent that processes IncidentBundles where country or disaster_type
  is still None after deterministic classification. Uses DSPy typed signatures to extract
  country, disaster_type, estimated_affected, and estimated_deaths from unstructured text
  across all raw records in each bundle, including supplementary DDG News results. Processes
  ~10 bundles per AI call. After extraction, the pipeline re-runs deterministic classification
  with the newly populated fields (country group, level derivation, priority matrix). Lives
  in ai/extractor.py.

  Rule: Extractor batches ten bundles per call

    Scenario Outline: AI Extractor batches bundles per call
      Given <bundle_count> bundles need extraction
      When the Extractor processes the batch
      Then the Extractor makes <expected_calls> AI calls

      Examples:
        | bundle_count | expected_calls |
        | 0            | 0              |
        | 7            | 1              |
        | 10           | 1              |
        | 11           | 2              |
        | 20           | 2              |
        | 28           | 3              |

  Rule: Extractor uses all raw records for context

    Example: AI Extractor uses all multi source records
      Given a bundle with GDACS, WHO, GDELT, and DDG-NEWS raw records
      When the Extractor processes the bundle for AI extraction
      Then all raw records from the bundle are included in the AI prompt context

  Rule: Mid batch failure saves processed bundles

    Scenario Outline: AI Extractor mid batch failure saves bundles
      Given a batch of 10 bundles needing extraction
      And the AI fails after processing <processed_count> bundles
      When the AIProvider raises an unrecoverable exception
      Then <processed_count> bundles are saved with AI enrichment
      And <failed_count> bundles are saved without AI enrichment

      Examples:
        | processed_count | failed_count |
        | 0               | 10           |
        | 4               | 6            |
        | 9               | 1            |

  Rule: Extractor runs before Classifier agent

    Example: AI Extractor executes before Classifier
      Given 5 bundles need extraction and 8 bundles have should_report set to True
      When the AI Enrich step executes
      Then Extractor processing completes before Classifier processing begins

    Example: AI Extractor empty Classifier still runs
      Given 0 bundles need extraction and 5 bundles have should_report set to True
      When the AI Enrich step executes
      Then the Classifier processes the 5 reportable bundles

    Example: AI Extractor failure Classifier still runs
      Given 5 bundles need extraction and 8 bundles have should_report set to True
      And the Extractor fails mid batch
      When the pipeline continues
      Then the Classifier processes the reportable bundles after Extractor failure

  Rule: Re-classification preserves incident ID

    Example: AI Extractor keeps incident ID unchanged
      Given a bundle with incident_id "20260514-UNX-OTH"
      And the Extractor resolves the country to "Philippines" and type to "Earthquake"
      When re-classification occurs
      Then the incident_id remains "20260514-UNX-OTH"

  # Constraints:
  # - Reliability: AI extraction failure must not block storage — bundles stored with
  #   ai_enriched=False and enrichment_failed=True
  # - Performance: full batch with AI for 50 incidents completes in under 5 minutes
  #   (~90s estimated: ~6 AI calls × 15s rate limit)
