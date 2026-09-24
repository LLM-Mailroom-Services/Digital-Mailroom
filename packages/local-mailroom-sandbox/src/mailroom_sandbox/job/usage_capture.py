"""Per-item token / TTFT capture helpers for the job runner.

Pulls OpenAI-compatible ``usage`` from the vendored pipeline's run accumulator
(``pipeline.limits.usage_summary``) after a live graph invoke, or from a raw
chat-completions response. TTFT is never inferred from e2e — only persisted
when an explicit first-token timestamp is supplied.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

_log = logging.getLogger("mailroom_sandbox.job.usage_capture")


def usage_from_pipeline() -> dict[str, int]:
    """Read the current thread's pipeline usage accumulator (post-invoke)."""
    try:
        from pipeline.limits import usage_summary
    except Exception as exc:  # noqa: BLE001 — soft: mock / no vendor
        _log.debug("pipeline.limits unavailable for usage capture: %s", exc)
        return {}
    try:
        summary = usage_summary() or {}
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "usage_summary() raised — item will lack prompt/completion tokens "
            "(estimated_cost_usd will be absent): %s",
            exc,
        )
        return {}
    prompt = int(summary.get("prompt_tokens") or 0)
    completion = int(summary.get("completion_tokens") or 0)
    calls = int(summary.get("calls") or 0)
    out: dict[str, int] = {}
    if prompt:
        out["prompt_tokens"] = prompt
    if completion:
        out["completion_tokens"] = completion
    if calls:
        out["llm_calls"] = calls
    return out


def usage_from_openai_response(resp: Any) -> dict[str, int]:
    """Extract prompt/completion tokens from an OpenAI SDK response object."""
    usage = getattr(resp, "usage", None)
    if usage is None:
        return {}
    if isinstance(usage, Mapping):
        prompt = usage.get("prompt_tokens") or usage.get("input_tokens")
        completion = usage.get("completion_tokens") or usage.get("output_tokens")
    else:
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
    out: dict[str, int] = {}
    try:
        if prompt is not None:
            out["prompt_tokens"] = int(prompt)
        if completion is not None:
            out["completion_tokens"] = int(completion)
    except (TypeError, ValueError):
        return {}
    return out


def merge_item_metrics(
    *,
    latency_ms: float | None = None,
    usage: Mapping[str, Any] | None = None,
    ttft_ms: float | None = None,
) -> dict[str, Any]:
    """Build the per-item metrics block persisted to ``items.jsonl``."""
    out: dict[str, Any] = {}
    if latency_ms is not None:
        out["latency_ms"] = float(latency_ms)
    if ttft_ms is not None:
        out["ttft_ms"] = float(ttft_ms)
    if usage:
        for key in ("prompt_tokens", "completion_tokens", "llm_calls"):
            val = usage.get(key)
            if val is not None:
                try:
                    out[key] = int(val)
                except (TypeError, ValueError):
                    continue
    return out
