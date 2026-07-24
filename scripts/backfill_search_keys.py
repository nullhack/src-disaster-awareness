"""Backfill incident `search_keys:` with adapter-dispatched derive_repoll_keys.

Walks every incident YAML under data/incidents/*/incident.yaml and rewrites
the search_keys list by dispatching to the genesis report's adapter
`derive_repoll_keys` method. Only the search_keys block is rewritten;
the rest of the file is preserved as closely as possible.
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

from disaster_report.models import ReportPlace, SourceReport
from disaster_report.sources.gdacs import GDACSAdapter
from disaster_report.sources.usgs import USGSAdapter
from disaster_report.sources.who import WHODiseaseOutbreakAdapter

_ADAPTERS: dict[str, Any] = {
    "USGS": USGSAdapter(),
    "GDACS": GDACSAdapter(),
    "WHO": WHODiseaseOutbreakAdapter(),
}


def _to_report_places(raw_places: list[dict[str, Any]]) -> list[ReportPlace]:
    return [
        ReportPlace(
            country_code=str(p.get("country_code", "")),
            subdivision=str(p.get("subdivision", "")),
            locality=str(p.get("locality", "")),
        )
        for p in raw_places
    ]


def _load_genesis(incident_dir: Path) -> tuple[SourceReport | None, str | None]:
    """Load the genesis (earliest-dated) report for an incident."""
    reports: list[tuple[str, Path, dict[str, Any]]] = []
    for report_dir in sorted(incident_dir.glob("reports/source=*")):
        source = report_dir.name.split("=", 1)[1]
        for yaml_path in sorted(report_dir.glob("*.yaml")):
            raw = yaml.safe_load(yaml_path.read_text())
            if not raw:
                continue
            report_date = str(raw.get("report_date") or "")
            reports.append((report_date, yaml_path, raw | {"_source": source}))
    if not reports:
        return None, None
    reports.sort(key=lambda r: (r[0], str(r[1].name)))
    _, path, raw = reports[0]
    source = str(raw.pop("_source"))
    raw_fields = dict(raw.get("raw_fields") or {})
    # Old WHO reports (pre-PR #50) don't have raw_fields["title"]; inject the
    # stored name so _resolve_disease_country can scan_countries on it.
    if source == "WHO" and "title" not in raw_fields:
        raw_fields["title"] = str(raw.get("name") or "")
    report = SourceReport(
        source=source,
        source_id=str(raw.get("source_id") or ""),
        incident_type=str(raw.get("incident_type") or ""),
        name=str(raw.get("name") or ""),
        places=_to_report_places(raw.get("places") or []),
        report_date=str(raw.get("report_date") or ""),
        raw_fields=raw_fields,
    )
    return report, source


def _derive_keys(report: SourceReport, source: str) -> list[str]:
    adapter = _ADAPTERS.get(source)
    if adapter is not None:
        return adapter.derive_repoll_keys(report)
    from disaster_report._search_keys import derive_repoll_keys

    return derive_repoll_keys(report)


_SEARCH_KEYS_BLOCK_RE = re.compile(
    r"^search_keys:\s*\n(?:[ \t]*- .*\n)*", re.MULTILINE
)


def _build_search_keys_block(keys: list[str]) -> str:
    lines = ["search_keys:"]
    for key in keys:
        lines.append(f"  - {key}")
    return "\n".join(lines) + "\n"


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
    samples: list[tuple[str, str, list[str]]] = []

    for incident_dir in sorted(tree.iterdir()):
        if not incident_dir.is_dir():
            continue
        incident_yaml = incident_dir / "incident.yaml"
        if not incident_yaml.exists():
            continue
        total += 1
        raw_inc = yaml.safe_load(incident_yaml.read_text()) or {}
        old_keys = list(raw_inc.get("search_keys") or [])
        report, source = _load_genesis(incident_dir)
        if report is None:
            skipped["no-reports"] += 1
            continue
        try:
            new_keys = _derive_keys(report, source or "")
        except Exception as exc:  # noqa: BLE001
            skipped["error"] += 1
            print(f"  ERR {incident_dir.name}: {exc}", file=sys.stderr)
            continue
        if new_keys == old_keys:
            skipped["unchanged"] += 1
            continue
        changed[source or "?"] += 1
        if len(samples) < 20 or source == "WHO":
            samples.append((source or "?", incident_dir.name[:16], new_keys))
        if not args.dry_run:
            original = incident_yaml.read_text()
            new_block = _build_search_keys_block(new_keys)
            if _SEARCH_KEYS_BLOCK_RE.search(original):
                updated = _SEARCH_KEYS_BLOCK_RE.sub(new_block, original, count=1)
            else:
                updated = original + "\n" + new_block
            if updated != original:
                incident_yaml.write_text(updated)

    print("\n=== samples (source | incident → new keys) ===", file=sys.stderr)
    for source, inc, keys in samples:
        print(f"  [{source}] {inc}: {keys}", file=sys.stderr)

    print("\n=== summary ===", file=sys.stderr)
    print(f"total incidents scanned: {total}", file=sys.stderr)
    print(f"changed by source:       {dict(changed)}", file=sys.stderr)
    print(f"skipped:                 {dict(skipped)}", file=sys.stderr)
    print(f"dry-run:                 {args.dry_run}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
