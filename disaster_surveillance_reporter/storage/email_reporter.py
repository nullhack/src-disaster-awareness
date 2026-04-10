"""Email reporter for sending incident reports via Gmail."""

import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

# Load environment variables from .env file
from dotenv import load_dotenv

# Look for .env in project root (parent of storage directory)
env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
)
load_dotenv(env_path)


class EmailReporter:
    """Send incident reports via email as HTML table."""

    def __init__(
        self,
        sender_email: str | None = None,
        password: str | None = None,
        recipient_email: str | None = None,
    ):
        """Initialize EmailReporter.

        Args:
            sender_email: Gmail address. Reads from GMAIL_EMAIL env var if not provided.
            password: App password. Reads from GMAIL_PASSWORD env var if not provided.
            recipient_email: Where to send. Reads from GMAIL_RECIPIENT env var if not provided.
        """
        self._sender_email = sender_email or os.environ.get("GMAIL_EMAIL")
        self._password = (password or os.environ.get("GMAIL_PASSWORD") or "").replace(
            " ", ""
        )
        self._recipient_email = recipient_email or os.environ.get("GMAIL_RECIPIENT")

        if not self._sender_email:
            raise ValueError("GMAIL_EMAIL environment variable is required")
        if not self._password:
            raise ValueError("GMAIL_PASSWORD environment variable is required")
        if not self._recipient_email:
            raise ValueError("GMAIL_RECIPIENT environment variable is required")

    def write(self, incidents: list[dict[str, Any]]) -> None:
        """Send incident report via email.

        Args:
            incidents: List of incident dictionaries to include in report.
        """
        if not incidents:
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"Disaster Surveillance Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        )
        msg["From"] = self._sender_email
        msg["To"] = self._recipient_email

        html_table = self._build_html_table(incidents)
        plain_text = self._build_plain_text(incidents)

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_table, "html"))

        self._send_email(msg)

    def _build_html_table(self, incidents: list[dict[str, Any]]) -> str:
        """Build HTML table from incidents."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h2 {{ color: #333; }}
        .summary-section {{ background: #f9f9f9; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }}
        th {{ background-color: #2196F3; color: white; }}
        tr:nth-child(even) {{ background-color: #f5f5f5; }}
        tr:hover {{ background-color: #e3f2fd; }}
        .priority-HIGH {{ color: #d32f2f; font-weight: bold; }}
        .priority-MEDIUM {{ color: #f57c00; font-weight: bold; }}
        .priority-LOW {{ color: #388e3c; }}
        .status-Active {{ color: #d32f2f; }}
        .status-Forecasted {{ color: #1976D2; }}
        .sources {{ font-size: 10px; color: #666; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }}
        .summary {{ font-size: 11px; color: #444; max-width: 250px; }}
    </style>
</head>
<body>
    <h2>Disaster Surveillance Report - {today}</h2>
    <p><strong>Total incidents:</strong> {len(incidents)}</p>
    <table>
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Summary</th>
            <th>Country</th>
            <th>Type</th>
            <th>Level</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Affected</th>
            <th>Deaths</th>
            <th>Sources</th>
            <th>Classification</th>
        </tr>
"""

        for incident in incidents:
            priority = incident.get("priority", "N/A")
            status = incident.get("status", "N/A")
            priority_class = f"priority-{priority}"
            status_class = f"status-{status}"

            # Get summary (required, never null)
            summary = incident.get("summary", "N/A")
            if summary and len(summary) > 100:
                summary = summary[:100] + "..."

            # Get impact numbers
            affected = incident.get("estimated_affected")
            deaths = incident.get("estimated_deaths")
            affected_str = f"{affected:,}" if affected else "-"
            deaths_str = f"{deaths:,}" if deaths else "-"

            # Get sources as clickable links
            sources = incident.get("sources", [])
            if sources:
                if isinstance(sources, list):
                    source_links = []
                    for s in sources[:3]:  # Max 3 sources
                        name = s.get("name", "?")
                        url = s.get("url", "")
                        if url:
                            source_links.append(f'<a href="{url}">{name}</a>')
                    sources_str = " ".join(source_links)
                else:
                    sources_str = str(sources)[:50]
            else:
                sources_str = "-"

            # Get classification info
            classification = incident.get("classification", {})
            if isinstance(classification, dict):
                class_info = []
                if classification.get("country_group"):
                    class_info.append(f"Group: {classification['country_group']}")
                if classification.get("incident_level"):
                    class_info.append(f"Lvl: {classification['incident_level']}")
                if classification.get("should_report"):
                    class_info.append(f"Report: {classification['should_report']}")
                class_str = ", ".join(class_info) if class_info else "-"
            else:
                class_str = str(classification)[:30] if classification else "-"

            html += f"""        <tr>
            <td><strong>{incident.get("incident_id", "N/A")}</strong></td>
            <td>{incident.get("incident_name", "N/A")}</td>
            <td class="summary">{summary}</td>
            <td>{incident.get("country", "N/A")}</td>
            <td>{incident.get("incident_type", "N/A")}</td>
            <td>{incident.get("incident_level", "-")}</td>
            <td class="{priority_class}">{priority}</td>
            <td class="{status_class}">{status}</td>
            <td>{affected_str}</td>
            <td>{deaths_str}</td>
            <td class="sources">{sources_str}</td>
            <td>{class_str}</td>
        </tr>
"""

        html += """    </table>
    <p style="margin-top: 20px; color: #666; font-size: 12px;">
        Generated by Disaster Surveillance Reporter
    </p>
</body>
</html>"""

        return html

    def _build_plain_text(self, incidents: list[dict[str, Any]]) -> str:
        """Build plain text version of the report."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        lines = [
            f"DISASTER SURVEILLANCE REPORT - {today}",
            f"Total incidents: {len(incidents)}",
            "",
            "ID | Name | Country | Type | Priority | Status",
            "-" * 60,
        ]

        for incident in incidents:
            lines.append(
                f"{incident.get('incident_id', 'N/A')} | "
                f"{incident.get('incident_name', 'N/A')} | "
                f"{incident.get('country', 'N/A')} | "
                f"{incident.get('incident_type', 'N/A')} | "
                f"{incident.get('priority', 'LOW')} | "
                f"{incident.get('status', 'N/A')}"
            )

        lines.append("")
        lines.append("Generated by Disaster Surveillance Reporter")

        return "\n".join(lines)

    def _send_email(self, msg: MIMEMultipart) -> None:
        """Send email via SMTP."""
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(self._sender_email, self._password)
            server.send_message(msg)

    def read(self) -> list[dict[str, Any]]:
        """Read is not supported for email - returns empty list."""
        return []

    def append(self, incidents: list[dict[str, Any]]) -> None:
        """Append is same as write - sends email report."""
        self.write(incidents)


def create_email_reporter(
    sender_email: str | None = None,
    password: str | None = None,
    recipient_email: str | None = None,
) -> EmailReporter:
    """Factory function to create EmailReporter."""
    return EmailReporter(sender_email, password, recipient_email)
