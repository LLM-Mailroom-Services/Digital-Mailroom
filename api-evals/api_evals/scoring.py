"""api_evals.scoring — deterministic scoring reuse for api-evals runs.

Scoring is delegated to the sandbox's existing dojo-backed layer (the
``run_isolated_eval`` whole-run path scores every row with the vendored
llm-dojo-scoring suite, including the SAND-026 empty-GT extraction scope).
This module only lifts the headline numbers into the api-evals report shape.
"""

from __future__ import annotations

from typing import Any

#: Headline score keys, in preferred display order.
HEADLINE_KEYS = (
    "overall_extraction_score",
    "exact_match",
    "doc_type_accuracy",
    "subclass_accuracy",
    "error_count",
    "offline_fallback",
    "n",
)


def headline_scores(scores: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in HEADLINE_KEYS:
        if scores is not None and scores.get(key) is not None:
            out[key] = scores[key]
    if not out and scores:
        out["scores"] = dict(scores)
    return out


def extraction_score(scores: dict[str, Any] | None) -> float | None:
    """The single headline extraction number, when present."""
    if not scores:
        return None
    for key in ("overall_extraction_score", "exact_match"):
        val = scores.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None
