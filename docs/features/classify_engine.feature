Feature: Classify Engine

  Deterministic classification engine that assigns incident levels (1–4), priorities
  (HIGH/MED/LOW), country groups (A/B/C), and override flags (O1–O6) to IncidentBundles
  using pure Python rules with no I/O. Operates in two phases: Initial Classification
  (O2/O4/O6 during pipeline step 3) and Override Re-evaluation (O1/O3/O5 after AI
  enrichment in pipeline step 6). Same raw records always produce identical results.

  Rule: GDACS alertlevel maps to incident levels with Group A severity bump

    Scenario Outline: GDACS alert level to incident level mapping per country group
      Given a bundle with a GDACS record having alertlevel <alert> for <country>
      When the classify engine classifies the bundle
      Then the incident level is <level>

      Examples:
        | alert  | country    | level |
        | Green  | Japan      | 2     |
        | Orange | Japan      | 4     |
        | Red    | Japan      | 4     |
        | Green  | Australia  | 1     |
        | Orange | Australia  | 3     |
        | Red    | Australia  | 4     |
        | Green  | France     | 1     |
        | Orange | France     | 3     |
        | Red    | France     | 4     |

  Rule: WHO keyword scan maps to incident levels

    Scenario Outline: WHO keyword to incident level mapping
      Given a bundle with a WHO record containing <keyword> in its text
      When the classify engine classifies the bundle
      Then the incident level is <level>

      Examples:
        | keyword        | level |
        | pandemic       | 4     |
        | PHEIC          | 4     |
        | epidemic       | 3     |
        | widespread     | 3     |
        | cluster        | 2     |
        | cases reported | 2     |
        | isolated case  | 1     |

    Example: WHO record with no level keyword defaults to Level 2
      Given a bundle with a WHO record containing no level indicating keywords
      When the classify engine classifies the bundle
      Then the incident level is 2

  Rule: GDELT title keyword scan maps to incident levels

    Scenario Outline: GDELT title keyword to incident level mapping
      Given a bundle with a GDELT record containing <keyword> in its title
      When the classify engine classifies the bundle
      Then the incident level is <level>

      Examples:
        | keyword              | level |
        | major                | 3     |
        | catastrophic         | 3     |
        | deadly               | 3     |
        | massive              | 3     |
        | devastating          | 4     |
        | hundreds dead        | 4     |
        | thousands displaced  | 4     |
        | PHEIC                | 4     |

    Example: GDELT record with no severity keyword defaults to Level 2
      Given a bundle with a GDELT record containing no severity keywords in the title
      When the classify engine classifies the bundle
      Then the incident level is 2

  Rule: Unknown country defaults to Group C with warning

    Example: Unrecognized country code assigned to Group C
      Given a bundle with a GDACS record having country code ZZ
      When the classify engine classifies the bundle
      Then the country group is C

  Rule: Default Level 2 when no source provides level data

    Example: Bundle with no source level data defaults to Level 2
      Given a bundle with records that provide no level relevant fields
      When the classify engine classifies the bundle
      Then the incident level is 2

  Rule: Most reliable source wins for level derivation

    Example: GDACS level wins over WHO and GDELT levels
      Given a bundle with a GDACS Orange record for Australia and a WHO pandemic record and a GDELT devastating record
      When the classify engine classifies the bundle
      Then the incident level is 3

    Example: WHO level wins over GDELT when GDACS provides no level
      Given a bundle with a WHO pandemic record and a GDELT major record but no GDACS level data
      When the classify engine classifies the bundle
      Then the incident level is 4

  Rule: Level 4 always produces should_report True regardless of country group

    Scenario Outline: Level 4 incident is always reportable across all groups
      Given a bundle with a GDACS Red alert in <country>
      When the classify engine classifies the bundle
      Then should_report is True

      Examples:
        | country   |
        | Japan     |
        | Australia |
        | France    |

  Rule: Classification is fully deterministic

    Example: Identical input bundles produce identical classification output
      Given a fixed IncidentBundle with GDACS and WHO records
      When the classify engine classifies the bundle multiple times
      Then every classification result is byte identical

  Rule: Incident level must be between 1 and 4 inclusive

    Example: Classified bundle always has a valid incident level
      Given a bundle with a GDACS Orange alert for Japan
      When the classify engine classifies the bundle
      Then the incident level is between 1 and 4 inclusive

  Rule: Country group must be one of A B or C

    Example: Classified bundle always has a valid country group
      Given a bundle with a GDACS record for a known Group A country
      When the classify engine classifies the bundle
      Then the country group is one of A B or C

  Rule: Priority must be one of HIGH MED or LOW

    Example: Classified bundle always has a valid priority
      Given a bundle with a GDACS Red alert for Philippines
      When the classify engine classifies the bundle
      Then the priority is one of HIGH MED or LOW

  Rule: Override O4 Environmental triggers for wildfire drought and flood in Group A countries

    Scenario Outline: O4 triggers for environmental disaster type in Group A country
      Given a bundle with disaster type <disaster_type> in a Group A country
      When the classify engine classifies the bundle
      Then O4 is in the overrides list

      Examples:
        | disaster_type |
        | WF            |
        | DR            |
        | FL            |

    Example: O4 does not trigger for environmental disaster in Group B country
      Given a bundle with disaster type FL in Australia
      When the classify engine classifies the bundle
      Then O4 is not in the overrides list

  Rule: Override O6 Singapore SRC forces priority HIGH and should_report True

    Example: O6 triggers on Singapore keyword and forces HIGH priority
      Given a bundle with a record containing Singapore in the text
      When the classify engine classifies the bundle
      Then the priority is HIGH

    Example: O6 forces should_report True regardless of level
      Given a bundle with a record containing SRC in the text at Level 1 in Group C
      When the classify engine classifies the bundle
      Then should_report is True

  Rule: Override O1 Humanitarian Crisis forces priority HIGH and should_report True post enrichment

    Example: O1 forces HIGH priority after AI enrichment detects humanitarian crisis
      Given an enriched bundle with AI detected humanitarian crisis flag
      When the classify engine reevaluates overrides
      Then the priority is HIGH

    Example: O1 forces should_report True post enrichment
      Given an enriched bundle at Level 1 in Group C with AI detected humanitarian crisis flag
      When the classify engine reevaluates overrides
      Then should_report is True

  Rule: Override O2 Multi Regional triggers on multiple affected countries

    Example: O2 triggers when GDACS alert affects multiple countries
      Given a bundle with a GDACS record having more than 1 affected country
      When the classify engine classifies the bundle
      Then the priority is HIGH

    Example: O2 forces should_report True on multi regional alert
      Given a bundle with a GDACS record affecting 3 countries at Level 2 in Group C
      When the classify engine classifies the bundle
      Then should_report is True

  Rule: Override O3 Likely Development bumps level and re applies priority matrix post enrichment

    Example: O3 bumps level and reapplies priority matrix
      Given an enriched bundle at Level 3 in Group B with AI detected likely development flag
      When the classify engine reevaluates overrides
      Then the incident level is 4
      And the priority is HIGH

    Example: O3 bump is capped at Level 4
      Given an enriched bundle already at Level 4 with AI detected likely development flag
      When the classify engine reevaluates overrides
      Then the incident level remains 4

  Rule: Override O5 Forecast Early Warning bumps level post enrichment

    Example: O5 bumps level by one via GDACS istemporary flag
      Given an enriched bundle at Level 2 with GDACS istemporary set to true
      When the classify engine reevaluates overrides
      Then the incident level is 3

    Example: O5 forces should_report True
      Given an enriched bundle at Level 1 in Group C with GDACS istemporary set to true
      When the classify engine reevaluates overrides
      Then should_report is True

  Rule: Overrides are independent and cumulative

    Example: Multiple overrides stack on the same bundle
      Given a bundle with a GDACS wildfire record for Philippines affecting 3 countries
      When the classify engine classifies the bundle
      Then O2 is in the overrides list
      And O4 is in the overrides list
      And the priority is HIGH

  Rule: Post extraction reclassification upgrades priority when country group changes

    Example: Priority upgrades when country is resolved from unknown to Group A
      Given a bundle initially classified as Group C Level 2 with disaster type EQ and priority LOW
      When AI extraction resolves the country to Philippines
      And the classify engine reclassifies the bundle
      Then the country group is A
      And the priority is MED

  Rule: Post extraction reclassification adds O4 for environmental types in Group A countries

    Example: O4 is added when environmental disaster resolved to Group A country
      Given a bundle initially classified as Group C with disaster type WF and unknown country
      When AI extraction resolves the country to Indonesia
      And the classify engine reclassifies the bundle
      Then O4 is in the overrides list
      And the priority is HIGH

  Rule: Incident ID is stable through all reclassification phases

    Example: Incident ID does not change during reclassification
      Given a bundle with incident ID 20260514-UNX-FL
      When the classify engine reclassifies the bundle after country extraction
      Then the incident ID is still 20260514-UNX-FL

  # Constraints:
  # - Reproducibility: identical input fixtures produce byte-identical classification
  #   output across repeated runs. No randomness, no timestamps in output
  # - Testability: 100% rule coverage for classify.py — all 65 countries (24+41), all 12
  #   priority matrix cells, all 6 overrides, all 4 source level derivations
  # - Performance: initial classification must complete in < 1 second for 50 bundles
  #   with no network calls
