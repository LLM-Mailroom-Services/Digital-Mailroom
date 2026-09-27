"""Grant-style Modal/vLLM cost-compare parity (sandbox == dojo) — no GPU."""

from __future__ import annotations

import json

import pytest
from llm_dojo_scoring import get_suite
from llm_dojo_scoring.serving import classify_serving_kind, compare_serving, estimate_cost

from mailroom_sandbox.datasets import load_cost_compare_fixtures
from mailroom_sandbox.eval.serving_parity import (
    grant_table_row,
    score_cost_compare,
    split_serving_records,
    to_dojo_serving_record,
)
from mailroom_sandbox.job import metrics


def test_adapter_converts_ms_and_stamps_modal_kind():
    rec = to_dojo_serving_record(
        {
            "profile": "modal-vllm",
            "provider": "vllm",
            "model": "Qwen/Qwen3-8B",
            "gpu": "L4",
            "latency_ms": 1800,
            "ttft_ms": 250,
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "n": 2,
        }
    )
    assert rec["serving_kind"] == "modal"
    assert rec["e2e_latency_seconds"] == pytest.approx(1.8)
    assert rec["ttft_seconds"] == pytest.approx(0.25)
    # Champion table: 1000×0.03/1e6 + 500×0.13/1e6
    assert rec["estimated_cost_usd"] == pytest.approx(0.000095)
    assert rec["cost_per_document"] == pytest.approx(0.0000475)
    assert rec["estimated_gpu_cost_usd"] is not None


def test_dojo_price_table_misses_hf_id_adapter_fills():
    assert estimate_cost(1000, 500, "Qwen/Qwen3-8B") is None
    assert metrics._estimate_cost(1000, 500, "Qwen/Qwen3-8B") == pytest.approx(0.000095)
    assert estimate_cost(1000, 500, "qwen/qwen3.7-flash") == pytest.approx(0.000095)


def test_dojo_remaps_modal_identity_but_metrics_match():
    rec = to_dojo_serving_record(
        {
            "profile": "modal-vllm",
            "provider": "vllm",
            "model": "Qwen/Qwen3-8B",
            "e2e_latency_seconds": 1.8,
            "ttft_seconds": 0.25,
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "n": 2,
            "scores": {"accuracy": 0.98, "f1_macro": 0.97},
        }
    )
    assert rec["serving_kind"] == "modal"
    assert classify_serving_kind(rec) == "local"
    dojo = get_suite("local_vs_api")
    # Score modal vs a tiny API twin through the same suite Jack uses.
    api = to_dojo_serving_record(
        {
            "profile": "openrouter",
            "provider": "openrouter",
            "model": "qwen/qwen3.7-flash",
            "e2e_latency_seconds": 0.9,
            "ttft_seconds": 0.15,
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "n": 2,
            "scores": {"accuracy": 0.99, "f1_macro": 0.98},
        }
    )
    compared = dojo.score(rec, api)
    assert compared["local"]["e2e_latency_seconds"] == pytest.approx(1.8)
    assert compared["local"]["estimated_cost_usd"] == pytest.approx(0.000095)
    assert compared["local"]["quality"]["accuracy"] == pytest.approx(0.98)
    assert compared["api"]["estimated_cost_usd"] == pytest.approx(0.000095)
    assert compared["local"]["identity"]["serving_kind"] == "local"


def test_split_keeps_modal_out_of_local():
    buckets = split_serving_records(
        [
            {"profile": "ollama", "provider": "ollama"},
            {"profile": "modal-vllm", "provider": "vllm"},
            {"profile": "openrouter", "provider": "openrouter"},
        ]
    )
    assert len(buckets["local"]) == 1
    assert len(buckets["modal"]) == 1
    assert len(buckets["api"]) == 1
    assert buckets["modal"][0]["serving_kind"] == "modal"


def test_fixture_parity_ok():
    fixtures = load_cost_compare_fixtures()
    assert set(fixtures) >= {"local", "modal", "api"}
    result = score_cost_compare(fixtures)
    assert result["parity_ok"] is True
    assert result["grant_table"]["modal"]["serving_kind"] == "modal"
    assert result["grant_table"]["modal"]["estimated_cost_usd"] == pytest.approx(0.000095)
    assert result["grant_table"]["api"]["estimated_cost_usd"] == pytest.approx(0.000095)
    assert result["grant_table"]["local"].get("estimated_cost_usd") is None
    assert result["grant_table"]["modal"]["estimated_gpu_cost_usd"] == pytest.approx(
        round(3.0 / 3600.0 * 0.80, 6)
    )
    # Three-way sandbox table still buckets modal separately.
    assert set(result["sandbox"]["buckets"]) >= {"local", "modal", "api"}
    assert result["dojo_pairs"]["modal_vs_api"]["local"]["e2e_latency_seconds"] == pytest.approx(
        1.8
    )


def test_compare_serving_direct_matches_sandbox_row():
    fixtures = load_cost_compare_fixtures()
    modal = to_dojo_serving_record(fixtures["modal"])
    api = to_dojo_serving_record(fixtures["api"])
    pair = compare_serving(modal, api)
    grant_modal = grant_table_row(fixtures["modal"])
    assert pair["local"]["e2e_latency_seconds"] == pytest.approx(grant_modal["e2e_latency_seconds"])
    assert pair["local"]["estimated_cost_usd"] == pytest.approx(grant_modal["estimated_cost_usd"])
    assert pair["local"]["prompt_tokens"] == grant_modal["prompt_tokens"]


def test_compare_from_records_modal_vs_api(tmp_path, monkeypatch):
    from mailroom_sandbox.eval import experiment_log, runners

    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    fixtures = load_cost_compare_fixtures()
    experiment_log.append(experiment_log.new_record(**fixtures["modal"]))
    experiment_log.append(experiment_log.new_record(**fixtures["api"]))
    result = runners.run_local_vs_api_eval(from_log=True, experiment_name="test_modal_from_log")
    assert result["comparison"]["modal_n"] == 1
    assert result["comparison"]["local_n"] == 0
    assert result["comparison"]["api_n"] == 1
    assert result["comparison"]["left_serving"] == "modal"
    assert result["scores"]["cost_api"] == pytest.approx(0.000095)


def test_cli_metrics_compare_fixture(capsys):
    from mailroom_sandbox.cli import main

    rc = main(["metrics", "compare", "--fixture", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["parity_ok"] is True
    assert payload["agent"] == "cost_compare"
