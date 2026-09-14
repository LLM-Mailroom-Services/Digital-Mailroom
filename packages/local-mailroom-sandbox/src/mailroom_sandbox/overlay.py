"""Taxonomy overlay + OpenRouter→local model map.

Mailroom's ``pipeline.config.CONFIG_PATH`` is hardcoded to the installed
package. The sandbox deep-merges a local overlay, rewrites every agent's
provider/model for the active profile, writes the result under
``data/runtime/taxonomy.yaml``, and monkeypatches CONFIG_PATH onto that file.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from mailroom_sandbox.paths import config_dir, profiles_dir, runtime_dir


def deep_merge(base: Any, overlay: Any) -> Any:
    """Recursive dict merge; overlay wins. Non-dicts replace."""
    if not isinstance(base, dict) or not isinstance(overlay, dict):
        return deepcopy(overlay)
    out = deepcopy(base)
    for key, value in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing YAML: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_model_map() -> dict:
    return load_yaml(config_dir() / "models.yaml")


def load_profile(name: str) -> dict:
    path = profiles_dir() / f"{name}.yaml"
    if not path.is_file():
        available = sorted(p.stem for p in profiles_dir().glob("*.yaml"))
        raise FileNotFoundError(f"Unknown profile {name!r}. Available: {available}")
    profile = load_yaml(path)
    profile.setdefault("name", name)
    return profile


def list_profiles() -> list[str]:
    return sorted(p.stem for p in profiles_dir().glob("*.yaml"))


def mailroom_taxonomy_path() -> Path:
    """Shipped mailroom taxonomy: installed package, then vendored base."""
    try:
        import pipeline.config as cfg  # type: ignore

        packaged = Path(cfg.CONFIG_PATH)
        if packaged.is_file():
            return packaged
    except Exception:
        pass
    vendored = config_dir() / "mailroom.taxonomy.base.yaml"
    if vendored.is_file():
        return vendored
    raise FileNotFoundError(
        "Could not locate mailroom taxonomy.yaml. Run `sandbox fetch-deps` "
        "to refresh the tracked vendor snapshot."
    )


def map_model(openrouter_id: str, serving: str, model_map: dict | None = None) -> str:
    """Map an OpenRouter champion id onto a local serving tag."""
    model_map = model_map or load_model_map()
    entry = (model_map.get("map") or {}).get(openrouter_id) or {}
    if serving in entry:
        return str(entry[serving])
    defaults = model_map.get("defaults") or {}
    if serving in defaults:
        return str(defaults[serving])
    return openrouter_id


def serving_family(profile: dict) -> str:
    """Which column of models.yaml this profile uses (ollama/vllm/llamacpp/...)."""
    name = str(profile.get("name") or profile.get("provider") or "ollama")
    if name in {"vllm-local", "modal-vllm", "vllm-remote", "vllm"}:
        return "vllm"
    if name in {"llamacpp"}:
        return "llamacpp"
    if name in {"lmstudio"}:
        return "lmstudio"
    if name in {"openrouter"}:
        return "openrouter"
    return "ollama"


AGENT_CONFIG_KEYS = (
    "provider",
    "model",
    "temperature",
    "max_tokens",
    "max_input_chars",
    "reasoning_effort",
)


def parse_agent_models(specs: list[str] | None) -> dict[str, str]:
    """Parse repeatable CLI ``NAME=tag`` specs into an agent→model map."""
    out: dict[str, str] = {}
    for spec in specs or []:
        if "=" not in spec:
            raise ValueError(f"Expected NAME=model, got {spec!r}")
        name, model = spec.split("=", 1)
        name, model = name.strip(), model.strip()
        if not name or not model:
            raise ValueError(f"Expected NAME=model, got {spec!r}")
        out[name] = model
    return out


def apply_agent_overrides(taxonomy: dict, overrides: dict | None, *, keys: tuple[str, ...] | None = None) -> dict:
    """Copy selected agent knobs onto the merged taxonomy (missing keys skipped)."""
    if not overrides:
        return taxonomy
    allowed = keys or AGENT_CONFIG_KEYS
    out = deepcopy(taxonomy)
    agents = out.setdefault("agents", {})
    for name, patch in overrides.items():
        if not isinstance(patch, dict):
            continue
        target = agents.setdefault(name, {})
        if not isinstance(target, dict):
            continue
        for key in allowed:
            if key in patch and patch[key] is not None:
                target[key] = deepcopy(patch[key])
    return out


def apply_agent_models(taxonomy: dict, agent_models: dict[str, str] | None) -> dict:
    """Surgical per-agent model tags (CLI ``--agent-model``). Wins last."""
    if not agent_models:
        return taxonomy
    out = deepcopy(taxonomy)
    agents = out.setdefault("agents", {})
    for name, model in agent_models.items():
        target = agents.setdefault(name, {})
        if isinstance(target, dict):
            target["model"] = model
    return out


def rewrite_agents(taxonomy: dict, profile: dict, *, model_override: str | None = None) -> dict:
    """Set every agent's provider + model from the profile (judge may differ)."""
    out = deepcopy(taxonomy)
    agents = out.setdefault("agents", {})
    provider = profile.get("provider") or "ollama"
    default_model = model_override or profile.get("default_model")
    judge_model = profile.get("judge_model") or default_model
    family = serving_family(profile)
    model_map = load_model_map()
    for name, agent in agents.items():
        if not isinstance(agent, dict):
            continue
        original = agent.get("model") or ""
        agent["provider"] = provider
        if name == "judge":
            mapped = map_model(original, family, model_map) if original else judge_model
            agent["model"] = judge_model or mapped
        else:
            mapped = map_model(original, family, model_map) if original else default_model
            agent["model"] = model_override or mapped or default_model
    return out


def build_merged_taxonomy(
    profile: dict,
    *,
    model_override: str | None = None,
    extra_overlay: dict | None = None,
    agent_models: dict[str, str] | None = None,
) -> dict:
    from mailroom_sandbox.components import load_components, routing_overlay

    base = load_yaml(mailroom_taxonomy_path())
    overlay = load_yaml(config_dir() / "taxonomy.overlay.yaml")
    merged = deep_merge(base, overlay)
    merged = deep_merge(merged, routing_overlay(load_components()))
    if extra_overlay:
        merged = deep_merge(merged, extra_overlay)
    merged = rewrite_agents(merged, profile, model_override=model_override)
    # Overlay agent knobs (temp / tokens / optional model) win after rewrite.
    merged = apply_agent_overrides(merged, overlay.get("agents") or {})
    # CLI --agent-model is surgical and always wins last.
    merged = apply_agent_models(merged, agent_models)
    return merged


def write_runtime_taxonomy(taxonomy: dict, dest: Path | None = None) -> Path:
    dest = dest or (runtime_dir() / "taxonomy.yaml")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(taxonomy, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return dest


def patch_mailroom_config(taxonomy_path: Path) -> bool:
    """Point mailroom's cached config loader at the sandbox runtime YAML."""
    try:
        import pipeline.config as cfg  # type: ignore
    except Exception:
        return False
    cfg.CONFIG_PATH = Path(taxonomy_path)
    cache_clear = getattr(cfg.load_config, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    return True


def agent_assignments(taxonomy: dict) -> list[tuple[str, str, str]]:
    rows = []
    for name, agent in (taxonomy.get("agents") or {}).items():
        if isinstance(agent, dict):
            rows.append((name, str(agent.get("provider", "?")), str(agent.get("model", "?"))))
    return rows


def agent_roster(taxonomy: dict) -> list[dict]:
    """Merged taxonomy agents plus sandbox component enablement."""
    from mailroom_sandbox.components import is_enabled, load_components

    components = load_components()
    rows = []
    for name, agent in (taxonomy.get("agents") or {}).items():
        if not isinstance(agent, dict):
            continue
        rows.append(
            {
                "agent": name,
                "provider": agent.get("provider"),
                "model": agent.get("model"),
                "temperature": agent.get("temperature"),
                "max_tokens": agent.get("max_tokens"),
                "max_input_chars": agent.get("max_input_chars"),
                "reasoning_effort": agent.get("reasoning_effort"),
                "enabled": is_enabled("agents", name, components),
                "retired": name in {str(x) for x in (components.get("retired_agents") or [])},
            }
        )
    return rows
