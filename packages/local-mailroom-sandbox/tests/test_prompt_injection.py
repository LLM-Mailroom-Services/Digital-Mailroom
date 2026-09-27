"""Runtime prompt injection must reach Family A specialists (SAND-027-3).

Preflight imports ``llm.prompts.prompt_templates()``, which binds
``from llm.prompts import get_managed_prompt`` inside each Family A
specialist module. Patching only ``llm.prompts.get_managed_prompt`` would
leave those bindings on vendor/Langfuse production text — the Modal + vLLM
specialist evals would not run eval-environment frozen v1.
"""

from __future__ import annotations

import pytest

from mailroom_sandbox.prompt_registry import (
    apply_runtime_overrides,
    deactivate_runtime_overrides,
)


@pytest.fixture
def restore_overrides():
    deactivate_runtime_overrides()
    yield
    deactivate_runtime_overrides()


def test_family_a_import_binding_sees_override(restore_overrides):
    pytest.importorskip("langchain_core")
    import mailroom_sandbox  # noqa: F401 — put vendor on sys.path

    import llm.prompts as llm_prompts  # type: ignore

    # Simulate preflight: import the agent module BEFORE applying overrides.
    import agents.correspondence_specialist as corr  # type: ignore

    original = corr.get_managed_prompt
    assert original is llm_prompts.get_managed_prompt or callable(original)

    pinned = "PINNED eval-environment correspondence_specialist_v1"
    patched = apply_runtime_overrides({"correspondence_specialist": pinned})
    assert "correspondence_specialist" in patched

    text, _obj = corr.get_managed_prompt("correspondence_specialist", "VENDOR DEFAULT")
    assert text == pinned
    text2, _obj2 = llm_prompts.get_managed_prompt(
        "correspondence_specialist", "VENDOR DEFAULT"
    )
    assert text2 == pinned


def test_langchain_role_and_version_keys_see_override(restore_overrides):
    pytest.importorskip("langchain_core")
    import mailroom_sandbox  # noqa: F401

    from langchain_agents.prompts import get_prompt  # type: ignore

    pinned = "PINNED eval-environment contracts_specialist_v1"
    patched = apply_runtime_overrides({"contracts_specialist": pinned})
    assert "contracts_specialist" in patched
    assert get_prompt("contracts_specialist") == pinned
    assert get_prompt("contracts_specialist_v33") == pinned
