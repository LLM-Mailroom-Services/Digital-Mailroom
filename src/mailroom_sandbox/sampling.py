"""Run-scoped sampling for specialist calls.

Temperature is a literal at every vendored ``_call_structured`` call site
(``agents/*_specialist.py`` and ``langchain_agents/specialist_agents.py``,
drift-guarded). A ``temperature`` in the agent config therefore never reaches
the request unless this wrapper replaces that argument.

The Modal vLLM deployment is a plain OpenAI-compatible server. It is separate
from the LangChain specialist pipeline. Optimized sampling (``top_p``,
``top_k``, ``presence_penalty``, length re-sample) is merged into the kwargs
``llm.retry.retry_chat_completion`` posts to ``client.chat.completions.create``.
Contracts and merger, whose classes are LangChain subclasses, take that native
request when those knobs are set — this module does not call ``ChatOpenAI.bind``
or ``with_structured_output``.

``top_k`` is a vLLM extension and travels in ``extra_body``, merged with any
reasoning ``extra_body`` already on the request. A completion whose
``finish_reason`` is ``length`` is re-sampled up to ``length_retries`` times.
"""

from __future__ import annotations

import contextvars
import functools
import inspect
import json
import logging
from typing import Any, Mapping

_log = logging.getLogger("mailroom_sandbox.sampling")

_OVERRIDES: dict[str, float] = {}
_EXTRA: dict[str, dict[str, Any]] = {}  # agent → {top_p, top_k, presence_penalty, length_retries}
_PATCHED: set[str] = set()
_EXTRA_KEYS = ("top_p", "top_k", "presence_penalty", "length_retries")
# Per-agent count of length-capped completions re-sampled in this process.
LENGTH_RETRIES: dict[str, int] = {}
# Set for the duration of one structured call so the chat-completion wrapper
# knows which agent's knobs to merge. Empty outside that call.
_REQUEST: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "sandbox_modal_sampling", default=None
)

# (module, class) of every vendored ``_call_structured`` implementation.
_TARGETS: tuple[tuple[str, str], ...] = (
    ("agents.base", "BaseAgent"),
    ("langchain_agents.base_agent", "BaseAgent"),
)


def temperature_overrides(agent_knobs: Mapping[str, Any] | None) -> dict[str, float]:
    """``{agent: temperature}`` for every agent whose run-scoped knobs set one."""
    out: dict[str, float] = {}
    for agent, knobs in (agent_knobs or {}).items():
        if isinstance(knobs, Mapping) and knobs.get("temperature") is not None:
            out[str(agent)] = float(knobs["temperature"])
    return out


def extra_overrides(agent_knobs: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """``{agent: {top_p, top_k, presence_penalty, length_retries}}`` from run-scoped knobs."""
    out: dict[str, dict[str, Any]] = {}
    for agent, knobs in (agent_knobs or {}).items():
        if not isinstance(knobs, Mapping):
            continue
        extra = {k: knobs[k] for k in _EXTRA_KEYS if knobs.get(k) is not None}
        if extra:
            out[str(agent)] = extra
    return out


def chat_sampling_kwargs(extra: Mapping[str, Any]) -> dict[str, Any]:
    """OpenAI chat-completion fields. vLLM takes ``top_k`` through ``extra_body``."""
    kw: dict[str, Any] = {}
    if extra.get("top_p") is not None:
        kw["top_p"] = float(extra["top_p"])
    if extra.get("presence_penalty") is not None:
        kw["presence_penalty"] = float(extra["presence_penalty"])
    if extra.get("top_k") is not None:
        kw["extra_body"] = {"top_k": int(extra["top_k"])}
    return kw


def merge_endpoint_kwargs(kwargs: dict[str, Any], extra: Mapping[str, Any]) -> dict[str, Any]:
    """Copy ``kwargs`` with sampling fields merged in. Existing ``extra_body`` keys stay."""
    out = dict(kwargs)
    bind = chat_sampling_kwargs(extra)
    body = dict(out.get("extra_body") or {})
    body.update(bind.pop("extra_body", {}))
    if body:
        out["extra_body"] = body
    elif "extra_body" in out and not out["extra_body"]:
        out.pop("extra_body", None)
    for key, value in bind.items():
        out.setdefault(key, value)
    return out


def _is_length_finish(exc: BaseException) -> bool:
    return type(exc).__name__ == "LengthFinishReasonError" or "length limit was reached" in str(exc)


def _finish_reason(response: Any) -> str | None:
    try:
        return response.choices[0].finish_reason
    except Exception:
        return None


def _install_retry_patch() -> None:
    """Merge the active request's sampling into ``retry_chat_completion`` kwargs."""
    import llm.retry as retry_mod

    current = retry_mod.retry_chat_completion
    if getattr(current, "__sandbox_sampling__", False):
        return

    @functools.wraps(current)
    def retry_chat_completion(client, **kwargs):
        spec = _REQUEST.get()
        extra = (spec or {}).get("extra") or {}
        agent = str((spec or {}).get("agent") or "")
        if extra:
            kwargs = merge_endpoint_kwargs(kwargs, extra)
        retries = max(0, int(extra.get("length_retries") or 0))
        attempt = 0
        while True:
            response = current(client, **kwargs)
            if _finish_reason(response) != "length" or attempt >= retries:
                return response
            attempt += 1
            LENGTH_RETRIES[agent] = LENGTH_RETRIES.get(agent, 0) + 1
            _log.warning(
                "%s: runaway decode at the output cap — re-sampling (%d/%d)",
                agent, attempt, retries,
            )

    retry_chat_completion.__sandbox_sampling__ = True  # type: ignore[attr-defined]
    retry_mod.retry_chat_completion = retry_chat_completion


def _record_native_usage(self, response: Any, model: str | None) -> None:
    """Feed the OpenAI ``usage`` object into ``pipeline.limits`` for this item.

    Vendored ``agents.base._call_llm`` records after ``retry_chat_completion``.
    The native Modal path returns parsed JSON directly, so without this the
    runner's ``usage_from_pipeline()`` sees no prompt or completion tokens.
    """
    try:
        from pipeline.limits import record_usage
    except Exception as exc:  # noqa: BLE001 — mock / no vendor
        _log.debug("pipeline.limits unavailable for native usage: %s", exc)
        return
    agent = str(getattr(self, "agent_name", "") or "") or None
    try:
        record_usage(getattr(response, "usage", None), model, agent=agent)
    except Exception as exc:  # noqa: BLE001
        _log.debug("native completion usage not recorded: %s", exc)


def _native_structured_completion(self, bound, temperature: float | None) -> dict:
    """One structured extraction via ``chat.completions.create`` (no LangChain)."""
    from llm.retry import retry_chat_completion

    args = bound.arguments
    user_message = args["user_message"]
    json_schema = args.get("json_schema") or {}
    system_prompt = args.get("system_prompt")
    max_tokens = args.get("max_tokens")
    if max_tokens is None:
        max_tokens = getattr(self, "_max_tokens", None)
    if temperature is None:
        temperature = args.get("temperature")
    with_skills = getattr(self, "system_prompt_with_skills", None)
    if callable(with_skills):
        system = with_skills(system_prompt)
    elif system_prompt is not None:
        system = system_prompt
    else:
        system = self.system_prompt()
    client = getattr(self, "client", None)
    model = getattr(self, "model", None)
    if client is None:
        from llm.client import get_llm

        client, resolved = get_llm(str(getattr(self, "agent_name", "")))
        model = model or resolved
    schema_name = str(getattr(self, "agent_name", "extraction") or "extraction").replace(" ", "_")[:64]
    request: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": json_schema},
        },
    }
    if temperature is not None:
        request["temperature"] = temperature
    if max_tokens:
        request["max_tokens"] = int(max_tokens)
    response = retry_chat_completion(client, **request)
    _record_native_usage(self, response, model)
    raw = ""
    try:
        raw = response.choices[0].message.content or ""
    except Exception:
        raw = ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw, "_parse_error": True}
    if not isinstance(parsed, dict):
        return {"_raw": raw, "_parse_error": True}
    return parsed


def _wrap(original, *, native_endpoint: bool = False):
    signature = inspect.signature(original)

    @functools.wraps(original)
    def _call_structured(self, *args, **kwargs):
        name = str(getattr(self, "agent_name", ""))
        override = _OVERRIDES.get(name)
        extra = _EXTRA.get(name) or {}
        if override is None and not extra:
            return original(self, *args, **kwargs)
        bound = signature.bind(self, *args, **kwargs)
        if override is not None:
            bound.arguments["temperature"] = override
        retries = max(0, int(extra.get("length_retries") or 0))
        token = _REQUEST.set({"agent": name, "extra": dict(extra)}) if extra else None
        try:
            # Optimized knobs on a LangChain specialist go out as a native
            # chat completion. Temperature-only overrides keep the original
            # call (the LangChain pipeline is a separate stack).
            if native_endpoint and extra:
                return _native_structured_completion(self, bound, override)
            attempt = 0
            while True:
                try:
                    return original(*bound.args, **bound.kwargs)
                except Exception as exc:  # noqa: BLE001 — only the length class is retried
                    if attempt >= retries or not _is_length_finish(exc):
                        raise
                    attempt += 1
                    LENGTH_RETRIES[name] = LENGTH_RETRIES.get(name, 0) + 1
                    _log.warning(
                        "%s: runaway decode at the output cap — re-sampling (%d/%d)",
                        name, attempt, retries,
                    )
        finally:
            if token is not None:
                _REQUEST.reset(token)

    _call_structured.__sandbox_sampling__ = True  # type: ignore[attr-defined]
    return _call_structured


def apply_sampling_overrides(agent_knobs: Mapping[str, Any] | None) -> dict[str, float]:
    """Install the wrapper (once per class) and set this run's overrides.

    Last call wins: an activation without temperature knobs clears earlier
    overrides, so the call-site values stand again. Returns the active map.
    """
    _OVERRIDES.clear()
    _OVERRIDES.update(temperature_overrides(agent_knobs))
    _EXTRA.clear()
    _EXTRA.update(extra_overrides(agent_knobs))
    if not _OVERRIDES and not _EXTRA:
        return {}
    if _EXTRA:
        _install_retry_patch()
    for module_name, class_name in _TARGETS:
        key = f"{module_name}.{class_name}"
        if key in _PATCHED:
            continue
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
        except Exception as exc:  # noqa: BLE001 — optional (pipeline extra)
            _log.debug("%s unavailable — temperature override skipped: %s", key, exc)
            continue
        original = cls.__dict__.get("_call_structured")
        if original is None or getattr(original, "__sandbox_sampling__", False):
            _PATCHED.add(key)
            continue
        if "temperature" not in inspect.signature(original).parameters:
            _log.warning("%s._call_structured has no temperature parameter — not patched", key)
            continue
        cls._call_structured = _wrap(
            original, native_endpoint=module_name.startswith("langchain_agents")
        )
        _PATCHED.add(key)
    _log.info("specialist sampling overrides active: temperature %s · extra %s", _OVERRIDES, _EXTRA)
    return dict(_OVERRIDES)


def active_overrides() -> dict[str, float]:
    """The temperature overrides currently in force in this process."""
    return dict(_OVERRIDES)


def active_extra() -> dict[str, dict[str, Any]]:
    """The top_p / top_k / presence_penalty / length_retries overrides in force."""
    return {k: dict(v) for k, v in _EXTRA.items()}
