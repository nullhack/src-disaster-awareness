

from __future__ import annotations

import html
import re
from email.utils import parsedate_to_datetime
from typing import Any


_TAG_RE = re.compile(r"<[^>]+>")


def local_tag(tag: str) -> str:

    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def to_iso_date(rfc822: str) -> str:

    if not rfc822:
        return ""
    try:
        dt = parsedate_to_datetime(rfc822)
    except (TypeError, ValueError):
        return ""
    if dt is None:
        return ""
    return dt.date().isoformat()


def clean_html(raw: str) -> str:

    text = _TAG_RE.sub("", raw)
    return html.unescape(text).strip()


def as_dict(obj: Any) -> dict[str, Any]:

    if isinstance(obj, dict):
        return dict(obj)
    return {}


def safe_float(value: object) -> float | None:

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None
