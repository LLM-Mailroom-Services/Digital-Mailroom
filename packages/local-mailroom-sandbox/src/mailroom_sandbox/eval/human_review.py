"""Documents routed to human review: one metric, reported by every run type.

The share of documents that go to a person is the mailroom's main cost-of-operation number,
so pipeline runs, isolated sorter runs and decision-reviewer runs all report it under the same
keys (``routed_to_human_review``, ``routed_to_human_review_rate``,
``routed_to_human_review_by_class``) with a ``routed_to_human_review_basis`` that says what
"routed" means for that run type:

- ``pipeline``: the document finished in stage ``review`` (the graph's human-review node).
- ``sorter``: the sorter alone could not send it on unattended: an unknown or non-extractable
  class, no confidence, or a confidence below its class's ``high`` band. In the pipeline
  these documents get a retry and, for decision classes, the reviewer, before a person.
- ``reviewer``: the decision reviewer's verdict was a human verdict (route_to_human_review,
  unreadable, out_of_scope, multiple_documents), or with cutoffs, its gated confidence was
  below the cutoff of its class or its class has no cutoff.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

KEY = "routed_to_human_review"


def summarize(flags: Iterable[tuple[bool, str | None]], basis: str) -> dict[str, Any]:
    """``(routed, class)`` pairs -> count, rate and per-class ``{class: {routed, n, rate}}``."""
    total: Counter[str] = Counter()
    routed: Counter[str] = Counter()
    for flag, cls in flags:
        name = str(cls or "unknown")
        total[name] += 1
        routed[name] += int(bool(flag))
    n = sum(total.values())
    count = sum(routed.values())
    return {
        KEY: count,
        f"{KEY}_rate": round(count / n, 6) if n else None,
        f"{KEY}_by_class": {
            name: {"routed": routed[name], "n": total[name], "rate": round(routed[name] / total[name], 6)}
            for name in sorted(total)
        },
        f"{KEY}_basis": basis,
    }


def sorter_routes_to_human(pred: Mapping[str, Any] | None) -> bool:
    """True when a single sorter answer would not continue unattended (see module docstring)."""
    pred = pred or {}
    doc_type = pred.get("doc_type")
    confidence = pred.get("confidence")
    try:
        from pipeline.config import get_confidence_thresholds, is_extractable_doc_type
    except Exception:  # noqa: BLE001 - no mailroom config: fall back to the global defaults
        get_confidence_thresholds = None
        is_extractable_doc_type = None
    if not doc_type or doc_type == "unknown":
        return True
    if is_extractable_doc_type is not None and not is_extractable_doc_type(doc_type):
        return True
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return True
    high = 0.95
    if get_confidence_thresholds is not None:
        high = float(get_confidence_thresholds(doc_type).get("high", high))
    return float(confidence) < high


def reviewer_routes_to_human(pred: Mapping[str, Any] | None, cutoffs: Mapping[str, float] | None = None) -> bool:
    """True when the decision reviewer sends the document to a person.

    Without ``cutoffs`` only the verdict counts (a calibration run has no cutoffs yet). With
    them, a class without a cutoff, or a gated confidence below it, also routes to a person.
    """
    pred = pred or {}
    if pred.get("route_to_human"):
        return True
    if cutoffs is None:
        return False
    cutoff = cutoffs.get(str(pred.get("doc_type")))
    confidence = pred.get("confidence")
    if cutoff is None or not isinstance(confidence, (int, float)):
        return True
    return float(confidence) < float(cutoff)


def for_isolated(task: str, preds: Iterable[Mapping[str, Any] | None]) -> dict[str, Any] | None:
    """The metric for an isolated run of ``task`` (None for tasks that do not route documents)."""
    preds = list(preds)
    if task == "sorter_reviewer":
        return summarize(((reviewer_routes_to_human(p), (p or {}).get("doc_type")) for p in preds), "reviewer")
    if task == "sorter":
        return summarize(((sorter_routes_to_human(p), (p or {}).get("doc_type")) for p in preds), "sorter")
    return None


def for_pipeline(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """The metric for a pipeline run: documents that finished in stage ``review``."""
    return summarize(((str(r.get("stage")) == "review", r.get("doc_type")) for r in results), "pipeline")
