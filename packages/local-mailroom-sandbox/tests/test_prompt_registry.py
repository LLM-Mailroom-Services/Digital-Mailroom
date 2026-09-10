"""Prompt registry tests (DMR-027) — network-free."""

from __future__ import annotations

import pytest

import mailroom_sandbox.prompt_registry as pr
from mailroom_sandbox.job.spec import PromptRef


@pytest.fixture
def variant_dir(tmp_path, monkeypatch):
    (tmp_path / "judge_local_v0.txt").write_text("JUDGE PROMPT", encoding="utf-8")
    monkeypatch.setattr(pr, "prompts_dir", lambda: tmp_path)
    return tmp_path


def test_agents_surface():
    names = pr.agent_prompt_names()
    assert "sorter" in names
    assert "judge-classification" in names
    assert "relations" in names


def test_local_variants_and_resolve(variant_dir):
    assert "judge_local_v0" in pr.local_variants()
    resolved = pr.resolve_prompt("judge", PromptRef(source="local", file="judge_local_v0"))
    assert resolved["source"] == "local"
    assert resolved["text"] == "JUDGE PROMPT"
    assert len(resolved["sha256"]) == 64


def test_code_default():
    resolved = pr.resolve_prompt("sorter", PromptRef(source="code-default"))
    assert resolved["source"] == "code-default"
    assert resolved["text"] is None
    assert resolved["name"].startswith("mailroom-")


def test_langfuse_offline_requires_version():
    with pytest.raises(RuntimeError):
        pr.resolve_prompt("sorter", PromptRef(source="langfuse", name="mailroom-sorter"), offline=True)
    got = pr.resolve_prompt("sorter", PromptRef(source="langfuse", name="mailroom-sorter", version=3), offline=True)
    assert got["version"] == 3 and got["offline"] is True


def test_prompt_lock_block_rejects_unknown_agent():
    with pytest.raises(KeyError):
        pr.prompt_lock_block({"agents": {"extract": {"source": "code-default"}}}, offline=True)


def test_apply_runtime_overrides_no_crash():
    # Neither llm.prompts nor langchain_agents is necessarily importable in
    # the test env; the override should degrade to [] without raising.
    result = pr.apply_runtime_overrides({"sorter": "X", "judge": "Y"})
    assert isinstance(result, list)