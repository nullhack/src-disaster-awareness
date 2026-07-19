"""Process open GitHub issues labeled ``monitoring-request`` into flag toggles.

For each issue:
  1. Parse the `incident-id` and `action` fields from the issue body via the
     GitHub form YAML structure. Missing/invalid → reject + close.
  2. Resolve the identifier against `store.read_incidents()`. Accepts either a
     full 32-hex UUID or an 8-char unique prefix. Ambiguous/no-match → reject.
  3. Apply `store.set_extended_monitoring(iuuid, enabled)` with enabled = (action == Enable).
  4. Comment with the resolved incident id + new state + name.
  5. Relabel `monitoring-applied` (kept open as a record) or `monitoring-rejected`
     (closed with reason).

Requires the ``gh`` CLI on PATH with repo write access for issues + labels.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report.store.content import ContentStore

logger = logging.getLogger(__name__)

REQUEST_LABEL = "monitoring-request"
APPLIED_LABEL = "monitoring-applied"
REJECTED_LABEL = "monitoring-rejected"

_SUBMISSION_LABELS = (
    "submission-pending",
    "submission-imported",
    "submission-rejected",
)

_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def _gh(args: list[str]) -> str:
    proc = subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def _list_request_issues() -> list[dict]:
    out = _gh(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--label",
            REQUEST_LABEL,
            "--search",
            " ".join(
                [
                    f"-label:{APPLIED_LABEL}",
                    f"-label:{REJECTED_LABEL}",
                    *[f"-label:{lbl}" for lbl in _SUBMISSION_LABELS],
                ]
            ),
            "--json",
            "number,title,body,author,url",
            "--limit",
            "50",
        ]
    )
    return json.loads(out) if out.strip() else []


def _parse_body(body: str) -> tuple[str | None, str | None]:
    """Extract (incident_id, action_lower) from a GitHub form issue body.

    Form YAML renders as plain-text key/value pairs in the issue body, e.g.:
        ### Incident ID
        03d6656a4a1852ff

        ### Action
        Enable extended monitoring

        ### Rationale (optional)
        Aftershock sequence ongoing.
    """
    incident_id: str | None = None
    action: str | None = None
    current_heading: str | None = None
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            current_heading = stripped[4:].strip().lower()
            continue
        if not stripped or current_heading is None:
            continue
        if current_heading.startswith("incident id") and incident_id is None:
            incident_id = stripped.split()[0] if stripped else None
        elif current_heading.startswith("action") and action is None:
            action = stripped.lower()
    return incident_id, action


def _resolve_incident(store: ContentStore, identifier: str) -> str | None:
    """Return the full iuuid matching `identifier`, or None if not unique.

    Accepts a full 32-hex UUID or an 8-char prefix. If multiple incidents share
    the prefix, returns None (ambiguous).
    """
    cleaned = identifier.strip().lower()
    if not cleaned or not _HEX_RE.match(cleaned):
        return None
    incidents = store.read_incidents()
    if len(cleaned) >= 32:
        return cleaned if any(i.incident_id == cleaned for i in incidents) else None
    matches = [i.incident_id for i in incidents if i.incident_id.startswith(cleaned)]
    if len(matches) == 1:
        return matches[0]
    return None


def _add_label(number: int, label: str) -> None:
    _gh(["issue", "edit", str(number), "--add-label", label])


def _remove_label(number: int, label: str) -> None:
    try:
        _gh(["issue", "edit", str(number), "--remove-label", label])
    except RuntimeError as exc:
        logger.warning("issue %s: remove-label %s failed: %s", number, label, exc)


def _close(number: int, reason: str) -> None:
    _gh(["issue", "close", str(number), "--reason", "not planned", "--comment", reason])


def _comment(number: int, body: str) -> None:
    _gh(["issue", "comment", str(number), "--body", body])


def _reject(number: int, reason: str) -> None:
    _remove_label(number, REQUEST_LABEL)
    _add_label(number, REJECTED_LABEL)
    _close(number, f"Rejected: {reason}")


def _apply(number: int, iuuid: str, enabled: bool, name: str) -> None:
    _remove_label(number, REQUEST_LABEL)
    _add_label(number, APPLIED_LABEL)
    state = "ENABLED" if enabled else "DISABLED"
    _comment(
        number,
        f"Extended monitoring {state.lower()} for incident `{iuuid[:8]}` "
        f"({name}). Next repoll cycle will include it.",
    )


def _process_issue(issue: dict, store: ContentStore) -> str:
    number = issue["number"]
    body = issue.get("body") or ""
    incident_id, action = _parse_body(body)
    if not incident_id:
        _reject(number, "issue body has no Incident ID value")
        return "rejected:no-id"
    if action not in ("enable extended monitoring", "disable extended monitoring"):
        _reject(number, f"issue body has unrecognized Action value: {action!r}")
        return "rejected:bad-action"
    iuuid = _resolve_incident(store, incident_id)
    if iuuid is None:
        _reject(
            number,
            f"identifier `{incident_id}` did not resolve to a unique incident "
            "(needs full UUID or 8-char unique prefix)",
        )
        return "rejected:no-match"
    enabled = action.startswith("enable")
    store.set_extended_monitoring(iuuid, enabled)
    incident = next(
        (i for i in store.read_incidents() if i.incident_id == iuuid), None
    )
    name = incident.name if incident else "?"
    _apply(number, iuuid, enabled, name)
    return "applied:enabled" if enabled else "applied:disabled"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-root", default="data")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    store = ContentStore(args.tree_root)
    pending = _list_request_issues()
    logger.info("monitoring: %d pending issues", len(pending))

    counts = {
        "applied:enabled": 0,
        "applied:disabled": 0,
        "rejected:no-id": 0,
        "rejected:bad-action": 0,
        "rejected:no-match": 0,
        "error": 0,
    }
    for issue in pending[: args.limit]:
        try:
            outcome = _process_issue(issue, store)
        except Exception as exc:
            logger.exception("issue %s failed", issue.get("number"))
            counts["error"] += 1
            try:
                _comment(issue["number"], f"Bot error: {exc}")
            except Exception:
                pass
            continue
        counts[outcome] += 1
    print(
        "monitoring: "
        f"enabled={counts['applied:enabled']} "
        f"disabled={counts['applied:disabled']} "
        f"rejected(no-id)={counts['rejected:no-id']} "
        f"rejected(bad-action)={counts['rejected:bad-action']} "
        f"rejected(no-match)={counts['rejected:no-match']} "
        f"errors={counts['error']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
