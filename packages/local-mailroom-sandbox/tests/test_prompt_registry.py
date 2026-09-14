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


def test_langfuse_floating_label_falls_back_without_key(monkeypatch):
    """DMR-052 G28: no Langfuse credentials + a floating label locks the code
    default (mirroring the mailroom runtime's soft fallback); a PINNED
    version still refuses (silent prompt swaps are never acceptable)."""
    monkeypatch.setattr(pr, "_langfuse_client", lambda: None)
    got = pr.resolve_prompt("sorter", PromptRef(source="langfuse", name="mailroom-sorter"))
    assert got["source"] == "code-default"
    assert got["text"] is None
    with pytest.raises(RuntimeError, match="pinned version cannot fall back"):
        pr.resolve_prompt(
            "sorter",
            PromptRef(source="langfuse", name="mailroom-sorter", version=7),
        )


def test_prompt_lock_block_rejects_unknown_agent():
    with pytest.raises(KeyError):
        pr.prompt_lock_block({"agents": {"extract": {"source": "code-default"}}}, offline=True)


def test_apply_runtime_overrides_no_crash():
    # Neither llm.prompts nor langchain_agents is necessarily importable in
    # the test env; the override should degrade to [] without raising.
    result = pr.apply_runtime_overrides({"sorter": "X", "judge": "Y"})
    assert isinstance(result, list)


def test_apply_runtime_overrides_warns_on_unimportable_family(caplog, monkeypatch):
    # hub#40: an unimportable vendor tree must log a warning naming the
    # agents whose overrides could not be applied — never silent.
    import sys

    monkeypatch.setitem(sys.modules, "langchain_agents.prompts", None)
    monkeypatch.setitem(sys.modules, "llm.prompts", None)
    with caplog.at_level("WARNING", logger="mailroom_sandbox.prompt_registry"):
        result = pr.apply_runtime_overrides({"sorter": "X", "judge": "Y"})
    assert result == []
    assert "prompt overrides not applied" in caplog.text
    assert "sorter" in caplog.text and "judge" in caplog.text


def test_agent_prompt_names_warns_on_static_roster_degradation(caplog, monkeypatch):
    # hub#40: the agent surface must not silently degrade to the static
    # roster when the vendored llm.prompts tree is unimportable.
    import sys

    monkeypatch.setitem(sys.modules, "llm.prompts", None)
    with caplog.at_level("WARNING", logger="mailroom_sandbox.prompt_registry"):
        names = pr.agent_prompt_names()
    assert names  # static roster still answers
    assert "agent surface degraded to the static roster" in caplog.text


def test_runner_raises_when_pinned_override_unpatched(tmp_path, monkeypatch, job_data_dir):
    # hub#40: a lock pinning local/langfuse text whose patch cannot apply
    # must fail the run loudly instead of executing code-default prompts.
    import json

    from mailroom_sandbox.job import preflight, runner
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import DatasetSpec, RunSpec, run_dir

    path = tmp_path / "f.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(2):
            fh.write(
                json.dumps(
                    {"id": f"d{i}", "filename": f"{i}.txt", "doc_text": f"t{i}",
                     "expected": "contract", "expected_subclass": "service"}
                )
                + "\n"
            )
    spec = RunSpec(
        run_id="run-ovr",
        task="sorter",
        dataset=DatasetSpec(local_path=f"file://{path}", limit=2),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        job={"mock": True},
    )
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    store = RunStore(run_dir(report["run_id"]))
    store.write_prompt_lock(
        {
            "default": {"source": "code-default"},
            "agents": {
                "sorter": {
                    "source": "local",
                    "file": "sorter_x",
                    "version": None,
                    "label": None,
                    "text": "PINNED SORTER TEXT",
                    "prompt_text_sha": "abc123",
                }
            },
        }
    )
    monkeypatch.setattr(
        "mailroom_sandbox.prompt_registry.apply_runtime_overrides",
        lambda texts: [],
    )
    with pytest.raises(RuntimeError, match="prompt overrides not applied for.*sorter"):
        runner.run_job(store, mock=None)