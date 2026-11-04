"""Recommended run ceilings, derived from the experiment design (SAND-089).

``sandbox experiment create`` fills ``job.cost_cap_usd`` (GPU), ``job.max_wall_seconds``
(the wall-clock limit after which the run aborts and its fleet is torn down) and
``job.api_cost_cap_usd`` (token spend) from these figures unless the operator sets
them, and ``experiment review``/``preflight`` show configured against recommended.

The estimate reuses the pre-flight suite tables in ``job/metrics.py``: busy seconds
per document by task ("likely" band), tokens per call, the Modal GPU rate for every
app the run bills, and the token price of every API model. It applies a safety
margin, then rounds up. These are planning figures, not measurements: replace them
with a smoke run's numbers when you have one.
"""

from __future__ import annotations

import math
from typing import Any

MARGIN = 1.5            # headroom over the likely-band estimate
COLD_START_S = 120.0    # first boot of a scale-to-zero app (docs: may exceed 120 s)
MIN_WALL_S = 600        # never recommend a ceiling a cold boot alone could hit
# In-flight documents one Modal replica sustains before latency stops improving
# (jobs.md: 4 is the efficient default; DMR-072: 8-way on 1×L4 piled at the proxy).
# The SAND42 contracts c8 run measured 914 s for 50 documents, ~146 busy s/doc,
# against the 40 s/doc run-posture figure, so the posture table is not used here.
PER_REPLICA_CONCURRENCY = 4
# Single-call tasks the suite tables do not list. The reviewer probe gates on
# under 10 s per document (config/experiments/decision-pilot/README.md).
SINGLE_CALL_SEC_PER_DOC = {"sorter_reviewer": 10.0}
# Pipeline stages that make one LLM call per document; all five specialists are one stage.
PIPELINE_STAGES = ("sorter", "sorter_reviewer", "specialist", "judge")
SPECIALIST_AGENTS = frozenset({"contracts_specialist", "merger_agreement_specialist",
                               "corporate_records_specialist", "correspondence_specialist",
                               "insurance_claims_specialist"})


def _ceil_to(value: float, step: float) -> float:
    return math.ceil(value / step - 1e-9) * step


def _task_key(spec: Any) -> str:
    """The suite-table key for this run's per-document latency and tokens."""
    if spec.task == "specialist" and spec.target:
        from mailroom_sandbox.eval.primary import SPECIALISTS

        return SPECIALISTS.get(spec.target, spec.task)
    if spec.task == "pipeline":
        return "sorter"  # the suite tables' multi-call (~5 calls/doc) band
    return spec.task


def _modal_apps(spec: Any) -> list[dict[str, Any]]:
    """Every Modal app the run deploys (engine + per-agent routes)."""
    apps = []
    if spec.engine.kind == "modal-vllm" and spec.engine.modal:
        apps.append(spec.engine.modal.model_dump())
    seen = set()
    for route in spec.agent_routes.values():
        if route.provider == "modal-vllm" and route.modal and route.modal.app not in seen:
            seen.add(route.modal.app)
            apps.append(route.modal.model_dump())
    return apps


def _fleet_usd_per_hour(spec: Any) -> float:
    """USD/hour while every Modal app the run deploys is warm."""
    from mailroom_sandbox.job.metrics import _billed_gpu, gpu_usd_per_hour

    total = 0.0
    for app in _modal_apps(spec):
        gpu, count = _billed_gpu(app)
        total += gpu_usd_per_hour(gpu) * count
    return total


def _api_calls_per_doc(spec: Any, api_models: list[str]) -> int:
    if not api_models:
        return 0
    if spec.task != "pipeline":
        return 5 if spec.task == "sorter" else 1
    if spec.engine.kind == "openrouter" and not spec.agent_routes:
        return len(PIPELINE_STAGES)
    from mailroom_sandbox.agent_routes import describe

    stages = set()
    for name, assignment in describe(spec).items():
        if assignment.get("provider") == "openrouter":
            stages.add("specialist" if name in SPECIALIST_AGENTS else name)
    return max(1, len(stages & set(PIPELINE_STAGES)))


def _max_completion(spec: Any) -> int | None:
    caps = [int(knobs["max_tokens"]) for knobs in (spec.agent_knobs or {}).values()
            if isinstance(knobs, dict) and isinstance(knobs.get("max_tokens"), int)]
    return max(caps) if caps else None


def recommend(spec: Any) -> dict[str, Any]:
    """Recommended GPU cap, wall ceiling and API cap for one run, with the basis for each."""
    from mailroom_sandbox.job.api_budget import price_bound, spec_api_models, unpriced
    from mailroom_sandbox.job.metrics import _sec_per_doc_for, _tokens_for

    docs = int(spec.dataset.limit or 0)
    concurrency = max(1, int(spec.job.concurrency or 1))
    apps = _modal_apps(spec)
    if apps:  # the smallest app is the bottleneck
        concurrency = min(concurrency, *(PER_REPLICA_CONCURRENCY * max(1, int(app.get("max_containers") or 1))
                                         for app in apps))
    key = _task_key(spec)
    sec_per_doc = SINGLE_CALL_SEC_PER_DOC.get(key) or _sec_per_doc_for("", key)["likely"]  # not the run postures
    busy_wall = docs * sec_per_doc / concurrency
    scaledown = max((float(app.get("scaledown_seconds") or 0) for app in apps), default=0.0)
    fleet_rate = _fleet_usd_per_hour(spec)
    overhead = (COLD_START_S + scaledown) if fleet_rate else 0.0
    wall = int(max(MIN_WALL_S, _ceil_to(busy_wall * MARGIN + overhead, 60)))
    gpu_cap = round(_ceil_to(wall / 3600.0 * fleet_rate, 0.05), 2) if fleet_rate else None

    models = spec_api_models(spec)
    api_cap = None
    api_basis: dict[str, Any] = {"models": models}
    if models:
        missing = unpriced(models)
        if missing:
            api_basis["unpriced"] = missing
        else:
            price_in, price_out = price_bound(models)
            tokens = _tokens_for(spec.run_id or "", key)
            completion = tokens["completion"]
            if (cap := _max_completion(spec)) is not None:
                completion = min(completion, cap)
            calls = _api_calls_per_doc(spec, models)
            per_doc = calls * (tokens["prompt"] * price_in + completion * price_out) / 1_000_000
            api_cap = round(max(0.05, _ceil_to(docs * per_doc * MARGIN, 0.05)), 2)
            api_basis.update({"usd_per_million_tokens": [price_in, price_out], "calls_per_document": calls,
                              "tokens_per_call": {"prompt": tokens["prompt"], "completion": completion},
                              "usd_per_document": round(per_doc, 6)})
    return {
        "gpu_cost_cap_usd": gpu_cap,
        "max_wall_seconds": wall,
        "api_cost_cap_usd": api_cap,
        "basis": {
            "documents": docs, "effective_concurrency": concurrency, "latency_table": key,
            "busy_seconds_per_document": sec_per_doc, "margin": MARGIN,
            "cold_start_and_scaledown_seconds": overhead, "fleet_usd_per_hour": round(fleet_rate, 4),
            "api": api_basis,
        },
    }


def compare(spec: Any, advice: dict[str, Any] | None = None) -> list[str]:
    """Warnings where a configured ceiling sits below its recommendation (or is missing)."""
    advice = advice or recommend(spec)
    job = spec.job
    warnings = []
    for field, label, configured in (("gpu_cost_cap_usd", "cost_cap_usd", job.cost_cap_usd),
                                     ("max_wall_seconds", "max_wall_seconds", job.max_wall_seconds),
                                     ("api_cost_cap_usd", "api_cost_cap_usd", job.api_cost_cap_usd)):
        want = advice.get(field)
        if want is None:
            continue
        if configured is None:
            warnings.append(f"{label} is unset; recommended {want}")
        elif configured < want:
            warnings.append(f"{label}={configured} is below the recommended {want}; the run may abort early")
    unpriced = (advice.get("basis") or {}).get("api", {}).get("unpriced")
    if unpriced:
        warnings.append(f"no token price for {', '.join(unpriced)}: paid launch will be refused")
    return warnings
