Feature: Classify Engine

  Deterministic classification engine that assigns incident levels (1–4), priorities
  (HIGH/MED/LOW), country groups (A/B/C), and override flags (O1–O6) to IncidentBundles
  using pure Python rules with no I/O. Operates in two phases: Initial Classification
  (O2/O4/O6 during pipeline step 3) and Override Re-evaluation (O1/O3/O5 after AI
  enrichment in pipeline step 6). Same raw records always produce identical results.

  Rule: GDACS alertlevel maps to incident levels with Group A severity bump
  Rule: WHO keyword scan maps to incident levels
  Rule: GDELT title keyword scan maps to incident levels
  Rule: Unknown country defaults to Group C with warning
  Rule: Default Level 2 when no source provides level data
  Rule: Most reliable source wins for level derivation
  Rule: Level 4 always produces should_report True regardless of country group
  Rule: Classification is fully deterministic
  Rule: Incident level must be between 1 and 4 inclusive
  Rule: Country group must be one of A B or C
  Rule: Priority must be one of HIGH MED or LOW
  Rule: Override O4 Environmental triggers for wildfire drought and flood in Group A countries
  Rule: Override O6 Singapore SRC forces priority HIGH and should_report True
  Rule: Override O1 Humanitarian Crisis forces priority HIGH and should_report True post enrichment
  Rule: Override O2 Multi Regional triggers on multiple affected countries
  Rule: Override O3 Likely Development bumps level and re applies priority matrix post enrichment
  Rule: Override O5 Forecast Early Warning bumps level post enrichment
  Rule: Overrides are independent and cumulative
  Rule: Post extraction reclassification upgrades priority when country group changes
  Rule: Post extraction reclassification adds O4 for environmental types in Group A countries
  Rule: Incident ID is stable through all reclassification phases

  # Constraints:
  # - Reproducibility: identical input fixtures produce byte-identical classification
  #   output across repeated runs. No randomness, no timestamps in output
  # - Testability: 100% rule coverage for classify.py — all 65 countries (24+41), all 12
  #   priority matrix cells, all 6 overrides, all 4 source level derivations
  # - Performance: initial classification must complete in < 1 second for 50 bundles
  #   with no network calls
