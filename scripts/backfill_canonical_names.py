"""Backfill report `name:` fields with canonical names from adapter extractors.

Walks every report YAML under data/incidents/.../reports/source=*/ and rewrites
the `name` field by dispatching to the source adapter's `_extract_canonical_name`.
Only the `name:` line is rewritten; the rest of the file is preserved byte-for-byte.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report.models import ReportPlace
from disaster_report.sources.ercc import _extract_canonical_name as _ercc_name
from disaster_report.sources.gdacs import _extract_canonical_name as _gdacs_name
from disaster_report.sources.usgs import _extract_canonical_name as _usgs_name
from disaster_report.sources.who import _extract_canonical_name as _who_name

_NAME_LINE_RE = re.compile(r"^(?P<key>name): (?P<value>.*)$", re.MULTILINE)


def _to_report_places(raw_places: list[dict[str, Any]]) -> list[ReportPlace]:
    return [
        ReportPlace(
            country_code=str(p.get("country_code", "")),
            subdivision=str(p.get("subdivision", "")),
            locality=str(p.get("locality", "")),
        )
        for p in raw_places
    ]


def _new_name(source: str, raw: dict[str, Any]) -> str:
    raw_fields = dict(raw.get("raw_fields") or {})
    places = _to_report_places(raw.get("places") or [])
    report_date = str(raw.get("report_date") or "")
    incident_type = str(raw.get("incident_type") or "")
    old_name = str(raw.get("name") or "")
    if source == "WHO" and "title" not in raw_fields:
        if report_date and old_name.endswith(report_date):
            return old_name
        raw_fields["title"] = old_name
    if source == "USGS":
        return _usgs_name(raw_fields, places, report_date, incident_type or "Earthquake")
    if source == "GDACS":
        return _gdacs_name(raw_fields, places, report_date, incident_type)
    if source == "WHO":
        return _who_name(raw_fields, places, report_date, incident_type)
    if source == "ERCC":
        return _ercc_name(raw_fields, places, report_date, incident_type)
    return old_name


def _replace_name_line(text: str, new_value: str) -> str:
    def _sub(match: re.Match[str]) -> str:
        return f"{match.group('key')}: {new_value}"

    return _NAME_LINE_RE.sub(_sub, text, count=1)


def _process_report(
    yaml_path: Path,
    source: str,
    dry_run: bool,
) -> tuple[str, str | None, str | None, str | None]:
    """Return (source, old_name, new_name, error) for one report.

    new_name is None when skipped (unchanged or error). error is None unless
    an exception was raised.
    """
    raw = yaml.safe_load(yaml_path.read_text())
    if not raw:
        return (source, None, None, None)
    old_name = str(raw.get("name") or "")
    try:
        new_name = _new_name(source, raw)
    except Exception as exc:  # noqa: BLE001
        return (source, old_name, None, str(exc))
    if new_name == old_name:
        return (source, old_name, None, None)
    if not dry_run:
        original = yaml_path.read_text()
        updated = _replace_name_line(original, new_name)
        if updated != original:
            yaml_path.write_text(updated)
    return (source, old_name, new_name, None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-root", default="data")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tree = Path(args.tree_root) / "incidents"
    if not tree.is_dir():
        print(f"backfill: {tree} is not a directory", file=sys.stderr)
        return 2

    total = 0
    changed: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    samples: list[tuple[str, str, str]] = []

    for report_dir in sorted(tree.glob("*/reports/source=*")):
        source = report_dir.name.split("=", 1)[1]
        for yaml_path in sorted(report_dir.glob("*.yaml")):
            total += 1
            src, old_name, new_name, error = _process_report(
                yaml_path, source, args.dry_run
            )
            if error is not None:
                skipped[src] += 1
                print(f"  ERR {src} {yaml_path.name}: {error}", file=sys.stderr)
                continue
            if new_name is None:
                skipped[src] += 1
                continue
            changed[src] += 1
            if len(samples) < 12 or src == "WHO":
                samples.append((src, (old_name or "")[:60], new_name[:60]))

    print("\n=== samples (source | old → new) ===", file=sys.stderr)
    for source, old, new in samples:
        print(f"  [{source}] {old!r}\n        → {new!r}", file=sys.stderr)

    print("\n=== summary ===", file=sys.stderr)
    print(f"total reports scanned: {total}", file=sys.stderr)
    print(f"changed by source:     {dict(changed)}", file=sys.stderr)
    print(f"skipped by source:     {dict(skipped)}", file=sys.stderr)
    print(f"dry-run:               {args.dry_run}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
