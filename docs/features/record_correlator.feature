Feature: Record Correlator

  Groups RawRecords from different sources that describe the same real-world incident
  into IncidentBundles using three matching criteria: date proximity (±1 calendar day),
  country overlap (shared country or one record has no country), and title similarity
  (normalized Levenshtein ratio ≥ 0.6). Single-source records become bundles with one
  record. Records with no matching criteria form singleton bundles with default
  classification. Pure grouping logic with no side effects.

  Rule: Every Record Belongs to One Bundle
    Every RawRecord from the primary fetch must be assigned to exactly one
    IncidentBundle. No record appears in more than one bundle (no duplicates)
    and no record is left unassigned (no orphans).

  Rule: Unmatched Records Create Singleton Bundles
    A RawRecord that does not correlate with any other record still becomes an
    IncidentBundle containing exactly that one record.

  Rule: Empty Input Produces Empty Output
    When given an empty list of RawRecords, the correlator returns an empty list
    of IncidentBundles. Zero records in, zero bundles out.

  Rule: Correlation Uses Three Matching Criteria
    Two records are correlation candidates based on three criteria:
    1. Date proximity: dates within ±1 calendar day. If a record has no
       parseable date, it passes this criterion vacuously.
    2. Country overlap: records share at least one country, OR at least one
       record has no country data. If both records lack country data, skip
       the country criterion for that pair.
    3. Title similarity: normalized Levenshtein ratio ≥ 0.6. If either record
       has no title, skip this criterion for that pair.

  Rule: Correlation Requires Date and Country or Title
    A pair correlates if the date criterion passes AND at least one of the
    country or title criteria passes. At least two criteria must be available
    for this combination logic to apply. If only one criterion is available,
    the pair correlates on that one criterion alone. If all three criteria are
    unavailable on both records, the records do not correlate and each forms
    its own singleton bundle.

  Rule: Blank Records Get Default Classification
    Records with no date, no country, and no title form singleton bundles with
    default classification: Level 1, Group C, Priority LOW, should_report=False.

  Rule: Incident ID Generated From Earliest Record Data
    Each IncidentBundle receives an incident_id in the format YYYYMMDD-CC-TTT:
    YYYYMMDD is the earliest date from any record in the bundle (current UTC
    date if no date available), CC is the ISO 3166-1 alpha-2 country code
    ("UNX" if unknown), and TTT is the disaster type code ("OTH" if unknown).
    The incident_id is stable identity — once generated, it must not change even
    if later pipeline steps fill in missing fields.

  # Constraints:
  # - Reproducibility: same set of raw records always produces the same grouping and
  #   incident IDs across repeated runs
  # - Testability: correlation matching criteria (date, country, title) and combination
  #   logic must have dedicated test coverage including boundary cases
