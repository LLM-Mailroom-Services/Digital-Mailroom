"""Sandbox component gates (eval skip + taxonomy routing overlay)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import yaml

from mailroom_sandbox.paths import config_dir

_CACHE: dict[str, Any] | None = None


def load_components(*, reload: bool = False) -> dict[str, Any]:
    global _CACHE
    if _CACHE is not None and not reload:
        return _CACHE
    path = config_dir() / "components.yaml"
    if not path.is_file():
        _CACHE = {}
        return _CACHE
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    _CACHE = data
    return data


def is_enabled(kind: str, name: str, components: dict[str, Any] | None = None) -> bool:
    cfg = components or load_components()
    retired = {str(x) for x in (cfg.get("retired_agents") or [])}
    if name in retired:
        return False
    table = cfg.get(kind) or {}
    if name not in table:
        return True
    return bool(table[name])


def routing_overlay(components: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = components or load_components()
    routing = cfg.get("routing") or {}
    out: dict[str, Any] = {}
    if "confidence" in routing:
        out["confidence"] = deepcopy(routing["confidence"])
    return out


def prompt_for_agent(agent: str, components: dict[str, Any] | None = None) -> str | None:
    cfg = components or load_components()
    prompts = cfg.get("prompts") or {}
    value = prompts.get(agent)
    return str(value) if value else None
