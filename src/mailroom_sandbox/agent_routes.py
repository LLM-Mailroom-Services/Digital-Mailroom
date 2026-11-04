"""Sandbox-owned per-agent transport adapter at the family's shared resolution seam.

Both native and LangChain agents use llm.client.resolve_agent_model. Keeping the
adapter here preserves byte-identical vendor snapshots and the family guardrails.
"""
from __future__ import annotations

import functools
import os
import json
from pathlib import Path

from mailroom_sandbox.job.spec import AgentRoute
from mailroom_sandbox.services._exec import ServiceError

_ROUTES: dict[str, dict] = {}


def parse_routes(values: list[str] | None) -> dict[str, AgentRoute]:
    """Parse NAME=PROVIDER:MODEL or NAME=@route.yaml (endpoint/GPU/serving knobs)."""
    import yaml
    result = {}
    for value in values or []:
        name, sep, raw = value.partition("=")
        if not sep or name not in known_agents():
            raise ServiceError(f"agent route needs a live agent NAME=PROVIDER:MODEL or NAME=@route.yaml: {value!r}")
        try:
            if raw.startswith("@"):
                data = yaml.safe_load(Path(raw[1:]).read_text())
            elif raw.startswith("{"):
                data = json.loads(raw)
            else:
                provider, colon, model = raw.partition(":")
                if not colon:
                    raise ValueError("route needs PROVIDER:MODEL")
                data = {"provider": provider, "model": model}
                if provider == "modal-vllm":
                    data["modal"] = {"app": "sandbox-vllm-route-" + name.replace("_", "-")}
            result[name] = AgentRoute.model_validate(data)
        except (ValueError, OSError) as exc:
            raise ServiceError(f"invalid route for {name}: {exc}") from exc
    return result


SPECIALIST_TIERS = ("base", "mid", "full")


def critical_route(agent: str) -> AgentRoute | None:
    """The models.yaml ``critical_tier`` Modal route for an agent (SAND-078)."""
    from mailroom_sandbox.overlay import load_model_map
    raw = (load_model_map().get("critical_tier") or {}).get(agent)
    return AgentRoute.model_validate(raw) if raw else None


def specialist_tier(tier: str, provider: str) -> AgentRoute | str | None:
    """What a specialist tier runs on (SAND-079): a Modal route, an OpenRouter
    model id, or None for ``base`` (the run's own model)."""
    from mailroom_sandbox.overlay import load_model_map
    if tier not in SPECIALIST_TIERS:
        raise ServiceError(f"unknown specialist tier {tier!r}; choose one of {', '.join(SPECIALIST_TIERS)}")
    raw = (((load_model_map().get("critical_tier") or {}).get("specialists") or {}).get(tier) or {}).get(provider)
    if raw is None:
        if tier != "base":
            raise ServiceError(f"specialist tier {tier!r} has no {provider} entry in config/models.yaml")
        return None
    return AgentRoute.model_validate(raw) if isinstance(raw, dict) else str(raw)


def live_specialists() -> list[str]:
    return sorted(name for name in known_agents() if name.endswith("_specialist"))


def known_agents() -> set[str]:
    from mailroom_sandbox.components import load_components
    from mailroom_sandbox.overlay import load_yaml, mailroom_taxonomy_path
    retired = set(load_components().get("retired_agents") or [])
    return set(load_yaml(mailroom_taxonomy_path()).get("agents") or {}) - retired


def describe(spec) -> dict[str, dict[str, str]]:
    """Resolve the full agent model/provider table without creating any clients."""
    from mailroom_sandbox.overlay import build_merged_taxonomy, load_profile
    taxonomy = build_merged_taxonomy(load_profile(spec.profile), model_override=spec.engine.model,
                                      agent_models=spec.agent_models, agent_knobs=spec.agent_knobs)
    assignments = {}
    for name, agent in (taxonomy.get("agents") or {}).items():
        if name not in known_agents():
            continue
        route = spec.agent_routes.get(name)
        assignments[name] = {
            "provider": route.provider if route else str(agent.get("provider")),
            "model": spec.agent_models.get(name) or (route.model if route else str(agent.get("model"))),
        }
    return assignments


def endpoint(route: AgentRoute) -> str:
    if route.base_url:
        return route.base_url.rstrip("/")
    if route.provider == "openrouter":
        return os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    workspace = os.environ.get("MODAL_WORKSPACE", "").strip()
    if not workspace or route.modal is None:
        raise ServiceError("per-agent Modal route requires MODAL_WORKSPACE and modal.app")
    return f"https://{workspace}--{route.modal.app}-serve.modal.run/v1"


def credential_env(route: AgentRoute) -> str:
    return route.api_key_env or ("OPENROUTER_API_KEY" if route.provider == "openrouter" else "VLLM_API_KEY")


def validate(routes: dict[str, AgentRoute], *, credentials: bool = False) -> None:
    unknown = set(routes) - known_agents()
    if unknown:
        raise ServiceError(f"unknown or retired agents in routes: {sorted(unknown)}")
    for name, route in routes.items():
        if credentials or route.provider != "modal-vllm":
            endpoint(route)
        if credentials and route.provider in {"api", "openrouter"}:
            key = credential_env(route)
            if not os.environ.get(key, "").strip() or os.environ[key] == "mock-key":
                raise ServiceError(f"{name}: set {key} for the selected API route")


def install(routes: dict[str, dict], taxonomy: dict, *, agent_models: dict | None = None) -> None:
    """Replace the active route map on every activation; explicit agent models win last."""
    global _ROUTES
    parsed = {name: AgentRoute.model_validate(value) for name, value in routes.items()}
    if set(parsed) - set(taxonomy.get("agents") or {}):
        raise ServiceError("agent route does not name a pipeline agent")
    _ROUTES = {name: route.model_dump() for name, route in parsed.items()}
    if not parsed:
        return
    from llm import client
    from llm.providers import ProviderConfig

    for name, route in parsed.items():
        model = (agent_models or {}).get(name) or route.model
        _ROUTES[name]["model"] = model
        taxonomy["agents"][name].update(provider="vllm" if route.provider == "modal-vllm" else route.provider, model=model)
    if getattr(client.resolve_agent_model, "_sandbox_agent_routes", False):
        return
    original = client.resolve_agent_model

    @functools.wraps(original)
    def resolve(agent_name: str, agent_cfg: dict | None = None):
        raw = _ROUTES.get(agent_name)
        if raw is None:
            return original(agent_name, agent_cfg)
        route = AgentRoute.model_validate(raw)
        key_env = credential_env(route)
        if route.provider in {"api", "openrouter"} and (not os.environ.get(key_env, "").strip() or os.environ.get(key_env) == "mock-key"):
            raise ValueError(f"{agent_name}: API route requires {key_env}")
        provider = ProviderConfig(name="vllm" if route.provider == "modal-vllm" else route.provider,
                                  base_url=endpoint(route), api_key_env=key_env,
                                  default_model=route.model, available_models=["*"])
        return client.ResolvedModel(provider=provider, model=route.model, champion=route.model)

    resolve._sandbox_agent_routes = True
    client.resolve_agent_model = resolve
