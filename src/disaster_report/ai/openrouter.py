from __future__ import annotations

import time
from typing import Any, Literal

import dspy

from disaster_report.classification import is_disease_type

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
PandemicPotential = Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
EventStatus = Literal[
    "new_outbreak", "ongoing", "escalating", "containment",
    "elimination_declared", "non_event",
]
# Canonical WHO/CDC short pathogen names. The Literal is enforced at parse
# time by dspy's adapter (pydantic TypeAdapter), so the model MUST emit one of
# these exact strings (or "Other") or the prediction fails parsing and is
# retried. This is the conformance mechanism that killed the "Ebola disease
# caused by Bundibugyo virus" / "Ebola" / "Ebola virus disease" label split.
DiseaseName = Literal[
    "Ebola", "Marburg", "Mpox", "Nipah", "Cholera", "Measles", "Polio",
    "Yellow Fever", "Plague", "Anthrax", "Dengue", "Malaria", "Influenza",
    "COVID-19", "Hantavirus", "Lassa", "MERS", "SARS", "Rabies",
    "Hand Foot Mouth Disease", "Gastroenteritis", "Leishmaniasis",
    "Diphtheria", "Pneumonia", "Meningitis", "Avian Influenza",
    "West Nile", "Melioidosis", "Tuberculosis", "Shigellosis",
    "Japanese Encephalitis", "Rift Valley Fever",
    "Crimean-Congo Hemorrhagic Fever", "Other",
]

# Shared task framing folded into every Signature docstring. Keeps the model
# grounded, English-only, and compliant with the update-mode rules.
_TASK_INSTRUCTIONS = """\
You are an incident analyst for a disaster surveillance pipeline. Read the source \
reports and news articles about ONE incident and produce structured output.

OUTPUT LANGUAGE: English only. Translate or transliterate non-English source text.

ABSOLUTE RULES (NEVER VIOLATE):
1. GROUND EVERY CLAIM IN THE INPUT. If a figure, casualty count, location, or fact is \
not stated verbatim in source_reports or news_articles, you MUST NOT include it.
2. NEVER FABRICATE NUMBERS. Do not invent death tolls, injury counts, magnitudes, \
affected populations, dates, or place names. If the input is silent, say so.
3. NEVER MIX INCIDENTS. Use only facts about THIS incident.

UPDATE MODE (when a source_report has source_name="PRIOR_DIGEST"):
- The PRIOR_DIGEST report describes the IDENTITY of the incident. This IS the incident \
you are updating. Do NOT change the identity to match a different incident in the news.
- news_articles may contain IRRELEVANT articles returned by imperfect search queries. \
IGNORE any article not clearly about THIS incident (same place + same date + same type).
- If ALL news articles are irrelevant, treat the incident as LOW severity / NONE pp / \
ongoing event_status, and write a short summary based on the prior digest only.
"""

_SEVERITY_RUBRIC = """\
SEVERITY RUBRIC (current human impact of THIS event):
- LOW      : No casualties, minor or no damage, highly localized / single or few cases.
- MEDIUM   : Localized impact, cluster or local outbreak, limited casualties or damage.
- HIGH     : Significant response required, widespread outbreak, multiple casualties.
- CRITICAL : Catastrophic, mass casualties or large-scale destruction / overwhelming epidemic.
Severity MUST match evidence: no casualties + no widespread damage => LOW.
"""

_DISEASE_RUBRIC = """\
PANDEMIC POTENTIAL RUBRIC (risk of wider spread, independent of current severity):
- NONE     : Not an infectious-disease transmission event (environmental, single imported \
case with no local spread, animal-only).
- LOW      : Known endemic pathogen, contained, familiar transmission route, no novel strain.
- MEDIUM   : Sustained local transmission in one area, or a pathogen with moderate spread history.
- HIGH     : Cross-border spread, novel/high-pathogenic strain, healthcare-worker transmission, \
or WHO-flagged concern.
- CRITICAL : Sustained human-to-human transmission across multiple countries, or a known \
pandemic-prone pathogen (ebola, marburg, mpox, nipah, h5n1, sars, mers) with active cases.

EVENT STATUS RUBRIC (what kind of signal is this?):
- new_outbreak          : A genuinely NEW outbreak report.
- ongoing               : An established, continuing outbreak.
- escalating            : Cases actively rising or spreading to new areas.
- containment           : Outbreak being brought under control / case counts falling.
- elimination_declared  : Area declared disease-free / elimination milestone (NOT a new event).
- non_event             : NOT an actual outbreak - false alarm, eradication milestone, historical \
recap, policy/insurance/computer-virus news, or unrelated article matched by keyword noise.

CRITICAL EVENT_STATUS RULES (NEVER VIOLATE):
- If the source describes an area being declared polio-free / disease-free / elimination \
milestone, event_status MUST be "elimination_declared" (NOT new_outbreak) and \
pandemic_potential MUST be "NONE".
- If the article is about a "computer virus", "insurance", policy, or a non-disease story that \
matched a keyword by accident, event_status MUST be "non_event", pandemic_potential MUST be \
"NONE", and severity MUST be "LOW".
- Only set "new_outbreak", "ongoing", or "escalating" when real active cases/outbreak are described.

DISEASE LABEL RULE (for the disease_name field):
- Return the SINGLE canonical pathogen name from the allowed enum (e.g. "Ebola", "Marburg", \
"Cholera", "COVID-19", "Mpox", "Nipah", "Measles", "Polio", "Yellow Fever", "Plague", \
"Anthrax", "Dengue", "MERS", "Influenza", "Hantavirus", "Lassa", "Meningitis").
- Use the common SHORT name, NOT the full title. Strip clade/variant qualifiers: e.g. an outbreak \
of "Ebola disease caused by Bundibugyo virus" is disease_name "Ebola"; "Mpox clade Ib" is "Mpox"; \
"Avian Influenza A(H5N1)" is "Avian Influenza".
- If the pathogen is NOT in the enum, return "Other".
- If the incident is genuinely NOT an infectious disease (non_event / computer virus / policy), \
return "Other".
"""


class DiseaseClassify(dspy.Signature):
    f"""{_TASK_INSTRUCTIONS}
    {_SEVERITY_RUBRIC}
    {_DISEASE_RUBRIC}

    Classify the INFECTIOUS-DISEASE incident described in the inputs. Return the \
    canonical disease_name (enum), current severity, pandemic_potential, and event_status.
    """
    source_reports: str = dspy.InputField(desc="JSON array of source reports")
    news_articles: str = dspy.InputField(desc="JSON array of news articles")
    severity: Severity = dspy.OutputField(desc="current human impact per rubric")
    disease_name: DiseaseName = dspy.OutputField(desc="canonical WHO/CDC short pathogen name from the enum, or 'Other'")
    pandemic_potential: PandemicPotential = dspy.OutputField(desc="wider-spread risk per rubric")
    event_status: EventStatus = dspy.OutputField(desc="what kind of signal this is, per rubric")


class DiseaseSummary(dspy.Signature):
    f"""{_TASK_INSTRUCTIONS}
    Write a 2-3 sentence factual English summary of the INFECTIOUS-DISEASE incident: \
    pathogen, place, scale (cases/deaths if stated), and response. Ground every claim \
    in the inputs; never fabricate figures.
    """
    source_reports: str = dspy.InputField(desc="JSON array of source reports")
    news_articles: str = dspy.InputField(desc="JSON array of news articles")
    summary: str = dspy.OutputField(desc="2-3 sentence factual English summary")


class PhysicalSummary(dspy.Signature):
    f"""{_TASK_INSTRUCTIONS}
    {_SEVERITY_RUBRIC}
    Write a 2-3 sentence factual English summary of the PHYSICAL-disaster incident \
    (earthquake, flood, storm, wildfire, volcano). Cover location, magnitude/scale \
    if stated, and reported impact (casualties/damage). Ground every claim; never \
    fabricate figures. Severity is derived downstream from magnitude/alert levels, \
    so the summary prose should focus on what happened, not on rating severity.
    """
    source_reports: str = dspy.InputField(desc="JSON array of source reports")
    news_articles: str = dspy.InputField(desc="JSON array of news articles")
    summary: str = dspy.OutputField(desc="2-3 sentence factual English summary")


def _build_inputs(sources: str | list[dict[str, Any]] | dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Return (reports, {source_reports, news_articles}) normalising input shapes."""
    import json

    if isinstance(sources, dict) and {"source_reports", "news_articles"} <= sources.keys():
        reports = sources.get("source_reports") or []
        articles = sources.get("news_articles") or []
    elif isinstance(sources, list):
        reports, articles = sources, []
    elif isinstance(sources, str):
        reports, articles = [{"text": sources}], []
    else:
        reports = [sources] if sources else []
        articles = []
    inputs = {
        "source_reports": json.dumps(reports, ensure_ascii=False),
        "news_articles": json.dumps(articles, ensure_ascii=False),
    }
    return reports, inputs


def _is_disease_material(reports: list[dict[str, Any]]) -> bool:
    """Route onto the disease track when any source report declares a disease type."""
    for report in reports:
        if not isinstance(report, dict):
            continue
        if is_disease_type(str(report.get("incident_type", ""))):
            return True
    return False


class OpenRouterDigester:
    """LLM digester backed by dspy typed Signatures over OpenRouter.

    The AI surface is split into focused Signatures for partial-success:
      * disease  -> DiseaseClassify (severity/disease_name/pandemic_potential/event_status) + DiseaseSummary
      * physical -> PhysicalSummary (summary only; severity is derived in code)
    Per-call ``lm=`` override is used so concurrent callers (e.g. the batch
    redigest) do not race on dspy's global LM setting. Each piece retries with
    backoff across all configured models, so a transient free-tier failure on
    one piece does not lose the others.
    """

    def __init__(
        self,
        api_key: str,
        models: tuple[str, ...],
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 120.0,
        max_attempts: int = 3,
        backoff: float = 2.0,
    ) -> None:
        if not models:
            raise ValueError("at least one model is required")
        self._max_attempts = max_attempts
        self._backoff = backoff
        common = {
            "api_base": base_url.rstrip("/"),
            "api_key": api_key,
            "timeout": timeout,
            "extra_headers": {
                "HTTP-Referer": "https://disaster.report",
                "X-Title": "disaster-report",
            },
        }
        self._lms: list[dspy.LM] = [
            dspy.LM(model=f"openrouter/{m.removeprefix('openrouter/')}", **common)
            for m in models
        ]
        self._classify = dspy.Predict(DiseaseClassify)
        self._disease_summary = dspy.Predict(DiseaseSummary)
        self._physical_summary = dspy.Predict(PhysicalSummary)

    def _invoke(
        self, predictor: dspy.Predict, inputs: dict[str, str], require_field: str | None = None,
    ) -> tuple[dspy.Prediction | None, str]:
        """Loop models x attempts. Returns (Prediction, "") or (None, last_error)."""
        last_error = ""
        for lm in self._lms:
            model_name = lm.model
            for attempt in range(self._max_attempts):
                try:
                    pred = predictor(lm=lm, **inputs)
                except Exception as exc:  # network / parse / transient provider error
                    last_error = f"{model_name}: {type(exc).__name__}: {str(exc)[:200]}"
                    if attempt < self._max_attempts - 1:
                        time.sleep(self._backoff * (attempt + 1))
                        continue
                    break  # retries exhausted for this model -> try the next
                if require_field:
                    if not (getattr(pred, require_field, "") or ""):
                        last_error = f"{model_name}: empty {require_field}"
                        break  # model-quality issue -> next model
                return pred, ""
        return None, last_error

    def digest(self, sources: str | list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
        """Route by incident_type and run the focused Signatures.

        Returns a dict of ONLY the AI-produced fields. Disease may yield any
        subset of {severity, disease_name, pandemic_potential, event_status,
        summary} (partial success: classify and summarize run independently).
        Physical yields {summary} (severity is derived by the caller).

        Raises RuntimeError only if EVERY piece failed.
        """
        reports, inputs = _build_inputs(sources)
        disease_track = _is_disease_material(reports)
        out: dict[str, Any] = {}
        errors: list[str] = []

        if disease_track:
            pred, err = self._invoke(self._classify, inputs)
            if pred is not None:
                out["severity"] = getattr(pred, "severity", "") or ""
                out["disease_name"] = getattr(pred, "disease_name", "") or ""
                out["pandemic_potential"] = getattr(pred, "pandemic_potential", "") or ""
                out["event_status"] = getattr(pred, "event_status", "") or ""
            elif err:
                errors.append(f"classify: {err}")

            pred, err = self._invoke(
                self._disease_summary, inputs, require_field="summary",
            )
            if pred is not None:
                out["summary"] = getattr(pred, "summary", "") or ""
            elif err:
                errors.append(f"summary: {err}")

            if not out:
                raise RuntimeError(
                    f"disease digest failed (classify+summary); last={' | '.join(errors)}"
                )
        else:
            pred, err = self._invoke(
                self._physical_summary, inputs, require_field="summary",
            )
            if pred is not None:
                out["summary"] = getattr(pred, "summary", "") or ""
            else:
                raise RuntimeError(f"physical digest failed (summary); last={err}")
        return out
