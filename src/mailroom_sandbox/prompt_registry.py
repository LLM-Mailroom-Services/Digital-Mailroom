"""Pipeline-agent prompt registry + runtime overrides (DMR-027).

Resolves a prompt version for ANY pipeline agent from three sources: local
``config/prompts/*.txt`` variants, Langfuse-managed prompts (by integer
version — the reproducible pin), or the code default. Enumerates the full
agent surface as the union of the sandbox static roster and the vendored
``llm.prompts.prompt_templates()`` keys (DMR-057 — the snapshot is always
importable).

``apply_runtime_overrides`` injects locked text the same way eval-environment
``evals.prompts.registry.activate`` does: mutate
``langchain_agents.prompts.PROMPT_VERSIONS`` (role key + ``{role}_v*`` aliases)
AND replace ``llm.prompts.get_managed_prompt`` on every already-imported
module that bound the original. Family A specialists
(``from llm.prompts import get_managed_prompt``) are imported during
preflight via ``prompt_templates()`` — patching only the module attribute
would leave those bindings on vendor/Langfuse production text.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any

from mailroom_sandbox.job.spec import PromptRef
from mailroom_sandbox.paths import prompts_dir

logger = logging.getLogger(__name__)

STATIC_AGENTS = (
    "sorter",
    "sorter_reviewer",
    "contracts_specialist",
    "merger_agreement_specialist",
    "corporate_records_specialist",
    "correspondence_specialist",
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
# Keys are the PROMPT_VERSIONS entries that the agent constructor looks up.
# contracts also has a production alias ("contracts_specialist") — runtime
# apply patches BOTH so either lookup sees the locked local text.
FAMILY_B_KEYS = {
    "sorter": "sorter_v14",
    "contracts_specialist": "contracts_specialist_v33",
}

# Extra PROMPT_VERSIONS keys to patch when an agent override lands (aliases).
FAMILY_B_ALIASES = {
    "contracts_specialist": ("contracts_specialist",),
}

# Family A agents whose fetch name differs from the registry key.
FETCH_NAME_ALIASES = {
    "judge-classification": "judge-classification",
    "judge-correctness": "judge-correctness",
}


def agent_prompt_names() -> list[str]:
    """Full agent surface: sandbox static roster merged with the vendored
    ``llm.prompts.prompt_templates()`` keys (DMR-057).

    The vendored snapshot is always importable now, so the templates are the
    pipeline's live keys (vendored templates gmail_triage / intake / relations);
    the static roster is a superset/backstop that keeps the sandbox-only
    agents (relations / gmail_triage / intake) registered even when the
    vendored templates' roster naming differs. The reporter is retired in the
    vendored graph (see ``config/components.yaml`` ``retired_agents``).
    """
    names = set(STATIC_AGENTS)
    try:
        import llm.prompts as prompts  # type: ignore

        names.update(prompts.prompt_templates())
    except Exception as exc:  # noqa: BLE001 — live-or-loud (hub#40)
        logger.warning(
            "vendored llm.prompts not importable; agent surface degraded to "
            "the static roster (%s agents): %s",
            len(names), exc,
        )
    return sorted(names)


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
        from mailroom_sandbox.eval_environment_lineage import assert_catalog_sha

        assert_catalog_sha(agent, ref.file, text)
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
            if ref.version is not None:
                # A pinned version cannot fall back — the run would silently
                # use a different prompt than the lock claims.
                raise RuntimeError(
                    f"langfuse prompt {name!r} version {ref.version} requested but "
                    "LANGFUSE_SECRET_KEY is unset — a pinned version cannot fall back"
                )
            # Floating label without credentials: mirror the mailroom runtime's
            # soft fallback — log and lock the code default (DMR-052 G28).
            logger.warning(
                "langfuse prompt %s requested but LANGFUSE_SECRET_KEY is unset — "
                "locking code-default (floating label cannot be pinned)",
                name,
            )
            return resolve_prompt(agent, PromptRef(source="code-default"), offline=offline)
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


@dataclass
class _OverrideState:
    """What apply_runtime_overrides changed, so tests can restore it."""

    original_get_managed_prompt: Any = None
    original_get_prompt: Any = None
    original_prompt_versions: dict[str, str] | None = None
    rebound_managed: list[Any] = field(default_factory=list)
    rebound_get_prompt: list[Any] = field(default_factory=list)
    table: dict[str, str] = field(default_factory=dict)
    active: bool = False


_OVERRIDE_STATE = _OverrideState()


def _langchain_keys_for(agent: str, versions: dict[str, Any]) -> list[str]:
    """PROMPT_VERSIONS keys belonging to a role (role + ``{role}_v*`` + aliases)."""
    found: list[str] = []
    if agent in versions:
        found.append(agent)
    prefix = f"{agent}_v"
    found.extend(key for key in versions if key.startswith(prefix) and key not in found)
    pinned = FAMILY_B_KEYS.get(agent)
    if pinned and pinned not in found:
        found.append(pinned)
    for alias in FAMILY_B_ALIASES.get(agent, ()):
        if alias not in found:
            found.append(alias)
    return found


def _rebind_attr(attr: str, originals: tuple[Any, ...], injected: Any) -> list[Any]:
    """Point every loaded module's ``attr`` at ``injected`` when it still holds an original."""
    rebound: list[Any] = []
    targets = {obj for obj in originals if obj is not None}
    if not targets:
        return rebound
    for mod in list(sys.modules.values()):
        if mod is None:
            continue
        try:
            current = getattr(mod, attr, None)
        except Exception:
            continue
        if current not in targets:
            continue
        try:
            setattr(mod, attr, injected)
        except Exception:
            continue
        rebound.append(mod)
    return rebound


def apply_runtime_overrides(resolved_texts: dict[str, str]) -> list[str]:
    """Patch the importable pipeline so resolved prompts actually take effect.

    Mirrors eval-environment ``evals.prompts.registry.activate`` so Modal +
    vLLM specialist evals run the frozen v1 catalog text, not vendor
    code-defaults:

    1. Mutate ``langchain_agents.prompts.PROMPT_VERSIONS`` for the role key,
       Family B pins, and every ``{role}_v*`` alias (LangChain specialists
       call ``get_prompt``).
    2. Replace ``llm.prompts.get_managed_prompt`` *and* rebind that name on
       every already-imported module (Family A ``from llm.prompts import
       get_managed_prompt`` happens during preflight).

    Returns patched agent names. Best-effort: agents for non-importable
    modules are skipped (loud warning, hub#40).
    """
    if not resolved_texts:
        return []

    _OVERRIDE_STATE.table.update(resolved_texts)
    langchain_ok = False
    managed_ok = False

    try:
        import langchain_agents.prompts as lc_prompts  # type: ignore

        if not hasattr(lc_prompts, "PROMPT_VERSIONS"):
            raise RuntimeError("langchain_agents.prompts.PROMPT_VERSIONS missing")
        if _OVERRIDE_STATE.original_get_prompt is None:
            _OVERRIDE_STATE.original_get_prompt = getattr(lc_prompts, "get_prompt", None)
        if _OVERRIDE_STATE.original_prompt_versions is None:
            _OVERRIDE_STATE.original_prompt_versions = dict(lc_prompts.PROMPT_VERSIONS)
        versions = lc_prompts.PROMPT_VERSIONS
        for agent, text in resolved_texts.items():
            for key in _langchain_keys_for(agent, versions):
                versions[key] = text
            versions[agent] = text

        def _injected_get_prompt(version: str) -> str:
            table = lc_prompts.PROMPT_VERSIONS
            if version in table:
                return table[version]
            raise KeyError(
                f"Prompt version {version!r} not found. "
                f"Available versions: {list(table)}"
            )

        originals = (_OVERRIDE_STATE.original_get_prompt,)
        lc_prompts.get_prompt = _injected_get_prompt  # type: ignore[assignment]
        previous = list(_OVERRIDE_STATE.rebound_get_prompt)
        _OVERRIDE_STATE.rebound_get_prompt = _rebind_attr(
            "get_prompt", originals, _injected_get_prompt
        )
        for mod in previous:
            try:
                setattr(mod, "get_prompt", _injected_get_prompt)
            except Exception:
                continue
            if mod not in _OVERRIDE_STATE.rebound_get_prompt:
                _OVERRIDE_STATE.rebound_get_prompt.append(mod)
        langchain_ok = True
    except Exception as exc:  # noqa: BLE001 — live-or-loud (hub#40)
        logger.warning(
            "prompt overrides not applied for %s (langchain import failed): %s",
            sorted(resolved_texts), exc,
        )

    try:
        import llm.prompts as prompts  # type: ignore

        if _OVERRIDE_STATE.original_get_managed_prompt is None:
            _OVERRIDE_STATE.original_get_managed_prompt = prompts.get_managed_prompt
        table = _OVERRIDE_STATE.table
        original = _OVERRIDE_STATE.original_get_managed_prompt

        def _lookup(agent_name: str, *args: Any, **kwargs: Any):
            for candidate in (agent_name, agent_name.replace("-", "_")):
                if candidate in table:
                    return table[candidate], None
            for key, text in table.items():
                if key == "judge" and str(agent_name).startswith("judge"):
                    return text, None
            if original is None:
                raise RuntimeError("get_managed_prompt original missing")
            return original(agent_name, *args, **kwargs)

        originals = (_OVERRIDE_STATE.original_get_managed_prompt,)
        prompts.get_managed_prompt = _lookup  # type: ignore[assignment]
        previous = list(_OVERRIDE_STATE.rebound_managed)
        _OVERRIDE_STATE.rebound_managed = _rebind_attr(
            "get_managed_prompt", originals, _lookup
        )
        for mod in previous:
            try:
                setattr(mod, "get_managed_prompt", _lookup)
            except Exception:
                continue
            if mod not in _OVERRIDE_STATE.rebound_managed:
                _OVERRIDE_STATE.rebound_managed.append(mod)
        managed_ok = True
    except Exception as exc:  # noqa: BLE001 — live-or-loud (hub#40)
        still = [
            agent for agent in resolved_texts
            if agent not in FAMILY_B_KEYS
        ]
        if still:
            logger.warning(
                "prompt overrides not applied for %s (family A import failed): %s",
                sorted(still), exc,
            )

    _OVERRIDE_STATE.active = bool(
        _OVERRIDE_STATE.original_get_managed_prompt is not None
        or _OVERRIDE_STATE.original_get_prompt is not None
        or _OVERRIDE_STATE.original_prompt_versions is not None
    )
    patched: list[str] = []
    for agent in resolved_texts:
        if agent in FAMILY_B_KEYS:
            if langchain_ok:
                patched.append(agent)
        elif managed_ok:
            patched.append(agent)
    return patched


def deactivate_runtime_overrides() -> None:
    """Restore the pipeline's original prompt surfaces (tests)."""
    state = _OVERRIDE_STATE
    if not state.active:
        state.table.clear()
        return
    try:
        import llm.prompts as prompts  # type: ignore

        if state.original_get_managed_prompt is not None:
            prompts.get_managed_prompt = state.original_get_managed_prompt
    except Exception:
        pass
    try:
        import langchain_agents.prompts as lc_prompts  # type: ignore

        if state.original_get_prompt is not None:
            lc_prompts.get_prompt = state.original_get_prompt
        if state.original_prompt_versions is not None:
            lc_prompts.PROMPT_VERSIONS.clear()
            lc_prompts.PROMPT_VERSIONS.update(state.original_prompt_versions)
    except Exception:
        pass
    for mod in state.rebound_managed:
        try:
            if state.original_get_managed_prompt is not None:
                setattr(mod, "get_managed_prompt", state.original_get_managed_prompt)
        except Exception:
            pass
    for mod in state.rebound_get_prompt:
        try:
            if state.original_get_prompt is not None:
                setattr(mod, "get_prompt", state.original_get_prompt)
        except Exception:
            pass
    state.rebound_managed = []
    state.rebound_get_prompt = []
    state.original_get_managed_prompt = None
    state.original_get_prompt = None
    state.original_prompt_versions = None
    state.table.clear()
    state.active = False