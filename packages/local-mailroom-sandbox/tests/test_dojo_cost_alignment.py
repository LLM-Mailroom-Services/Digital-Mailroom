"""The sandbox's pre-priced serving record follows the dojo's repaired usage rules.

A cost written by ``record_from_run`` is authoritative in the dojo, so the sandbox
must apply the same gates the dojo applies when it derives a cost itself:
dojo 0.24.2 (an unobserved request makes the run cost unknown) and DMR-113
(explicit zero usage is observed; an all-zero priced run costs 0.0).
"""

from __future__ import annotations

import pytest
from llm_dojo_scoring.serving import normalize_serving_record

from mailroom_sandbox.job.metrics import record_from_run
from mailroom_sandbox.job.usage_capture import usage_from_openai_response

MODEL = "Qwen/Qwen3-8B"  # priced in the sandbox table


def _record(items, model=MODEL):
    return record_from_run(
        run_id="r", spec_hash="h", task="pipeline", profile="openrouter", model=model,
        prompt_version="v", dataset_fingerprint="f", items=items,
    )


def test_complete_usage_is_priced():
    rec = _record([{"ok": True, "prompt_tokens": 1000, "completion_tokens": 100}] * 2)
    assert rec["estimated_cost_usd"] > 0 and "usage_unobserved_items" not in rec


def test_one_unobserved_ok_item_makes_the_cost_unknown():
    rec = _record([{"ok": True, "prompt_tokens": 1000, "completion_tokens": 100}, {"ok": True}])
    assert "estimated_cost_usd" not in rec and rec["usage_unobserved_items"] == 1
    assert rec["total_tokens"] == 1100  # the tokens that were observed are still reported


def test_failed_items_without_a_response_do_not_block_the_estimate():
    rec = _record([{"ok": True, "prompt_tokens": 1000, "completion_tokens": 100}, {"ok": False, "error": "timeout"}])
    assert rec["estimated_cost_usd"] > 0


def test_one_component_usage_is_observed():
    rec = _record([{"ok": True, "prompt_tokens": 1000}, {"ok": True, "completion_tokens": 50}])
    assert rec["estimated_cost_usd"] > 0


def test_explicit_zero_usage_on_a_priced_model_costs_a_known_zero():
    rec = _record([{"ok": True, "prompt_tokens": 0, "completion_tokens": 0}] * 3)
    assert rec["estimated_cost_usd"] == 0.0 and rec["cost_per_document"] == 0.0


@pytest.mark.parametrize("items", [
    [{"ok": True}, {"ok": True}],  # nothing observed
    [{"ok": True, "prompt_tokens": 0, "completion_tokens": 0}, {"ok": True}],  # zero + unobserved
])
def test_missing_usage_never_becomes_zero(items):
    assert "estimated_cost_usd" not in _record(items)


def test_zero_usage_on_an_unpriced_model_stays_unknown():
    assert "estimated_cost_usd" not in _record([{"ok": True, "prompt_tokens": 0, "completion_tokens": 0}], model="nope/unpriced")


@pytest.mark.parametrize("items", [
    [{"ok": True, "prompt_tokens": 1000, "completion_tokens": 100}] * 2,
    [{"ok": True, "prompt_tokens": 1000, "completion_tokens": 100}, {"ok": True}],
    [{"ok": True, "prompt_tokens": 0, "completion_tokens": 0}],
])
def test_dojo_reads_the_same_cost_the_sandbox_wrote(items):
    rec = _record(items)
    run = normalize_serving_record(rec)
    assert run.estimated_cost_usd == rec.get("estimated_cost_usd")


@pytest.mark.parametrize(("usage", "expected"), [
    ({"prompt_tokens": 0, "completion_tokens": 0}, {"prompt_tokens": 0, "completion_tokens": 0}),
    ({"prompt_tokens": 0, "input_tokens": 7, "completion_tokens": 3}, {"prompt_tokens": 0, "completion_tokens": 3}),
    ({"input_tokens": 7, "output_tokens": 0}, {"prompt_tokens": 7, "completion_tokens": 0}),
    ({}, {}),
])
def test_openai_usage_keeps_an_explicit_zero(usage, expected):
    class _Resp:
        pass

    resp = _Resp()
    resp.usage = usage
    assert usage_from_openai_response(resp) == expected
