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
    env override or it reports on the wrong server (DMR-048). When the env is
    unset but ``MODAL_WORKSPACE`` is known, derive the same gateway URL the run
    spec uses instead of probing localhost.
    """
    env_name = str(profile.get("base_url_env") or "").strip()
    if env_name:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    from mailroom_sandbox.providers import modal_gateway_url

    return modal_gateway_url(profile)


def probe_models(profile: dict, *, timeout: float = 3.0, expect_json: bool = True) -> ProbeResult:
    """GET the profile's models URL and report reachability.

    A model endpoint must answer JSON; a non-JSON 2xx body is reported as a failure
    instead of raising. Liveness endpoints (Langfuse, Phoenix) pass
    ``expect_json=False``: any 2xx is healthy and the body is ignored.
    """
    endpoints = endpoints_for(profile, base_url_override=_effective_base_url(profile))
    url = endpoints.models_url
    try:
        resp = httpx.get(url, headers=_headers(profile), timeout=timeout)
        if not resp.is_success:
            return ProbeResult(False, profile.get("name", "?"), url, f"HTTP {resp.status_code}")
        if not expect_json:
            return ProbeResult(True, profile.get("name", "?"), url, "ok")
        try:
            payload = resp.json()
        except ValueError:
            return ProbeResult(False, profile.get("name", "?"), url, f"HTTP {resp.status_code} but non-JSON body")
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


def explain_modal_timeout(profile: dict, result: ProbeResult) -> bool:
    """Say why a Modal endpoint timed out; True when the app status explains it, not proof of startup or health.

    True covers a deployed app with containers up (booting or hung) and one with no
    container yet (queued for a GPU or starting). False leaves the timeout a failure.

    A request to a scale-to-zero app waits on a GPU, so a timeout alone reads like an
    outage. The app listing answers without touching the endpoint. ``result.detail`` keeps
    the raw error when the listing is unavailable.
    """
    if str(profile.get("name") or "") != "modal-vllm" or "Timeout" not in result.detail:
        return False
    from mailroom_sandbox.services._exec import ServiceError
    from mailroom_sandbox.services.modal_cli import app_status, vllm_app

    app = vllm_app()
    try:
        status = app_status(app)
    except ServiceError:
        return False
    tasks = status["tasks"]
    if not status["deployed"]:
        result.detail = f"{app} is not deployed; run `sandbox modal deploy` ({result.detail})"
        return False
    if tasks is None:
        return False
    if tasks:
        # The app listing cannot tell a booting engine from a hung one; say both.
        result.detail = (f"{app}: {tasks} container(s) up but not answering: engine still booting "
                         f"(billing), or hung; if it persists, see `sandbox modal logs`")
    else:
        result.detail = f"{app}: no container yet, queued for a GPU or starting (not billing); see `sandbox modal logs`"
    return True


def probe_chat(profile: dict, *, timeout: float = 8.0, json_object: bool = True) -> ProbeResult:
    endpoints = endpoints_for(profile, base_url_override=_effective_base_url(profile))
    url = endpoints.chat_url
    from mailroom_sandbox.overlay import resolve_served_vllm_model, serving_family

    # VLLM_MODEL pins the GPU half of a hybrid run; an API profile keeps its own id.
    served = resolve_served_vllm_model() if serving_family(profile) == "vllm" else None
    model = served or profile.get("default_model") or "local"
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


def _api_key(env_name: str) -> str:
    key = os.environ.get(env_name, "").strip()
    return "" if key == "mock-key" else key


def probe_openrouter_key(
    base_url: str | None = None, *, key_env: str = "OPENROUTER_API_KEY", timeout: float = 5.0, name: str = "openrouter"
) -> ProbeResult:
    """GET OpenRouter's ``/key`` and report whether the API key is accepted.

    OpenRouter's ``/models`` listing is public, so it proves reachability but
    not the credential; ``/key`` answers 401 for a bad key and returns the
    key's label, usage and limit for a good one. The key itself is never
    echoed: only the label OpenRouter shows for it.
    """
    base = (base_url or os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1").rstrip("/")
    url = f"{base}/key"
    key = _api_key(key_env)
    if not key:
        return ProbeResult(False, name, url, f"{key_env} is not set (export it or add it to .env)")
    try:
        resp = httpx.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
    except httpx.HTTPError as exc:
        return ProbeResult(False, name, url, f"{type(exc).__name__}: {exc}")
    if resp.status_code in (401, 403):
        return ProbeResult(False, name, url, f"HTTP {resp.status_code}: {key_env} was rejected (revoked or mistyped)")
    if not resp.is_success:
        return ProbeResult(False, name, url, f"HTTP {resp.status_code}")
    try:
        data = resp.json().get("data")
    except (ValueError, AttributeError):
        return ProbeResult(False, name, url, f"HTTP {resp.status_code} but non-JSON body")
    if not isinstance(data, dict) or not data:
        # A missing, empty or non-object `data` would otherwise read as "key accepted".
        return ProbeResult(False, name, url, f"HTTP {resp.status_code} but no key record in `data`")
    usage, limit, remaining = data.get("usage"), data.get("limit"), data.get("limit_remaining")
    parts = [f"key accepted ({data.get('label') or 'unlabelled'})"]
    if isinstance(limit, (int, float)) and isinstance(remaining, (int, float)):
        reset = f" {data['limit_reset']}" if data.get("limit_reset") else ""
        parts.append(f"${remaining:.2f} of ${limit:.2f}{reset} limit left")
    else:
        parts.append("no credit limit")
    if isinstance(usage, (int, float)):
        parts.append(f"lifetime usage ${usage:.4f}")
    if data.get("is_free_tier"):
        parts.append("free tier")
    if isinstance(remaining, (int, float)) and remaining <= 0:
        # OpenRouter answers 402 for every paid request until the limit resets.
        return ProbeResult(False, name, url, ", ".join(parts) + "; credit limit exhausted")
    return ProbeResult(True, name, url, ", ".join(parts))


def missing_modal_endpoint(profile: dict) -> bool:
    """True when the Modal profile has no endpoint to probe (not deployed/exported)."""
    return str(profile.get("name") or "") == "modal-vllm" and _effective_base_url(profile) is None


def health_check(profile_name: str) -> dict:
    """Probe a profile's models and chat endpoints and report ``ok`` only when both succeed.

    A ``modal-vllm`` profile with no endpoint (neither ``VLLM_BASE_URL`` nor ``MODAL_WORKSPACE``) fails without probing, so localhost is never reported as the Modal endpoint.
    """
    profile = load_profile(profile_name)
    if missing_modal_endpoint(profile):
        # Never report a localhost probe as the Modal endpoint's health: the
        # profile's static URL is only a parity fallback. Fail with the fix.
        detail = "set VLLM_BASE_URL (or MODAL_WORKSPACE) after `modal deploy`"
        models = ProbeResult(False, profile_name, "(VLLM_BASE_URL unset)", detail)
        chat = ProbeResult(
            False, profile_name, "(VLLM_BASE_URL unset)", "skipped (models probe failed)"
        )
        return {
            "profile": profile_name,
            "ok": False,
            "models": models.as_dict(),
            "chat": chat.as_dict(),
        }
    override = _effective_base_url(profile)
    if str(profile.get("provider")) == "openrouter":
        return _openrouter_health(profile, profile_name, override)
    models = probe_models(profile)
    explain_modal_timeout(profile, models)
    chat = probe_chat(profile) if models.ok else ProbeResult(
        False, profile_name, endpoints_for(profile, base_url_override=override).chat_url, "skipped (models probe failed)"
    )
    return {
        "profile": profile_name,
        "ok": models.ok and chat.ok,
        "models": models.as_dict(),
        "chat": chat.as_dict(),
    }


def _openrouter_health(profile: dict, profile_name: str, override: str | None) -> dict:
    """Key first, then models and a one-shot chat: a bad key never spends a request."""
    base = endpoints_for(profile, base_url_override=override).base_url
    key = probe_openrouter_key(base, key_env=str(profile.get("api_key_env") or "OPENROUTER_API_KEY"), name=profile_name)
    skipped = "skipped (API key probe failed)"
    models = probe_models(profile) if key.ok else ProbeResult(False, profile_name, endpoints_for(profile, base_url_override=override).models_url, skipped)
    if models.ok and profile.get("default_model") and models.models and profile["default_model"] not in models.models:
        models = ProbeResult(False, profile_name, models.url, f"default_model {profile['default_model']} is not in the OpenRouter catalog", models=None)
    else:
        models.models = None  # the full catalog is hundreds of ids; the key/chat rows carry the signal
    chat = probe_chat(profile) if models.ok else ProbeResult(False, profile_name, endpoints_for(profile, base_url_override=override).chat_url, "skipped (models probe failed)")
    return {
        "profile": profile_name,
        "ok": key.ok and models.ok and chat.ok,
        "key": key.as_dict(),
        "models": models.as_dict(),
        "chat": chat.as_dict(),
    }


def local_llm_available() -> bool:
    return os.environ.get("SANDBOX_LOCAL_LLM", "").strip() in {"1", "true", "yes"}
