"""Named local serving profiles and URL construction (no sockets)."""

from __future__ import annotations

from dataclasses import dataclass

from mailroom_sandbox.overlay import load_profile, list_profiles


KNOWN_PROFILES = ("ollama", "vllm-local", "vllm-remote", "modal-vllm", "llamacpp", "lmstudio", "openrouter")

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


def available_profiles() -> list[str]:
    names = list_profiles()
    # Stable documented order first, then any extras.
    ordered = [n for n in KNOWN_PROFILES if n in names]
    ordered.extend(n for n in names if n not in ordered)
    return ordered
