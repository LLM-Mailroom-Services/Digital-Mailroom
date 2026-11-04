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
from mailroom_sandbox.paths import dotenv_files, repo_root, runtime_dir, vendor_dir
from mailroom_sandbox.providers import default_profile, endpoints_for, modal_gateway_url

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
_ACTIVE_REVIEWER: dict[str, Any] | None = None
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


def active_reviewer() -> dict[str, Any] | None:
    """The reviewer block of the last activation (a locked run's includes its frozen question set)."""
    return _ACTIVE_REVIEWER


def agent_knobs_for(agent: str) -> dict[str, Any]:
    """Run-scoped knobs for one agent in the current activation ({} when none)."""
    knobs = (_ACTIVE.agent_knobs if _ACTIVE else {}) or {}
    value = knobs.get(agent)
    return dict(value) if isinstance(value, dict) else {}


def _load_dotenv() -> None:
    """Load the sandbox ``.env`` files into ``os.environ`` without overriding variables that are already set.

    """
    if os.environ.get("SANDBOX_SKIP_DOTENV"):
        return  # tests: a developer's real keys must never reach a test
    for candidate in dotenv_files():
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


def dojo_uses_installed_release() -> bool:
    from mailroom_sandbox import dojo_source

    choice = dojo_source.current()
    return choice is not None and choice.source == "installed"


def resolve_dojo_src() -> Path | None:
    """llm-dojo-scoring source tree to prepend, or None when the installed release is in use.

    ``mailroom_sandbox.dojo_source`` picks the installed release first and the vendored
    snapshot (DMR-057) as the fallback; a sibling checkout is the last resort.
    """
    if dojo_uses_installed_release():
        return None
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
    """Export the profile's provider settings into ``os.environ``.

    Sets ``SANDBOX_PROFILE`` and ``DEFAULT_PROVIDER``, the profile's base-URL variable when it is unset, and the Langfuse and observability defaults. For ``modal-vllm`` an unset URL stays unset unless ``MODAL_WORKSPACE`` derives the gateway URL.
    """
    endpoints = endpoints_for(profile, base_url_override=base_url_override)
    os.environ["SANDBOX_PROFILE"] = str(profile.get("name") or "")
    os.environ["DEFAULT_PROVIDER"] = str(
        profile.get("default_provider_env") or profile.get("provider") or "ollama"
    )
    if endpoints.base_url_env:
        # A deployed Modal endpoint wins: either the exported VLLM_BASE_URL or
        # the deterministic gateway URL from MODAL_WORKSPACE. For the Modal
        # profile an unset URL stays unset: seeding its static localhost value
        # would defeat the pipeline's live-or-loud warning (DMR-052) and let a
        # live run quietly use whatever listens on localhost:8000.
        if not os.environ.get(endpoints.base_url_env):
            gateway = modal_gateway_url(profile)
            if gateway:
                os.environ[endpoints.base_url_env] = gateway
            elif str(profile.get("name") or "") != "modal-vllm":
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
    # Parked human reviews keep their graph position across a process restart.
    os.environ.setdefault("MAILROOM_CHECKPOINTER", "sqlite")


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


def _install_reviewer(reviewer: Any, taxonomy: dict) -> Any:
    """Write the taxonomy ``reviewer`` block; return the backend to register (or None).

    The base taxonomy comes from the shipped file (``overlay.mailroom_taxonomy_path``),
    and the reviewer block is overwritten unconditionally, including when no
    reviewer is configured, so earlier settings do not carry over.
    """
    if reviewer is None:
        taxonomy["reviewer"] = {"default_mode": "llm", "by_class": {}}
        return None
    from mailroom_sandbox.decision_backends import build_backend
    from mailroom_sandbox.job.spec import ReviewerSpec

    if not isinstance(reviewer, ReviewerSpec):
        # A locked block also carries the frozen question set and its hash.
        reviewer = {k: v for k, v in dict(reviewer).items() if k not in {"question_set", "questions_sha256", "handoff"}}
    spec = reviewer if isinstance(reviewer, ReviewerSpec) else ReviewerSpec.model_validate(reviewer)
    taxonomy["reviewer"] = {
        "default_mode": "llm",
        "by_class": {name: {"mode": "decision_only", "cutoff": cutoff} for name, cutoff in spec.classes.items()},
    }
    if spec.backend == "decisions":
        from mailroom_sandbox.decision_backends import decisions_backend

        policy = _LOCKED_RUNTIME.get()
        locked = ((policy or {}).get("lock") or {}).get("reviewer") or {}
        # A locked run answers from the frozen question set, never a later edit of the file.
        return decisions_backend(spec.model, spec.questions, qset=locked.get("question_set"))
    return build_backend(spec.backend, spec.model, questions=spec.questions)


def _extraction_gate_backend(gate: Any, *, mock: bool = False) -> Any:
    """The gate callable for a locked ``extraction_gate`` block (frozen question set), or None.

    ``mock`` (a ``job.mock`` run) gives an offline stub that never calls the Decisions API.
    """
    if not gate:
        return None
    from mailroom_sandbox.decision_backends import extraction_gate_backend, mock_extraction_gate_backend

    if mock:
        return mock_extraction_gate_backend(str(gate.get("model") or ""), gate.get("question_set") or {})

    qset = gate.get("question_set")
    if not qset:
        raise ValueError("extraction_gate needs its frozen question set; re-run sandbox run preflight")
    return extraction_gate_backend(str(gate["model"]), qset)


def _register_extraction_gate(gate: Any) -> None:
    """Replace the process-wide pipeline extraction gate (None clears it)."""
    try:
        from agents.extraction_gate import register_extraction_gate
    except ImportError:
        if gate is not None:
            raise RuntimeError("the vendored llm-mailroom has no extraction-gate hook (agents.extraction_gate); "
                               "re-vendor llm-mailroom at a commit that includes it") from None
        return
    register_extraction_gate(gate)


def _register_reviewer(backend: Any) -> None:
    """Replace the process-wide decision backend (None clears it)."""
    try:
        from agents.decision_backend import register_decision_backend
    except ImportError:
        if backend is not None:
            raise
        return  # no mailroom source: nothing could have been registered
    register_decision_backend(backend)


def activate(
    profile_name: str | None = None,
    *,
    model: str | None = None,
    prompt_variant: str | None = None,
    base_url: str | None = None,
    load_env_file: bool = True,
    agent_models: dict[str, str] | None = None,
    agent_knobs: dict | None = None,
    agent_routes: dict | None = None,
    reviewer: Any = None,
    extraction_gate: Any = None,
) -> Activation:
    """Load overlay, write runtime taxonomy, patch mailroom, set env.

    Safe to call more than once; last call wins.

    ``agent_knobs`` (SAND-019) is a run-scoped generation-budget override —
    ``{agent: {max_tokens, max_input_chars, temperature, ...}}`` — applied after
    the global overlay so a run on a wider window (e.g. AWQ 32768) can raise its
    own decode/input budget. When None, it is read from the
    ``SANDBOX_AGENT_KNOBS`` env var (JSON), which is how ``sandbox run`` carries
    it without threading a new field through every call site.

    ``extraction_gate`` (a locked block with its frozen question set) registers the
    advisory pipeline extraction gate with llm-mailroom; without it any earlier gate is cleared.
    ``reviewer`` (a ``ReviewerSpec`` or its dict form) selects the decision-model
    reviewer: its classes become ``decision_only`` in the runtime taxonomy and
    its backend is registered with the graph. There is no deactivate step, so
    every activation replaces the previous registration and rewrites the
    ``reviewer`` block; an activation without ``reviewer`` leaves every class
    on ``llm`` and nothing registered.

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
    gate_mock = False
    if policy is not None:
        lock = policy["lock"]
        profile_name = lock.get("profile") or default_profile()
        model = (lock.get("engine") or {}).get("model")
        agent_models = deepcopy(lock.get("agent_models") or {})
        agent_knobs = deepcopy(lock.get("agent_knobs") or {})
        agent_routes = deepcopy(lock.get("agent_routes") or {})
        reviewer = deepcopy(lock.get("reviewer"))
        extraction_gate = deepcopy(lock.get("extraction_gate"))
        # A mock run patches the LLM clients, not the Decisions gate: it gets an offline stub.
        gate_mock = bool((lock.get("job") or {}).get("mock"))
        prompt_variant = None  # the locked TEXT, not today's local stem
        base_url = None
    if load_env_file:
        _load_dotenv()
    agent_knobs = resolve_agent_knobs(agent_knobs)
    name = profile_name or default_profile()
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
    elif not dojo_uses_installed_release():
        _log.warning(
            "no llm-dojo-scoring source resolvable (vendored snapshot under %s, "
            "sibling repo, or DOJO_SRC) — scoring will fail on import. Run "
            "`sandbox fetch-deps` to restore the vendored snapshot.",
            vendor_dir() / "llm-dojo-scoring",
        )

    frozen_models = {name: row["model"] for name, row in (policy["lock"].get("agent_assignments") or {}).items()} if policy else {}
    # A frozen assignment is the *resolved* table: for agents whose model comes from a
    # per-agent knob ("model") it only echoes the engine default, and must not clobber
    # the knob that was frozen alongside it.
    knob_models = {name for name, knob in (agent_knobs or {}).items() if isinstance(knob, dict) and knob.get("model")}
    effective_agent_models = {
        **{name: model for name, model in frozen_models.items() if name not in knob_models},
        **(agent_models or {}),
    }
    taxonomy = build_merged_taxonomy(
        profile,
        model_override=model,
        agent_models=effective_agent_models,
        agent_knobs=agent_knobs,
    )
    from mailroom_sandbox.agent_routes import install as install_agent_routes

    install_agent_routes(agent_routes or {}, taxonomy, agent_models=effective_agent_models)
    reviewer_backend = _install_reviewer(reviewer, taxonomy)
    global _ACTIVE_REVIEWER
    # Process-wide, like the registered backend: agent-task workers do not inherit the lock's ContextVar.
    _ACTIVE_REVIEWER = None if reviewer is None else (
        reviewer.model_dump() if hasattr(reviewer, "model_dump") else deepcopy(dict(reviewer)))
    taxonomy_path = write_runtime_taxonomy(taxonomy)
    os.environ["MAILROOM_TAXONOMY"] = str(taxonomy_path)
    patched = patch_mailroom_config(taxonomy_path)
    _register_reviewer(reviewer_backend)
    # Always replaced, so a gate from an earlier activation never carries over.
    _register_extraction_gate(_extraction_gate_backend(extraction_gate, mock=gate_mock))

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
