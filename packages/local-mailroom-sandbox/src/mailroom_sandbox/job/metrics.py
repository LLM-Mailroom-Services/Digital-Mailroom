"""Serving metrics capture + local / Modal / API comparison (DMR-027).

Builds dojo-compatible serving records from run stores and compares offline
(local), remote-GPU (Modal), and API-key (OpenRouter) runs on latency,
throughput, tokens, cost efficiency, and total cost. Reuses
``llm_dojo_scoring.serving`` for price/cost math and pairwise comparisons.

Cost honesty
------------
* **Token-proxy USD** (``estimated_cost_usd``) uses OpenRouter-like
  per-1M prices (dojo table + sandbox champion fallback). Configurable via
  ``SANDBOX_TOKEN_PRICE_IN_PER_M`` / ``SANDBOX_TOKEN_PRICE_OUT_PER_M``.
* **Modal GPU USD** (``estimated_gpu_cost_usd``) is wall/busy GPU-seconds ×
  ``$/hr`` for the locked GPU class (default L4 ≈ $0.80/hr). Configurable via
  ``MODAL_GPU_USD_PER_HOUR`` or ``MODAL_GPU_USD_PER_SEC``. Never fabricate $0
  when tokens/GPU seconds are missing — omit the field and warn loudly.
* **TTFT** is only present when items record ``ttft_ms`` (never inferred).
"""

from __future__ import annotations

import logging
import os
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from llm_dojo_scoring.serving import compare_serving, estimate_cost

from mailroom_sandbox.job.specialist_posture import as_metrics_sec_tables

_log = logging.getLogger("mailroom_sandbox.job.metrics")

SPECIALIST_SEC_PER_DOC, SPECIALIST_TOKENS_PER_DOC = as_metrics_sec_tables()

_COST_WARNED = False
_GPU_WARNED = False

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
}

# Modal GPU $/hr (modal.com/pricing, verified 2026-09-09 — see deploy/README.md).
# Override a single rate with MODAL_GPU_USD_PER_HOUR (applies to whatever GPU
# class the run locked) or MODAL_GPU_USD_PER_SEC for a precise per-second rate.
DEFAULT_GPU_USD_PER_HOUR: dict[str, float] = {
    "L4": 0.80,
    "A10": 1.10,
    "A10G": 1.10,
    "A100": 2.10,
    "A100-40GB": 2.10,
    "A100-80GB": 2.50,
    "L40S": 1.95,
    "H100": 3.95,
    "H200": 4.54,
    "B200": 6.25,
    "T4": 0.59,
}

# ModernBERT ONNX-CPU inference is essentially free vs LLM tokens; document
# the plan's ~$1e-6/doc floor so comparisons stay honest (mailroom-ml plan §1).
MODERNBERT_DEFAULT_COST_PER_DOC_USD = 1e-6


def _env_float(name: str) -> float | None:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        _log.warning("ignoring non-float env %s=%r", name, raw)
        return None


def gpu_usd_per_hour(gpu: str | None = None) -> float:
    """Resolve Modal GPU $/hr: env override → table → L4 default ($0.80)."""
    per_sec = _env_float("MODAL_GPU_USD_PER_SEC")
    if per_sec is not None:
        return per_sec * 3600.0
    override = _env_float("MODAL_GPU_USD_PER_HOUR")
    if override is not None:
        return override
    key = (gpu or os.environ.get("MODAL_VLLM_GPU") or "L4").split(":")[0]
    if key in DEFAULT_GPU_USD_PER_HOUR:
        return DEFAULT_GPU_USD_PER_HOUR[key]
    _log.warning(
        "unknown GPU class %r — falling back to L4 rate $%.2f/hr; set "
        "MODAL_GPU_USD_PER_HOUR to override",
        key,
        DEFAULT_GPU_USD_PER_HOUR["L4"],
    )
    return DEFAULT_GPU_USD_PER_HOUR["L4"]


def estimate_gpu_cost_usd(
    gpu_seconds: float,
    *,
    gpu: str | None = None,
) -> float | None:
    """USD for ``gpu_seconds`` of billed/busy time at the configured rate."""
    if gpu_seconds is None or gpu_seconds <= 0:
        return None
    rate = gpu_usd_per_hour(gpu)
    return round(gpu_seconds / 3600.0 * rate, 6)


def _token_price_override() -> tuple[float, float] | None:
    """Optional global token price override (per-1M in/out)."""
    pin = _env_float("SANDBOX_TOKEN_PRICE_IN_PER_M")
    pout = _env_float("SANDBOX_TOKEN_PRICE_OUT_PER_M")
    if pin is None and pout is None:
        return None
    return (pin if pin is not None else 0.0, pout if pout is not None else 0.0)


def _estimate_cost(
    prompt_tokens: int, completion_tokens: int, model: str
) -> float | None:
    """Dojo cost first; fall back to the sandbox champion-price table."""
    override = _token_price_override()
    if override is not None:
        if prompt_tokens + completion_tokens <= 0:
            return None
        per_million_in, per_million_out = override
        return round(
            prompt_tokens * per_million_in / 1_000_000
            + completion_tokens * per_million_out / 1_000_000,
            6,
        )
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


def _gpu_seconds_from_items(
    items: Sequence[Mapping[str, Any]],
    *,
    billed_window_seconds: float | None = None,
) -> float | None:
    """GPU-seconds attribution for a run.

    Prefer an explicit billed window (Modal warm interval). Else sum ok-item
    ``latency_ms`` as a busy-time lower bound (overcounts under concurrency —
    still better than silent $0).
    """
    if billed_window_seconds is not None and billed_window_seconds > 0:
        return float(billed_window_seconds)
    env_billed = _env_float("MODAL_BILLED_GPU_SECONDS")
    if env_billed is not None and env_billed > 0:
        return env_billed
    ok_items = [i for i in items if i.get("ok", True) is not False]
    latencies = [
        float(i["latency_ms"])
        for i in ok_items
        if i.get("latency_ms") is not None
    ]
    if not latencies:
        return None
    return sum(latencies) / 1000.0


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
    gpu: str | None = None,
    billed_window_seconds: float | None = None,
    mock: bool = False,
) -> dict[str, Any]:
    """Aggregate per-item captures into one dojo-compatible serving record."""
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
    n = len(items)
    n_ok = len(ok_items)
    rec: dict[str, Any] = {
        "serving_kind": kind,
        "provider": _provider_for(profile),
        "profile": profile,
        "model": model,
        "prompt_version": prompt_version or "mailroom-default",
        "task": task,
        "dataset_fingerprint": dataset_fingerprint,
        "n": n,
        "run_id": run_id,
        "spec_hash": spec_hash,
    }
    if gpu:
        rec["gpu"] = gpu
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

    # Token-proxy cost (OpenRouter-like). Absent when tokens or prices missing —
    # never write estimated_cost_usd=0 as a stand-in for "unknown".
    try:
        cost = _estimate_cost(prompt_tokens, completion_tokens, model)
        if cost is not None:
            rec["estimated_cost_usd"] = float(cost)
            if n_ok > 0:
                rec["cost_per_document"] = round(float(cost) / n_ok, 8)
        elif not mock and n_ok > 0 and total_tokens <= 0:
            _log.warning(
                "run %r (%s/%s): %d ok items but 0 tokens recorded — "
                "estimated_cost_usd ABSENT (not $0); ensure the OpenAI-"
                "compatible server returns usage.prompt_tokens",
                run_id,
                kind,
                profile,
                n_ok,
            )
        elif not mock and total_tokens > 0 and cost is None:
            _log.warning(
                "run %r: tokens recorded but no price for model %r — "
                "estimated_cost_usd ABSENT; set SANDBOX_TOKEN_PRICE_IN_PER_M / "
                "OUT_PER_M or extend SANDBOX_MODEL_PRICES",
                run_id,
                model,
            )
    except Exception as exc:
        _log.warning(
            "cost estimation for run %r failed outright (inner function "
            "covered) — estimated_cost_usd will be ABSENT from the record: %s",
            run_id,
            exc,
        )

    # Modal GPU-hour cost (orthogonal to token proxy). Local Ollama and API
    # buckets skip this; Modal / vLLM-remote may attribute busy GPU seconds.
    if kind == "modal" or (kind == "local" and profile in {"vllm-local", "vllm-remote"}):
        gpu_seconds = _gpu_seconds_from_items(
            items, billed_window_seconds=billed_window_seconds
        )
        if gpu_seconds is not None:
            rec["gpu_seconds"] = round(gpu_seconds, 3)
            gpu_cost = estimate_gpu_cost_usd(gpu_seconds, gpu=gpu)
            if gpu_cost is not None:
                rec["estimated_gpu_cost_usd"] = gpu_cost
                if n_ok > 0:
                    rec["gpu_cost_per_document"] = round(gpu_cost / n_ok, 8)
            else:
                global _GPU_WARNED
                if not _GPU_WARNED:
                    _GPU_WARNED = True
                    _log.warning(
                        "gpu_seconds=%s but GPU rate resolved to no cost — "
                        "estimated_gpu_cost_usd ABSENT",
                        gpu_seconds,
                    )
        elif kind == "modal" and not mock and n_ok > 0:
            _log.warning(
                "modal run %r has no latency_ms / billed window — "
                "estimated_gpu_cost_usd ABSENT (not $0); set "
                "MODAL_BILLED_GPU_SECONDS or ensure items record latency_ms",
                run_id,
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
    gpu_cost = [
        float(r["estimated_gpu_cost_usd"])
        for r in records
        if r.get("estimated_gpu_cost_usd") is not None
    ]
    cpd = [float(r["cost_per_document"]) for r in records if r.get("cost_per_document") is not None]
    gcpd = [
        float(r["gpu_cost_per_document"])
        for r in records
        if r.get("gpu_cost_per_document") is not None
    ]
    dur = sum(lat) if lat else None
    return {
        "n": n,
        "mean_ttft_s": _mean(ttft),
        "mean_e2e_s": _mean(lat),
        "total_tokens": prom + comp,
        "tokens_per_s": round((prom + comp) / dur, 2) if dur else None,
        "estimated_cost_usd": round(sum(cost), 6) if cost else None,
        "estimated_gpu_cost_usd": round(sum(gpu_cost), 6) if gpu_cost else None,
        "mean_cost_per_document": _mean(cpd),
        "mean_gpu_cost_per_document": _mean(gcpd),
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
        "estimated_gpu_cost_usd": delta_vs_api("estimated_gpu_cost_usd"),
        "mean_cost_per_document": delta_vs_api("mean_cost_per_document"),
    }

    pairs: dict[str, Any] = {}
    if buckets.get("local") and buckets.get("api"):
        pairs["local_vs_api"] = compare_serving(buckets["local"], buckets["api"])
    if buckets.get("modal") and buckets.get("api"):
        pairs["modal_vs_api"] = compare_serving(buckets["modal"], buckets["api"])
    if buckets.get("local") and buckets.get("modal"):
        pairs["local_vs_modal"] = compare_serving(buckets["local"], buckets["modal"])

    cost_total = {
        kind: (agg.get("estimated_cost_usd") if agg else None)
        for kind, agg in summary.items()
    }
    gpu_cost_total = {
        kind: (agg.get("estimated_gpu_cost_usd") if agg else None)
        for kind, agg in summary.items()
    }
    markdown = _markdown(summary, deltas, pairs)
    return {
        "buckets": summary,
        "deltas_vs_api": deltas,
        "total_cost_usd": cost_total,
        "total_gpu_cost_usd": gpu_cost_total,
        "pairwise": pairs,
        "markdown": markdown,
    }


def _score_quality(rec: Mapping[str, Any]) -> dict[str, float | None]:
    scores = rec.get("scores") if isinstance(rec.get("scores"), Mapping) else {}
    out: dict[str, float | None] = {}
    for key in ("accuracy", "exact_match", "f1_macro", "doc_type_accuracy", "subclass_accuracy"):
        val = scores.get(key) if scores else rec.get(key)
        if val is not None:
            try:
                out[key] = float(val)
            except (TypeError, ValueError):
                continue
    return out


def compare_sorter_vs_modernbert(
    sorter: Mapping[str, Any],
    modernbert: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare LLM sorter vs trained ModernBERT on accuracy + cost/latency.

    Both sides should carry comparable fields (``n``, ``e2e_latency_seconds``,
    quality scores, and either ``cost_per_document`` / ``estimated_cost_usd``
    or ModernBERT's CPU inference floor). Does not load the mailroom-ml
    package — callers supply already-scored records (job run / eval fixture).
    """
    s_q = _score_quality(sorter)
    m_q = _score_quality(modernbert)
    s_n = int(sorter.get("n") or 0)
    m_n = int(modernbert.get("n") or 0)
    s_lat = _as_float(sorter.get("e2e_latency_seconds"))
    m_lat = _as_float(modernbert.get("e2e_latency_seconds"))
    s_cpd = _as_float(sorter.get("cost_per_document"))
    if s_cpd is None and sorter.get("estimated_cost_usd") is not None and s_n:
        s_cpd = float(sorter["estimated_cost_usd"]) / s_n
    # Prefer GPU cost-per-doc for Modal sorter when token proxy is absent.
    if s_cpd is None:
        s_cpd = _as_float(sorter.get("gpu_cost_per_document"))
    m_cpd = _as_float(modernbert.get("cost_per_document"))
    if m_cpd is None and modernbert.get("estimated_cost_usd") is not None and m_n:
        m_cpd = float(modernbert["estimated_cost_usd"]) / m_n
    if m_cpd is None:
        m_cpd = MODERNBERT_DEFAULT_COST_PER_DOC_USD
        modernbert_cost_note = (
            f"modernbert cost_per_document defaulted to "
            f"{MODERNBERT_DEFAULT_COST_PER_DOC_USD} (ONNX-CPU floor from "
            f"mailroom-ml plan); override on the record to use a measured rate"
        )
    else:
        modernbert_cost_note = None

    def _delta(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return round(a - b, 6)

    def _pct_delta(base: float | None, other: float | None) -> float | None:
        return _pct(base, other)

    accuracy_keys = sorted(set(s_q) | set(m_q))
    quality = {
        key: {
            "sorter": s_q.get(key),
            "modernbert": m_q.get(key),
            "delta_sorter_minus_modernbert": _delta(s_q.get(key), m_q.get(key)),
        }
        for key in accuracy_keys
    }
    latency = {
        "sorter_e2e_s": s_lat,
        "modernbert_e2e_s": m_lat,
        "delta_sorter_minus_modernbert": _delta(s_lat, m_lat),
        "pct_sorter_vs_modernbert": _pct_delta(m_lat, s_lat),
    }
    cost = {
        "sorter_cost_per_document": s_cpd,
        "modernbert_cost_per_document": m_cpd,
        "delta_sorter_minus_modernbert": _delta(s_cpd, m_cpd),
        "sorter_estimated_cost_usd": _as_float(sorter.get("estimated_cost_usd")),
        "sorter_estimated_gpu_cost_usd": _as_float(sorter.get("estimated_gpu_cost_usd")),
        "modernbert_estimated_cost_usd": _as_float(modernbert.get("estimated_cost_usd")),
    }
    honest_gaps: list[str] = []
    if s_cpd is None:
        honest_gaps.append(
            "sorter cost_per_document unknown (no tokens/GPU attribution on record)"
        )
    if not s_q and not m_q:
        honest_gaps.append("no quality scores on either side")
    if modernbert_cost_note:
        honest_gaps.append(modernbert_cost_note)

    markdown = _sorter_vs_modernbert_md(
        quality, latency, cost, sorter=sorter, modernbert=modernbert, gaps=honest_gaps
    )
    return {
        "agent": "sorter_vs_modernbert",
        "sorter": {
            "model": sorter.get("model"),
            "serving_kind": sorter.get("serving_kind") or bucket_kind(sorter),
            "profile": sorter.get("profile"),
            "n": s_n,
            "classifier": "llm_sorter",
        },
        "modernbert": {
            "model": modernbert.get("model")
            or "Lucius-Morningstar/mailroom-modernbert-classifier",
            "serving_kind": modernbert.get("serving_kind") or "modernbert",
            "n": m_n,
            "classifier": "modernbert",
        },
        "quality": quality,
        "latency": latency,
        "cost": cost,
        "honest_gaps": honest_gaps,
        "markdown": markdown,
    }


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sorter_vs_modernbert_md(
    quality: Mapping[str, Any],
    latency: Mapping[str, Any],
    cost: Mapping[str, Any],
    *,
    sorter: Mapping[str, Any],
    modernbert: Mapping[str, Any],
    gaps: Sequence[str],
) -> str:
    lines = [
        "## Sorter vs ModernBERT (classification)",
        "",
        f"| side | model | n | e2e (s) | $/doc |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| sorter | {sorter.get('model') or '-'} | {sorter.get('n') or '-'} | "
            f"{latency.get('sorter_e2e_s') or '-'} | "
            f"{cost.get('sorter_cost_per_document') or '-'} |"
        ),
        (
            f"| modernbert | {modernbert.get('model') or 'mailroom-modernbert-classifier'} | "
            f"{modernbert.get('n') or '-'} | {latency.get('modernbert_e2e_s') or '-'} | "
            f"{cost.get('modernbert_cost_per_document') or '-'} |"
        ),
        "",
        "### Quality",
        "| metric | sorter | modernbert | Δ (sorter − modernbert) |",
        "| --- | --- | --- | --- |",
    ]
    for key, row in quality.items():
        lines.append(
            f"| {key} | {row.get('sorter') if row.get('sorter') is not None else '-'} | "
            f"{row.get('modernbert') if row.get('modernbert') is not None else '-'} | "
            f"{row.get('delta_sorter_minus_modernbert') if row.get('delta_sorter_minus_modernbert') is not None else '-'} |"
        )
    if gaps:
        lines += ["", "### Honest gaps"]
        for g in gaps:
            lines.append(f"- {g}")
    return "\n".join(lines)


def _markdown(summary: dict[str, Any], deltas: dict[str, Any], pairs: dict[str, Any]) -> str:
    lines = ["## Serving metrics (local vs Modal vs API)", ""]
    header = (
        "| bucket | n | mean e2e (s) | mean ttft (s) | tok/s | total tokens | "
        "est. token $ | est. GPU $ | $/doc (token) |"
    )
    lines += [header, "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for kind in ("local", "modal", "api"):
        agg = summary.get(kind)
        if not agg:
            continue
        lines.append(
            f"| {kind} | {agg['n']} | {agg['mean_e2e_s'] or '-'} | "
            f"{agg['mean_ttft_s'] or '-'} | {agg['tokens_per_s'] or '-'} | "
            f"{agg['total_tokens'] or '-'} | {agg['estimated_cost_usd'] or '-'} | "
            f"{agg.get('estimated_gpu_cost_usd') or '-'} | "
            f"{agg.get('mean_cost_per_document') or '-'} |"
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
            lines += ["", f"### Pairwise: {name}", str(md)]
    return "\n".join(lines)


# ── Cost extrapolation (benchmark → full corpus / industry scale) ───────────


def per_document_rates(record: Mapping[str, Any]) -> dict[str, Any]:
    """Derive $/doc, latency/doc, tokens/doc from a serving record.

    Never invents $0 — missing inputs yield ``None`` rates and an honest gap.
    """
    n = int(record.get("n") or 0)
    gaps: list[str] = []
    token_cpd = _as_float(record.get("cost_per_document"))
    if token_cpd is None and record.get("estimated_cost_usd") is not None and n > 0:
        token_cpd = float(record["estimated_cost_usd"]) / n
    gpu_cpd = _as_float(record.get("gpu_cost_per_document"))
    if gpu_cpd is None and record.get("estimated_gpu_cost_usd") is not None and n > 0:
        gpu_cpd = float(record["estimated_gpu_cost_usd"]) / n

    latency = _as_float(record.get("e2e_latency_seconds"))
    prompt_tok = int(record.get("prompt_tokens") or 0)
    completion_tok = int(record.get("completion_tokens") or 0)
    tokens_per_doc = None
    if n > 0 and (prompt_tok + completion_tok) > 0:
        tokens_per_doc = (prompt_tok + completion_tok) / n
    elif n > 0:
        gaps.append("tokens/doc unknown (no prompt/completion tokens on record)")

    if token_cpd is None:
        gaps.append("token $/doc unknown (no estimated_cost_usd / cost_per_document)")
    if gpu_cpd is None and bucket_kind(record) == "modal":
        gaps.append(
            "GPU $/doc unknown (set MODAL_BILLED_GPU_SECONDS or ensure latency_ms)"
        )

    combined = None
    if token_cpd is not None or gpu_cpd is not None:
        combined = (token_cpd or 0.0) + (gpu_cpd or 0.0)

    return {
        "n": n,
        "token_cost_per_document": token_cpd,
        "gpu_cost_per_document": gpu_cpd,
        "combined_cost_per_document": combined,
        "latency_seconds_per_document": latency,
        "tokens_per_document": tokens_per_doc,
        "prompt_tokens_per_document": (prompt_tok / n) if n and prompt_tok else None,
        "completion_tokens_per_document": (
            (completion_tok / n) if n and completion_tok else None
        ),
        "honest_gaps": gaps,
        "gpu": record.get("gpu"),
        "model": record.get("model"),
        "profile": record.get("profile"),
        "run_id": record.get("run_id"),
    }


def extrapolate_cost(
    record: Mapping[str, Any],
    *,
    corpus_size: int,
    docs_per_day: float | None = None,
    docs_per_month: float | None = None,
    cold_start_seconds: float = 120.0,
    scaledown_seconds: float = 120.0,
    concurrency: int = 4,
    gpu: str | None = None,
) -> dict[str, Any]:
    """Extrapolate a measured run to a larger corpus / industry throughput.

    Two views:

    * **linear** — ``combined_$/doc × N`` (busy-time lower/upper bound depending
      on whether GPU $ came from billed wall seconds or summed item latency).
    * **with_overhead** — one cold-start + one scaledown window billed at the
      GPU hourly rate, plus linear variable cost for ``N`` docs. Use this when
      estimating a single suite that warms once and tears down once.

    Confidence notes are always attached — never present a single number as
    ground truth.
    """
    if corpus_size < 1:
        raise ValueError("corpus_size must be >= 1")
    rates = per_document_rates(record)
    n = int(rates["n"] or 0)
    token_cpd = rates["token_cost_per_document"]
    gpu_cpd = rates["gpu_cost_per_document"]
    combined = rates["combined_cost_per_document"]
    latency = rates["latency_seconds_per_document"]
    gpu_class = gpu or record.get("gpu") or "L4"
    rate_hr = gpu_usd_per_hour(str(gpu_class))

    notes: list[str] = list(rates.get("honest_gaps") or [])
    if n > 0 and corpus_size > n * 20:
        notes.append(
            f"extrapolation factor {corpus_size}/{n} ≈ {corpus_size / n:.1f}× — "
            "treat as order-of-magnitude until a larger pilot confirms rates"
        )
    if gpu_cpd is not None and record.get("gpu_seconds") is not None and n > 0:
        # Summed item latency overcounts wall under concurrency; flag it.
        notes.append(
            f"GPU $/doc from measured gpu_seconds={record.get('gpu_seconds')} "
            f"(prefer MODAL_BILLED_GPU_SECONDS for suite wall time; with "
            f"concurrency={concurrency}, busy-sum ≈ {concurrency}× wall when saturated)"
        )

    linear_token = (token_cpd * corpus_size) if token_cpd is not None else None
    linear_gpu = (gpu_cpd * corpus_size) if gpu_cpd is not None else None
    linear_combined = (combined * corpus_size) if combined is not None else None

    overhead_s = max(0.0, float(cold_start_seconds)) + max(0.0, float(scaledown_seconds))
    overhead_usd = estimate_gpu_cost_usd(overhead_s, gpu=str(gpu_class)) or 0.0
    with_overhead = None
    if linear_combined is not None:
        with_overhead = round(linear_combined + overhead_usd, 6)

    # Wall-time corpus estimate: if we have per-doc latency, concurrent wall ≈
    # (latency * N) / concurrency (saturated continuous batching).
    corpus_wall_hours = None
    if latency is not None and latency > 0:
        wall_s = (latency * corpus_size) / max(1, int(concurrency))
        corpus_wall_hours = round(wall_s / 3600.0, 4)
        # Alternate GPU $ from wall estimate (orthogonal check).
        wall_gpu_usd = estimate_gpu_cost_usd(wall_s, gpu=str(gpu_class))
    else:
        wall_gpu_usd = None

    industry: dict[str, Any] = {}
    if docs_per_day is not None and docs_per_day > 0 and combined is not None:
        industry["docs_per_day"] = docs_per_day
        industry["usd_per_day"] = round(combined * docs_per_day, 4)
        industry["usd_per_month_30d"] = round(combined * docs_per_day * 30.0, 2)
    if docs_per_month is not None and docs_per_month > 0 and combined is not None:
        industry["docs_per_month"] = docs_per_month
        industry["usd_per_month"] = round(combined * docs_per_month, 2)

    result = {
        "agent": "cost_extrapolate",
        "sample": rates,
        "corpus_size": int(corpus_size),
        "gpu_usd_per_hour": rate_hr,
        "linear": {
            "token_usd": round(linear_token, 6) if linear_token is not None else None,
            "gpu_usd": round(linear_gpu, 6) if linear_gpu is not None else None,
            "combined_usd": round(linear_combined, 6) if linear_combined is not None else None,
            "formula": "combined_cost_per_document × corpus_size",
        },
        "with_overhead": {
            "cold_start_seconds": cold_start_seconds,
            "scaledown_seconds": scaledown_seconds,
            "overhead_usd": round(overhead_usd, 6),
            "combined_usd": with_overhead,
            "formula": (
                "linear_combined + gpu_rate × (cold_start + scaledown) — "
                "one warm + one teardown suite"
            ),
        },
        "wall_time_estimate": {
            "concurrency": concurrency,
            "corpus_wall_hours": corpus_wall_hours,
            "gpu_usd_from_wall": (
                round(wall_gpu_usd, 6) if wall_gpu_usd is not None else None
            ),
            "formula": "(e2e_latency_s × N) / concurrency × gpu_$/hr",
        },
        "industry": industry or None,
        "confidence_notes": notes,
        "markdown": "",  # filled below
    }
    result["markdown"] = _extrapolate_md(result)
    return result


def _extrapolate_md(result: Mapping[str, Any]) -> str:
    sample = result.get("sample") or {}
    linear = result.get("linear") or {}
    oh = result.get("with_overhead") or {}
    wall = result.get("wall_time_estimate") or {}
    industry = result.get("industry") or {}
    lines = [
        "## Cost extrapolation",
        "",
        f"- sample n={sample.get('n')} model={sample.get('model')} "
        f"profile={sample.get('profile')} run={sample.get('run_id')}",
        f"- token $/doc={sample.get('token_cost_per_document')} "
        f"GPU $/doc={sample.get('gpu_cost_per_document')} "
        f"combined $/doc={sample.get('combined_cost_per_document')}",
        f"- latency s/doc={sample.get('latency_seconds_per_document')} "
        f"tokens/doc={sample.get('tokens_per_document')}",
        f"- target corpus_size={result.get('corpus_size')} "
        f"(GPU rate ${result.get('gpu_usd_per_hour')}/hr)",
        "",
        "### Linear (variable only)",
        f"- token $ = {linear.get('token_usd')}",
        f"- GPU $ = {linear.get('gpu_usd')}",
        f"- **combined $ = {linear.get('combined_usd')}**",
        f"- formula: `{linear.get('formula')}`",
        "",
        "### With fixed warm/teardown overhead",
        f"- overhead $ = {oh.get('overhead_usd')} "
        f"(cold={oh.get('cold_start_seconds')}s + "
        f"scaledown={oh.get('scaledown_seconds')}s)",
        f"- **combined + overhead $ = {oh.get('combined_usd')}**",
        "",
        "### Wall-time GPU check",
        f"- corpus wall hours ≈ {wall.get('corpus_wall_hours')} "
        f"(concurrency={wall.get('concurrency')})",
        f"- GPU $ from wall ≈ {wall.get('gpu_usd_from_wall')}",
    ]
    if industry:
        lines += ["", "### Industry scale"]
        for k, v in industry.items():
            lines.append(f"- {k}: {v}")
    notes = result.get("confidence_notes") or []
    if notes:
        lines += ["", "### Confidence / honesty"]
        for note in notes:
            lines.append(f"- {note}")
    return "\n".join(lines)


# ── Pre-flight suite estimate (no live GPU spend) ───────────────────────────

# Per-doc busy latency + token tables live at module import via
# specialist_posture (DMR-078). Task fallbacks when run_id is unknown:
TASK_SEC_PER_DOC: dict[str, dict[str, float]] = {
    "correspondence_specialist": {"low": 30.0, "likely": 70.0, "high": 150.0},
    "insurance_claims_specialist": {"low": 45.0, "likely": 95.0, "high": 200.0},
    "corporate_records_specialist": {"low": 50.0, "likely": 110.0, "high": 240.0},
    "contracts_specialist": {"low": 80.0, "likely": 180.0, "high": 380.0},
    "merger_agreement_specialist": {"low": 100.0, "likely": 220.0, "high": 420.0},
    "sorter": {"low": 200.0, "likely": 400.0, "high": 900.0},  # ~5 calls/doc
}

_BANDS = ("low", "likely", "high")


def _sec_per_doc_for(run_id: str, task: str) -> dict[str, float]:
    if run_id in SPECIALIST_SEC_PER_DOC:
        return dict(SPECIALIST_SEC_PER_DOC[run_id])
    if task in TASK_SEC_PER_DOC:
        return dict(TASK_SEC_PER_DOC[task])
    # Unknown specialist/task: sorter-like upper bound so we never under-quote.
    return {"low": 60.0, "likely": 150.0, "high": 300.0}


def _tokens_for(run_id: str, task: str) -> dict[str, int]:
    if run_id in SPECIALIST_TOKENS_PER_DOC:
        return dict(SPECIALIST_TOKENS_PER_DOC[run_id])
    # Generic specialist guess
    if "specialist" in task or "specialist" in run_id:
        return {"prompt": 6000, "completion": 1500}
    return {"prompt": 4000, "completion": 1000}


def estimate_suite(
    configs: Sequence[Mapping[str, Any] | str | Path],
    *,
    gpu_usd_per_hour_rate: float | None = None,
    sec_per_doc_override: float | None = None,
    cold_start_seconds: float = 120.0,
    scaledown_seconds: float | None = None,
    inter_run_gap_seconds: float = 60.0,
    corpus_size: int | None = None,
    gen_tok_per_s: float | None = None,
) -> dict[str, Any]:
    """Pre-flight GPU $ + wall-time estimate from run YAML metadata.

    Does **not** call Modal. Reads docs / concurrency / GPU / scaledown from
    each config (path or already-parsed mapping) and applies conservative
    low/likely/high busy-sec/doc assumptions. Suite wall assumes one warm
    1×GPU app across all configs (no redeploy), plus one cold-start and one
    scaledown tail.

    ``gen_tok_per_s`` (optional) replaces sec/doc via
    ``(prompt_prefill_s≈8 + completion/gen_rate)`` when tokens tables exist.
    """
    rows: list[dict[str, Any]] = []
    notes: list[str] = [
        "Pre-flight only — replace with MODAL_BILLED_GPU_SECONDS after the suite",
        "Specialists ≈1 LLM call/doc (vs sorter ~5); per-doc GPU $ should beat "
        "run-50 sorter ≈$0.16/doc if doc length is similar",
        "Anchors: run-50 sorter ~77 min / ~$8 on 2–3×L4; L4 gen ≈8.7–13.9 tok/s "
        "(docs/scale-matrix.md); Modal L4 ≈$0.80/GPU-hr",
        "Alternate ceiling: sorter ≈$0.032–0.05 per LLM-call × 150 docs ≈ "
        "$4.80–$7.50 if specialist docs match run-50 filing length and decode "
        "tails (use HIGH band + this ceiling when budgeting credits)",
        "Excludes Modal region multipliers (docs cite 1.15–1.75×) and "
        "download_model CPU time; first GPU cold boot may exceed 120 s",
    ]

    for raw in configs:
        if isinstance(raw, (str, Path)):
            from mailroom_sandbox.job.spec import load_run_spec

            spec = load_run_spec(raw)
            data = {
                "run_id": spec.run_id or "",
                "task": spec.task,
                "docs": int(spec.dataset.limit or 0),
                "concurrency": int(spec.job.concurrency or 1),
                "model": spec.engine.model,
                "gpu": (spec.engine.modal.gpu if spec.engine.modal else "L4"),
                "scaledown_seconds": (
                    int(spec.engine.modal.scaledown_seconds) if spec.engine.modal else 120
                ),
                "max_containers": (
                    int(spec.engine.modal.max_containers) if spec.engine.modal else 1
                ),
                "source": str(raw),
            }
        else:
            data = dict(raw)

        run_id = str(data.get("run_id") or "")
        task = str(data.get("task") or "")
        docs = int(data.get("docs") or data.get("limit") or 0)
        concurrency = max(1, int(data.get("concurrency") or 4))
        gpu = str(data.get("gpu") or "L4").split(":")[0]
        model = str(data.get("model") or "Qwen/Qwen3-8B")
        sd = data.get("scaledown_seconds")
        max_c = int(data.get("max_containers") or 1)

        bands = _sec_per_doc_for(run_id, task)
        if sec_per_doc_override is not None and sec_per_doc_override > 0:
            bands = {b: float(sec_per_doc_override) for b in _BANDS}
            notes.append(f"{run_id or task}: sec/doc override={sec_per_doc_override}")

        tok = _tokens_for(run_id, task)
        if gen_tok_per_s is not None and gen_tok_per_s > 0:
            # Decode-dominated busy time + small prefill pad.
            decode_s = float(tok["completion"]) / float(gen_tok_per_s)
            prefill_s = 8.0
            bands = {
                "low": round((prefill_s + decode_s) * 0.7, 1),
                "likely": round(prefill_s + decode_s, 1),
                "high": round((prefill_s + decode_s) * 1.6, 1),
            }

        rate = (
            float(gpu_usd_per_hour_rate)
            if gpu_usd_per_hour_rate is not None
            else gpu_usd_per_hour(gpu)
        )

        wall: dict[str, float] = {}
        cost: dict[str, float] = {}
        for band in _BANDS:
            sec = float(bands[band])
            wall_s = (docs * sec) / concurrency
            wall[band] = round(wall_s, 1)
            cost[band] = round(wall_s / 3600.0 * rate, 4)

        if max_c > 1:
            notes.append(
                f"{run_id}: max_containers={max_c} — estimate assumes 1 warm "
                "replica (benchmark default); multiply GPU $ if more stay warm"
            )

        rows.append(
            {
                "run_id": run_id,
                "task": task,
                "docs": docs,
                "concurrency": concurrency,
                "gpu": gpu,
                "model": model,
                "scaledown_seconds": int(sd) if sd is not None else 120,
                "sec_per_doc": {b: float(bands[b]) for b in _BANDS},
                "tokens_assumed": tok,
                "wall_seconds": wall,
                "gpu_usd": cost,
                "gpu_usd_per_hour": rate,
                "notes": (
                    "1 LLM call/doc; wall=(docs×sec/doc)/concurrency on 1×GPU"
                ),
            }
        )

    if not rows:
        raise ValueError("estimate_suite requires at least one run config")

    # Suite overhead: one cold-start + one scaledown (max across configs unless
    # caller overrides) + small gaps between runs while the app stays warm.
    suite_scaledown = (
        float(scaledown_seconds)
        if scaledown_seconds is not None
        else float(max(int(r["scaledown_seconds"]) for r in rows))
    )
    n_runs = len(rows)
    gap_total = max(0, n_runs - 1) * float(inter_run_gap_seconds)
    overhead_s = float(cold_start_seconds) + suite_scaledown + gap_total
    rate0 = float(rows[0]["gpu_usd_per_hour"])
    overhead_usd = round(overhead_s / 3600.0 * rate0, 4)

    suite_wall: dict[str, float] = {}
    suite_usd: dict[str, float] = {}
    for band in _BANDS:
        busy = sum(float(r["wall_seconds"][band]) for r in rows)
        suite_wall[band] = round(busy + overhead_s, 1)
        suite_usd[band] = round(
            sum(float(r["gpu_usd"][band]) for r in rows) + overhead_usd, 4
        )

    total_docs = sum(int(r["docs"]) for r in rows)
    cpd = {
        band: round(suite_usd[band] / total_docs, 6) if total_docs else None
        for band in _BANDS
    }

    corpus: dict[str, Any] | None = None
    if corpus_size is not None and corpus_size > 0 and total_docs > 0:
        # Linear GPU $/doc × N; with_overhead adds one cold+scaledown only.
        linear = {
            band: round(float(cpd[band]) * corpus_size, 2) if cpd[band] else None
            for band in _BANDS
        }
        # Re-scale wall from likely sec/doc mix: use suite busy (excl overhead)
        # / total_docs as mean busy, then wall = (mean × N) / concurrency.
        conc = max(1, int(rows[0]["concurrency"]))
        corpus_wall_h = {}
        for band in _BANDS:
            busy_suite = sum(float(r["wall_seconds"][band]) for r in rows)
            mean_busy_per_doc_wall = busy_suite / total_docs  # already /conc
            # mean_busy_per_doc_wall is wall-seconds contribution per doc at c;
            # for corpus at same c: mean_busy_per_doc_wall * corpus_size
            wall_h = (mean_busy_per_doc_wall * corpus_size) / 3600.0
            corpus_wall_h[band] = round(wall_h, 2)
        oh_only = round(
            (float(cold_start_seconds) + suite_scaledown) / 3600.0 * rate0, 4
        )
        corpus = {
            "corpus_size": int(corpus_size),
            "gpu_usd_per_document": cpd,
            "linear_gpu_usd": linear,
            "with_overhead_gpu_usd": {
                band: round(float(linear[band]) + oh_only, 2)
                if linear[band] is not None
                else None
                for band in _BANDS
            },
            "corpus_wall_hours": corpus_wall_h,
            "formula": (
                "suite_gpu_$/doc(band) × corpus_size; with_overhead adds one "
                "cold_start + scaledown at GPU $/hr"
            ),
            "note": (
                f"Extrapolation factor {corpus_size}/{total_docs} ≈ "
                f"{corpus_size / total_docs:.1f}× — order-of-magnitude until "
                "live specialist rates replace assumptions"
            ),
        }

    result = {
        "agent": "cost_estimate_suite",
        "rows": rows,
        "suite": {
            "runs": n_runs,
            "docs": total_docs,
            "cold_start_seconds": cold_start_seconds,
            "scaledown_seconds": suite_scaledown,
            "inter_run_gap_seconds": inter_run_gap_seconds,
            "overhead_seconds": round(overhead_s, 1),
            "overhead_usd": overhead_usd,
            "wall_seconds": suite_wall,
            "wall_hours": {b: round(suite_wall[b] / 3600.0, 3) for b in _BANDS},
            "gpu_usd": suite_usd,
            "gpu_usd_per_document": cpd,
            "posture": "one warm 1×GPU app across configs; teardown after last",
        },
        "corpus_extrapolation": corpus,
        "confidence_notes": notes,
        "optimizations": _estimate_optimizations(suite_usd, suite_scaledown, rate0),
        "markdown": "",
    }
    result["markdown"] = _estimate_suite_md(result)
    return result


def _estimate_optimizations(
    suite_usd: Mapping[str, float],
    scaledown_seconds: float,
    rate_hr: float,
) -> list[dict[str, Any]]:
    """Ranked cost cutters with expected $ savings vs likely suite total."""
    likely = float(suite_usd.get("likely") or 0.0)
    sd_save_to_120 = max(0.0, (scaledown_seconds - 120.0) / 3600.0 * rate_hr)
    # AWQ ~1.5–1.76× throughput → wall/cost shrink ~33–43% on busy portion
    # (overhead fixed). Approximate busy = likely − overhead_at_current_sd.
    overhead = scaledown_seconds / 3600.0 * rate_hr + 120.0 / 3600.0 * rate_hr
    busy_likely = max(0.0, likely - overhead)
    awq_save = round(busy_likely * (1.0 - 1.0 / 1.6), 2)  # ~1.6× mid of 1.5–1.76
    return [
        {
            "rank": 1,
            "name": "Keep one warm app (no redeploy / no teardown between classes)",
            "expected_usd_saved": "already in baseline — teardown×5 would add ~4× scaledown",
            "safe_now": True,
            "note": "Runbook default (DMR-076); tearing down between classes wastes scaledown tails",
        },
        {
            "rank": 2,
            "name": "Attended scaledown 120s (run-30 YAML + MODAL_VLLM_SCALEDOWN_SECONDS)",
            "expected_usd_saved": round(sd_save_to_120, 2),
            "safe_now": True,
            "note": (
                "DMR-076 default in specialist YAMLs is 120s attended; "
                "restore MODAL_VLLM_SCALEDOWN_SECONDS=600 (and YAML) for "
                "unattended/overnight. If estimate still uses 600, "
                f"savings to 120 ≈ ${sd_save_to_120:.2f} at ${rate_hr}/hr"
            ),
        },
        {
            "rank": 3,
            "name": "AWQ cost-saver path (Qwen3-8B-AWQ) after DMR-068 accuracy gate",
            "expected_usd_saved": awq_save,
            "safe_now": False,
            "note": (
                "Gate: ≥1.5× docs/min AND ≥98% accuracy (docs/scale-matrix.md). "
                "Do not swap the default bf16 suite until gated; optional path: "
                'eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"'
            ),
        },
        {
            "rank": 4,
            "name": "Per-doc-type max_tokens / max_input_chars (DMR-078 specialist_posture)",
            "expected_usd_saved": "decode time only — already pinned in overlay",
            "safe_now": True,
            "note": (
                "Overlay budgets fit Qwen/Qwen3-8B L4 16k context; further "
                "cuts need a measured completion histogram (truncating JSON "
                "hurts reproducibility)"
            ),
        },
        {
            "rank": 5,
            "name": "Teardown between specialist classes",
            "expected_usd_saved": -round(4 * scaledown_seconds / 3600.0 * rate_hr, 2),
            "safe_now": False,
            "note": "Usually worse — negative savings (extra scaledown tails)",
        },
    ]


def _estimate_suite_md(result: Mapping[str, Any]) -> str:
    rows = result.get("rows") or []
    suite = result.get("suite") or {}
    corpus = result.get("corpus_extrapolation")
    lines = [
        "## Pre-flight suite cost estimate (Modal GPU)",
        "",
        "| run | docs | sec/doc L/M/H | wall min L/M/H | GPU $ L/M/H | notes |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for r in rows:
        spd = r["sec_per_doc"]
        w = r["wall_seconds"]
        g = r["gpu_usd"]
        lines.append(
            f"| {r.get('run_id') or r.get('task')} | {r.get('docs')} | "
            f"{spd['low']:.0f}/{spd['likely']:.0f}/{spd['high']:.0f} | "
            f"{w['low']/60:.1f}/{w['likely']/60:.1f}/{w['high']/60:.1f} | "
            f"${g['low']:.2f}/${g['likely']:.2f}/${g['high']:.2f} | "
            f"c={r.get('concurrency')} {r.get('gpu')} |"
        )
    wh = suite.get("wall_hours") or {}
    gu = suite.get("gpu_usd") or {}
    cpd = suite.get("gpu_usd_per_document") or {}
    lines += [
        "",
        "### Suite total (1× warm GPU + cold-start + scaledown + inter-run gaps)",
        f"- docs={suite.get('docs')} runs={suite.get('runs')} "
        f"overhead_s={suite.get('overhead_seconds')} "
        f"(cold={suite.get('cold_start_seconds')}s + "
        f"scaledown={suite.get('scaledown_seconds')}s + gaps)",
        f"- wall hours L/M/H: "
        f"{wh.get('low')}/{wh.get('likely')}/{wh.get('high')}",
        f"- GPU $ L/M/H: "
        f"**${gu.get('low')}/${gu.get('likely')}/${gu.get('high')}**",
        f"- GPU $/doc L/M/H: "
        f"{cpd.get('low')}/{cpd.get('likely')}/{cpd.get('high')}",
        f"- posture: {suite.get('posture')}",
    ]
    if corpus:
        lin = corpus.get("linear_gpu_usd") or {}
        woh = corpus.get("with_overhead_gpu_usd") or {}
        cwh = corpus.get("corpus_wall_hours") or {}
        lines += [
            "",
            f"### Full-corpus extrapolation (N={corpus.get('corpus_size')})",
            f"- linear GPU $ L/M/H: ${lin.get('low')}/${lin.get('likely')}/${lin.get('high')}",
            f"- +overhead GPU $ L/M/H: "
            f"${woh.get('low')}/${woh.get('likely')}/${woh.get('high')}",
            f"- wall hours L/M/H: "
            f"{cwh.get('low')}/{cwh.get('likely')}/{cwh.get('high')}",
            f"- {corpus.get('note')}",
        ]
    opts = result.get("optimizations") or []
    if opts:
        lines += ["", "### Ranked optimizations (expected $ vs likely suite)"]
        for o in opts:
            lines.append(
                f"{o.get('rank')}. **{o.get('name')}** — save ≈ {o.get('expected_usd_saved')} "
                f"{'(safe now)' if o.get('safe_now') else '(gated / usually worse)'}: "
                f"{o.get('note')}"
            )
    notes = result.get("confidence_notes") or []
    if notes:
        lines += ["", "### Confidence / honesty"]
        for n in notes:
            lines.append(f"- {n}")
    return "\n".join(lines)
