"""SAND-018: the LangChain agent timeout must honor ``run_limits``.

The vendored ``langchain_agents.base_agent`` hardcodes ``timeout=120`` and is
drift-guarded.  A bf16 L4 specialist generation can exceed that, so the call
ladders through the retry contract.  The harness installs a ``ChatOpenAI``
subclass carrying the taxonomy pin instead of editing the vendored file.
"""

from __future__ import annotations

import pytest


def test_llm_timeout_noop_without_value(monkeypatch):
    import mailroom_sandbox.llm_timeout as lt

    monkeypatch.setattr(lt, "_APPLIED", None)
    assert lt.apply_llm_timeout(None) is False
    assert lt.apply_llm_timeout(0) is False
    assert lt.applied_timeout() is None


def test_llm_timeout_override_forces_client_timeout(monkeypatch):
    import mailroom_sandbox.llm_timeout as lt

    base_agent = pytest.importorskip("langchain_agents.base_agent")
    original = base_agent.ChatOpenAI
    monkeypatch.setattr(lt, "_APPLIED", None)
    monkeypatch.setattr(base_agent, "ChatOpenAI", original)

    assert lt.apply_llm_timeout(600) is True
    assert lt.applied_timeout() == 600

    client = base_agent.ChatOpenAI(
        model="m",
        api_key="x",
        base_url="http://127.0.0.1:1/v1",
        timeout=120,
    )
    got = getattr(client, "request_timeout", None)
    if got is None:
        got = getattr(client, "timeout", None)
    assert float(got) == 600.0


def test_activate_wires_run_limits_timeout(monkeypatch):
    """``runtime.activate`` must push ``run_limits`` into the agent client."""
    import mailroom_sandbox.llm_timeout as lt
    from mailroom_sandbox import runtime

    monkeypatch.setattr(lt, "_APPLIED", None)
    runtime.activate("ollama")
    assert lt.applied_timeout() == 600.0