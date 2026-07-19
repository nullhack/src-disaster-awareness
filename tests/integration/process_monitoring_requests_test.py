from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from disaster_report.models import Incident, ReportPlace, SourceReport
from disaster_report.store.content import ContentStore
from scripts import process_monitoring_requests as pmr


def _build_report(*, source_id: str = "us6000test") -> SourceReport:
    return SourceReport(
        source="USGS",
        source_id=source_id,
        incident_type="Earthquake",
        name="M 5.0 - Test",
        places=[ReportPlace(country_code="JP", subdivision="", locality="")],
        report_date="2026-07-04",
        raw_fields={},
    )


def _birth(store: ContentStore, tmp_path: Path, *, source_id: str) -> str:
    import uuid

    rid = store.ingest_source_report(_build_report(source_id=source_id))
    inc = uuid.uuid4().hex
    store.add_report_incident(rid, inc)
    return inc


class TestParseBody:
    def test_parses_incident_id_and_action(self) -> None:
        body = (
            "### Incident ID\n"
            "03d6656a4a1852ff\n\n"
            "### Action\n"
            "Enable extended monitoring\n\n"
            "### Rationale (optional)\n"
            "Aftershock sequence ongoing.\n"
        )
        incident_id, action = pmr._parse_body(body)
        assert incident_id == "03d6656a4a1852ff"
        assert action == "enable extended monitoring"

    def test_returns_none_when_heading_absent(self) -> None:
        body = "Just a freeform issue body with no form fields."
        assert pmr._parse_body(body) == (None, None)

    def test_returns_none_for_empty_body(self) -> None:
        assert pmr._parse_body("") == (None, None)


class TestResolveIncident:
    def test_full_uuid_exact_match(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        inc = _birth(store, tmp_path, source_id="us-res-full")
        assert pmr._resolve_incident(store, inc) == inc

    def test_eight_char_prefix_unique(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        inc = _birth(store, tmp_path, source_id="us-res-prefix")
        assert pmr._resolve_incident(store, inc[:8]) == inc

    def test_ambiguous_prefix_returns_none(self, tmp_path: Path) -> None:
        # Mint two incidents with same first-8 chars (very unlikely randomly;
        # mock store.read_incidents to control test setup)
        inc_a = "deadbeefdeadbeefdeadbeefdeadbeef"
        inc_b = "deadbeef00000000000000000000000a"
        mock = MagicMock()
        mock.read_incidents.return_value = [
            Incident(
                incident_id=inc_a,
                incident_category="geophysical",
                incident_type="Earthquake",
                name="A",
                first_seen_at="2026-07-04",
                genesis_report_id="r1",
            ),
            Incident(
                incident_id=inc_b,
                incident_category="geophysical",
                incident_type="Earthquake",
                name="B",
                first_seen_at="2026-07-04",
                genesis_report_id="r2",
            ),
        ]
        assert pmr._resolve_incident(mock, "deadbeef") is None

    def test_no_match_returns_none(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        _birth(store, tmp_path, source_id="us-res-nomatch")
        assert pmr._resolve_incident(store, "ffffffff") is None

    def test_non_hex_returns_none(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        assert pmr._resolve_incident(store, "not-a-hex-id") is None


class TestProcessIssue:
    def _patch_common(self, monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
        calls: dict[str, MagicMock] = {}
        for name in ("_reject", "_apply", "_remove_label", "_add_label", "_close", "_comment"):
            mock = MagicMock(name=name)
            monkeypatch.setattr(pmr, name, mock)
            calls[name] = mock
        return calls

    def test_applies_enable_action(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = ContentStore(tmp_path)
        inc = _birth(store, tmp_path, source_id="us-proc-enable")
        self._patch_common(monkeypatch)
        issue = {
            "number": 42,
            "body": (
                f"### Incident ID\n{inc[:8]}\n\n"
                "### Action\nEnable extended monitoring\n"
            ),
        }
        outcome = pmr._process_issue(issue, store)
        assert outcome == "applied:enabled"
        assert store.extended_monitoring_incidents()[0].incident_id == inc

    def test_applies_disable_action(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = ContentStore(tmp_path)
        inc = _birth(store, tmp_path, source_id="us-proc-disable")
        store.set_extended_monitoring(inc, True)
        self._patch_common(monkeypatch)
        issue = {
            "number": 43,
            "body": (
                f"### Incident ID\n{inc}\n\n"
                "### Action\nDisable extended monitoring\n"
            ),
        }
        outcome = pmr._process_issue(issue, store)
        assert outcome == "applied:disabled"
        assert store.extended_monitoring_incidents() == []

    def test_rejects_when_incident_id_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = ContentStore(tmp_path)
        calls = self._patch_common(monkeypatch)
        issue = {
            "number": 44,
            "body": "### Action\nEnable extended monitoring\n",
        }
        outcome = pmr._process_issue(issue, store)
        assert outcome == "rejected:no-id"
        calls["_reject"].assert_called_once()

    def test_rejects_when_action_unrecognized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = ContentStore(tmp_path)
        inc = _birth(store, tmp_path, source_id="us-proc-bad-action")
        calls = self._patch_common(monkeypatch)
        issue = {
            "number": 45,
            "body": f"### Incident ID\n{inc[:8]}\n\n### Action\nMaybe track it?\n",
        }
        outcome = pmr._process_issue(issue, store)
        assert outcome == "rejected:bad-action"
        calls["_reject"].assert_called_once()

    def test_rejects_when_identifier_does_not_resolve(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = ContentStore(tmp_path)
        calls = self._patch_common(monkeypatch)
        issue = {
            "number": 46,
            "body": (
                "### Incident ID\nffffffff\n\n"
                "### Action\nEnable extended monitoring\n"
            ),
        }
        outcome = pmr._process_issue(issue, store)
        assert outcome == "rejected:no-match"
        calls["_reject"].assert_called_once()
