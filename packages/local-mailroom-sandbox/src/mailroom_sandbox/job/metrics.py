"""Serving metrics capture + local / Modal / API comparison (DMR-027).

Builds dojo-compatible serving records from run stores and compares offline
(local), remote-GPU (Modal), and API-key (OpenRouter) runs on latency,
throughput, tokens, cost efficiency, and total cost. Reuses
``llm_dojo_scoring.serving`` for price/cost math and pairwise comparisons.
"""

from __future__ import annotations

import statistics
from typing import Any, Mapping, Sequence

from llm_dojo_scoring.serving import compare_serving, estimate_cost

MODAL_PROFILES = ("modal-vllm",)
LOCAL_PROFILES = ("ollama", "vllm-local", "vllm-remote", "llamacpp", "lmstudio")
API_PROFILES = ("openrouter",)


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
) -> dict[str, Any]:
    """Aggregate per-item captures into one dojo-compatible serving record."""
    kind = bucket_kind({"serving_kind": "", "profile": profile, "provider": _provider_for(profile)})
    latencies = [float(i.get("latency_ms", 0)) for i in items if i.get("latency_ms") is not None]
    prompt_tokens = sum(int(i.get("prompt_tokens") or 0) for i in items)
    completion_tokens = sum(int(i.get("completion_tokens") or 0) for i in items)
    total_tokens = prompt_tokens + completion_tokens
    ttfts = [float(i.get("ttft_ms", 0)) for i in items if i.get("ttft_ms") is not None]
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
    try:
        cost = estimate_cost(prompt_tokens, completion_tokens, model)
        if cost is not None:
            rec["estimated_cost_usd"] = float(cost)
    except Exception:
        pass
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
    dur = sum(lat) if lat else None
    return {
        "n": n,
        "mean_ttft_s": _mean(ttft),
        "mean_e2e_s": _mean(lat),
        "total_tokens": prom + comp,
        "tokens_per_s": round((prom + comp) / dur, 2) if dur else None,
        "estimated_cost_usd": round(sum(cost), 6) if cost else None,
    }


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
