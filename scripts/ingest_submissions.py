"""Process open GitHub issues labeled ``submission-pending`` into v5 incidents.

For each issue:
  1. Extract the first http(s) URL from the body. None → reject + close.
  2. Compute ``source_id = sha1(url)[:16]``. If a MANUAL report with that id
     already exists → relabel ``submission-imported`` (idempotent skip).
  3. URL dedup: if URL is already a news item in the store, short-circuit with
     ``imported:existing-news`` — no fetch, no DSPy, no ingest.
  4. Fetch article via trafilatura. None → reject + close with reason.
  5. DSPy ``classify_submission``. Not a disaster → reject + close with reason.
     Empty country_code → reject (cannot place event).
  6. Synthesize SourceReport(source="MANUAL", source_id=...) and ingest.
  7. If report has no existing incident link → birth uuid4 incident.
  8. Ingest news + link to incident (only if URL news has no prior assignment;
     never steal pending news from another incident).
  9. Relabel ``submission-imported`` and comment with the incident id.

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
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report.ai.openrouter import OpenRouterDigester
from disaster_report.fetchers import fetch_article
from disaster_report.models import NewsItem, ReportPlace, SourceReport
from disaster_report.store.content import ContentStore

logger = logging.getLogger(__name__)

PENDING_LABEL = "submission-pending"
IMPORTED_LABEL = "submission-imported"
REJECTED_LABEL = "submission-rejected"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def _list_pending_issues() -> list[dict]:
    out = _gh(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--label",
            PENDING_LABEL,
            "--search",
            f"-label:{IMPORTED_LABEL} -label:{REJECTED_LABEL}",
            "--json",
            "number,title,body,author,createdAt,url",
            "--limit",
            "50",
        ]
    )
    return json.loads(out) if out.strip() else []


def _extract_url(body: str) -> str | None:
    tokens = body.replace("<", " ").replace(">", " ").split()
    for tok in tokens:
        if tok.startswith("http://") or tok.startswith("https://"):
            return tok.rstrip(",.;)")
    return None


def _source_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _existing_manual_keys(store: ContentStore) -> set[str]:
    return {
        k.split(":", 1)[1]
        for k in store.read_source_report_keys()
        if k.startswith("MANUAL:")
    }


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
    _remove_label(number, PENDING_LABEL)
    _add_label(number, REJECTED_LABEL)
    _close(number, f"Rejected: {reason}")


def _url_already_tracked(number: int, store: ContentStore, url: str) -> str | None:
    nuuid = cast(Any, store)._news_by_url.get(url)
    if not nuuid:
        return None
    existing_inc = store.read_incident_for_news(nuuid)
    if existing_inc:
        _remove_label(number, PENDING_LABEL)
        _add_label(number, IMPORTED_LABEL)
        _comment(
            number,
            f"URL already tracked as news on incident `{existing_inc[:8]}`. Relabeled.",
        )
    else:
        _remove_label(number, PENDING_LABEL)
        _add_label(number, IMPORTED_LABEL)
        _comment(number, "URL already in store as pending news. Relabeled.")
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


def _process_issue(
    issue: dict,
    store: ContentStore,
    digester: OpenRouterDigester,
    manual_keys: set[str],
) -> str:
    number = issue["number"]
    body = issue.get("body") or ""
    url = _extract_url(body)
    if not url:
        _reject(number, "no http(s) URL found in issue body")
        return "rejected:no-url"
    sid = _source_id(url)
    if sid in manual_keys:
        _remove_label(number, PENDING_LABEL)
        _add_label(number, IMPORTED_LABEL)
        _comment(number, f"Already tracked as `MANUAL:{sid}`. Relabeled.")
        return "imported:existing"
    url_short = _url_already_tracked(number, store, url)
    if url_short:
        return url_short
    fetched = fetch_article(url)
    if fetched is None:
        _reject(number, f"could not fetch article from {url}")
        return "rejected:fetch-failed"
    cls = digester.classify_submission(
        url=url, title=fetched.title, body=fetched.description
    )
    if not cls.is_disaster:
        _reject(number, "DSPy classifier says this is not a disaster event.")
        return "rejected:not-disaster"
    if not cls.country_code:
        _reject(number, "DSPy classifier could not determine the event country.")
        return "rejected:no-country"
    places: list[ReportPlace] = [
        ReportPlace(country_code=cls.country_code, subdivision="", locality="")
    ]
    report = SourceReport(
        source="MANUAL",
        source_id=sid,
        incident_type=cls.incident_type or "Unknown",
        name=cls.summary or fetched.title or issue.get("title", "")[:120],
        places=places,
        report_date=cls.event_date or fetched.published_date or issue.get("createdAt", "")[:10],
        raw_fields={
            "url": url,
            "submitted_by": issue.get("author", {}).get("login", "") if isinstance(issue.get("author"), dict) else str(issue.get("author", "")),
            "issue_number": number,
            "issue_url": issue.get("url", ""),
            "fetched_title": fetched.title,
            "fetched_sitename": fetched.sitename,
            "classified_at": _now_iso(),
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
    _remove_label(number, PENDING_LABEL)
    _add_label(number, IMPORTED_LABEL)
    _comment(
        number,
        f"Tracking as incident `{incident_id[:8]}`. "
        f"Type={cls.incident_type or 'Unknown'}, country={cls.country_code or '?'}.",
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

    api_key = args.api_key or (
        __import__("os").environ.get(args.api_key_env, "")
    )
    if not api_key:
        print(f"error: api key missing (set ${args.api_key_env} or pass --api-key)", file=sys.stderr)
        return 2

    digester = OpenRouterDigester(args.model, api_key)
    store = ContentStore(args.tree_root)
    manual_keys = _existing_manual_keys(store)

    pending = _list_pending_issues()
    logger.info("submissions: %d pending issues", len(pending))
    counts = {
        "imported:new": 0,
        "imported:existing": 0,
        "imported:existing-news": 0,
        "rejected:no-url": 0,
        "rejected:fetch-failed": 0,
        "rejected:not-disaster": 0,
        "rejected:no-country": 0,
        "error": 0,
    }
    for issue in pending[: args.limit]:
        try:
            outcome = _process_issue(issue, store, digester, manual_keys)
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
        "submissions: "
        f"new={counts['imported:new']} "
        f"existing={counts['imported:existing']} "
        f"existing-news={counts['imported:existing-news']} "
        f"rejected(no-url)={counts['rejected:no-url']} "
        f"rejected(fetch)={counts['rejected:fetch-failed']} "
        f"rejected(not-disaster)={counts['rejected:not-disaster']} "
        f"rejected(no-country)={counts['rejected:no-country']} "
        f"errors={counts['error']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
