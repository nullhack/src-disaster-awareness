"""Process open GitHub news-submission issues into v5 incidents.

For each issue:
  1. Extract the first http(s) URL. None → reject + close (malformed input).
  2. Parse the optional category/country form hints as classifier fallbacks.
  3. Compute ``source_id = sha1(url)[:16]``. If a MANUAL report with that id
     already exists → relabel ``submission-imported`` (idempotent skip).
  4. URL dedup: if URL is already a news item in the store, short-circuit with
     ``imported:existing-news`` — no fetch, no DSPy, no ingest.
  5. Fetch article via trafilatura. None → ``submission-review``.
  6. DSPy ``classify_submission``. Not a disaster → ``submission-review``
     unless a maintainer added ``submission-approved`` (human override).
  7. Resolve country from the classifier, then the form hint. Missing →
     ``submission-review``.
  8. Synthesize SourceReport(source="MANUAL", source_id=...) and ingest.
  9. If report has no existing incident link → birth uuid4 incident.
 10. Ingest news + link to incident (only if URL news has no prior assignment;
     never steal pending news from another incident).
 11. Relabel ``submission-imported`` and comment with the incident id.

A maintainer resolves ``submission-review`` by adding ``submission-approved``
(import) or by adding ``submission-rejected`` and closing the issue. The bot
only closes malformed submissions with no URL.

URL is the sole dedup key for issue submissions. Two articles about the same
event produce two incidents; merge later via ``store.merge_incidents`` if
needed. Requires the ``gh`` CLI on PATH with repo write access for issues +
labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report.ai.openrouter import OpenRouterDigester
from disaster_report.fetchers import fetch_article
from disaster_report.models import NewsItem, ReportPlace, SourceReport
from disaster_report.store.content import ContentStore

from scripts._gh_issues import add_label as _add_label
from scripts._gh_issues import close as _close
from scripts._gh_issues import comment as _comment
from scripts._gh_issues import gh as _gh
from scripts._gh_issues import remove_label as _remove_label

logger = logging.getLogger(__name__)

PENDING_LABEL = "submission-pending"
REVIEW_LABEL = "submission-review"
APPROVED_LABEL = "submission-approved"
IMPORTED_LABEL = "submission-imported"
REJECTED_LABEL = "submission-rejected"

_INCIDENT_TYPE_MAP: dict[str, str] = {
    "War": "Conflict",
}

_CATEGORY_HINTS: tuple[tuple[str, str], ...] = (
    ("volcanic", "Volcanic eruption"),
    ("earthquake", "Earthquake"),
    ("tsunami", "Tsunami"),
    ("flood", "Flood"),
    ("cyclone", "Cyclone"),
    ("hurricane", "Cyclone"),
    ("typhoon", "Cyclone"),
    ("landslide", "Landslide"),
    ("mudslide", "Landslide"),
    ("wildfire", "Wildfire"),
    ("drought", "Drought"),
    ("disease", "Disease outbreak"),
    ("heat wave", "Heat wave"),
    ("severe storm", "Severe storm"),
    ("other", "Other"),
)

_MONITORING_LABELS = (
    "monitoring-request",
    "monitoring-applied",
    "monitoring-rejected",
)


@dataclass(frozen=True)
class _SubmissionHints:
    incident_type: str = ""
    country_code: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _list_issues(label: str, exclude: tuple[str, ...]) -> list[dict]:
    out = _gh(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--label",
            label,
            "--search",
            " ".join(f"-label:{lbl}" for lbl in exclude),
            "--json",
            "number,title,body,author,createdAt,url",
            "--limit",
            "50",
        ]
    )
    return json.loads(out) if out.strip() else []


def _list_pending_issues() -> list[dict]:
    return _list_issues(
        PENDING_LABEL,
        (
            IMPORTED_LABEL,
            REJECTED_LABEL,
            REVIEW_LABEL,
            APPROVED_LABEL,
            *_MONITORING_LABELS,
        ),
    )


def _list_approved_issues() -> list[dict]:
    return _list_issues(
        APPROVED_LABEL,
        (IMPORTED_LABEL, REJECTED_LABEL, *_MONITORING_LABELS),
    )


def _extract_url(body: str) -> str | None:
    tokens = body.replace("<", " ").replace(">", " ").split()
    for tok in tokens:
        if tok.startswith("http://") or tok.startswith("https://"):
            return tok.rstrip(",.;)")
    return None


def _parse_form_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current = ""
    for line in body.splitlines():
        if line.startswith("### "):
            current = line[4:].strip().lower()
            fields[current] = ""
        elif current:
            value = line.strip()
            if value:
                fields[current] = (fields[current] + " " + value).strip()
    return fields


def _form_field(fields: dict[str, str], prefix: str) -> str:
    for key, value in fields.items():
        if key.startswith(prefix):
            return value
    return ""


def _clean_hint(value: str) -> str:
    if value.strip().lower() in {"", "none", "_no response_"}:
        return ""
    return value.strip()


def _parse_country_hint(value: str) -> str:
    match = re.search(r"\b([A-Z]{2})\b", _clean_hint(value))
    return match.group(1).upper() if match else ""


def _parse_category_hint(value: str) -> str:
    lower = _clean_hint(value).lower()
    if not lower or "let the ai classify" in lower:
        return ""
    for keyword, incident_type in _CATEGORY_HINTS:
        if keyword in lower:
            return incident_type
    return ""


def _parse_submission_hints(body: str) -> _SubmissionHints:
    fields = _parse_form_fields(body)
    return _SubmissionHints(
        incident_type=_parse_category_hint(_form_field(fields, "category hint")),
        country_code=_parse_country_hint(_form_field(fields, "country")),
    )


def _source_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _existing_manual_keys(store: ContentStore) -> set[str]:
    return {
        k.split(":", 1)[1]
        for k in store.read_source_report_keys()
        if k.startswith("MANUAL:")
    }


def _reject(number: int, reason: str) -> None:
    for label in (PENDING_LABEL, REVIEW_LABEL, APPROVED_LABEL):
        _remove_label(number, label)
    _add_label(number, REJECTED_LABEL)
    _close(number, f"Rejected: {reason}")


def _review(number: int, reason: str) -> None:
    _remove_label(number, PENDING_LABEL)
    _remove_label(number, APPROVED_LABEL)
    _add_label(number, REVIEW_LABEL)
    _comment(
        number,
        f"Needs maintainer review: {reason}\n\n"
        "A maintainer can add `submission-approved` to import this submission, "
        "or add `submission-rejected` and close this issue to decline it.",
    )


def _mark_imported(number: int, message: str) -> None:
    for label in (PENDING_LABEL, REVIEW_LABEL, APPROVED_LABEL):
        _remove_label(number, label)
    _add_label(number, IMPORTED_LABEL)
    _comment(number, message)


def _url_already_tracked(number: int, store: ContentStore, url: str) -> str | None:
    nuuid = store.find_news_id_by_url(url)
    if not nuuid:
        return None
    existing_inc = store.read_incident_for_news(nuuid)
    if existing_inc:
        _mark_imported(
            number,
            f"URL already tracked as news on incident `{existing_inc[:8]}`. Relabeled.",
        )
    else:
        _mark_imported(number, "URL already in store as pending news. Relabeled.")
    return "imported:existing-news"


def _ingest_news_safely(
    store: ContentStore, news: NewsItem, incident_id: str, number: int
) -> None:
    nid = store.ingest_news_item(news)
    current_inc = store.read_incident_for_news(nid)
    if current_inc is None:
        store.assign_news_to_incident(nid, incident_id)
        return
    if current_inc != incident_id:
        logger.warning(
            "issue %s: news %s already on %s, not stealing (target %s)",
            number, nid[:8], current_inc[:8], incident_id[:8],
        )


def _resolve_incident_type(classified: str, hint: str) -> str:
    raw = classified or hint or "Unknown"
    return _INCIDENT_TYPE_MAP.get(raw, raw)


def _process_issue(
    issue: dict,
    store: ContentStore,
    digester: OpenRouterDigester,
    manual_keys: set[str],
    approved: bool = False,
) -> str:
    number = issue["number"]
    body = issue.get("body") or ""
    hints = _parse_submission_hints(body)
    url = _extract_url(body)
    if not url:
        _reject(number, "no http(s) URL found in issue body")
        return "rejected:no-url"
    sid = _source_id(url)
    if sid in manual_keys:
        _mark_imported(number, f"Already tracked as `MANUAL:{sid}`. Relabeled.")
        return "imported:existing"
    url_short = _url_already_tracked(number, store, url)
    if url_short:
        return url_short
    fetched = fetch_article(url)
    if fetched is None:
        _review(
            number,
            f"could not fetch article from {url}. A maintainer can re-add "
            "`submission-approved` after the URL is reachable.",
        )
        return "review:fetch-failed"
    cls = digester.classify_submission(
        url=url, title=fetched.title, body=fetched.description
    )
    if not cls.is_disaster and not approved:
        _review(number, "DSPy classifier says this is not a disaster event.")
        return "review:not-disaster"
    country_code = cls.country_code or hints.country_code
    if not country_code:
        _review(
            number,
            "neither the DSPy classifier nor the issue form identified the event "
            "country. Edit the Country field, then re-add `submission-approved`.",
        )
        return "review:no-country"
    incident_type = _resolve_incident_type(cls.incident_type, hints.incident_type)
    places: list[ReportPlace] = [
        ReportPlace(country_code=country_code, subdivision="", locality="")
    ]
    report = SourceReport(
        source="MANUAL",
        source_id=sid,
        incident_type=incident_type,
        name=cls.summary or fetched.title or issue.get("title", "")[:120],
        places=places,
        report_date=(
            cls.event_date
            or fetched.published_date
            or issue.get("createdAt", "")[:10]
        ),
        raw_fields={
            "url": url,
            "submitted_by": (
                issue.get("author", {}).get("login", "")
                if isinstance(issue.get("author"), dict)
                else str(issue.get("author", ""))
            ),
            "issue_number": number,
            "issue_url": issue.get("url", ""),
            "fetched_title": fetched.title,
            "fetched_sitename": fetched.sitename,
            "classified_at": _now_iso(),
            "approved_override": bool(approved and not cls.is_disaster),
            "form_category_hint": hints.incident_type,
            "form_country_hint": hints.country_code,
        },
    )
    rid = store.ingest_source_report(report)
    store.ingest_report_places(rid, report.places)
    existing_inc = store.read_incident_ids_for_report(rid)
    if existing_inc:
        incident_id = existing_inc[0]
        outcome = "imported:existing"
    else:
        incident_id = uuid.uuid4().hex
        store.add_report_incident(rid, incident_id)
        outcome = "imported:new"
    news = NewsItem(
        url=url,
        title=fetched.title,
        body=fetched.description,
        published_date=fetched.published_date or issue.get("createdAt", "")[:10],
        source="manual",
        domain=urlparse(url).netloc,
        image="",
        author=fetched.author,
        sitename=fetched.sitename,
    )
    _ingest_news_safely(store, news, incident_id, number)
    _mark_imported(
        number,
        f"Tracking as incident `{incident_id[:8]}`. "
        f"Type={incident_type}, country={country_code}.",
    )
    manual_keys.add(sid)
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-root", default="data")
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key", default="")
    parser.add_argument(
        "--api-key-env",
        default="OPENROUTER_API_KEY",
        help="env var to read when --api-key is empty",
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    api_key = args.api_key or os.environ.get(args.api_key_env, "")
    if not api_key:
        print(f"error: api key missing (set ${args.api_key_env} or pass --api-key)", file=sys.stderr)
        return 2

    digester = OpenRouterDigester(args.model, api_key)
    store = ContentStore(args.tree_root)
    manual_keys = _existing_manual_keys(store)

    pending = _list_pending_issues()
    approved = _list_approved_issues()
    logger.info(
        "submissions: %d pending issues, %d approved issues",
        len(pending),
        len(approved),
    )
    work = [(issue, False) for issue in pending]
    seen = {issue["number"] for issue in pending}
    work.extend(
        (issue, True) for issue in approved if issue["number"] not in seen
    )
    counts = {
        "imported:new": 0,
        "imported:existing": 0,
        "imported:existing-news": 0,
        "review:fetch-failed": 0,
        "review:not-disaster": 0,
        "review:no-country": 0,
        "rejected:no-url": 0,
        "error": 0,
    }
    for issue, is_approved in work[: args.limit]:
        try:
            outcome = _process_issue(
                issue, store, digester, manual_keys, approved=is_approved
            )
        except Exception as exc:
            logger.exception("issue %s failed", issue.get("number"))
            counts["error"] += 1
            try:
                if is_approved:
                    _review(
                        issue["number"],
                        f"bot error while processing approved submission: {exc}",
                    )
                else:
                    _comment(issue["number"], f"Bot error: {exc}")
            except Exception:
                pass
            continue
        counts[outcome] += 1
    print(
        "submissions: "
        f"new={counts['imported:new']} "
        f"existing={counts['imported:existing']} "
        f"existing-news={counts['imported:existing-news']} "
        f"review(fetch)={counts['review:fetch-failed']} "
        f"review(not-disaster)={counts['review:not-disaster']} "
        f"review(no-country)={counts['review:no-country']} "
        f"rejected(no-url)={counts['rejected:no-url']} "
        f"errors={counts['error']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
