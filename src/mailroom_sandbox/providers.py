"""Named local serving profiles and URL construction (no sockets)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from mailroom_sandbox.overlay import load_profile, list_profiles

# The sandbox default is the Modal-served vLLM endpoint: no local GPU, no
# Ollama daemon, the same OpenAI /v1 surface every eval path already uses.
# Offline work opts out explicitly with `--profile ollama` (or SANDBOX_PROFILE).
# Keep this in one place: CLI parsing, runtime activation, and the health hint
# all read it.
DEFAULT_PROFILE = "modal-vllm"

KNOWN_PROFILES = ("modal-vllm", "ollama", "vllm-local", "vllm-remote", "llamacpp", "lmstudio", "openrouter")

MAILROOM_PROVIDER_KEYS = ("openrouter", "ollama", "vllm", "generic")


@dataclass(frozen=True)
class ProviderEndpoints:
    name: str
    mailroom_provider: str
    base_url: str
    base_url_env: str
    api_key_env: str | None
    models_url: str
    chat_url: str
    default_model: str
    requires_api_key: bool


def _join(base: str, suffix: str) -> str:
    return base.rstrip("/") + "/" + suffix.lstrip("/")


def endpoints_for(profile: dict, *, base_url_override: str | None = None) -> ProviderEndpoints:
    base = (base_url_override or profile.get("base_url") or "").rstrip("/")
    health = profile.get("health") or {}
    models = str(health.get("models_url") or _join(base, "models"))
    chat = str(health.get("chat_url") or _join(base, "chat/completions"))
    models = models.replace("{base_url}", base)
    chat = chat.replace("{base_url}", base)
    return ProviderEndpoints(
        name=str(profile.get("name")),
        mailroom_provider=str(profile.get("provider")),
        base_url=base,
        base_url_env=str(profile.get("base_url_env") or ""),
        api_key_env=profile.get("api_key_env"),
        models_url=models,
        chat_url=chat,
        default_model=str(profile.get("default_model") or ""),
        requires_api_key=bool(profile.get("requires_api_key")),
    )


def load_endpoints(name: str, *, base_url_override: str | None = None) -> ProviderEndpoints:
    return endpoints_for(load_profile(name), base_url_override=base_url_override)


def _dotenv_profile() -> str:
    """``SANDBOX_PROFILE`` from the sandbox ``.env`` files, without touching ``os.environ``.

    The CLI resolves its default at parser-build time, before any ``.env`` is
    loaded; reading the file here keeps an existing ``SANDBOX_PROFILE=ollama``
    opt-out working. Same precedence as ``load_dotenv(override=False)``.
    """
    from dotenv import dotenv_values

    from mailroom_sandbox.paths import dotenv_files

    for path in dotenv_files():
        value = (dotenv_values(path).get("SANDBOX_PROFILE") or "").strip()
        if value:
            return value
    return ""


def default_profile() -> str:
    """Active default: real env ``SANDBOX_PROFILE``, then ``.env``, then ``DEFAULT_PROFILE``."""
    return (os.environ.get("SANDBOX_PROFILE") or "").strip() or _dotenv_profile() or DEFAULT_PROFILE


def modal_gateway_url(profile: dict) -> str | None:
    """Deterministic endpoint for a deployed Modal app, when known.

    Same contract as ``RunSpec.engine.base_url``: the Modal workspace *slug*
    plus the app name. Returns None for non-Modal profiles or when
    ``MODAL_WORKSPACE`` is unset — the operator then exports the URL printed by
    ``modal deploy`` (an unset URL must stay unset, never fall back to
    localhost, or a Modal run silently probes the wrong server).
    """
    if str(profile.get("name") or "") != "modal-vllm":
        return None
    workspace = (os.environ.get("MODAL_WORKSPACE") or "").strip()
    if not workspace:
        return None
    app = (os.environ.get("MODAL_VLLM_APP_NAME") or "sandbox-vllm").strip() or "sandbox-vllm"
    return f"https://{workspace}--{app}-serve.modal.run/v1"


def available_profiles() -> list[str]:
    names = list_profiles()
    # Stable documented order first, then any extras.
    ordered = [n for n in KNOWN_PROFILES if n in names]
    ordered.extend(n for n in names if n not in ordered)
    return ordered
