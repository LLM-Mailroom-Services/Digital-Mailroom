"""Activate a sandbox profile before any mailroom import does real work."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from mailroom_sandbox.overlay import (
    agent_assignments,
    build_merged_taxonomy,
    load_profile,
    patch_mailroom_config,
    write_runtime_taxonomy,
)
from mailroom_sandbox.paths import repo_root, runtime_dir, vendor_dir
from mailroom_sandbox.providers import endpoints_for

_log = logging.getLogger("mailroom_sandbox.runtime")


@dataclass
class Activation:
    profile_name: str
    taxonomy_path: Path
    assignments: list[tuple[str, str, str]] = field(default_factory=list)
    patched_config: bool = False
    patched_prompts: bool = False
    mailroom_src: Path | None = None
    agent_models: dict[str, str] = field(default_factory=dict)
    agent_knobs: dict[str, Any] = field(default_factory=dict)


_ACTIVE: Activation | None = None
_LOCKED_RUNTIME: ContextVar[dict[str, Any] | None] = ContextVar("sandbox_locked_runtime", default=None)


@contextmanager
def locked_runtime(lock: dict[str, Any], prompt_lock: dict[str, Any]):
    """Make activations in this context use copies of the frozen run settings.

    Clear existing prompt overrides and selection on entry. Keep all knob keys
    verbatim (including model, temperature, and chunk/input budgets); an empty
    locked map defeats ambient knob overrides. Transport credentials/endpoints
    remain operator configuration. Yield without activating the runtime.
    Restore the prior context policy on exit, including on errors; applied
    runtime globals, environment, and prompt patches are not restored.
    """
    from mailroom_sandbox.prompt_registry import deactivate_runtime_overrides
    from mailroom_sandbox.prompt_versions import clear_active_selection

    deactivate_runtime_overrides()
    clear_active_selection()
    token = _LOCKED_RUNTIME.set({"lock": deepcopy(lock), "prompt": deepcopy(prompt_lock)})
    try:
        yield
    finally:
        _LOCKED_RUNTIME.reset(token)


def active() -> Activation | None:
    return _ACTIVE


def agent_knobs_for(agent: str) -> dict[str, Any]:
    """Run-scoped knobs for one agent in the current activation ({} when none)."""
    knobs = (_ACTIVE.agent_knobs if _ACTIVE else {}) or {}
    value = knobs.get(agent)
    return dict(value) if isinstance(value, dict) else {}


def _load_dotenv() -> None:
    root = repo_root()
    for candidate in (root / ".env", root / "config" / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)


def load_env_file() -> None:
    """Load the sandbox .env files (idempotent; never overrides real env)."""
    _load_dotenv()


def _prepend_sys_path(path: Path) -> None:
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def resolve_mailroom_src() -> Path | None:
    env = os.environ.get("MAILROOM_SRC")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            vendor_dir() / "llm-mailroom",
            repo_root().parent / "llm-mailroom",
        ]
    )
    for cand in candidates:
        src = cand / "src" if (cand / "src" / "pipeline").is_dir() else cand
        if (src / "pipeline" / "config.py").is_file():
            return src
    return None


def resolve_dojo_src() -> Path | None:
    """llm-dojo-scoring import root (vendored snapshot first, DMR-057)."""
    env = os.environ.get("DOJO_SRC")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            vendor_dir() / "llm-dojo-scoring" / "src",
            repo_root().parent / "llm-dojo-scoring" / "src",
        ]
    )
    for cand in candidates:
        if (cand / "llm_dojo_scoring" / "__init__.py").is_file():
            return cand
    return None


def apply_profile_env(profile: dict, *, base_url_override: str | None = None) -> None:
    endpoints = endpoints_for(profile, base_url_override=base_url_override)
    os.environ["SANDBOX_PROFILE"] = str(profile.get("name") or "")
    os.environ["DEFAULT_PROVIDER"] = str(
        profile.get("default_provider_env") or profile.get("provider") or "ollama"
    )
    if endpoints.base_url_env:
        os.environ.setdefault(endpoints.base_url_env, endpoints.base_url)
        if not os.environ.get(endpoints.base_url_env):
            os.environ[endpoints.base_url_env] = endpoints.base_url
    init_pub = os.environ.get("LANGFUSE_INIT_PROJECT_PUBLIC_KEY")
    init_sec = os.environ.get("LANGFUSE_INIT_PROJECT_SECRET_KEY")
    if init_pub:
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", init_pub)
    if init_sec:
        os.environ.setdefault("LANGFUSE_SECRET_KEY", init_sec)
    if os.environ.get("LANGFUSE_SECRET_KEY"):
        os.environ.setdefault("OBSERVABILITY_PROVIDER", "langfuse")
    else:
        os.environ.setdefault("OBSERVABILITY_PROVIDER", "phoenix")
    # hub#62: honor LANGFUSE_BASE_URL as the cloud-alias — don't force LANGFUSE_HOST
    # to localhost when an operator exported only LANGFUSE_BASE_URL (production).
    # Every HOST-first consumer (health probe, export_traces, vendored llm-mailroom
    # _resolve_host) would otherwise resolve to the wrong sink.
    os.environ.setdefault(
        "LANGFUSE_HOST",
        os.environ.get("LANGFUSE_BASE_URL") or "http://localhost:3000",
    )
    mode = (os.environ.get("SANDBOX_RUN_MODE") or "").lower()
    if mode == "mock":
        os.environ["OBSERVABILITY_ENVIRONMENT"] = "mock"
    elif mode == "local":
        os.environ.setdefault("OBSERVABILITY_ENVIRONMENT", "pilot")
    else:
        os.environ.setdefault("OBSERVABILITY_ENVIRONMENT", "pilot")
    os.environ.setdefault("PHOENIX_TRACING", "enabled")
    os.environ.setdefault("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces")
    os.environ.setdefault("PHOENIX_PROJECT", "mailroom-sandbox")
    os.environ.setdefault("MAILROOM_BASE_DIR", str(repo_root() / "data"))


def resolve_agent_knobs(agent_knobs: dict | None = None) -> dict:
    """Return a deep copy of explicit knobs, or resolve them from the environment.

    When ``agent_knobs`` is None, read ``SANDBOX_AGENT_KNOBS`` as JSON. Missing,
    invalid, or non-object JSON yields an empty map. An explicit empty map
    suppresses the environment fallback.
    """
    if agent_knobs is None:
        raw = os.environ.get("SANDBOX_AGENT_KNOBS")
        if raw:
            try:
                parsed = json.loads(raw)
                agent_knobs = parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                _log.warning("SANDBOX_AGENT_KNOBS is not valid JSON — ignoring run-scoped generation-budget override")
    return deepcopy(agent_knobs or {})


def stamp_locked_record(record: dict[str, Any]) -> None:
    """Mutate a record with the active lock's run/spec/generation and task identity.

    Set ``run_state`` to ``done`` when a locked context exists; otherwise leave
    the record untouched.
    """
    policy = _LOCKED_RUNTIME.get()
    if policy is not None:
        from mailroom_sandbox.job.checkpoint import generation_identity

        lock = policy["lock"]
        record.update(run_id=lock["run_id"], spec_hash=lock["spec_hash"],
                      run_generation=generation_identity(lock), run_task=lock["task"], run_state="done")


def activate(
    profile_name: str | None = None,
    *,
    model: str | None = None,
    prompt_variant: str | None = None,
    base_url: str | None = None,
    load_env_file: bool = True,
    agent_models: dict[str, str] | None = None,
    agent_knobs: dict | None = None,
) -> Activation:
    """Load overlay, write runtime taxonomy, patch mailroom, set env.

    Safe to call more than once; last call wins.

    ``agent_knobs`` (SAND-019) is a run-scoped generation-budget override —
    ``{agent: {max_tokens, max_input_chars, temperature, ...}}`` — applied after
    the global overlay so a run on a wider window (e.g. AWQ 32768) can raise its
    own decode/input budget. When None, it is read from the
    ``SANDBOX_AGENT_KNOBS`` env var (JSON), which is how ``sandbox run`` carries
    it without threading a new field through every call site.

    Inside ``locked_runtime``, the frozen profile, model, per-agent settings,
    and prompt texts override these arguments; ambient knob JSON is ignored.
    The explicit ``base_url`` argument is ignored there, while transport
    configuration still comes from the profile and environment. Return and
    retain the resulting Activation as the active runtime. Profile, taxonomy,
    and required prompt-application errors propagate; timeout, credential,
    and sampling patch failures are caught so activation can continue.
    """
    global _ACTIVE
    policy = _LOCKED_RUNTIME.get()
    if policy is not None:
        lock = policy["lock"]
        profile_name = lock.get("profile") or "ollama"
        model = (lock.get("engine") or {}).get("model")
        agent_models = deepcopy(lock.get("agent_models") or {})
        agent_knobs = deepcopy(lock.get("agent_knobs") or {})
        prompt_variant = None  # the locked TEXT, not today's local stem
        base_url = None
    if load_env_file:
        _load_dotenv()
    agent_knobs = resolve_agent_knobs(agent_knobs)
    name = profile_name or os.environ.get("SANDBOX_PROFILE") or "ollama"
    profile = load_profile(name)
    apply_profile_env(profile, base_url_override=base_url)
    if not model and str(profile.get("provider") or "") == "vllm":
        from mailroom_sandbox.overlay import resolve_served_vllm_model

        model = resolve_served_vllm_model()
    if model and str(profile.get("provider") or "") == "vllm":
        os.environ["VLLM_MODEL"] = str(model)

    mailroom_src = resolve_mailroom_src()
    if mailroom_src is not None:
        _prepend_sys_path(mailroom_src)
    else:
        _log.warning(
            "no mailroom source resolvable (vendored snapshot under %s, sibling "
            "repo, or MAILROOM_SRC) — activation proceeds, but the first family "
            "import will fail. Run `sandbox fetch-deps` to restore the vendored "
            "snapshot.",
            vendor_dir() / "llm-mailroom",
        )
    dojo_src = resolve_dojo_src()
    if dojo_src is not None:
        _prepend_sys_path(dojo_src)
    else:
        _log.warning(
            "no llm-dojo-scoring source resolvable (vendored snapshot under %s, "
            "sibling repo, or DOJO_SRC) — scoring will fail on import. Run "
            "`sandbox fetch-deps` to restore the vendored snapshot.",
            vendor_dir() / "llm-dojo-scoring",
        )

    taxonomy = build_merged_taxonomy(
        profile,
        model_override=model,
        agent_models=agent_models,
        agent_knobs=agent_knobs,
    )
    taxonomy_path = write_runtime_taxonomy(taxonomy)
    os.environ["MAILROOM_TAXONOMY"] = str(taxonomy_path)
    patched = patch_mailroom_config(taxonomy_path)

    # SAND-018: the vendored LangChain agents hardcode timeout=120 (drift-
    # guarded). Apply the taxonomy's run_limits pin so a long L4 generation does
    # not ladder through the retry contract instead of completing.
    try:
        from mailroom_sandbox.llm_timeout import apply_llm_timeout

        limits = taxonomy.get("run_limits") or {}
        apply_llm_timeout(limits.get("llm_call_timeout_seconds"))
    except Exception as exc:  # noqa: BLE001 — never block activation
        _log.warning("llm timeout override failed — 120s vendor default stands: %s", exc)

    # SAND-038: the vendored LangChain agents default api_key to
    # OPENROUTER_API_KEY ahead of the resolved provider's key (drift-guarded),
    # which 401s every contracts/merger row against Modal vLLM when .env holds
    # an OpenRouter key. Defer to provider.api_key_env instead.
    try:
        from mailroom_sandbox.provider_credentials import apply_provider_credentials

        apply_provider_credentials()
    except Exception as exc:  # noqa: BLE001 — never block activation
        _log.warning("provider credential fix failed — vendored key precedence stands: %s", exc)

    # SAND-037: the vendored specialists pass temperature=0.1 as a call-site
    # literal (drift-guarded), so a run-scoped temperature knob is applied by
    # wrapping their _call_structured. No temperature knobs → no-op.
    try:
        from mailroom_sandbox.sampling import apply_sampling_overrides

        apply_sampling_overrides(agent_knobs)
    except Exception as exc:  # noqa: BLE001 — never block activation
        _log.warning("temperature override failed — call-site temperatures stand: %s", exc)

    patched_prompts = False
    if prompt_variant:
        from mailroom_sandbox.prompts import patch_managed_prompt

        patched_prompts = patch_managed_prompt(prompt_variant)

    # eval-environment prompt versions selected for this process (CLI / job lock):
    # apply their texts (loud when a role cannot be patched).
    from mailroom_sandbox.prompt_versions import apply_selection

    if policy is not None:
        from mailroom_sandbox.prompt_registry import apply_locked_prompts

        apply_locked_prompts(policy["prompt"])
        patched_prompts = True
    elif apply_selection():
        patched_prompts = True

    activation = Activation(
        profile_name=name,
        taxonomy_path=taxonomy_path,
        assignments=agent_assignments(taxonomy),
        patched_config=patched,
        patched_prompts=patched_prompts,
        mailroom_src=mailroom_src,
        agent_models=dict(agent_models or {}),
        agent_knobs=dict(agent_knobs or {}),
    )
    _ACTIVE = activation
    runtime_dir()  # ensure exists
    return activation
