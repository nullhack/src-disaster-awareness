from __future__ import annotations

import dataclasses
import shutil
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from disaster_report._search_keys import derive_repoll_keys
from disaster_report.models import (
    Incident,
    IncidentLog,
    NewsItem,
    ReportPlace,
    SourceReport,
)
from disaster_report.store import _tree
from disaster_report.store._tree import (
    dump_yaml,
    incident_dir,
    incident_manifest_path,
    incident_news_path,
    incident_report_path,
    load_yaml,
    log_dir,
    log_news_path,
    log_path,
    news_staging_path,
    report_staging_path,
)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _place_dict(p: ReportPlace) -> dict[str, str]:
    return {
        "country_code": p.country_code,
        "subdivision": p.subdivision,
        "locality": p.locality,
    }


def _place_from_dict(d: dict[str, Any]) -> ReportPlace:
    return ReportPlace(
        country_code=d.get("country_code", ""),
        subdivision=d.get("subdivision", ""),
        locality=d.get("locality", ""),
    )


def _coerce_raw(raw: object) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _natural_key(d: dict[str, Any]) -> str:
    return f"{d.get('source', '')}:{d.get('source_id', '')}"


def _load_yaml_files(
    directory: Path, *, recursive: bool
) -> list[tuple[dict[str, Any], Path]]:
    if not directory.is_dir():
        return []
    paths = directory.rglob("*.yaml") if recursive else directory.glob("*.yaml")
    result: list[tuple[dict[str, Any], Path]] = []
    for p in paths:
        d = load_yaml(p)
        if d.get("id"):
            result.append((d, p))
    return result


class ContentStore:
    def __init__(
        self,
        tree_root: str | Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._root = Path(tree_root)
        self._clock: Callable[[], datetime] = clock or _default_clock
        self._root.mkdir(parents=True, exist_ok=True)
        self._scan()

    # ------------------------------------------------------------------ scan

    def _scan(self) -> None:
        self._reports: dict[str, dict[str, Any]] = {}
        self._reports_by_natural: dict[str, str] = {}
        self._report_incident: dict[str, str | None] = {}
        self._report_path: dict[str, Path] = {}

        self._news: dict[str, dict[str, Any]] = {}
        self._news_by_url: dict[str, str] = {}
        self._news_incident: dict[str, str | None] = {}
        self._news_log: dict[str, str | None] = {}
        self._news_path: dict[str, Path] = {}

        self._incidents: dict[str, dict[str, Any]] = {}
        self._logs: dict[str, dict[str, dict[str, Any]]] = {}

        for d, p in _load_yaml_files(self._root / "reports", recursive=True):
            self._index_report(d, p, incident_id=None)
        for d, p in _load_yaml_files(self._root / "news", recursive=False):
            self._index_news(d, p, incident_id=None, log_date=None)

        incidents_root = self._root / "incidents"
        if incidents_root.is_dir():
            for idir in incidents_root.iterdir():
                if idir.is_dir():
                    self._scan_incident(idir, idir.name)

    def _index_report(
        self, d: dict[str, Any], path: Path, incident_id: str | None
    ) -> None:
        ruuid = d["id"]
        self._reports[ruuid] = d
        self._reports_by_natural[_natural_key(d)] = ruuid
        self._report_incident[ruuid] = incident_id
        self._report_path[ruuid] = path

    def _index_news(
        self,
        d: dict[str, Any],
        path: Path,
        incident_id: str | None,
        log_date: str | None,
    ) -> None:
        nuuid = d["id"]
        self._news[nuuid] = d
        url = d.get("url")
        if url:
            self._news_by_url[url] = nuuid
        self._news_incident[nuuid] = incident_id
        self._news_log[nuuid] = log_date
        self._news_path[nuuid] = path

    def _scan_incident(self, idir: Path, iuuid: str) -> None:
        manifest = idir / "incident.yaml"
        if manifest.is_file():
            self._incidents[iuuid] = load_yaml(manifest)
        else:
            self._incidents[iuuid] = {"id": iuuid, "search_keys": []}
        for d, p in _load_yaml_files(idir / "reports", recursive=True):
            self._index_report(d, p, incident_id=iuuid)
        for d, p in _load_yaml_files(idir / "news", recursive=False):
            self._index_news(d, p, incident_id=iuuid, log_date=None)
        logs_dir = idir / "logs"
        if logs_dir.is_dir():
            for ldir in logs_dir.iterdir():
                if ldir.is_dir():
                    self._scan_log_dir(ldir, iuuid)

    def _scan_log_dir(self, ldir: Path, iuuid: str) -> None:
        log_date = ldir.name
        lp = ldir / "log.yaml"
        if lp.is_file():
            self._logs.setdefault(iuuid, {})[log_date] = load_yaml(lp)
        for d, p in _load_yaml_files(ldir / "news", recursive=False):
            self._index_news(d, p, incident_id=iuuid, log_date=log_date)

    # ------------------------------------------------------------ file moves

    @staticmethod
    def _move(src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.replace(dst)

    # ------------------------------------------------------------ incidents

    def _ensure_incident(self, incident_id: str) -> dict[str, Any]:
        inc = self._incidents.get(incident_id)
        if inc is not None:
            return inc
        inc = {"id": incident_id, "search_keys": []}
        self._incidents[incident_id] = inc
        dump_yaml(incident_manifest_path(self._root, incident_id), inc)
        return inc

    def _linked_reports(self, iuuid: str) -> list[str]:
        return [ruuid for ruuid, inc in self._report_incident.items() if inc == iuuid]

    def _genesis(self, report_ids: list[str]) -> str | None:
        best_key: tuple[str, str] | None = None
        best_uuid: str | None = None
        for ruuid in report_ids:
            rdate = self._reports.get(ruuid, {}).get("report_date", "")
            key = (rdate, ruuid)
            if best_key is None or key < best_key:
                best_key, best_uuid = key, ruuid
        return best_uuid

    def _derive_incidents(self) -> list[Incident]:
        result: list[Incident] = []
        for iuuid in self._incidents:
            genesis = self._genesis(self._linked_reports(iuuid))
            if genesis is None:
                continue
            greport = self._reports.get(genesis, {})
            source = greport.get("source", "")
            category = "disease" if source == "WHO" else "geophysical"
            result.append(
                Incident(
                    incident_id=iuuid,  # type: ignore[arg-type]
                    incident_category=category,
                    incident_type=greport.get("incident_type", ""),
                    name=greport.get("name", ""),
                    first_seen_at=greport.get("report_date", ""),
                    genesis_report_id=genesis,  # type: ignore[arg-type]
                )
            )
        result.sort(key=lambda i: i.first_seen_at)
        return result

    def set_search_keys(self, incident_id: str, search_keys: list[str]) -> None:
        inc = self._ensure_incident(incident_id)
        inc["search_keys"] = list(search_keys)
        dump_yaml(incident_manifest_path(self._root, incident_id), inc)

    # ----------------------------------------------------- source reports in

    def ingest_source_report(self, report: SourceReport) -> str:
        ruuid = _tree.report_uuid(report.source, report.source_id)
        if ruuid in self._reports:
            return ruuid
        data: dict[str, Any] = {
            "id": ruuid,
            "source": report.source,
            "source_id": report.source_id,
            "incident_type": report.incident_type,
            "name": report.name,
            "report_date": report.report_date,
            "news_searched_at": report.news_searched_at or "",
            "places": [],
            "raw_fields": _coerce_raw(report.raw_fields),
        }
        path = report_staging_path(self._root, report.source, ruuid)
        dump_yaml(path, data)
        self._index_report(data, path, incident_id=None)
        return ruuid

    def ingest_report_places(
        self, report_id: str, places: list[ReportPlace]
    ) -> None:
        report = self._reports.get(report_id)
        if report is None:
            return
        existing = {
            (p["country_code"], p["subdivision"], p["locality"]): p
            for p in report.get("places", [])
        }
        changed = False
        for pl in places:
            key = (pl.country_code, pl.subdivision, pl.locality)
            if key not in existing:
                existing[key] = _place_dict(pl)
                changed = True
        if not changed:
            return
        report["places"] = list(existing.values())
        dump_yaml(self._report_path[report_id], report)

    def mark_report_searched(
        self, source: str, source_id: str, timestamp: str
    ) -> None:
        ruuid = self._reports_by_natural.get(f"{source}:{source_id}")
        if ruuid is None:
            return
        report = self._reports.get(ruuid)
        if report is None:
            return
        report["news_searched_at"] = timestamp
        dump_yaml(self._report_path[ruuid], report)

    # --------------------------------------------------- source reports out

    def _report_to_model(self, ruuid: str) -> SourceReport:
        d = self._reports[ruuid]
        return SourceReport(
            source=d.get("source", ""),
            source_id=d.get("source_id", ""),
            incident_type=d.get("incident_type", ""),
            name=d.get("name", ""),
            places=[],
            report_date=d.get("report_date", ""),
            raw_fields=_coerce_raw(d.get("raw_fields")),
            news_searched_at=d.get("news_searched_at", ""),
        )

    def _report_full(self, ruuid: str) -> SourceReport:
        return dataclasses.replace(
            self._report_to_model(ruuid), places=self.read_report_places(ruuid)
        )

    def read_report_places(self, report_id: str) -> list[ReportPlace]:
        report = self._reports.get(report_id)
        if report is None:
            return []
        return [_place_from_dict(p) for p in report.get("places", [])]

    def read_searched_report_keys(self) -> set[str]:
        return {
            _natural_key(d)
            for d in self._reports.values()
            if d.get("news_searched_at")
        }

    def read_source_report_keys(self) -> set[str]:
        return {_natural_key(d) for d in self._reports.values()}

    def read_source_reports(self) -> list[SourceReport]:
        return [self._report_to_model(ruuid) for ruuid in self._reports]

    def read_source_report_by_id(self, report_id: str) -> SourceReport | None:
        if report_id not in self._reports:
            return None
        return self._report_full(report_id)

    # ------------------------------------------------------------- news in/out

    def _news_to_model(self, nuuid: str) -> NewsItem:
        d = self._news[nuuid]
        return NewsItem(
            url=d.get("url", ""),
            title=d.get("title", ""),
            body=d.get("body", ""),
            published_date=d.get("published_date", ""),
            source=d.get("source", ""),
            domain=d.get("domain", ""),
            image=d.get("image", ""),
            news_id=nuuid,  # type: ignore[arg-type]
        )

    def ingest_news_item(self, item: NewsItem) -> str:
        nuuid = _tree.news_uuid(item.url)
        if nuuid in self._news:
            return nuuid
        data: dict[str, Any] = {
            "id": nuuid,
            "url": item.url,
            "title": item.title,
            "body": item.body,
            "published_date": item.published_date,
            "source": item.source,
            "domain": item.domain,
            "image": item.image,
        }
        path = news_staging_path(self._root, nuuid)
        dump_yaml(path, data)
        self._index_news(data, path, incident_id=None, log_date=None)
        return nuuid

    def read_news_item(self, news_id: str) -> NewsItem:
        if news_id not in self._news:
            raise KeyError(news_id)
        return self._news_to_model(news_id)

    # -------------------------------------------------- news <-> incident link

    def assign_news_to_incident(self, news_id: str, incident_id: str) -> None:
        if news_id not in self._news:
            return
        if self._news_log.get(news_id) is not None:
            return
        self._ensure_incident(incident_id)
        current = self._news_incident.get(news_id)
        if current == incident_id:
            return
        new_path = incident_news_path(self._root, incident_id, news_id)
        self._move(self._news_path[news_id], new_path)
        self._news_incident[news_id] = incident_id
        self._news_path[news_id] = new_path

    def read_incident_for_news(self, news_id: str) -> str | None:
        if news_id not in self._news:
            return None
        return self._news_incident.get(news_id)

    def read_incidents_for_news(
        self, news_ids: set[str]
    ) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for nuuid in news_ids:
            out[nuuid] = set()
            inc = self.read_incident_for_news(nuuid)
            if inc is not None:
                out[nuuid].add(inc)
        return out

    # ----------------------------------------------- report <-> incident link

    def add_report_incident(self, report_id: str, incident_id: str) -> None:
        report = self._reports.get(report_id)
        if report is None:
            return
        inc = self._ensure_incident(incident_id)
        if self._report_incident.get(report_id) == incident_id:
            return
        source = report.get("source", "")
        new_path = incident_report_path(self._root, incident_id, source, report_id)
        self._move(self._report_path[report_id], new_path)
        self._report_incident[report_id] = incident_id
        self._report_path[report_id] = new_path
        if not inc.get("search_keys"):
            keys = derive_repoll_keys(self._report_full(report_id))
            if keys:
                inc["search_keys"] = keys
                dump_yaml(incident_manifest_path(self._root, incident_id), inc)

    def read_report_ids_for_incident(self, incident_id: str) -> list[str]:
        return self._linked_reports(incident_id)

    def read_incident_ids_for_report(self, report_id: str) -> list[str]:
        inc = self._report_incident.get(report_id)
        return [inc] if inc is not None else []

    def read_incident_ids_for_source_id(self, source_id: str) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for ruuid, r in self._reports.items():
            if r.get("source_id") != source_id:
                continue
            inc = self._report_incident.get(ruuid)
            if inc is not None and inc not in seen:
                seen.add(inc)
                out.append(inc)
        return out

    # ------------------------------------------------------------- timeline

    def _upsert_log(
        self, incident_id: str, log_date: str, summary: str
    ) -> dict[str, Any]:
        bucket = self._logs.setdefault(incident_id, {})
        existing = bucket.get(log_date)
        if existing is None:
            data = {"log_date": log_date, "summary": summary}
        else:
            data = existing
            if summary and summary not in data.get("summary", ""):
                data["summary"] = f"{data.get('summary', '')}\n{summary}".strip("\n")
        bucket[log_date] = data
        dump_yaml(log_path(self._root, incident_id, log_date), data)
        return data

    def append_timeline(self, row: IncidentLog) -> None:
        self._upsert_log(str(row.incident_id), row.log_date, row.summary)

    def append_timeline_with_provenance(
        self, log: IncidentLog, news_ids: set[str]
    ) -> None:
        incident_id = str(log.incident_id)
        self._upsert_log(incident_id, log.log_date, log.summary)
        for nuuid in news_ids:
            if nuuid not in self._news:
                continue
            if self._news_log.get(nuuid) is not None:
                continue
            dst = log_news_path(self._root, incident_id, log.log_date, nuuid)
            self._move(self._news_path[nuuid], dst)
            self._news_log[nuuid] = log.log_date
            self._news_path[nuuid] = dst

    def read_summarized_news_ids(self, incident_id: str) -> set[str]:
        return {
            nuuid
            for nuuid, ld in self._news_log.items()
            if ld is not None and self._news_incident.get(nuuid) == incident_id
        }

    def read_timeline(self, incident_id: str) -> list[IncidentLog]:
        bucket = self._logs.get(incident_id, {})
        return [
            IncidentLog(
                incident_id=incident_id,  # type: ignore[arg-type]
                log_date=log_date,
                summary=bucket[log_date].get("summary", ""),
            )
            for log_date in sorted(bucket)
        ]

    # ------------------------------------------------------------- read model

    def read_incidents(self) -> list[Incident]:
        return self._derive_incidents()

    def read_news(self, incident_id: str) -> list[NewsItem]:
        return [
            self._news_to_model(nuuid)
            for nuuid in self._news
            if self._news_incident.get(nuuid) == incident_id
        ]

    def _pending_news_max_dates(self) -> dict[str, datetime]:
        max_pub: dict[str, datetime] = {}
        for nuuid, n in self._news.items():
            inc = self._news_incident.get(nuuid)
            if inc is None or self._news_log.get(nuuid) is not None:
                continue
            try:
                dt = _as_utc(datetime.fromisoformat(n.get("published_date", "")))
            except (ValueError, TypeError):
                continue
            if inc not in max_pub or dt > max_pub[inc]:
                max_pub[inc] = dt
        return max_pub

    def active_incidents(self, window_days: int) -> list[Incident]:
        now = _as_utc(self._clock())
        cutoff = now - timedelta(days=window_days)
        max_pub = self._pending_news_max_dates()
        active_ids = [inc for inc, dt in max_pub.items() if cutoff <= dt <= now]
        if not active_ids:
            return []
        by_id = {i.incident_id: i for i in self.read_incidents()}
        return [by_id[i] for i in sorted(active_ids) if i in by_id]

    def read_logs_with_news(
        self, incident_id: str
    ) -> list[tuple[IncidentLog, list[NewsItem]]]:
        bucket = self._logs.get(incident_id, {})
        out: list[tuple[IncidentLog, list[NewsItem]]] = []
        for log_date in sorted(bucket):
            log = IncidentLog(
                incident_id=incident_id,  # type: ignore[arg-type]
                log_date=log_date,
                summary=bucket[log_date].get("summary", ""),
            )
            linked = [
                self._news_to_model(nuuid)
                for nuuid in self._news
                if self._news_incident.get(nuuid) == incident_id
                and self._news_log.get(nuuid) == log_date
            ]
            out.append((log, linked))
        return out

    # ---------------------------------------------------------- incident merge

    def merge_incidents(self, source: str, target: str) -> None:
        if source not in self._incidents or target not in self._incidents:
            return
        if source == target:
            return
        self._merge_reports(source, target)
        self._merge_pending_news(source, target)
        source_logs = self._logs.pop(source, {})
        target_logs = self._logs.setdefault(target, {})
        for log_date, s_log in sorted(source_logs.items()):
            self._merge_one_log(source, target, log_date, s_log, target_logs)
        shutil.rmtree(incident_dir(self._root, source), ignore_errors=True)
        self._incidents.pop(source, None)

    def _merge_reports(self, source: str, target: str) -> None:
        for ruuid in list(self._linked_reports(source)):
            r_source = self._reports[ruuid].get("source", "")
            new_path = incident_report_path(self._root, target, r_source, ruuid)
            self._move(self._report_path[ruuid], new_path)
            self._report_incident[ruuid] = target
            self._report_path[ruuid] = new_path

    def _merge_pending_news(self, source: str, target: str) -> None:
        for nuuid, inc in list(self._news_incident.items()):
            if inc != source or self._news_log.get(nuuid) is not None:
                continue
            new_path = incident_news_path(self._root, target, nuuid)
            self._move(self._news_path[nuuid], new_path)
            self._news_incident[nuuid] = target
            self._news_path[nuuid] = new_path

    def _merge_one_log(
        self,
        source: str,
        target: str,
        log_date: str,
        s_log: dict[str, Any],
        target_logs: dict[str, dict[str, Any]],
    ) -> None:
        if log_date not in target_logs:
            self._move(
                log_path(self._root, source, log_date),
                log_path(self._root, target, log_date),
            )
            target_logs[log_date] = s_log
        else:
            self._merge_summary(target, log_date, s_log, target_logs[log_date])
        self._relocate_log_news(source, target, log_date)

    def _merge_summary(
        self,
        target: str,
        log_date: str,
        s_log: dict[str, Any],
        t_log: dict[str, Any],
    ) -> None:
        s_sum = s_log.get("summary", "")
        if not s_sum or s_sum in t_log.get("summary", ""):
            return
        t_log["summary"] = f"{t_log.get('summary', '')}\n{s_sum}".strip("\n")
        dump_yaml(log_path(self._root, target, log_date), t_log)

    def _relocate_log_news(self, source: str, target: str, log_date: str) -> None:
        s_news_dir = log_dir(self._root, source, log_date) / "news"
        if not s_news_dir.is_dir():
            return
        for p in s_news_dir.glob("*.yaml"):
            nuuid = p.stem
            dst = log_news_path(self._root, target, log_date, nuuid)
            self._move(p, dst)
            self._news_incident[nuuid] = target
            self._news_path[nuuid] = dst
