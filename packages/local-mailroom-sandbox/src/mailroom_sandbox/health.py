"""Reachability probes for local OpenAI-compatible servers."""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict

import httpx

from mailroom_sandbox.overlay import load_profile
from mailroom_sandbox.providers import endpoints_for


@dataclass
class ProbeResult:
    ok: bool
    name: str
    url: str
    detail: str
    models: list[str] | None = None
    json_object_ok: bool | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _headers(profile: dict) -> dict[str, str]:
    env_name = profile.get("api_key_env")
    headers = {"Content-Type": "application/json"}
    if env_name:
        key = os.environ.get(str(env_name), "").strip()
        if key:
            headers["Authorization"] = f"Bearer {key}"
    return headers


def _effective_base_url(profile: dict) -> str | None:
    """The environment override for the profile's base URL, when set.

    A deployed Modal endpoint lives in ``VLLM_BASE_URL`` while the profile's
    static ``base_url`` stays localhost — the health probe must follow the
    env override or it reports on the wrong server (DMR-048).
    """
    env_name = str(profile.get("base_url_env") or "").strip()
    if env_name:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return None


def probe_models(profile: dict, *, timeout: float = 3.0) -> ProbeResult:
    endpoints = endpoints_for(profile, base_url_override=_effective_base_url(profile))
    url = endpoints.models_url
    try:
        resp = httpx.get(url, headers=_headers(profile), timeout=timeout)
        if resp.status_code >= 400:
            return ProbeResult(False, profile.get("name", "?"), url, f"HTTP {resp.status_code}")
        payload = resp.json()
        models = []
        data = payload.get("data") if isinstance(payload, dict) else payload
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("id"):
                    models.append(str(item["id"]))
                elif isinstance(item, str):
                    models.append(item)
        return ProbeResult(True, profile.get("name", "?"), url, "ok", models=models)
    except httpx.HTTPError as exc:
        return ProbeResult(False, profile.get("name", "?"), url, f"{type(exc).__name__}: {exc}")


def probe_chat(profile: dict, *, timeout: float = 8.0, json_object: bool = True) -> ProbeResult:
    endpoints = endpoints_for(profile, base_url_override=_effective_base_url(profile))
    url = endpoints.chat_url
    model = profile.get("default_model") or "local"
    body: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Reply with json only."},
            {"role": "user", "content": 'Return json {"ok": true}'},
        ],
        "max_tokens": 16,
        "temperature": 0,
    }
    if json_object:
        body["response_format"] = {"type": "json_object"}
    try:
        resp = httpx.post(url, headers=_headers(profile), json=body, timeout=timeout)
        if resp.status_code >= 400:
            # Retry without json_object so we can report the structured-output gap.
            if json_object:
                retry = probe_chat(profile, timeout=timeout, json_object=False)
                retry.json_object_ok = False
                retry.detail = f"json_object rejected ({resp.status_code}); plain chat: {retry.detail}"
                return retry
            return ProbeResult(False, profile.get("name", "?"), url, f"HTTP {resp.status_code}")
        return ProbeResult(
            True,
            profile.get("name", "?"),
            url,
            "ok",
            json_object_ok=json_object,
        )
    except httpx.HTTPError as exc:
        return ProbeResult(False, profile.get("name", "?"), url, f"{type(exc).__name__}: {exc}")


def health_check(profile_name: str) -> dict:
    profile = load_profile(profile_name)
    override = _effective_base_url(profile)
    models = probe_models(profile)
    chat = probe_chat(profile) if models.ok else ProbeResult(
        False, profile_name, endpoints_for(profile, base_url_override=override).chat_url, "skipped (models probe failed)"
    )
    return {
        "profile": profile_name,
        "ok": models.ok and chat.ok,
        "models": models.as_dict(),
        "chat": chat.as_dict(),
    }


def local_llm_available() -> bool:
    return os.environ.get("SANDBOX_LOCAL_LLM", "").strip() in {"1", "true", "yes"}
