"""Compatibility adapter for the Dojo-owned sandbox CUAD benchmark."""

from __future__ import annotations

from typing import Any, Mapping

import llm_dojo_scoring as _dojo
from llm_dojo_scoring.sandbox_scoring import (
    FIELD_CATEGORY,
    VALUE_FIELDS,
    gt_categories,
    predicted_categories,
)


def score_cuad(pred: Mapping[str, Any], cuad_clause_labels: Any) -> dict[str, Any]:
    """Forward the prediction and raw labels to the canonical benchmark API."""
    return _dojo.score_sandbox_cuad(pred, cuad_clause_labels)
