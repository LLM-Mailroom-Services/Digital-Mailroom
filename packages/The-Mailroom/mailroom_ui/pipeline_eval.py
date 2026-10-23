"""Offline eval adapters; Dojo owns quality scoring under the optional eval extra.

Display/server imports stay light. API release prerequisite is documented in
 docs/core-engine-adoption.md; no fallback to a competing local scorer.
"""
from __future__ import annotations


def _engine():
    """Load the optional released engine only when an eval function is used."""
    try:
        from llm_dojo_scoring import pipeline_scoring
    except ImportError as exc:
        raise ImportError(
            "Offline pipeline evaluation requires The-Mailroom[eval] and the "
            "reviewed Dojo core-engine API release; see docs/core-engine-adoption.md"
        ) from exc
    return pipeline_scoring


def __getattr__(name):
    """Lazily retain public compatibility constants without loading Dojo for display."""
    if name == "ALIGN":
        return _engine().PIPELINE_ALIGNMENT
    if name == "FAILURE_MODES":
        return _engine().PIPELINE_FAILURE_MODES
    raise AttributeError(name)


def exact(expected: str | None, predicted: str | None) -> bool:
    """Delegate literal equality; trace/report adapters retain their GT guards."""
    return _engine().pipeline_labels_equal(expected, predicted)


def aligned(expected: str, predicted: str | None) -> bool:
    """Literal class match; MAUD remains distinct from CUAD."""
    return _engine().pipeline_classes_aligned(expected, predicted)


def predicted_subclass_token(row: dict) -> str | None:
    """Lift producer fields: predicted_subclass, doc_subclass, then CUAD subtype."""
    token = row.get("predicted_subclass") or row.get("doc_subclass") or row.get("contract_subtype")
    if token is None:
        return None
    text = str(token).strip()
    return text or None


def subclass_ok(expected: str | None, predicted: str | None) -> bool:
    """Compatibility name for the visualizer's exact subclass policy."""
    return _engine().pipeline_subclass_match(expected, predicted)


def classify_failure(row: dict) -> str:
    """Compatibility name for the pipeline lifecycle policy, not sorter failures."""
    return _engine().classify_pipeline_failure(row)


def score_rows(rows: list[dict]) -> dict:
    """Delegate quality; retain display aggregations and row-shape lifting."""
    lifted = [dict(r, predicted_subclass=predicted_subclass_token(r)) for r in rows]
    summary = _engine().score_pipeline_rows(lifted)
    costs = [r.get("cost_usd") for r in rows if isinstance(r.get("cost_usd"), (int, float))]
    tokens = [r.get("total_tokens") for r in rows if isinstance(r.get("total_tokens"), (int, float))]
    latencies = [r.get("seconds") for r in rows if isinstance(r.get("seconds"), (int, float))]
    summary.update({
        "cost_usd_sum": round(sum(costs), 6) if costs else 0.0,
        "tokens_sum": int(sum(tokens)) if tokens else 0,
        "latency_s_mean": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "intake_changed": sum(1 for r in rows if r.get("intake_changed")),
        "intake_messy": sum(1 for r in rows if r.get("intake_messy")),
    })
    return summary
