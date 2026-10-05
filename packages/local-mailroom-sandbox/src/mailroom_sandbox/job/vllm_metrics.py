"""SAND-032: scrape vLLM Prometheus ``/metrics`` through the Modal web URL.

Modal routes each GET to one replica, so repeated scrapes *sample* replicas;
``process_start_time_seconds`` is unique per vLLM process and groups them.
Coverage is reported honestly ("replicas observed: 1 of 2") — never padded.
TTFT here is MEASURED by vLLM (histogram sum/count), never inferred.
"""

from __future__ import annotations

import re
import time
from typing import Any

_LINE = re.compile(
    r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+([-+0-9.eE]+|NaN|\+Inf|-Inf)$"
)
_KEEP = frozenset(
    {
        "process_start_time_seconds",
        "vllm:request_success_total",
        "vllm:num_preemptions_total",
        "vllm:gpu_cache_usage_perc",
        "vllm:kv_cache_usage_perc",
        "vllm:prefix_cache_hits_total",
        "vllm:prefix_cache_queries_total",
        "vllm:time_to_first_token_seconds_sum",
        "vllm:time_to_first_token_seconds_count",
        "vllm:prompt_tokens_total",
        "vllm:generation_tokens_total",
    }
)


def parse_prometheus(text: str) -> dict[str, float]:
    """Kept metrics summed across label sets, plus ``length_finishes``."""
    out: dict[str, float] = {}
    length = 0.0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE.match(line)
        if not m or m.group(1) not in _KEEP:
            continue
        name, labels = m.group(1), m.group(2) or ""
        try:
            val = float(m.group(3))
        except ValueError:
            continue
        out[name] = out.get(name, 0.0) + val
        if name == "vllm:request_success_total" and 'finished_reason="length"' in labels:
            length += val
    out["length_finishes"] = length
    return out


def group_replicas(samples: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    reps: dict[str, dict[str, float]] = {}
    for s in samples:
        key = s.get("process_start_time_seconds")
        if key is None:
            continue
        reps[str(key)] = s  # later scrape of the same replica wins (monotonic counters)
    return reps


def replica_coverage(reps: dict[str, Any], *, expected: int) -> str:
    return f"replicas observed: {len(reps)} of {expected}"


def summarize(m: dict[str, float]) -> dict[str, float | None]:
    queries = m.get("vllm:prefix_cache_queries_total") or 0.0
    ttft_n = m.get("vllm:time_to_first_token_seconds_count") or 0.0
    kv = m.get("vllm:kv_cache_usage_perc", m.get("vllm:gpu_cache_usage_perc"))
    return {
        "requests": m.get("vllm:request_success_total"),
        "length_finishes": m.get("length_finishes"),
        "preemptions": m.get("vllm:num_preemptions_total"),
        "kv_cache_usage_perc": kv,
        "prefix_cache_hit_rate": (
            round(m["vllm:prefix_cache_hits_total"] / queries, 4) if queries else None
        ),
        "ttft_mean_seconds": (
            round(m["vllm:time_to_first_token_seconds_sum"] / ttft_n, 4) if ttft_n else None
        ),
        "prompt_tokens": m.get("vllm:prompt_tokens_total"),
        "generation_tokens": m.get("vllm:generation_tokens_total"),
    }


def scrape(
    base_url: str, api_key: str, *, attempts: int = 12, expected: int = 1
) -> dict[str, Any]:
    """Sample ``/metrics`` ``attempts`` times; group and summarize per replica."""
    import httpx

    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    samples: list[dict[str, float]] = []
    errors: list[str] = []
    for _ in range(max(1, int(attempts))):
        try:
            resp = httpx.get(f"{root}/metrics", headers=headers, timeout=15.0)
            resp.raise_for_status()
            samples.append(parse_prometheus(resp.text))
        except Exception as exc:  # noqa: BLE001 — report, never crash a run
            errors.append(f"{type(exc).__name__}: {str(exc)[:120]}")
        time.sleep(0.5)
    reps = group_replicas(samples)
    return {
        "coverage": replica_coverage(reps, expected=expected),
        "replicas": {k: summarize(v) for k, v in reps.items()},
        "errors": errors,
        "at": time.time(),
    }
