"""Compatibility adapter for the Dojo-owned sandbox MAUD benchmark."""

from __future__ import annotations

from typing import Any, Mapping

import llm_dojo_scoring as _dojo
from llm_dojo_scoring.sandbox_scoring import (
    CLEAN_QUESTIONS,
    CONFLICT,
    MULTI_CLASS_QUESTIONS,
    TYPE_OF_CONSIDERATION,
    gt_labels,
    is_non_answer,
    norm,
    parse_maud_answers,
    same_answer,
)


def score_maud(pred: Mapping[str, Any], maud_clause_labels: Any) -> dict[str, Any]:
    """Forward the prediction and raw labels to the canonical benchmark API."""
    return _dojo.score_sandbox_maud(pred, maud_clause_labels)
