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

  Example: All Records Assigned Without Duplicates
    Given five RawRecords about two distinct incidents from three sources
    When the records are correlated
    Then each record is assigned to exactly one IncidentBundle

  Rule: Unmatched Records Create Singleton Bundles
    A RawRecord that does not correlate with any other record still becomes an
    IncidentBundle containing exactly that one record.

  Example: Unmatched Record Creates Singleton Bundle
    Given a WHO record that does not correlate with any other record
    When the record is correlated
    Then the output contains one IncidentBundle with exactly that record

  Rule: Empty Input Produces Empty Output
    When given an empty list of RawRecords, the correlator returns an empty list
    of IncidentBundles. Zero records in, zero bundles out.

  Example: Empty Input Produces Empty Bundles
    Given an empty list of RawRecords
    When the records are correlated
    Then the output is an empty list of IncidentBundles

  Rule: Correlation Uses Three Matching Criteria
    Two records are correlation candidates based on three criteria:
    1. Date proximity: dates within ±1 calendar day. If a record has no
       parseable date, it passes this criterion vacuously.
    2. Country overlap: records share at least one country, OR at least one
       record has no country data. If both records lack country data, skip
       the country criterion for that pair.
    3. Title similarity: normalized Levenshtein ratio ≥ 0.6. If either record
        has no title, skip this criterion for that pair.

  Example: Date Within One Day Passes Proximity
    Given one record dated 2026-05-14
    And another record dated 2026-05-15
    When evaluating date proximity
    Then the date criterion passes

  Example: Shared Country Passes Overlap
    Given one record with country "Philippines"
    And another record also with country "Philippines"
    When evaluating country overlap
    Then the country criterion passes

  Example: Similar Titles Meet Levenshtein Threshold
    Given one record with title "Earthquake strikes Philippines"
    And another record with title "Earthquake struck Philippines"
    When evaluating title similarity
    Then the title criterion passes

  Rule: Country Codes Are Normalized Via Pycountry
    Country names from source-specific fields are normalized to ISO 3166-1
    alpha-2 codes via pycountry before correlation matching. GDACS provides
    iso3/affectedcountries directly; WHO and GDELT require AI extraction from
    title/text first. Unknown or non-standard country names that pycountry
    cannot resolve are treated as having no country data. Normalization is
    applied in the adapter layer before correlation.

  Example: Country Name Normalized To ISO Code
    Given a record with country name "Philippines"
    When the country is normalized via pycountry
    Then the country code is "PH"

  Example: Unknown Country Name Treated As No Country
    Given a record with country name "NonExistentia"
    When the country is normalized via pycountry
    Then the country code is None

  Rule: Country Match Required When Both Present
    When both records in a pair have country data (after pycountry normalization
    to ISO codes), they MUST share at least one country code to correlate.
    Title similarity does NOT override a country mismatch — cross-country
    correlation is prohibited. If record A has only JP and record B has only
    BD, the pair does NOT correlate regardless of title similarity. This
    constraint applies only when BOTH records have country data; if one
    record has no country, the country criterion is skipped.

  Example: Shared Country Enables Correlation
    Given one record with country code "PH"
    And another record with country code "PH"
    When evaluating country overlap
    Then the country criterion passes

  Example: Different Countries Block Correlation
    Given one record with country code "JP"
    And another record with country code "BD"
    When evaluating country overlap
    Then the country criterion fails regardless of title similarity

  Rule: Correlation Requires Date and Country or Title
    A pair correlates if the date criterion passes AND at least one of the
    country or title criteria passes. At least two criteria must be available
    for this combination logic to apply. If only one criterion is available,
    the pair correlates on that one criterion alone. If all three criteria are
    unavailable on both records, the records do not correlate and each forms
    its own singleton bundle.

  Scenario Outline: Date Plus Country Or Title Determines Grouping
    Given one record dated 2026-05-14 from "Philippines" with title "Earthquake in Philippines"
    And another record dated <other_date> from <other_country> with title <other_title>
    When the records are correlated
    Then the records <grouping>

    Examples:
      | other_date  | other_country | other_title                  | grouping                   |
      | 2026-05-14  | Philippines   | "Quake hits Philippines"      | are grouped into one bundle |
      | 2026-05-14  | Japan         | "Earthquake in Philippines"   | remain in separate bundles  |
      | 2026-05-14  | Japan         | "Typhoon warning Japan"       | remain in separate bundles  |
      | 2026-05-16  | Philippines   | "Earthquake in Philippines"   | remain in separate bundles  |

  Example: Sole Criterion Correlates Records Alone
    Given two records dated one day apart with no country data and no title text
    When the records are correlated
    Then the records are grouped into one IncidentBundle

  Rule: Blank Records Get Default Classification
    Records with no date, no country, and no title form singleton bundles with
    default classification: Level 1, Group C, Priority LOW, should_report=False.

  Example: Blank Records Receive Default Classification
    Given a RawRecord with no date no country and no title
    When the record is correlated
    Then the bundle is classified with the blank record defaults

  Rule: Incident ID Generated From Earliest Record Data
    Each IncidentBundle receives an incident_id in the format YYYYMMDD-CC-TTT:
    YYYYMMDD is the earliest date from any record in the bundle (current UTC
    date if no date available), CC is the ISO 3166-1 alpha-2 country code
    ("UNX" if unknown), and TTT is the disaster type code ("OTH" if unknown).
    The incident_id is stable identity — once generated, it must not change even
    if later pipeline steps fill in missing fields.

  Example: Incident ID Generated From Earliest Date
    Given a bundle with earliest record date "2026-05-13" country code "PH" and disaster type "EQ"
    When the incident ID is generated
    Then the incident ID is "20260513-PH-EQ"

  # Constraints:
  # - Reproducibility: same set of raw records always produces the same grouping and
  #   incident IDs across repeated runs
  # - Testability: correlation matching criteria (date, country, title) and combination
  #   logic must have dedicated test coverage including boundary cases
