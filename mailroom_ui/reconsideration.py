"""Objective review / reconsideration causes.

Self-reported ``classification_confidence`` / ``extraction_confidence`` can
be overconfident. These triggers are derived only from grounded scores,
ground-truth labels, judge verdicts, schema/guardrail flags, and reporting
completeness — never from the model's stated confidence alone.

Used by the visualizer to pull archived-but-wrong runs back onto the REVIEW
siding so they cannot silently snowball through the catalog. The sister
pipeline mirrors the same cause tokens in ``pipeline/reconsideration.py``.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence

from .pipeline_schema import EXTRACT_CLASS_ALIASES, PipelineSchema, canonical_score_name

# Canonical cause tokens (keep in sync with llm-mailroom).
CLASS_MISS = "class_miss"
SUBCLASS_MISS = "subclass_miss"
EXTRACTION_MISS = "extraction_miss"
JUDGE_MISS = "judge_miss"
JUDGE_PARTIAL = "judge_partial"
SCHEMA_INVALID = "schema_invalid"
GUARDRAIL = "guardrail"
PARSE_ERROR = "parse_error"
REPORTING_INCOMPLETE = "reporting_incomplete"
NEEDS_JUDGE = "needs_judge_review"

CAUSE_LABELS: dict[str, str] = {
    CLASS_MISS: "classification miss vs ground truth",
    SUBCLASS_MISS: "subclass miss vs ground truth",
    EXTRACTION_MISS: "extraction score below floor (not self-reported conf)",
    JUDGE_MISS: "judge verdict MISS",
    JUDGE_PARTIAL: "judge verdict PARTIAL — incomplete reporting",
    SCHEMA_INVALID: "schema invalid",
    GUARDRAIL: "guardrail triggered",
    PARSE_ERROR: "parse error",
    REPORTING_INCOMPLETE: "report / completeness incomplete",
    NEEDS_JUDGE: "deterministic scorer wanted a judge that the high-conf path skipped",
}

_TRUTHY_ZERO = frozenset({0, 0.0, "0", "false", "False", False})
_DONE_STAGES = frozenset({"archived", "archive", "catalog", "report", "compile_report"})


def _align_class(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    key = str(token).strip().lower()
    if not key:
        return None
    return EXTRACT_CLASS_ALIASES.get(key, key)


def _score(scores: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in scores and scores[name] is not None:
            return scores[name]
        canon = canonical_score_name(name)
        if canon in scores and scores[canon] is not None:
            return scores[canon]
    return None


def _as_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_falsey_flag(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value.strip().lower() in {"false", "no", "off"}:
        return True
    return value in _TRUTHY_ZERO


def _is_true_flag(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value.strip().lower() in {"true", "yes", "on", "1"}:
        return True
    try:
        return float(value) == 1.0
    except (TypeError, ValueError):
        return bool(value) and value not in _TRUTHY_ZERO


def collect_review_causes(
    *,
    doc_type: Optional[str] = None,
    doc_subclass: Optional[str] = None,
    contract_subtype: Optional[str] = None,
    expected_hf_class: Optional[str] = None,
    expected_subclass: Optional[str] = None,
    scores: Optional[Mapping[str, Any]] = None,
    verdict: Optional[str] = None,
    schema: Optional[PipelineSchema] = None,
) -> list[str]:
    """Return canonical cause tokens. Empty when no objective miss is present."""
    scores = scores or {}
    schema = schema or PipelineSchema()
    # Per-class severity (taxonomy confidence.by_class) wins over the global
    # floor so a stricter class (e.g. contract low=0.90) is judged by its own bar.
    try:
        floor = float(schema.thresholds_for(doc_type).get("low", schema.confidence_low))
    except (AttributeError, TypeError, ValueError):
        floor = float(getattr(schema, "confidence_low", 0.88) or 0.88)
    causes: list[str] = []

    expected = _align_class(expected_hf_class)
    predicted = _align_class(doc_type)
    if expected and predicted and expected != predicted:
        causes.append(CLASS_MISS)
    class_correct = _score(scores, "class_correct", "classification_correct")
    if _is_falsey_flag(class_correct) and CLASS_MISS not in causes:
        causes.append(CLASS_MISS)

    expected_sub = (expected_subclass or "").strip().lower() or None
    predicted_sub = (doc_subclass or contract_subtype or "").strip().lower() or None
    if expected_sub and predicted_sub and expected_sub != predicted_sub:
        causes.append(SUBCLASS_MISS)

    overall = _as_float(_score(scores, "extraction_overall_score", "extraction_field_score"))
    if overall is not None and overall < floor:
        causes.append(EXTRACTION_MISS)
    presence = _as_float(_score(scores, "expected_field_presence"))
    if presence is not None and presence < floor and EXTRACTION_MISS not in causes:
        causes.append(EXTRACTION_MISS)

    verdict_token = (verdict or "")
    if not verdict_token:
        raw = _score(scores, "mailroom-pipeline-judge")
        verdict_token = str(raw).strip() if raw is not None else ""
    upper = verdict_token.upper()
    if upper == "MISS":
        causes.append(JUDGE_MISS)
    elif upper == "PARTIAL":
        causes.append(JUDGE_PARTIAL)

    if _is_falsey_flag(_score(scores, "schema_valid")):
        causes.append(SCHEMA_INVALID)
    if _is_true_flag(_score(scores, "guardrail_triggered")):
        causes.append(GUARDRAIL)
    if _is_true_flag(_score(scores, "parse_error")):
        causes.append(PARSE_ERROR)

    completeness = _as_float(_score(scores, "completeness"))
    completeness_label = str(_score(scores, "completeness_label") or "").strip().upper()
    if (completeness is not None and completeness < floor) or completeness_label in {"LOW", "INCOMPLETE"}:
        causes.append(REPORTING_INCOMPLETE)

    if _is_true_flag(_score(scores, "extraction_needs_judge_review")):
        causes.append(NEEDS_JUDGE)

    # Stable unique order.
    seen: set[str] = set()
    ordered: list[str] = []
    for token in causes:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def format_causes(causes: Sequence[str]) -> Optional[str]:
    if not causes:
        return None
    labels = [CAUSE_LABELS.get(c, c.replace("_", " ")) for c in causes]
    return "reconsider: " + "; ".join(labels)


def should_reconsider(stage: Optional[str], causes: Iterable[str]) -> bool:
    """True when a run looks finished but objective misses remain."""
    if not causes:
        return False
    st = (stage or "").strip().lower()
    return st in _DONE_STAGES
