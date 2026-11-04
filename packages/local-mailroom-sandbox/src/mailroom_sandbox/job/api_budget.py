"""API token spend: which models bill per token, their price bound, and the run ceiling (SAND-089).

The GPU cap (``job.cost_cap_usd``) estimates Modal container time; it says nothing
about OpenRouter, which bills per token. A run that sends any agent to a token-billed
provider therefore needs its own ceiling, ``job.api_cost_cap_usd``, and a known price
for every such model: an unpriced model would make the ceiling unenforceable.

The running total prices every observed token at the highest input and output price
among the run's API models. In a hybrid run that also counts tokens a Modal agent
served, so the estimate errs high: the safe direction for a ceiling.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Iterable, Mapping
from typing import Any

API_PROVIDERS = frozenset({"openrouter"})


def task_agents(lock: Mapping[str, Any]) -> set[str] | None:
    """The agents a run's task calls, or None when it may call any (pipeline and the like).

    A single-agent task calls only that agent, so the profile's other assignments (for
    example the openrouter judge on deepseek) never set the price of a Qwen sorter run.
    """
    task = str(lock.get("task") or "")
    if task == "isolated":
        # The isolated runner always runs the sorter spec, whatever job.task says (job/runner.py).
        return {"sorter"}
    if task == "sorter" or task.endswith("_specialist"):
        return {task}
    return None


def api_models(lock: Mapping[str, Any]) -> list[str]:
    """Token-billed models a locked run (or a lock-shaped spec dump) can call."""
    models: set[str] = set()
    assignments = lock.get("agent_assignments") or {}
    used = task_agents(lock)
    for name, assignment in assignments.items():
        if used is not None and name not in used:
            continue
        if str(assignment.get("provider")) in API_PROVIDERS and assignment.get("model"):
            models.add(str(assignment["model"]))
    agent_models = lock.get("agent_models") or {}
    for name, route in (lock.get("agent_routes") or {}).items():
        if (route or {}).get("provider") in API_PROVIDERS:
            models.add(str(agent_models.get(name) or route.get("model") or ""))
    engine = lock.get("engine") or {}
    if engine.get("kind") in API_PROVIDERS and not assignments:
        models.add(str(engine.get("model") or ""))
    # Reviewer model (e.g. openai/gpt-6-luna-decisions) bills tokens too.
    reviewer = lock.get("reviewer") or {}
    rev_model = reviewer.get("model")
    if rev_model and str(reviewer.get("backend", "")) in ("decisions", "local", "api", "jev"):
        models.add(str(rev_model))
    # The pipeline extraction gate bills the Decisions API whatever the engine is.
    gate = lock.get("extraction_gate") or {}
    if gate.get("model"):
        models.add(str(gate["model"]))
    return sorted(model for model in models if model)


def spec_api_models(spec: Any) -> list[str]:
    """``api_models`` for an unlocked RunSpec, resolved as preflight would lock it."""
    shaped: dict[str, Any] = {
        "engine": spec.engine.model_dump(),
        "agent_models": dict(spec.agent_models),
        "agent_routes": {name: route.model_dump() for name, route in spec.agent_routes.items()},
    }
    if getattr(spec, "extraction_gate", None) is not None:
        shaped["extraction_gate"] = {"model": spec.extraction_gate.model}
    if spec.agent_routes or spec.agent_knobs or spec.agent_models:
        from mailroom_sandbox.agent_routes import describe

        shaped["agent_assignments"] = describe(spec)
    return api_models(shaped)


def unpriced(models: Iterable[str]) -> list[str]:
    from mailroom_sandbox.job.metrics import token_price

    return [model for model in models if token_price(model) is None]


def price_bound(models: Iterable[str]) -> tuple[float, float]:
    """Highest USD per 1M (input, output) tokens across ``models`` and their price tiers.

    Raises on an unpriced model.
    """
    from mailroom_sandbox.job.metrics import token_price_ceiling

    models = list(models)
    missing = unpriced(models)
    if missing:
        raise ValueError(f"no token price for {', '.join(missing)}")
    prices = [token_price_ceiling(model) for model in models]
    return (max((p[0] for p in prices), default=0.0), max((p[1] for p in prices), default=0.0))


def budget_errors(lock: Mapping[str, Any]) -> list[str]:
    """Why a paid run that bills API tokens may not start (empty when it may)."""
    models = api_models(lock)
    if not models:
        return []
    errors = []
    missing = unpriced(models)
    if missing:
        errors.append(
            f"no token price for {', '.join(missing)}: the API spend ceiling cannot be enforced. "
            "Add the model to SANDBOX_MODEL_PRICES (src/mailroom_sandbox/job/metrics.py) or set both "
            "SANDBOX_TOKEN_PRICE_IN_PER_M and SANDBOX_TOKEN_PRICE_OUT_PER_M "
            "(a missing side is priced at 0 and its tokens are not counted)"
        )
    cap = (lock.get("job") or {}).get("api_cost_cap_usd")
    if not isinstance(cap, (int, float)) or isinstance(cap, bool) or not math.isfinite(cap) or cap <= 0:
        errors.append(
            f"this run bills API tokens ({', '.join(models)}) and needs a finite job.api_cost_cap_usd; "
            "the GPU cost_cap_usd does not limit token spend"
        )
    return errors


class ApiBudget:
    """Running API token spend against ``job.api_cost_cap_usd``; checked between documents."""

    def __init__(self, cap_usd: float, usd_per_m_in: float, usd_per_m_out: float, models: list[str]):
        self.cap_usd = float(cap_usd)
        self.usd_per_m_in = float(usd_per_m_in)
        self.usd_per_m_out = float(usd_per_m_out)
        self.models = list(models)
        self.spent_usd = 0.0
        self.documents = 0
        self._lock = threading.Lock()

    def add(self, prompt_tokens: Any, completion_tokens: Any, calls: Any = 1) -> None:
        """Price the tokens at each model's tier for the average call size, the dearest model winning."""
        from mailroom_sandbox.job.metrics import call_cost

        prompt = float(prompt_tokens or 0)
        completion = float(completion_tokens or 0)
        costs = [call_cost(m, prompt, completion, calls=int(calls or 1)) for m in self.models]
        known = [c for c in costs if c is not None]
        cost = max(known) if known else (prompt * self.usd_per_m_in + completion * self.usd_per_m_out) / 1_000_000
        with self._lock:
            self.spent_usd += cost

    def add_usage(self, usage: Mapping[str, Any] | None) -> None:
        """Add one finished (or failed) document's token usage."""
        usage = usage or {}
        self.add(usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("llm_calls") or 1)
        with self._lock:
            self.documents += 1

    def projected_usd(self, in_flight: int = 0) -> float:
        """Spend so far plus ``in_flight`` unfinished documents at the mean cost per finished document."""
        with self._lock:
            mean = self.spent_usd / self.documents if self.documents else 0.0
            return self.spent_usd + max(0, int(in_flight)) * mean

    def exceeded(self, in_flight: int = 0) -> str | None:
        """Why no further document may start, or None.

        ``in_flight`` documents have started but not finished: their spend is not in the total yet,
        so concurrent runs count each at the mean finished-document cost.
        """
        projected = self.projected_usd(in_flight)
        if projected >= self.cap_usd:
            pending = f", {in_flight} in flight" if in_flight else ""
            return (f"api_cost_cap_usd={self.cap_usd} reached (est_api_usd={projected:.4f}{pending} "
                    f"at ${self.usd_per_m_in}/${self.usd_per_m_out} per 1M tokens) — aborting to protect spend")
        return None

    def check(self, prefix: str = "", in_flight: int = 0) -> None:
        """Raise when the cap is reached, counting ``in_flight`` documents (see ``exceeded``)."""
        reason = self.exceeded(in_flight)
        if reason:
            raise RuntimeError(prefix + reason)


FAILED_USAGE_EVENT = "api_usage_of_failed_document"


def usage_records(store: Any) -> list[dict[str, Any]]:
    """Every persisted item, plus each document that raised after a paid call (it has no item row)."""
    failed = [event.get("detail") or {} for event in store.events() if event.get("event") == FAILED_USAGE_EVENT]
    return [*store.load_items(), *failed]


def budget_for(lock: Mapping[str, Any], items: Iterable[Mapping[str, Any]] = ()) -> ApiBudget | None:
    """The run's API budget, seeded with tokens already spent by persisted items (resume)."""
    job = lock.get("job") or {}
    cap = job.get("api_cost_cap_usd")
    models = api_models(lock)
    if job.get("mock", False) or not models or not isinstance(cap, (int, float)) or cap <= 0:
        return None
    price_in, price_out = price_bound(models)
    budget = ApiBudget(cap, price_in, price_out, models)
    for item in items:
        budget.add_usage(item)
    return budget


def spend_estimate(lock: Mapping[str, Any], items: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Estimated API token spend of persisted items at the run's price bound (None: no priced API model)."""
    models = api_models(lock)
    if not models or unpriced(models):
        return None
    price_in, price_out = price_bound(models)
    budget = ApiBudget(float("inf"), price_in, price_out, models)
    for item in items:
        budget.add_usage(item)
    return {"est_api_usd": round(budget.spent_usd, 6), "usd_per_million_tokens": [price_in, price_out],
            "models": models, "basis": "observed tokens at each call's price tier, the highest API model price"}
