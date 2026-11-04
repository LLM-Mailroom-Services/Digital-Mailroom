"""Explicit initials attestation bound to a verified run generation and its endpoints.

This records an operator's review, not cryptographic proof of personal identity.
No credential values are written to the receipt or displayed during review.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import time
from typing import Any

from mailroom_sandbox.job.checkpoint import RunStore, _atomic_write
from mailroom_sandbox.services._exec import ServiceError
from mailroom_sandbox.services._redact import redact_urls

RECEIPT = "spend-authorization.json"
MAX_AGE_S = 24 * 3600
ATTESTATION = "I reviewed all settings and authorize the displayed Modal/OpenRouter spend."


def _safe(value):
    if isinstance(value, dict):
        return {key: _safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return redact_urls(value) if isinstance(value, str) else value


def paid(lock: dict, *, probe: bool = False) -> bool:
    job = lock.get("job") or {}
    return job.get("mode") == "modal" or (not job.get("mock", True) and bool(lock.get("agent_routes"))) or (
        (probe or not job.get("mock", True)) and (
            (lock.get("engine") or {}).get("kind") in {"modal-vllm", "openrouter"}
            or lock.get("profile") in {"modal-vllm", "openrouter"}
        )
    )


def review_settings(store: RunStore) -> dict[str, Any]:
    from mailroom_sandbox.job.otel import resolve_sink
    from mailroom_sandbox.overlay import load_profile
    from mailroom_sandbox.providers import endpoints_for, modal_gateway_url

    lock = store.verify_generation()
    profile = load_profile(lock["profile"])
    endpoint = endpoints_for(profile).base_url
    if lock.get("profile") == "modal-vllm":
        endpoint = os.environ.get("VLLM_BASE_URL", "").strip() or modal_gateway_url(profile) or "unresolved (deploy required)"
    trace = lock.get("trace") or {}
    sink = resolve_sink(sink=trace.get("sink", "none"), otlp=trace.get("otlp", True),
                        endpoint=trace.get("endpoint"), environment=trace.get("environment", "pilot"))
    context = {
        "provider_endpoint": endpoint,
        "trace_endpoint": sink.endpoint,
        "modal_workspace": os.environ.get("MODAL_WORKSPACE", "").strip(),
        "modal_profile": os.environ.get("MODAL_PROFILE", ""),
        "modal_environment": os.environ.get("MODAL_ENVIRONMENT", ""),
    }
    if lock.get("agent_routes"):
        from mailroom_sandbox.agent_routes import endpoint
        from mailroom_sandbox.job.spec import AgentRoute
        for name, raw in lock["agent_routes"].items():
            route = AgentRoute.model_validate(raw)
            try:
                context[f"agent_endpoint:{name}"] = endpoint(route)
            except ServiceError:
                # As for the main endpoint: a Modal route without MODAL_WORKSPACE is shown,
                # not refused; paid preparation validates every route with credentials.
                context[f"agent_endpoint:{name}"] = "unresolved (MODAL_WORKSPACE not set)"
    # Raw URLs are hashed in memory; only redacted context is persisted/displayed.
    fingerprint = hashlib.sha256(json.dumps({"lock": lock, "prompt": store.read_prompt_lock(),
                                            "context": context}, sort_keys=True).encode()).hexdigest()
    return _safe({"run_id": store.run_id, "fingerprint": fingerprint,
            "generation_id": lock.get("generation_id"), "settings": lock.get("spec_core"),
            "agent_knobs": lock.get("agent_knobs", {}), "dataset": lock.get("dataset"),
            "agents": lock.get("agent_assignments", {}),
            "context": {key: redact_urls(value) if isinstance(value, str) else value for key, value in context.items()},
            "budget": _budget_review(lock),
            "budget_note": "Modal cost caps estimate GPU time; CPU/build/scaledown and in-flight calls can add cost. "
                           "OpenRouter bills tokens: api_cost_cap_usd limits that spend, pricing every observed token "
                           "at the highest API model price. Both caps are checked between documents."})


def _budget_review(lock: dict) -> dict[str, Any]:
    """The run's three ceilings and the API models/prices the token ceiling relies on."""
    from mailroom_sandbox.job.api_budget import api_models
    from mailroom_sandbox.job.metrics import token_price

    job = lock.get("job") or {}
    models = api_models(lock)
    return {"gpu_cost_cap_usd": job.get("cost_cap_usd"), "max_wall_seconds": job.get("max_wall_seconds"),
            "api_cost_cap_usd": job.get("api_cost_cap_usd"),
            "api_models": {model: (list(price) if (price := token_price(model)) else "UNPRICED") for model in models}}


def bills_gpu(lock: dict) -> bool:
    """Whether the run warms a Modal GPU: the engine, a per-agent route, or a Modal job worker."""
    job = lock.get("job") or {}
    return (job.get("mode") == "modal" or (lock.get("engine") or {}).get("kind") == "modal-vllm"
            or any((route or {}).get("provider") == "modal-vllm" for route in (lock.get("agent_routes") or {}).values()))


def require_budget(lock: dict) -> None:
    job = lock.get("job") or {}
    cap = job.get("cost_cap_usd")
    wall = job.get("max_wall_seconds")
    gpu_cap_ok = isinstance(cap, (int, float)) and math.isfinite(cap) and cap > 0
    from mailroom_sandbox.job.api_budget import api_models

    # A run with no Modal GPU (API only) is bounded by api_cost_cap_usd instead of the GPU cap.
    if not wall or (not gpu_cap_ok and (bills_gpu(lock) or not api_models(lock))):
        raise ServiceError("paid execution requires finite job.cost_cap_usd and job.max_wall_seconds; review and re-preflight the configuration")
    # SAND-089: token-billed agents need a priced model and their own ceiling.
    from mailroom_sandbox.job.api_budget import budget_errors

    errors = budget_errors(lock)
    if errors:
        raise ServiceError("paid execution refused: " + "; ".join(errors))


OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"


def uses_openrouter(lock: dict) -> bool:
    engine = lock.get("engine") or {}
    reviewer = lock.get("reviewer") or {}
    return (engine.get("kind") == "openrouter" or lock.get("profile") == "openrouter"
            or reviewer.get("backend") == "decisions"
            or bool(lock.get("extraction_gate"))  # the pipeline gate is a Decisions-API model
            or any((r or {}).get("provider") == "openrouter" for r in (lock.get("agent_routes") or {}).values()))


# Owner-set floor (2026-11-01): this much of the OpenRouter key's remaining limit is never
# spent by any run. OPENROUTER_KEY_RESERVE_USD may raise the floor, never lower it.
KEY_RESERVE_USD = 3.0


def key_reserve_usd() -> float:
    """The untouchable reserve: the built-in floor, or a higher value from the environment."""
    try:
        extra = float(os.environ.get("OPENROUTER_KEY_RESERVE_USD", "") or 0.0)
    except ValueError:
        extra = 0.0
    return max(KEY_RESERVE_USD, extra)


def spendable_usd(remaining: float | None) -> float | None:
    """What runs may spend from ``remaining`` once the reserve is held back (None = unlimited key)."""
    return None if remaining is None else max(0.0, float(remaining) - key_reserve_usd())


def key_headroom() -> dict[str, Any]:
    """The OpenRouter key's own limit and what is left of it (no credential is returned)."""
    import httpx

    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    resp = httpx.get(OPENROUTER_KEY_URL, headers={"Authorization": f"Bearer {key}"}, timeout=20)
    resp.raise_for_status()
    data = resp.json().get("data") or {}
    return {"limit": data.get("limit"), "limit_remaining": data.get("limit_remaining"),
            "usage": data.get("usage"), "limit_reset": data.get("limit_reset")}


def require_key_headroom(lock: dict) -> None:
    """Refuse a paid OpenRouter run whose API cap does not fit in the key's remaining limit.

    The OpenRouter limit is hard: a run that crosses it fails mid-way with every later call
    refused. Checked at the spend gate, so it reflects the spend of every run before this one.
    """
    job = lock.get("job") or {}
    if job.get("mock", True) or not uses_openrouter(lock) or not os.environ.get("OPENROUTER_API_KEY", "").strip():
        return
    cap = job.get("api_cost_cap_usd")
    try:
        head = key_headroom()
    except Exception as exc:  # noqa: BLE001 - fail closed: an unknown headroom is not a fit
        raise ServiceError(f"paid execution refused: could not read the OpenRouter key's remaining limit ({type(exc).__name__})") from exc
    remaining = head.get("limit_remaining")
    spendable = spendable_usd(remaining)
    print(f"OpenRouter key: {remaining if remaining is not None else 'no limit'} USD remaining "
          f"(limit {head.get('limit')}, reset {head.get('limit_reset')}); reserve {key_reserve_usd():.2f} USD held back, "
          f"{'unlimited' if spendable is None else f'{spendable:.2f} USD'} spendable; this run's API cap {cap} USD",
          file=sys.stderr)
    if spendable is not None and isinstance(cap, (int, float)) and cap > spendable:
        raise ServiceError(f"paid execution refused: job.api_cost_cap_usd {cap} exceeds the spendable part of the "
                           f"OpenRouter key's remaining limit ({float(remaining):.2f} USD remaining minus the "
                           f"{key_reserve_usd():.2f} USD reserve = {spendable:.2f} USD); lower the cap (or the run) and re-preflight")


def authorize(store: RunStore, *, initials: str | None = None, probe: bool = False,
              extra: dict | None = None, ledger: dict | None = None) -> dict | None:
    """Verify a current receipt or display the complete review and require initials.

    ``ledger`` (``{"action": ..., "config": ...}``) appends a row to the run ledger
    (:mod:`mailroom_sandbox.job.ledger`) once the gate passes, with the receipt's initials.
    """
    receipt = _authorize(store, initials=initials, probe=probe, extra=extra)
    if receipt is not None and ledger is not None:
        from mailroom_sandbox.job import ledger as run_ledger

        lock = store.read_lock() or {}
        try:
            total = len(store.dataset_rows())
        except (OSError, ValueError):
            total = None
        run_ledger.record_signed(lock, initials=receipt["initials"], action=ledger.get("action", "start"),
                                 config=ledger.get("config"), rows_total=total)
    return receipt


def _authorize(store: RunStore, *, initials: str | None, probe: bool, extra: dict | None) -> dict | None:
    lock = store.verify_generation()
    if not paid(lock, probe=probe):
        return None
    require_budget(lock)
    require_key_headroom(lock)
    review = review_settings(store)
    if extra:
        review["workflow"] = extra
        review["fingerprint"] = hashlib.sha256(json.dumps(review, sort_keys=True).encode()).hexdigest()
    path = store.dir / RECEIPT
    try:
        receipt = json.loads(path.read_text())
        if not isinstance(receipt, dict):
            raise ValueError("invalid receipt")
        age = time.time() - float(receipt["signed_at"])
        if receipt.get("schema") == "mailroom.spend-authorization/v1" and receipt.get("fingerprint") == review["fingerprint"] and 0 <= age < MAX_AGE_S and re.fullmatch(r"[A-Z]{2,6}", receipt.get("initials", "")):
            return receipt
    except (OSError, ValueError, TypeError, KeyError):
        pass
    print("Spend review (no paid action has started):", file=sys.stderr)
    print(json.dumps(review, indent=2, sort_keys=True), file=sys.stderr)
    print(ATTESTATION, file=sys.stderr)
    if initials is None:
        if not sys.stdin.isatty():
            raise ServiceError("spend is NOT authorized: review the settings and supply --initials YOUR_INITIALS, or run interactively")
        try:
            initials = input("Sign with your initials (2–6 letters; blank cancels): ")
        except (EOFError, KeyboardInterrupt) as exc:
            raise ServiceError("spend authorization cancelled; no paid action started") from exc
    initials = initials.strip().upper()
    if not re.fullmatch(r"[A-Z]{2,6}", initials):
        raise ServiceError("spend is NOT authorized: initials must contain 2–6 letters")
    receipt = {"schema": "mailroom.spend-authorization/v1", **review, "initials": initials,
               "signed_at": time.time(), "attestation": ATTESTATION}
    _atomic_write(path, json.dumps(receipt, indent=2, sort_keys=True))
    path.chmod(0o600)
    store.append_event("spend_authorized", "info", initials=initials, fingerprint=review["fingerprint"])
    return receipt
