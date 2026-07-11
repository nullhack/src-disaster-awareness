
from __future__ import annotations

import html

from disaster_report.reporting.report import ReportDocument


class MarkdownRenderer:

    def __init__(self) -> None:
        pass

    def render(self, document: ReportDocument) -> str:

        meta = {
            inc.incident_id: (inc.incident_category, inc.incident_type)
            for inc in document.incidents
        }
        sections: dict[str, dict[str, list[str]]] = {
            "geophysical": {},
            "disease": {},
        }
        for row in document.timeline:
            cat, typ = meta.get(row.incident_id, ("geophysical", "Unknown"))
            sections[cat].setdefault(typ, []).append(f"- {html.escape(row.summary)}")
        parts: list[str] = [
            "# Disaster Report",
            f"_Generated: {document.generated_at}_",
        ]
        for cat in ("geophysical", "disease"):
            parts.append(f"## {cat.capitalize()}")
            for typ in sorted(sections[cat]):
                parts.append(f"### {typ}")
                parts.extend(sections[cat][typ])
        return "\n".join(parts)
