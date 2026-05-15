"""Record correlator — groups RawRecords into IncidentBundles.

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

import difflib

import pycountry

from disaster_surveillance_reporter.types import (
    IncidentBundle,
    RawRecord,
    generate_incident_id,
)


def _normalize_country(record: RawRecord) -> str | None:
    """Extract ISO 3166-1 alpha-2 code from a record's country field.

    Uses iso3 (GDACS) or country name (WHO/GDELT/DDG-NEWS) via pycountry.
    Returns None if no country info or lookup fails.
    """
    raw = record.raw_fields
    iso3 = raw.get("iso3")
    if iso3:
        try:
            return pycountry.countries.get(alpha_3=iso3).alpha_2
        except (LookupError, AttributeError):
            pass
    name = raw.get("country")
    if name:
        try:
            return pycountry.countries.lookup(name).alpha_2
        except LookupError:
            pass
    return None


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
        if not records:
            return []

        n = len(records)
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        # Pre-extract per-record data for efficient pair comparison.
        dates = [r.fetched_at for r in records]
        countries = [_normalize_country(r) for r in records]
        titles = [
            " ".join(r.raw_fields.get("title", "").lower().split()) for r in records
        ]

        for i in range(n):
            for j in range(i + 1, n):
                # Criterion 1: date proximity — ±1 calendar day.
                date_diff = abs((dates[i] - dates[j]).days)
                if date_diff > 1:
                    continue

                # Criterion 2+3: country and title matching.
                ci = countries[i]
                cj = countries[j]
                ti = titles[i]
                tj = titles[j]

                # Both have country: must match.
                if ci is not None and cj is not None:
                    if ci != cj:
                        continue
                # Both unknown country: shared missing country = match.
                elif ci is None and cj is None:
                    pass
                # One has country, other unknown: require title similarity.
                else:
                    if ti and tj:
                        if difflib.SequenceMatcher(None, ti, tj).ratio() < 0.6:
                            continue
                    else:
                        continue

                union(i, j)

        # Group records by their connected-component root.
        groups: dict[int, list[RawRecord]] = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(records[i])

        bundles: list[IncidentBundle] = []
        for group_records in groups.values():
            # Extract bundle-level country and disaster_type (first non-None).
            bundle_country: str | None = None
            bundle_disaster_type: str | None = None
            for r in group_records:
                if bundle_country is None:
                    bundle_country = _normalize_country(r)
                if bundle_disaster_type is None:
                    bundle_disaster_type = r.raw_fields.get("disaster_type")
                if bundle_country is not None and bundle_disaster_type is not None:
                    break

            incident_id = generate_incident_id(
                group_records, bundle_country, bundle_disaster_type
            )

            # All-unavailable records: no country AND no title → defaults.
            has_country = any(
                _normalize_country(r) is not None for r in group_records
            )
            has_title = any(r.raw_fields.get("title", "") != "" for r in group_records)

            if not has_country and not has_title:
                bundle = IncidentBundle(
                    incident_id=incident_id,
                    records=list(group_records),
                    country_group="C",
                    incident_level=1,
                    priority="LOW",
                    should_report=False,
                )
            else:
                bundle = IncidentBundle(
                    incident_id=incident_id,
                    records=list(group_records),
                )

            bundles.append(bundle)

        return bundles
