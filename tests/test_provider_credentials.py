"""SAND-038: LangChain specialists must send the RESOLVED provider's key.

The vendored ``langchain_agents.base_agent.BaseAgent.__init__`` defaults
``self.api_key`` to ``OPENROUTER_API_KEY`` before the provider is resolved, and
``llm()`` prefers that over ``provider.api_key_env``. With an OpenRouter key in
``.env``, contracts + merger sent it to the Modal vLLM endpoint and 401'd on
every row (SAND-37 grid, 2026-09-30). The file is drift-guarded, so the
harness installs the fix at activation instead.
"""

from __future__ import annotations

import pytest

OR_KEY = "sk-or-test-openrouter-key"
VLLM_KEY = "test-vllm-token"


@pytest.fixture
def keyed_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", OR_KEY)
    monkeypatch.setenv("VLLM_API_KEY", VLLM_KEY)
    monkeypatch.setenv("VLLM_BASE_URL", "https://example.invalid/v1")
    return monkeypatch


def _sent_key(agent) -> str:
    return agent.llm().openai_api_key.get_secret_value()


@pytest.mark.parametrize(
    "module_name, cls_name",
    [
        ("agents.contracts_specialist", "ContractsSpecialist"),
        ("agents.merger_agreement_specialist", "MergerAgreementSpecialist"),
    ],
)
def test_vllm_profile_sends_vllm_key_not_openrouter(keyed_env, module_name, cls_name):
    import importlib

    from mailroom_sandbox import runtime

    runtime.activate("modal-vllm")
    cls = getattr(importlib.import_module(module_name), cls_name)
    assert _sent_key(cls()) == VLLM_KEY


def test_openrouter_profile_still_sends_openrouter_key(keyed_env):
    from mailroom_sandbox import runtime

    runtime.activate("openrouter")
    from agents.contracts_specialist import ContractsSpecialist

    assert _sent_key(ContractsSpecialist()) == OR_KEY


def test_explicit_api_key_argument_still_wins(keyed_env):
    from mailroom_sandbox import runtime

    runtime.activate("modal-vllm")
    from agents.contracts_specialist import ContractsSpecialist

    assert _sent_key(ContractsSpecialist(api_key="explicit")) == "explicit"


def test_apply_is_idempotent():
    from mailroom_sandbox.provider_credentials import apply_provider_credentials

    assert apply_provider_credentials() is True
    assert apply_provider_credentials() is True
