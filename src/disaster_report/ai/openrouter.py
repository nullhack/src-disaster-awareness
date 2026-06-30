from __future__ import annotations

import json
import re
from typing import Any

import httpx

DEFAULT_FREE_MODELS: tuple[str, ...] = (
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

_SYSTEM_PROMPT = """\
You are an incident analyst for a disaster surveillance pipeline. Your job is to read \
source reports and news articles about ONE disaster incident and produce a structured \
digest that downstream code will persist.

OUTPUT LANGUAGE: English only. Translate or transliterate non-English source text.

ABSOLUTE RULES (NEVER VIOLATE):
1. GROUND EVERY CLAIM IN THE INPUT. If a figure, casualty count, location, or fact is \
not stated verbatim in <source_reports> or <news_articles>, you MUST NOT include it.
2. NEVER FABRICATE NUMBERS. Do not invent death tolls, injury counts, magnitudes, \
affected populations, dates, or place names. If the input says "no casualties reported" \
or is silent, the summary must reflect that - do NOT infer or estimate.
3. NEVER MIX INCIDENTS. Use only facts about THIS incident; ignore background or \
historical comparisons that appear in the input.
4. SEVERITY MUST MATCH EVIDENCE. If the input mentions no casualties and no widespread \
damage, severity MUST be LOW. Reserve HIGH/CRITICAL for input that explicitly states \
mass casualties or large-scale destruction.
5. When information is missing or sparse, write a shorter summary that says what is \
known and explicitly notes what is unconfirmed.

UPDATE MODE (when a source_report has source_name="PRIOR_DIGEST"):
- The PRIOR_DIGEST report describes the IDENTITY of the incident (canonical_name, country, \
type, prior_summary). This IS the incident you are updating. Do NOT change the identity \
to match a different incident that appears in the news.
- The <news_articles> may contain IRRELEVANT articles about other incidents returned by \
imperfect search queries. IGNORE any article that is not clearly about THIS incident \
(same place + same date + same type).
- Preserve the canonical_name and country from the PRIOR_DIGEST report unless the new \
news articles clearly show the original identity was wrong.
- Only update severity or summary using news that is UNAMBIGUOUSLY about THIS incident.
- If ALL news articles are irrelevant, return the prior summary verbatim and severity LOW.

RESPONSE FORMAT RULES:
1. Respond with a SINGLE JSON object - no markdown fences, no prose, no commentary \
before or after.
2. Include EXACTLY the keys defined in OUTPUT SCHEMA - no extra keys, no missing keys.
"""

_USER_TEMPLATE = """\
Produce the digest for the incident described below.

OUTPUT SCHEMA:
{{
  "canonical_name": string,   // Short human-readable name; max ~60 characters.
  "summary": string,          // 2-3 sentence factual summary in English.
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "search_keys": string[]     // 3-5 concise English search phrases for tracking future developments.
}}

SEVERITY RUBRIC:
- LOW      : No casualties, minor or no damage, highly localized.
- MEDIUM   : Localized impact, limited casualties or damage.
- HIGH     : Significant response required, multiple casualties or widespread damage.
- CRITICAL : Catastrophic, mass casualties or large-scale destruction.

SEARCH_KEYS RULES:
- Include 3-5 phrases suited for a news search engine.
- The FIRST phrase MUST be an impact-focused query of the form: "<place> <type> casualties deaths damage"
  (e.g. "Caraballeda earthquake casualties deaths damage"). This is mandatory - downstream code uses it
  to find follow-up news about human impact.
- Remaining phrases should target geography + time (e.g. "Venezuela quake June 2026").

EXAMPLE OUTPUT (shape only - values must come from the actual input, not this example):
{{
  "canonical_name": "Sarangani Earthquake June 2026",
  "summary": "A magnitude 5.2 earthquake struck off the coast of Sarangani, Philippines on 2026-06-29. No major damage or casualties were immediately reported.",
  "severity": "LOW",
  "search_keys": [
    "Sarangani earthquake casualties deaths damage",
    "Philippines quake June 2026",
    "Mindanao earthquake 2026"
  ]
}}

INPUT DATA:
<source_reports>
{source_reports}
</source_reports>

<news_articles>
{news_articles}
</news_articles>

Return only the JSON object.
"""


def _extract_json(content: str) -> dict[str, Any]:
    if not content or not content.strip():
        raise ValueError("empty content")
    text = content.strip()
    fenced = _JSON_FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _format_input(sources: str | list[dict[str, Any]] | dict[str, Any]) -> tuple[str, str]:
    if isinstance(sources, dict) and {"source_reports", "news_articles"} <= sources.keys():
        reports = sources.get("source_reports") or []
        articles = sources.get("news_articles") or []
    elif isinstance(sources, list):
        reports = sources
        articles = []
    elif isinstance(sources, str):
        reports = [{"text": sources}]
        articles = []
    else:
        reports = [sources] if sources else []
        articles = []
    return (
        json.dumps(reports, ensure_ascii=False),
        json.dumps(articles, ensure_ascii=False),
    )


def _build_messages(sources: str | list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, str]]:
    reports_json, articles_json = _format_input(sources)
    user = _USER_TEMPLATE.format(source_reports=reports_json, news_articles=articles_json)
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


class OpenRouterDigester:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        models: tuple[str, ...] = DEFAULT_FREE_MODELS,
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._models = models
        self._timeout = timeout

    def digest(self, sources: str | list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": _build_messages(sources),
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"
        last_error = ""
        for model in self._models:
            payload["model"] = model
            response = httpx.post(url, headers=headers, json=payload, timeout=self._timeout)
            if response.status_code == 200:
                try:
                    body = response.json()
                    content = body["choices"][0]["message"]["content"]
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    last_error = (
                        f"malformed 200 response from {model}: {exc}; "
                        f"body={response.text[:200]!r}"
                    )
                    continue
                try:
                    parsed = _extract_json(content)
                except (ValueError, json.JSONDecodeError) as exc:
                    last_error = f"unparseable content from {model}: {exc}; head={content[:120]!r}"
                    continue
                if not parsed.get("summary"):
                    last_error = f"empty summary from {model}"
                    continue
                return parsed
            last_error = f"{response.status_code} {response.text[:200]}"
        raise RuntimeError(f"all {len(self._models)} models failed; last={last_error}")
