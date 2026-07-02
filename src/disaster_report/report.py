"""Generate a Markdown disaster report from the incident store.

A pure renderer over :class:`IncidentView` objects: it takes an
:class:`IncidentStore` and reads everything it needs via the store's read-port
methods. No ``sqlite3`` import, no DB path parsing, no hand-written SQL — the
store owns persistence, this module owns presentation.

Emits a deterministic, AI-free report in two parts: **geophysical & weather
first, disease outbreaks second**. Each part is grouped by severity (CRITICAL,
then HIGH) and items are ordered by news volume within a severity.

By default only **HIGH and CRITICAL** severity incidents are shown
(``min_severity="HIGH"``); lower severities are dropped. Incidents are windowed
by ``event_date`` within ``[as_of - window, as_of]`` so only incidents that
actually occurred in the tracking window are listed.

The report surfaces four fields that WERE produced by the AI digester at ingest
time (``summary``, ``severity``, ``pandemic_potential``, ``event_status``) but
generating the report itself makes no AI calls - they are read as stored values
from the IncidentView.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from disaster_report.classification import SEVERITY_NAMES, is_disease_type
from disaster_report.store.base import IncidentStore, IncidentView, NewsView

NEWS_CAP_DEFAULT = 5

# Most-severe first, derived from the canonical severity vocabulary in
# ``classification`` (single source of truth). Anything not listed ranks below
# LOW and is filtered out when min_severity is HIGH/MEDIUM/LOW.
_SEVERITY_RANK = {
    name: rank for rank, name in enumerate(
        [n for _, n in sorted(SEVERITY_NAMES.items(), reverse=True)], start=1
    )
}
SEVERITY_CHOICES = tuple(_SEVERITY_RANK)


# --- rendering ---------------------------------------------------------------


def _source_str(is_disease: bool, counts: tuple) -> str:
    who, usgs, gdacs, hm, _ = counts
    parts = []
    if is_disease and who:
        parts.append(f"{who} WHO DON{'s' if who != 1 else ''}")
    if usgs:
        parts.append(f"{usgs} USGS")
    if gdacs:
        parts.append(f"{gdacs} GDACS")
    if hm:
        parts.append(f"{hm} HealthMap")
    return " · ".join(parts)


def _fmt_mag_alert(usgs_mag, gdacs_row) -> str:
    bits = []
    if usgs_mag is not None:
        bits.append(f"Mag {usgs_mag:.1f}")
    if gdacs_row and gdacs_row[0]:
        bits.append(f"{gdacs_row[0]} alert")
    return " · ".join(bits)


def _disease_meta(incident: IncidentView) -> list[str]:
    parts: list[str] = []
    if incident.disease_name:
        parts.append(incident.disease_name)
    if incident.pandemic_potential:
        parts.append(f"pp {incident.pandemic_potential}")
    if incident.event_status:
        parts.append(incident.event_status.replace("_", " "))
    return parts


def _render_incident(index: int, incident: IncidentView, counts: tuple,
                     news_list: list, usgs_mag, gdacs_row, is_disease: bool) -> list[str]:
    out: list[str] = []
    title = incident.canonical_name or incident.incident_id
    country = incident.country_name or "—"
    severity = (incident.severity or "—").upper()
    out.append(f"### {index}. {title} — {country} · **{severity}** · {counts[4]} news")

    extra = _fmt_mag_alert(usgs_mag, gdacs_row)
    meta: list[str] = [f"`{incident.incident_id}`"]
    if is_disease:
        meta.extend(_disease_meta(incident))
    elif extra:
        meta.append(extra)
    event_date = incident.event_date or "?"
    days = incident.days_since_event
    days_str = f"{days}d" if days is not None else "?"
    meta.append(f"event {event_date} ({days_str} ago)")
    source_str = _source_str(is_disease, counts)
    if source_str:
        meta.append(source_str)
    out.append(" · ".join(meta))

    summary = (incident.summary or "").strip()
    if summary:
        out.append(f"> {summary}")

    if news_list:
        out.append("")
        for article in news_list:
            outlet = f"*{article.outlet}* — " if article.outlet else ""
            out.append(f"- {article.published_date} · {outlet}[{article.headline}]({article.url})")
        more = counts[4] - len(news_list)
        if more > 0:
            out.append(f"- … +{more} more")
    out.append("")
    return out


def _part(title: str, incidents: list, src: dict, news: dict, usgs_mag: dict,
          gdacs: dict) -> list[str]:
    out = [f"## {title} ({len(incidents)})"]
    if not incidents:
        return out + ["_None._", ""]

    severity_order = sorted(
        {(incident.severity or "").upper() for incident in incidents},
        key=lambda severity_name: _SEVERITY_RANK.get(severity_name, 99),
    )
    index = 0
    for severity_name in severity_order:
        group = [
            incident for incident in incidents
            if (incident.severity or "").upper() == severity_name
        ]
        # within a severity: most news first, then most-recent event first
        group.sort(
            key=lambda incident: (
                src.get(incident.incident_key, (0, 0, 0, 0, 0))[4],
                incident.event_date or "",
            ),
            reverse=True,
        )
        out += ["", f"### {severity_name} ({len(group)})", ""]
        for incident in group:
            index += 1
            key = incident.incident_key
            is_disease = is_disease_type(incident.incident_type or "")
            out.extend(_render_incident(
                index, incident, src.get(key, (0, 0, 0, 0, 0)), news.get(key, []),
                usgs_mag.get(key), gdacs.get(key), is_disease,
            ))
    return out


def _render(as_of: date, window: int, incidents: list, src: dict, news: dict,
            usgs_mag: dict, gdacs: dict, don_range: tuple[str, str, int],
            news_cap: int, min_sev_label: str) -> str:
    cutoff = as_of - timedelta(days=window)
    lines: list[str] = [f"# Disaster Report — {as_of.isoformat()}\n", "## Overview\n"]

    by_severity = Counter((i.severity or "—").upper() for i in incidents)
    by_type = Counter(i.incident_type or "—" for i in incidents)
    sev_order = sorted(by_severity, key=lambda s: _SEVERITY_RANK.get(s, 99))
    total_news = sum(src.get(i.incident_key, (0, 0, 0, 0, 0))[4] for i in incidents)
    with_news = sum(1 for i in incidents if src.get(i.incident_key, (0, 0, 0, 0, 0))[4])

    lines += ["| Metric | Value |", "|---|---|",
              f"| Reporting incidents, {min_sev_label}+ (≤{window}d, since {cutoff.isoformat()}) | **{len(incidents)}** |",
              f"| By severity | {' · '.join(f'{s} **{by_severity[s]}**' for s in sev_order)} |",
              f"| By type | {' · '.join(f'{t} **{n}**' for t, n in by_type.most_common())} |"]
    don_min, don_max, don_n = don_range
    if don_n:
        lines.append(
            f"| WHO DONs in DB | {don_n} (pub. {don_min} → {don_max}) |"
        )
    lines.append(f"| News linked | {total_news} across {with_news} incidents |\n")
    lines.append(
        f"**Selection:** `should_report=1` AND `event_date >= {cutoff.isoformat()}` "
        f"AND severity `{min_sev_label}+`. Sorted by severity, then news volume. "
        f"News capped at {news_cap}/incident.\n"
    )
    lines.append("---\n")

    physical = [i for i in incidents if not is_disease_type(i.incident_type or "")]
    disease = [i for i in incidents if is_disease_type(i.incident_type or "")]

    lines += _part("Part 1 — Geophysical & weather", physical, src, news, usgs_mag, gdacs)
    lines.append("---\n")
    lines += _part("Part 2 — Disease outbreaks", disease, src, news, usgs_mag, gdacs)

    lines += ["---\n", "**Notes**",
              "- Report generation is deterministic (pure DB read, no AI calls). "
              "The `summary`, `severity`, `pandemic_potential`, and `event_status` "
              "fields were produced by the AI digester at ingest time.",
              "- Magnitudes are USGS-instrumental (max across linked events); "
              "the AI summary may cite report-based figures that differ for multi-event incidents.",
              "- Incidents with 0 news are deep/low-impact or under-reported; they still "
              "qualify on severity."]
    return "\n".join(lines)


def generate(store: IncidentStore, *, as_of: date, window: int,
             min_severity: str = "HIGH", news_cap: int = NEWS_CAP_DEFAULT) -> str:
    """Render the Markdown disaster report from the store's read-port.

    Parameters mirror the CLI flags: ``window`` is the tracking window in days,
    ``min_severity`` is the lowest severity to include (HIGH by default), and
    ``news_cap`` bounds the per-incident news list.
    """
    min_sev_label = min_severity.upper()
    if min_sev_label not in _SEVERITY_RANK:
        raise ValueError(f"unknown severity {min_severity!r}")
    min_rank = _SEVERITY_RANK[min_sev_label]
    cutoff = as_of - timedelta(days=window)

    # The store returns incidents fresh by last_updated; the report's own
    # selection is should_report + event_date window + severity floor.
    candidates = store.get_active_incidents(as_of=as_of, within_days=window)
    incidents = [
        incident for incident in candidates
        if incident.should_report
        and cutoff <= incident.event_date <= as_of
        and _SEVERITY_RANK.get((incident.severity or "").upper(), 99) <= min_rank
    ]
    if not incidents:
        return (f"# Disaster Report — {as_of.isoformat()}\n\n"
                f"_No `{min_sev_label}+` incidents active in the last {window} day(s)._\n")

    src = {i.incident_key: store.incident_source_counts(i.incident_key) for i in incidents}
    news = {i.incident_key: store.incident_news_capped(i.incident_key, news_cap) for i in incidents}
    usgs_mag = {
        i.incident_key: store.usgs_max_magnitude(i.incident_key)
        for i in incidents if not is_disease_type(i.incident_type or "")
    }
    gdacs = {
        i.incident_key: store.gdacs_alert(i.incident_key)
        for i in incidents if not is_disease_type(i.incident_type or "")
    }
    don_range = store.who_don_range()
    return _render(as_of, window, incidents, src, news, usgs_mag, gdacs, don_range,
                   news_cap, min_sev_label)
