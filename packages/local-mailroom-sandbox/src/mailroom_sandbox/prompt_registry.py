"""Pipeline-agent prompt registry + runtime overrides (DMR-027).

Resolves a prompt version for ANY pipeline agent from three sources: local
``config/prompts/*.txt`` variants, Langfuse-managed prompts (by integer
version — the reproducible pin), or the code default. Enumerates the full
agent surface from the vendored ``llm.prompts.prompt_templates()`` when
present, with a static fallback roster otherwise.

Family B (sorter, contracts_specialist) bypass ``get_managed_prompt``; their
override point is the ``langchain_agents.prompts.PROMPT_VERSIONS`` dict.
``apply_runtime_overrides`` writes both paths.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

from mailroom_sandbox.job.spec import PromptRef
from mailroom_sandbox.paths import prompts_dir

STATIC_AGENTS = (
    "sorter",
    "sorter_reviewer",
    "contracts_specialist",
    "corporate_records_specialist",
    "correspondence_specialist",
    "compliance_specialist",
    "insurance_claims_specialist",
    "judge",
    "judge-classification",
    "judge-correctness",
    "arbiter",
    "boss",
    "reporter",
    "pdf_transcriber",
    "image_extractor",
    "gmail_triage",
    "intake",
    "relations",
)

# Family B: agents whose only override point is the langchain prompt dict.
FAMILY_B_KEYS = {
    "sorter": "sorter_v14",
    "contracts_specialist": "contracts_specialist_v33",
}

# Family A agents whose fetch name differs from the registry key.
FETCH_NAME_ALIASES = {
    "judge-classification": "judge-classification",
    "judge-correctness": "judge-correctness",
}


def agent_prompt_names() -> list[str]:
    try:
        import llm.prompts as prompts  # type: ignore

        keys = prompts.prompt_templates()
        if keys:
            return sorted(keys)
    except Exception:
        pass
    return list(STATIC_AGENTS)


def local_variants() -> list[str]:
    return sorted(p.stem for p in prompts_dir().glob("*.txt"))


def load_variant_text(name: str) -> str:
    path = prompts_dir() / f"{name}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"unknown local prompt variant {name!r}; have {local_variants()}")
    return path.read_text(encoding="utf-8")


def managed_name_for(agent: str) -> str:
    return FETCH_NAME_ALIASES.get(agent) or f"mailroom-{agent}"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _langfuse_client():
    if not os.environ.get("LANGFUSE_SECRET_KEY"):
        return None
    try:
        from langfuse import Langfuse

        return Langfuse()
    except Exception:
        return None


def resolve_prompt(agent: str, ref: PromptRef, *, offline: bool = False) -> dict[str, Any]:
    """Resolve one agent's prompt to its locked form (text + version + hash).

    ``code-default`` lock entry has ``text=None`` (no patch). Local entries
    hash the file text. Langfuse entries pin the integer ``version``.
    """
    if ref.source == "code-default":
        return {
            "agent": agent,
            "source": "code-default",
            "name": managed_name_for(agent),
            "version": None,
            "label": None,
            "file": None,
            "sha256": None,
            "text": None,
        }
    if ref.source == "local":
        if not ref.file:
            raise ValueError(f"local prompt for {agent} requires file=stem")
        text = load_variant_text(ref.file)
        return {
            "agent": agent,
            "source": "local",
            "name": managed_name_for(agent),
            "version": None,
            "label": None,
            "file": ref.file,
            "sha256": _sha(text),
            "text": text,
        }
    if ref.source == "langfuse":
        name = ref.name or managed_name_for(agent)
        if offline:
            if ref.version is None:
                raise RuntimeError(
                    f"langfuse prompt {name!r} needs an explicit version to lock offline; "
                    f"a floating label cannot pin a run"
                )
            return {
                "agent": agent,
                "source": "langfuse",
                "name": name,
                "version": ref.version,
                "label": ref.label,
                "file": None,
                "sha256": None,
                "text": None,
                "offline": True,
            }
        client = _langfuse_client()
        if client is None:
            raise RuntimeError(f"langfuse prompt {name!r} requested but LANGFUSE_SECRET_KEY is unset")
        try:
            prompt_obj = client.get_prompt(name, version=ref.version, label=ref.label)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"could not resolve Langfuse prompt {name!r}: {exc}") from exc
        text = str(getattr(prompt_obj, "prompt", "") or "")
        return {
            "agent": agent,
            "source": "langfuse",
            "name": name,
            "version": getattr(prompt_obj, "version", None) or ref.version,
            "label": ref.label,
            "file": None,
            "sha256": _sha(text),
            "text": text,
        }
    raise ValueError(f"unknown prompt source {ref.source!r}")


def prompt_lock_block(prompt_map: dict[str, Any], *, offline: bool = False) -> dict[str, Any]:
    """Resolve a run spec's ``prompt`` section into a per-agent lock block."""
    default_ref = prompt_map.get("default") or {"source": "code-default"}
    overrides = prompt_map.get("agents") or {}
    default_resolved = resolve_prompt("default", PromptRef(**default_ref), offline=offline)

    agents: dict[str, Any] = {}
    known = set(agent_prompt_names())
    for agent, ref in overrides.items():
        if agent not in known:
            raise KeyError(f"unknown pipeline agent override {agent!r}; have {sorted(known)}")
        agents[agent] = resolve_prompt(agent, PromptRef(**ref), offline=offline)
    return {"default": default_resolved, "agents": agents, "known_agents": sorted(known)}


def apply_runtime_overrides(resolved_texts: dict[str, str]) -> list[str]:
    """Patch the importable pipeline so resolved prompts actually take effect.

    Family B (sorter / contracts_specialist): inject into
    ``langchain_agents.prompts.PROMPT_VERSIONS``. Family A: monkeypatch
    ``llm.prompts.get_managed_prompt`` to return the text for the fetch name.
    Returns patched agent names. Best-effort: agents for non-importable
    modules are skipped.
    """
    patched: list[str] = []
    remainder: dict[str, str] = dict(resolved_texts)

    try:
        import langchain_agents.prompts as lc_prompts  # type: ignore

        for agent, text in remainder.items():
            key = FAMILY_B_KEYS.get(agent)
            if key and hasattr(lc_prompts, "PROMPT_VERSIONS"):
                lc_prompts.PROMPT_VERSIONS[key] = text
                patched.append(agent)
        for agent in patched:
            remainder.pop(agent, None)
    except Exception:
        pass

    if remainder:
        try:
            import llm.prompts as prompts  # type: ignore

            original = prompts.get_managed_prompt
            table = dict(remainder)

            def _lookup(agent_name: str, *args, **kwargs):
                for candidate in (agent_name, agent_name.replace("-", "_")):
                    if candidate in table:
                        return table[candidate], None
                # judge family: a 'judge' override covers all three fetch names.
                for key, text in table.items():
                    if key == "judge" and agent_name.startswith("judge"):
                        return text, None
                return original(agent_name, *args, **kwargs)

            prompts.get_managed_prompt = _lookup  # type: ignore[assignment]
            patched.extend(sorted(remainder))
        except Exception:
            pass
    return patched