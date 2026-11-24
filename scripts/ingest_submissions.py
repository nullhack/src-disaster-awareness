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
from disaster_report._countries import scan_countries
from disaster_report._search_keys import derive_repoll_keys
from disaster_report._regions import (
    normalize_region_name,
    region_code_for_name,
    region_name_for_code,
    region_name_from_text,
)

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
    ("el niño", "El Niño"),
    ("el nino", "El Niño"),
    ("enso", "El Niño"),
    ("la niña", "La Niña"),
    ("la nina", "La Niña"),
    ("monsoon", "Monsoon"),
    ("climate", "Climate"),
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
    scope: str = ""
    region_code: str = ""
    region_name: str = ""
    monitoring_status: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_report_date(*candidates: str) -> str:
    for candidate in candidates:
        value = (candidate or "").strip()[:10]
        if not value:
            continue
        try:
            return datetime.fromisoformat(value).date().isoformat()
        except ValueError:
            continue
    return ""


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


def _parse_scope_hint(value: str) -> str:
    lower = _clean_hint(value).lower()
    if not lower or "let the ai" in lower:
        return ""
    if "regional" in lower or "region" == lower:
        return "regional"
    if "global" in lower:
        return "global"
    if "country" in lower or "single" in lower:
        return "country"
    return ""


def _parse_region_hint(value: str) -> tuple[str, str]:
    cleaned = _clean_hint(value)
    if not cleaned:
        return "", ""
    if cleaned.isdigit():
        name = region_name_for_code(cleaned)
        return cleaned, name
    name = normalize_region_name(cleaned)
    return region_code_for_name(name), name


def _parse_tracking_hint(value: str) -> str:
    lower = _clean_hint(value).lower()
    if not lower or "let the ai" in lower:
        return ""
    if "monitor" in lower or "ongoing" in lower or "slow" in lower:
        return "monitoring"
    if "event" in lower or "standard" in lower:
        return "event"
    return ""


def _parse_submission_hints(body: str) -> _SubmissionHints:
    fields = _parse_form_fields(body)
    region_code, region_name = _parse_region_hint(_form_field(fields, "region"))
    return _SubmissionHints(
        incident_type=_parse_category_hint(_form_field(fields, "category hint")),
        country_code=_parse_country_hint(_form_field(fields, "country")),
        scope=_parse_scope_hint(_form_field(fields, "scope")),
        region_code=region_code,
        region_name=region_name,
        monitoring_status=_parse_tracking_hint(_form_field(fields, "tracking")),
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


_CLIMATE_TYPES = frozenset({"El Niño", "La Niña", "Monsoon", "Climate"})


def _infer_climate_type(text: str) -> str:
    lower = (text or "").lower()
    if "el niño" in lower or "el nino" in lower or "enso" in lower:
        return "El Niño"
    if "la niña" in lower or "la nina" in lower:
        return "La Niña"
    if "monsoon" in lower:
        return "Monsoon"
    return ""


def _default_monitoring_status(scope: str, incident_type: str) -> str:
    if incident_type in _CLIMATE_TYPES or scope in {"regional", "global"}:
        return "monitoring"
    return "event"


def _incident_metadata(report: SourceReport) -> dict[str, object]:
    metadata: dict[str, object] = {
        "incident_type": report.incident_type,
        "name": report.name,
        "first_seen_at": report.report_date,
        "scope": report.scope,
        "region_code": report.region_code,
        "region_name": report.region_name,
        "monitoring_status": report.monitoring_status,
        "tracking_window_days": report.tracking_window_days,
        "extended_monitoring": report.monitoring_status == "monitoring",
    }
    if report.incident_type in _CLIMATE_TYPES:
        metadata["incident_category"] = "climate"
    return metadata


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
    scope = hints.scope or cls.scope or ""
    region_code = hints.region_code or cls.region_code
    region_name = hints.region_name or normalize_region_name(cls.region_name)
    if region_code and not region_name:
        region_name = region_name_for_code(region_code)
    if region_name and not region_code:
        region_code = region_code_for_name(region_name)
    country_code = cls.country_code or hints.country_code
    inferred_region = ""
    if not region_name and (
        scope == "regional"
        or (approved and not cls.is_disaster and not hints.country_code)
    ):
        inferred_region = region_name_from_text(
            f"{fetched.title} {fetched.description} {body}"
        )
        if inferred_region:
            region_name = inferred_region
            region_code = region_code_for_name(inferred_region)
            if approved and not cls.is_disaster and not hints.scope:
                scope = "regional"
                country_code = ""
    if not country_code and scope not in {"regional", "global"}:
        scanned = scan_countries(
            f"{fetched.title} {fetched.description} {fetched.body}"
        )
        if len(scanned) == 1:
            country_code = scanned[0][1]
    if not scope:
        if region_name or region_code:
            scope = "regional"
        elif country_code:
            scope = "country"
    if scope == "country":
        if not country_code:
            _review(
                number,
                "neither the DSPy classifier nor the issue form identified the event "
                "country. Edit the Country field, then re-add `submission-approved`.",
            )
            return "review:no-country"
        places: list[ReportPlace] = [
            ReportPlace(country_code=country_code, subdivision="", locality="")
        ]
    elif scope == "regional":
        country_code = ""
        if not region_name:
            _review(
                number,
                "the submission is regional but neither the classifier nor the issue "
                "form identified a region. Edit the Region field, then re-add "
                "`submission-approved`.",
            )
            return "review:no-region"
        places = []
    elif scope == "global":
        country_code = ""
        region_code = ""
        region_name = ""
        places = []
    else:
        if country_code:
            scope = "country"
            places = [
                ReportPlace(country_code=country_code, subdivision="", locality="")
            ]
        elif region_name:
            scope = "regional"
            places = []
        else:
            _review(
                number,
                "neither the DSPy classifier nor the issue form identified a country "
                "or region. Edit the Country/Region field, then re-add "
                "`submission-approved`.",
            )
            return "review:no-country"
    incident_type = _resolve_incident_type(cls.incident_type, hints.incident_type)
    if incident_type == "Unknown":
        inferred = _infer_climate_type(f"{fetched.title} {fetched.description}")
        if inferred:
            incident_type = inferred
    monitoring_status = (
        hints.monitoring_status
        or cls.monitoring_status
        or _default_monitoring_status(scope, incident_type)
    )
    tracking_window_days = 365 if monitoring_status == "monitoring" else 0
    report_name = cls.summary or fetched.title or issue.get("title", "")[:120]
    if scope == "regional" and incident_type in _CLIMATE_TYPES and region_name:
        report_name = f"{incident_type} — {region_name}"
    report = SourceReport(
        source="MANUAL",
        source_id=sid,
        incident_type=incident_type,
        name=report_name,
        places=places,
        report_date=_safe_report_date(
            cls.event_date,
            fetched.published_date,
            issue.get("createdAt", ""),
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
            "form_region_hint": hints.region_name,
            "form_scope_hint": hints.scope,
            "form_tracking_hint": hints.monitoring_status,
        },
        scope=scope,
        region_code=region_code,
        region_name=region_name,
        monitoring_status=monitoring_status,
        tracking_window_days=tracking_window_days,
    )
    rid = store.ingest_source_report(report)
    store.ingest_report_places(rid, report.places)
    metadata = _incident_metadata(report)
    existing_inc = store.read_incident_ids_for_report(rid)
    if existing_inc:
        incident_id = existing_inc[0]
        outcome = "imported:existing"
    elif scope == "regional" and (
        found := store.find_regional_incident(
            incident_type, region_code=region_code, region_name=region_name
        )
    ):
        incident_id = found
        store.add_report_incident(rid, incident_id)
        outcome = "imported:existing"
    else:
        incident_id = uuid.uuid4().hex
        store.add_report_incident(rid, incident_id, metadata=metadata)
        outcome = "imported:new"
    if monitoring_status == "monitoring":
        store.set_extended_monitoring(incident_id, True)
    if not store.read_incident_search_keys(incident_id):
        store.set_search_keys(incident_id, derive_repoll_keys(report))
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
    location = (
        f"region={region_name}"
        if scope == "regional"
        else f"country={country_code}"
        if country_code
        else "global"
    )
    _mark_imported(
        number,
        f"Tracking as incident `{incident_id[:8]}`. "
        f"Type={incident_type}, {location}.",
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
        "review:no-region": 0,
        "review:no-location": 0,
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
        f"review(no-region)={counts['review:no-region']} "
        f"review(no-location)={counts['review:no-location']} "
        f"rejected(no-url)={counts['rejected:no-url']} "
        f"errors={counts['error']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
