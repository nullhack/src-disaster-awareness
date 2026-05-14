Feature: Record Correlator

  Groups RawRecords from different sources that describe the same real-world incident
  into IncidentBundles using three matching criteria: date proximity (±1 calendar day),
  country overlap (shared country or one record has no country), and title similarity
  (normalized Levenshtein ratio ≥ 0.6). Single-source records become bundles with one
  record. Records with no matching criteria form singleton bundles with default
  classification. Pure grouping logic with no side effects.

  # Business rules:
  # - Every RawRecord assigned to exactly one IncidentBundle — no duplicates, no orphans
  # - Single-source records (no match found) become bundles with one record
  # - Empty record list produces empty bundle list — zero records in, zero bundles out
  # - Correlation uses date proximity (±1 calendar day), country overlap (shared country
  #   or one record has no country data), and title similarity (normalized Levenshtein
  #   ratio ≥ 0.6). A pair correlates if date AND (country passes OR title passes). At
  #   least two criteria must be available — if only one is available, the pair correlates
  #   on that one criterion
  # - Records with no date, no country, and no title form singleton bundles with default
  #   classification: Level 1, Group C, Priority LOW, should_report=False
  # - incident_id is generated as YYYYMMDD-CC-TTT using earliest date from bundle
  #   records, ISO alpha-2 country code ("UNX" if unknown), and disaster type code
  #   ("OTH" if unknown)

  # Constraints:
  # - Reproducibility: same set of raw records always produces the same grouping and
  #   incident IDs across repeated runs
  # - Testability: correlation matching criteria (date, country, title) and combination
  #   logic must have dedicated test coverage including boundary cases
