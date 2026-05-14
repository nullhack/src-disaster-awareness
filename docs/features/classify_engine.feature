Feature: Classify Engine

  Deterministic classification engine that assigns incident levels (1–4), priorities
  (HIGH/MED/LOW), country groups (A/B/C), and override flags (O1–O6) to IncidentBundles
  using pure Python rules with no I/O. Operates in two phases: Initial Classification
  (O2/O4/O6 during pipeline step 3) and Override Re-evaluation (O1/O3/O5 after AI
  enrichment in pipeline step 6). Same raw records always produce identical results.

  # Business rules:
  # - GDACS alertlevel maps to levels: Green → 1, Orange → 3, Red → 4. Severity bump
  #   for Group A: Orange → 4, Green → 2, Red unchanged. Group B/C get no bump
  # - WHO keyword scan maps to levels: "pandemic"/"PHEIC" → 4, "epidemic"/"widespread"
  #   → 3, "cluster"/"cases reported" → 2, "isolated case" → 1, default → 2
  # - GDELT title keyword scan maps to levels: "major"/"catastrophic"/"deadly"/"massive"
  #   → 3, "devastating"/"hundreds dead"/"thousands displaced"/"PHEIC" → 4, minor → 1,
  #   else → 2. ArtList mode has no tone field
  # - Unknown country defaults to Group C with a warning logged
  # - When no source provides level-relevant fields, default to Level 2
  # - Level 4 always produces should_report=True regardless of country group
  # - O4 Environmental triggers when disaster type is WF, DR, or FL AND country is
  #   Group A. Evaluated during Initial Classification (deterministic, no AI)
  # - O6 Singapore/SRC triggers on keywords "Singapore", "SRC", or "Red Cross" in any
  #   record's text. Forces priority HIGH and should_report=True regardless of level or
  #   country group. Evaluated during Initial Classification
  # - Classification is fully deterministic: same raw records in the same bundle always
  #   produce the same result with no randomness
  # - Source reliability order is GDACS > WHO > GDELT > DDG-NEWS. Use the level from
  #   the highest-reliability source that derived one (most-reliable-source-wins)
  # - Level must be between 1 and 4 inclusive
  # - Country group must be one of A, B, or C
  # - Priority must be one of HIGH, MED, or LOW
  # - O1 Humanitarian Crisis forces priority HIGH and should_report=True. Evaluated
  #   post-enrichment via AI-assisted detection
  # - O2 Multi-Regional triggers when GDACS affectedcountries count > 1. Evaluated
  #   during Initial Classification via structured field
  # - O3 Likely Development bumps level +1 capped at 4 and forces should_report=True.
  #   Re-apply priority matrix if level changed. Evaluated post-enrichment
  # - O5 Forecast/Early Warning triggers on GDACS istemporary="true" (string). Bumps
  #   level +1, forces should_report=True. Evaluated post-enrichment
  # - Post-extraction re-classification may upgrade priority when country changes from
  #   unknown to a known group, but does not regenerate incident_id
  # - Post-extraction re-classification may add O4 when environmental disaster type is
  #   found in a newly resolved Group A country
  # - Overrides are independent and cumulative: each matching override applies its
  #   effect. Multiple overrides stack (idempotent for force-HIGH)

  # Constraints:
  # - Reproducibility: identical input fixtures produce byte-identical classification
  #   output across repeated runs. No randomness, no timestamps in output
  # - Testability: 100% rule coverage for classify.py — all 65 countries (24+41), all 12
  #   priority matrix cells, all 6 overrides, all 4 source level derivations
  # - Performance: initial classification must complete in < 1 second for 50 bundles
  #   with no network calls
