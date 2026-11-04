"""Honor ``run_limits.llm_call_timeout_seconds`` for the LangChain agents.

The vendored ``langchain_agents.base_agent`` hardcodes ``ChatOpenAI(timeout=120)``
(drift-guarded — the sandbox must not edit it). A full specialist generation on a
single L4 can exceed 120s, so the call ladders through the shared retry contract
(SAND-018). This installs a ``ChatOpenAI`` subclass whose timeout comes from the
merged taxonomy's ``run_limits``, so the overlay pin actually takes effect
without touching the vendored file.
"""

from __future__ import annotations

import logging

_log = logging.getLogger("mailroom_sandbox.llm_timeout")

_APPLIED: float | None = None


def apply_llm_timeout(seconds: float | None) -> bool:
    """Force the LangChain agents' client timeout to ``seconds`` (idempotent).

    Returns True when a subclass was (already) installed. No-ops when the value
    is unset/non-positive or the vendored agent module is unavailable (e.g. the
    pipeline extra is not installed) — the default 120s then stands.
    """
    global _APPLIED
    if not seconds or float(seconds) <= 0:
        return False
    try:
        from langchain_agents import base_agent  # type: ignore
    except Exception as exc:  # noqa: BLE001 — optional (pipeline extra)
        _log.debug(
            "langchain_agents.base_agent unavailable — timeout override skipped: %s",
            exc,
        )
        return False

    if _APPLIED == float(seconds):
        return True
    original = getattr(base_agent, "ChatOpenAI", None)
    if original is None:
        return False

    class _TimeoutChatOpenAI(original):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            kwargs["timeout"] = float(seconds)
            super().__init__(*args, **kwargs)

    _TimeoutChatOpenAI.__name__ = "ChatOpenAI"
    base_agent.ChatOpenAI = _TimeoutChatOpenAI
    _APPLIED = float(seconds)
    _log.info("LangChain agent client timeout overridden to %ss", seconds)
    return True


def applied_timeout() -> float | None:
    """The override currently installed in this process, if any."""
    return _APPLIED
