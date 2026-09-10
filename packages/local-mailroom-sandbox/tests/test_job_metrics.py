"""Serving metrics capture + comparison tests (DMR-027) — network-free."""

from __future__ import annotations

import pytest

from mailroom_sandbox.job import metrics


def _rec(kind, profile, model="Qwen/Qwen3-8B", **extra):
    base = {
        "profile": profile,
        "model": model,
        "prompt_version": "code-default",
        "task": "sorter",
        "n": 10,
        "e2e_latency_seconds": 0.5,
        "prompt_tokens": 1000,
        "completion_tokens": 500,
    }
    base.update(extra)
    return base


def test_bucket_kind():
    assert metrics.bucket_kind({"profile": "ollama"}) == "local"
    assert metrics.bucket_kind({"profile": "modal-vllm"}) == "modal"
    assert metrics.bucket_kind({"profile": "openrouter"}) == "api"
    assert metrics.bucket_kind({"provider": "openrouter"}) == "api"
    assert metrics.bucket_kind({}) == "unknown"


def test_compare_three_way_buckets():
    records = [
        _rec("local", "ollama"),
        _rec("modal", "modal-vllm"),
        _rec("api", "openrouter"),
    ]
    result = metrics.compare(records)
    assert set(result["buckets"]) >= {"local", "modal", "api"}
    assert result["buckets"]["local"]["n"] == 1


def test_compare_deltas_vs_api():
    records = [
        _rec("local", "ollama", e2e_latency_seconds=1.0),
        _rec("api", "openrouter", e2e_latency_seconds=0.5),
    ]
    result = metrics.compare(records)
    d = result["deltas_vs_api"]["mean_e2e_s"]
    assert d["local"] == pytest.approx(100.0)  # 100% slower than API


def test_record_from_run_aggregates_items():
    rec = metrics.record_from_run(
        run_id="r1",
        spec_hash="sh",
        task="sorter",
        profile="ollama",
        model="Qwen/Qwen3-8B",
        prompt_version="code-default",
        dataset_fingerprint="fp",
        items=[
            {"latency_ms": 100, "prompt_tokens": 10, "completion_tokens": 5},
            {"latency_ms": 300, "prompt_tokens": 20, "completion_tokens": 5},
        ],
        scores={"exact_match": 1.0},
    )
    assert rec["serving_kind"] == "local"
    assert rec["n"] == 2
    assert rec["prompt_tokens"] == 30 and rec["completion_tokens"] == 10
    assert abs(rec["e2e_latency_seconds"] - 0.2) < 1e-9
    assert rec["scores"]["exact_match"] == 1.0