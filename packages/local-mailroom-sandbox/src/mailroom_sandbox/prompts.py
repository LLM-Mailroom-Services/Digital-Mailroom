"""Prompt-variant overlay for local-model experiments."""

from __future__ import annotations

import logging
from pathlib import Path

from mailroom_sandbox.eval_environment_lineage import agents_for_variant
from mailroom_sandbox.paths import prompts_dir

_log = logging.getLogger("mailroom_sandbox.prompts")


def list_variants() -> list[str]:
    return sorted(p.stem for p in prompts_dir().glob("*.txt"))


def load_variant(name: str) -> str:
    path = prompts_dir() / f"{name}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown prompt variant {name!r}. Have: {list_variants()}")
    return path.read_text(encoding="utf-8")


def patch_managed_prompt(variant: str) -> bool:
    """Inject a local stem into the live pipeline (LangChain + Family A).

    Catalog specialist stems (eval-environment frozen v1) and ``*_local_v0``
    smoke variants share ``apply_runtime_overrides`` so already-imported
    ``from llm.prompts import get_managed_prompt`` bindings are rebound.
    """
    text = load_variant(variant)
    agents = agents_for_variant(variant)
    if not agents:
        _log.warning("prompt variant %r: no pipeline agent mapping — not applied", variant)
        return False
    from mailroom_sandbox.prompt_registry import apply_runtime_overrides

    patched = apply_runtime_overrides({agent: text for agent in agents})
    missing = [agent for agent in agents if agent not in patched]
    if missing:
        _log.warning(
            "prompt variant %r: overrides not applied for %s — those agents "
            "will keep code-default prompts",
            variant,
            missing,
        )
    return bool(patched)


def variant_path(name: str) -> Path:
    return prompts_dir() / f"{name}.txt"
