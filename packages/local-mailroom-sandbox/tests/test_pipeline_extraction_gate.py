"""The pipeline extraction gate: spec, lock, registration and the sorter-subclass handoff."""
from __future__ import annotations

import pytest

from mailroom_sandbox import decision_backends as db
from mailroom_sandbox.job.spec import RunSpec, spec_hash

GATE = {"model": "openai/gpt-6-luna-decisions", "questions": "extraction_gate_v1.3.0"}


def _spec(**kw):
    """A pipeline run spec."""
    return RunSpec.model_validate({"task": "pipeline", "profile": "openrouter", **kw})


def test_spec_block_is_pipeline_only_and_hashed_only_when_set():
    """The block hashes only when set and is refused outside task: pipeline."""
    plain, gated = _spec(), _spec(extraction_gate=GATE)
    assert spec_hash(plain) != spec_hash(gated)
    assert "extraction_gate" not in plain.model_dump(exclude_none=True)
    with pytest.raises(ValueError, match="reviews pipeline extractions"):
        RunSpec.model_validate({"task": "specialist", "extraction_gate": GATE})
    with pytest.raises(ValueError, match="not a Decisions-API model"):
        _spec(extraction_gate={**GATE, "model": "openai/gpt-5"})


def test_lock_freezes_the_question_set():
    """Preflight freezes the gate question set by content and hash."""
    from mailroom_sandbox.job.preflight import _extraction_gate_lock

    block = _extraction_gate_lock(_spec(extraction_gate=GATE))
    assert block["question_set"]["kind"] == db.EXTRACTION_GATE
    assert len(block["questions_sha256"]) == 64
    with pytest.raises(ValueError, match="not an extraction_gate question set"):
        _extraction_gate_lock(_spec(extraction_gate={**GATE, "questions": "reviewer_decisions_v3.1.0"}))


def test_backend_sends_the_sorter_subclass_and_never_a_label(monkeypatch):
    """The gate uses the handoff's doc_subclass only; absent stays absent."""
    seen = []
    monkeypatch.setattr(db, "decide_extraction",
                        lambda doc_text, handoff, **kw: seen.append(kw["subclass"]) or {"verdict": "accept"})
    qset = db.load_question_set("extraction_gate_v1.3.0")
    gate = db.extraction_gate_backend(GATE["model"], qset)
    out = gate("text", {"doc_type": "insurance_claim", "doc_subclass": "inpatient", "fields": {}})
    assert seen == ["inpatient"] and out["question_set"] == "1.3.0" and out["model"] == GATE["model"]
    gate("text", {"doc_type": "insurance_claim", "fields": {}})
    assert seen[-1] is None
    with pytest.raises(ValueError):
        db.extraction_gate_backend("openai/gpt-5", qset)


def test_activation_registers_and_clears_the_gate(monkeypatch):
    """A locked gate block is registered; without one the hook is cleared; an old mailroom refuses."""
    from mailroom_sandbox import runtime

    registered = []
    import sys
    import types

    fake = types.ModuleType("agents.extraction_gate")
    fake.register_extraction_gate = registered.append
    monkeypatch.setitem(sys.modules, "agents.extraction_gate", fake)
    block = {**GATE, "question_set": db.load_question_set("extraction_gate_v1.3.0")}
    runtime._register_extraction_gate(runtime._extraction_gate_backend(block))
    runtime._register_extraction_gate(runtime._extraction_gate_backend(None))
    assert callable(registered[0]) and registered[1] is None
    with pytest.raises(ValueError, match="frozen question set"):
        runtime._extraction_gate_backend({**GATE})
    monkeypatch.setitem(sys.modules, "agents.extraction_gate", None)
    with pytest.raises(RuntimeError, match="no extraction-gate hook"):
        runtime._register_extraction_gate(lambda *a: {})
    runtime._register_extraction_gate(None)  # nothing to clear: fine


def test_gate_runs_count_as_openrouter_spend():
    """A gate block puts the run under the OpenRouter key checks and reserve."""
    from mailroom_sandbox.job.spend import uses_openrouter

    assert uses_openrouter({"engine": {"kind": "vllm"}, "extraction_gate": {"model": GATE["model"]}})
    assert not uses_openrouter({"engine": {"kind": "vllm"}})


def test_mock_runs_get_an_offline_gate(monkeypatch):
    """A job.mock run never reaches the Decisions API through the gate."""
    from mailroom_sandbox import runtime

    monkeypatch.setattr(db, "decide_extraction", lambda *a, **k: pytest.fail("mock gate called the Decisions API"))
    block = {**GATE, "question_set": db.load_question_set("extraction_gate_v1.3.0")}
    gate = runtime._extraction_gate_backend(block, mock=True)
    answer = gate("text", {"doc_type": "insurance_claim", "fields": {}})
    assert answer["mock"] is True and answer["verdict"] == "accept" and answer["doc_type"] == "insurance_claim"


def test_the_gate_model_is_in_the_api_budget():
    """A vLLM pipeline with a Decisions gate still bills the API: the cap check must see the gate."""
    from mailroom_sandbox.job import api_budget

    lock = {"task": "pipeline", "engine": {"kind": "vllm", "model": "Qwen/Qwen3-8B"},
            "extraction_gate": {"model": GATE["model"]}, "job": {"mock": False}}
    assert api_budget.api_models(lock) == [GATE["model"]]
    assert any("api_cost_cap_usd" in e for e in api_budget.budget_errors(lock))
    spec = _spec(extraction_gate=GATE)
    assert GATE["model"] in api_budget.spec_api_models(spec)
