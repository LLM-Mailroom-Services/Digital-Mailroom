"""Make the LangChain agents send the RESOLVED provider's API key (SAND-038).

The vendored ``langchain_agents.base_agent.BaseAgent.__init__`` defaults
``self.api_key`` to ``OPENROUTER_API_KEY`` before the provider is resolved, and
``llm()`` prefers ``self.api_key`` over ``provider.api_key_env``. With an
OpenRouter key in ``.env``, every LangChain specialist (contracts, merger) sent
it to the Modal vLLM endpoint and 401'd on every row (SAND-37 grid,
2026-09-30). The file is drift-guarded, so this wraps ``__init__`` instead:
when no ``api_key`` is passed explicitly, the eager default is cleared and
``llm()`` falls through to ``provider.api_key_env`` — ``OPENROUTER_API_KEY``
for openrouter, ``VLLM_API_KEY`` for vllm, the keyless placeholder for ollama.
An explicit ``api_key=`` argument still wins.
"""

from __future__ import annotations

import functools
import logging

_log = logging.getLogger("mailroom_sandbox.provider_credentials")

_MARK = "_sandbox_provider_credentials"


def apply_provider_credentials() -> bool:
    """Install the ``BaseAgent.__init__`` wrapper (idempotent).

    Returns True when the wrapper is (already) installed. No-ops when the
    vendored agent module is unavailable (e.g. the pipeline extra is not
    installed).
    """
    try:
        from langchain_agents import base_agent  # type: ignore
    except Exception as exc:  # noqa: BLE001 — optional (pipeline extra)
        _log.debug(
            "langchain_agents.base_agent unavailable — credential fix skipped: %s",
            exc,
        )
        return False

    cls = getattr(base_agent, "BaseAgent", None)
    if cls is None:
        return False
    if getattr(cls.__init__, _MARK, False):
        return True
    original = cls.__init__

    @functools.wraps(original)
    def __init__(self, model=None, api_key=None, *args, **kwargs):
        original(self, model, api_key, *args, **kwargs)
        if not api_key:
            self.api_key = ""

    setattr(__init__, _MARK, True)
    cls.__init__ = __init__
    _log.info("LangChain agents now resolve API keys from the active provider")
    return True
