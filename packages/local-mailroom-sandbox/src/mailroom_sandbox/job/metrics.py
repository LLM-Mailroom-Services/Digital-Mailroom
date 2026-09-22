"""Serving metrics capture + local / Modal / API comparison (DMR-027).

Builds dojo-compatible serving records from run stores and compares offline
(local), remote-GPU (Modal), and API-key (OpenRouter) runs on latency,
throughput, tokens, cost efficiency, and total cost. Reuses
``llm_dojo_scoring.serving`` for price/cost math and pairwise comparisons.
"""

from __future__ import annotations

import logging
import statistics
from typing import Any, Mapping, Sequence

from llm_dojo_scoring.serving import compare_serving, estimate_cost

_log = logging.getLogger("mailroom_sandbox.job.metrics")

_COST_WARNED = False

MODAL_PROFILES = ("modal-vllm",)
LOCAL_PROFILES = ("ollama", "vllm-local", "vllm-remote", "llamacpp", "lmstudio")
API_PROFILES = ("openrouter",)

# Champion-model prices for locally/Modal-served weights: the OpenRouter list
# price of the matrix champion each HF id maps to, so local-vs-API cost
# comparisons stay like-for-like. The dojo table only knows the OpenRouter
# slugs; without this the flagship default model always costed None (DMR-049).
SANDBOX_MODEL_PRICES: dict[str, tuple[float, float]] = {
    "Qwen/Qwen3-8B": (0.03, 0.13),  # qwen/qwen3.7-flash champion
    "Qwen/Qwen3-8B-AWQ": (0.03, 0.13),
    "Qwen/Qwen3-14B": (0.03, 0.13),
    "Qwen/Qwen3-14B-AWQ": (0.03, 0.13),
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B": (0.05, 0.25),  # deepseek-v4-flash
    "deepseek-ai/DeepSeek-R1-Distill-Llama-8B": (0.05, 0.25),
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B": (0.435, 0.87),  # deepseek-v4-pro
    # Real OpenRouter qwen3-8b price card (USD per 1M in / 1M out). The API-leg
    # record carries the OpenRouter slug, which matches neither the HF-id keys
    # above nor the startswith fallback otherwise — without this row the API
    # leg's estimated_cost_usd would stay None.
    "qwen/qwen3-8b": (0.05, 0.40),
}


def _estimate_cost(
    prompt_tokens: int, completion_tokens: int, model: str
) -> float | None:
    """Dojo cost first; fall back to the sandbox champion-price table."""
    try:
        cost = estimate_cost(prompt_tokens, completion_tokens, model)
        if cost is not None:
            return float(cost)
    except Exception as exc:
        global _COST_WARNED
        if not _COST_WARNED:
            _COST_WARNED = True
            _log.warning(
                "dojo estimate_cost raised for model %r — fell back to the "
                "sandbox champion-price table; a broken dojo cost fn would "
                "otherwise look like 'no price known'",
                model,
                exc_info=exc,
            )
    if not model:
        return None
    prices = SANDBOX_MODEL_PRICES.get(model)
    if prices is None:
        for known, price in SANDBOX_MODEL_PRICES.items():
            if model.startswith(known):
                prices = price
                break
    if prices is None or prompt_tokens + completion_tokens <= 0:
        return None
    per_million_in, per_million_out = prices
    return round(
        prompt_tokens * per_million_in / 1_000_000
        + completion_tokens * per_million_out / 1_000_000,
        6,
    )


def _as_float(value: Any) -> float | None:
    """Parse a numeric field; booleans/None are not numbers."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def bucket_kind(record: Mapping[str, Any]) -> str:
    kind = str(record.get("serving_kind") or "").lower()
    if kind in {"local", "api", "modal"}:
        return kind
    profile = str(record.get("profile") or "")
    if profile in MODAL_PROFILES:
        return "modal"
    if profile in API_PROFILES:
        return "api"
    if profile in LOCAL_PROFILES:
        return "local"
    provider = str(record.get("provider") or "").lower()
    if provider in {"openrouter"}:
        return "api"
    if provider in {"vllm", "ollama", "llamacpp", "lmstudio", "generic"}:
        return "local"
    return "unknown"


def record_from_run(
    *,
    run_id: str,
    spec_hash: str,
    task: str,
    profile: str,
    model: str,
    prompt_version: str,
    dataset_fingerprint: str,
    items: Sequence[Mapping[str, Any]],
    scores: Mapping[str, Any] | None = None,
    gpu_hourly_usd: float | None = None,
    warm_span_seconds: float | None = None,
) -> dict[str, Any]:
    """Aggregate per-item captures into one dojo-compatible serving record.

    ``gpu_hourly_usd`` / ``warm_span_seconds`` are the Modal/GPU billing
    inputs (hourly rate × warm span). For a Modal bucket they price the run
    by wall clock; when either is absent the GPU cost stays unknown (None)
    rather than being fabricated from a token price.
    """
    kind = bucket_kind({"serving_kind": "", "profile": profile, "provider": _provider_for(profile)})
    # hub#56: TTFT aggregation must treat failures like the latency
    # aggregation — failed/retried items carry inflated TTFT from backoff
    # sleeps, so average TTFT over the SAME ok_items as e2e latency (the two
    # must never disagree about which items are representative). Token sums
    # stay over ALL items (cost is real even for failures).
    ok_items = [i for i in items if i.get("ok", True) is not False]
    latencies = [float(i.get("latency_ms", 0)) for i in ok_items if i.get("latency_ms") is not None]
    prompt_tokens = sum(int(i.get("prompt_tokens") or 0) for i in items)
    completion_tokens = sum(int(i.get("completion_tokens") or 0) for i in items)
    total_tokens = prompt_tokens + completion_tokens
    ttfts = [float(i.get("ttft_ms", 0)) for i in ok_items if i.get("ttft_ms") is not None]
    rec: dict[str, Any] = {
        "serving_kind": kind,
        "provider": _provider_for(profile),
        "profile": profile,
        "model": model,
        "prompt_version": prompt_version or "mailroom-default",
        "task": task,
        "dataset_fingerprint": dataset_fingerprint,
        "n": len(items),
        "run_id": run_id,
        "spec_hash": spec_hash,
    }
    if gpu_hourly_usd is not None:
        rec["gpu_hourly_usd"] = float(gpu_hourly_usd)
    if warm_span_seconds is not None:
        rec["warm_span_seconds"] = float(warm_span_seconds)
    if latencies:
        rec["e2e_latency_seconds"] = statistics.mean(latencies) / 1000.0
    if ttfts:
        rec["ttft_seconds"] = statistics.mean(ttfts) / 1000.0
    if prompt_tokens:
        rec["prompt_tokens"] = prompt_tokens
    if completion_tokens:
        rec["completion_tokens"] = completion_tokens
    if total_tokens:
        rec["total_tokens"] = total_tokens
    if scores:
        rec["scores"] = dict(scores)
    if kind == "modal":
        # Modal/GPU billing is wall-clock (hourly rate × warm span), NOT an
        # OpenRouter champion token price. Unknown stays None.
        hourly = _as_float(rec.get("gpu_hourly_usd"))
        warm = _as_float(rec.get("warm_span_seconds"))
        if hourly is not None and warm is not None:
            rec["gpu_cost_usd"] = round(hourly * warm / 3600.0, 6)
        else:
            rec["gpu_cost_usd"] = None
    else:
        try:
            cost = _estimate_cost(prompt_tokens, completion_tokens, model)
            if cost is not None:
                rec["estimated_cost_usd"] = float(cost)
        except Exception as exc:
            _log.warning(
                "cost estimation for run %r failed outright (inner function "
                "covered) — estimated_cost_usd will be ABSENT from the record: %s",
                run_id,
                exc,
            )
    return {k: v for k, v in rec.items() if v is not None}


def _provider_for(profile: str) -> str:
    if profile in MODAL_PROFILES:
        return "vllm"
    if profile in API_PROFILES:
        return "openrouter"
    if profile in {"ollama"}:
        return "ollama"
    if profile in {"llamacpp", "lmstudio"}:
        return "generic"
    return "vllm"


def bucket_records(records: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {"local": [], "modal": [], "api": [], "unknown": []}
    for rec in records:
        buckets.setdefault(bucket_kind(rec), []).append(dict(rec))
    return buckets


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 4) if values else None


def aggregate_bucket(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Mean latency/throughput/cost + totals for one bucket."""
    n = len(records)
    lat = [float(r["e2e_latency_seconds"]) for r in records if r.get("e2e_latency_seconds")]
    ttft = [float(r["ttft_seconds"]) for r in records if r.get("ttft_seconds")]
    prom = sum(int(r.get("prompt_tokens") or 0) for r in records)
    comp = sum(int(r.get("completion_tokens") or 0) for r in records)
    cost = [float(r["estimated_cost_usd"]) for r in records if r.get("estimated_cost_usd") is not None]
    gpu_cost = [float(r["gpu_cost_usd"]) for r in records if r.get("gpu_cost_usd") is not None]
    dur = sum(lat) if lat else None
    agg = {
        "n": n,
        "mean_ttft_s": _mean(ttft),
        "mean_e2e_s": _mean(lat),
        "total_tokens": prom + comp,
        "tokens_per_s": round((prom + comp) / dur, 2) if dur else None,
        "estimated_cost_usd": round(sum(cost), 6) if cost else None,
    }
    if gpu_cost:
        agg["gpu_cost_usd"] = round(sum(gpu_cost), 6)
    return agg


def _pct(base: float | None, other: float | None) -> float | None:
    if base in (None, 0) or other is None:
        return None
    return round((other - base) / base * 100.0, 1)


def compare(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Three-way local / Modal / API comparison with pairwise dojo deltas."""
    buckets = bucket_records(records)
    summary = {kind: aggregate_bucket(rows) for kind, rows in buckets.items() if rows}
    api = summary.get("api")

    def delta_vs_api(metric: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        base = api.get(metric) if api else None
        for kind in ("local", "modal"):
            agg = summary.get(kind)
            if agg:
                out[kind] = _pct(base, agg.get(metric))
        return out

    deltas = {
        "mean_e2e_s": delta_vs_api("mean_e2e_s"),
        "mean_ttft_s": delta_vs_api("mean_ttft_s"),
        "tokens_per_s": delta_vs_api("tokens_per_s"),
        "estimated_cost_usd": delta_vs_api("estimated_cost_usd"),
    }

    pairs: dict[str, Any] = {}
    if buckets.get("local") and buckets.get("api"):
        pairs["local_vs_api"] = compare_serving(buckets["local"], buckets["api"])
    if buckets.get("modal") and buckets.get("api"):
        pairs["modal_vs_api"] = compare_serving(buckets["modal"], buckets["api"])

    cost_total = {
        kind: (agg.get("estimated_cost_usd") if agg else None)
        for kind, agg in summary.items()
    }
    markdown = _markdown(summary, deltas, pairs)
    return {
        "buckets": summary,
        "deltas_vs_api": deltas,
        "total_cost_usd": cost_total,
        "pairwise": pairs,
        "markdown": markdown,
    }


def _markdown(summary: dict[str, Any], deltas: dict[str, Any], pairs: dict[str, Any]) -> str:
    lines = ["## Serving metrics (local vs Modal vs API)", ""]
    header = "| bucket | n | mean e2e (s) | mean ttft (s) | tok/s | total tokens | est. cost ($) |"
    lines += [header, "| --- | --- | --- | --- | --- | --- | --- |"]
    for kind in ("local", "modal", "api"):
        agg = summary.get(kind)
        if not agg:
            continue
        lines.append(
            f"| {kind} | {agg['n']} | {agg['mean_e2e_s'] or '-'} | "
            f"{agg['mean_ttft_s'] or '-'} | {agg['tokens_per_s'] or '-'} | "
            f"{agg['total_tokens'] or '-'} | {agg['estimated_cost_usd'] or '-'} |"
        )
    lines.append("")
    lines.append("### Delta vs API (%)")
    lines.append("| metric | local | modal |")
    lines.append("| --- | --- | --- |")
    for metric, d in deltas.items():
        lines.append(f"| {metric} | {d.get('local') or '-'} | {d.get('modal') or '-'} |")
    for name, pair in pairs.items():
        md = pair.get("markdown") if isinstance(pair, dict) else None
        if md:
            lines += ["", str(md)]
    return "\n".join(lines)
