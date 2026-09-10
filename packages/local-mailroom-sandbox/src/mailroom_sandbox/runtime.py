"""Activate a sandbox profile before any mailroom import does real work."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

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


@dataclass
class Activation:
    profile_name: str
    taxonomy_path: Path
    assignments: list[tuple[str, str, str]] = field(default_factory=list)
    patched_config: bool = False
    patched_prompts: bool = False
    mailroom_src: Path | None = None
    agent_models: dict[str, str] = field(default_factory=dict)


_ACTIVE: Activation | None = None


def active() -> Activation | None:
    return _ACTIVE


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
    os.environ.setdefault("LANGFUSE_HOST", "http://localhost:3000")
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


def activate(
    profile_name: str | None = None,
    *,
    model: str | None = None,
    prompt_variant: str | None = None,
    base_url: str | None = None,
    load_env_file: bool = True,
    agent_models: dict[str, str] | None = None,
) -> Activation:
    """Load overlay, write runtime taxonomy, patch mailroom, set env.

    Safe to call more than once; last call wins.
    """
    global _ACTIVE
    if load_env_file:
        _load_dotenv()
    name = profile_name or os.environ.get("SANDBOX_PROFILE") or "ollama"
    profile = load_profile(name)
    apply_profile_env(profile, base_url_override=base_url)

    mailroom_src = resolve_mailroom_src()
    if mailroom_src is not None:
        _prepend_sys_path(mailroom_src)

    taxonomy = build_merged_taxonomy(
        profile, model_override=model, agent_models=agent_models
    )
    taxonomy_path = write_runtime_taxonomy(taxonomy)
    os.environ["MAILROOM_TAXONOMY"] = str(taxonomy_path)
    patched = patch_mailroom_config(taxonomy_path)

    patched_prompts = False
    if prompt_variant:
        from mailroom_sandbox.prompts import patch_managed_prompt

        patched_prompts = patch_managed_prompt(prompt_variant)

    activation = Activation(
        profile_name=name,
        taxonomy_path=taxonomy_path,
        assignments=agent_assignments(taxonomy),
        patched_config=patched,
        patched_prompts=patched_prompts,
        mailroom_src=mailroom_src,
        agent_models=dict(agent_models or {}),
    )
    _ACTIVE = activation
    runtime_dir()  # ensure exists
    return activation
