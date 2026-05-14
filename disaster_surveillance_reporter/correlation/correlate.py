"""Record correlator — groups RawRecords from different sources that describe
the same real-world incident into IncidentBundles.

Matching criteria (all must pass for a pair to correlate):
  1. Date proximity: within ±1 calendar day.  No parseable date → passes vacuously.
  2. Country overlap: shared country OR one record has no country data.
  3. Title similarity: normalised Levenshtein ratio ≥ 0.6 via difflib.SequenceMatcher.
     No title → skip this criterion.

Combination logic: date AND (country passes OR title passes).
Records with no date, no country, and no title → singleton bundles with
default classification (Level 1, Group C, Priority LOW, should_report=False).

Uses generate_incident_id() from disaster_surveillance_reporter.types for
stable YYYYMMDD-CC-TTT identifiers.
"""

from __future__ import annotations

from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


class Correlator:
    """Stateless correlator grouping RawRecords into IncidentBundles."""

    def correlate(self, records: list[RawRecord]) -> list[IncidentBundle]:
        """Group records describing the same real-world incident.

        Args:
            records: Raw records from all primary sources (GDACS, WHO, GDELT).

        Returns:
            One IncidentBundle per real-world incident.  Every input record
            is assigned to exactly one bundle.
        """
        raise NotImplementedError
