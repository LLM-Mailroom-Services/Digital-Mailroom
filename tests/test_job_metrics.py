"""Serving metrics capture + comparison tests (DMR-027) — network-free."""

from __future__ import annotations

from types import SimpleNamespace

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
    assert rec["estimated_cost_usd"] is not None
    assert rec["cost_per_document"] == pytest.approx(rec["estimated_cost_usd"] / 2)


# ── DMR-049: modal bucketing, cost table, ok-only latency ────────────────────


def test_attach_serving_identity_stamps_modal():
    from mailroom_sandbox.eval import scoring

    rec = scoring.attach_serving_identity(
        {"profile": "modal-vllm", "provider": "vllm", "model": "Qwen/Qwen3-8B"}
    )
    assert rec["serving_kind"] == "modal"
    # A pre-stamped record is never reclassified.
    assert scoring.attach_serving_identity({**rec, "serving_kind": "api"})["serving_kind"] == "api"


def test_estimate_cost_covers_flagship_default():
    cost = metrics._estimate_cost(1_000_000, 0, "Qwen/Qwen3-8B")
    assert cost == pytest.approx(0.03)
    assert metrics._estimate_cost(0, 0, "Qwen/Qwen3-8B") is None
    assert metrics._estimate_cost(10, 10, "not-a-model") is None


def test_record_from_run_latency_excludes_failed_items():
    rec = metrics.record_from_run(
        run_id="r2",
        spec_hash="sh",
        task="sorter",
        profile="ollama",
        model="Qwen/Qwen3-8B",
        prompt_version="code-default",
        dataset_fingerprint="fp",
        items=[
            {"latency_ms": 100, "ok": True},
            {"latency_ms": 9500, "ok": False},  # retry/backoff inflated
        ],
    )
    assert abs(rec["e2e_latency_seconds"] - 0.1) < 1e-9


def test_record_from_run_ttft_excludes_failed_items():
    """hub#56: TTFT aggregation must use the same ok_items as e2e latency —
    failed/retried items carry inflated TTFT from backoff sleeps, so a run
    with failures must not report TTFT over failures while excluding them
    from latency."""
    rec = metrics.record_from_run(
        run_id="r3",
        spec_hash="sh",
        task="sorter",
        profile="ollama",
        model="Qwen/Qwen3-8B",
        prompt_version="code-default",
        dataset_fingerprint="fp",
        items=[
            {"latency_ms": 100, "ttft_ms": 50, "ok": True},
            {"latency_ms": 200, "ttft_ms": 80, "ok": True},
            {"latency_ms": 9500, "ttft_ms": 8000, "ok": False},  # backoff-inflated
        ],
    )
    assert abs(rec["ttft_seconds"] - 0.065) < 1e-9, rec.get("ttft_seconds")
    assert abs(rec["e2e_latency_seconds"] - 0.15) < 1e-9


def test_gpu_usd_per_hour_defaults_l4():
    assert metrics.gpu_usd_per_hour("L4") == pytest.approx(0.80)
    assert metrics.gpu_usd_per_hour("H100") == pytest.approx(3.95)


def test_estimate_gpu_cost_usd_l4():
    # 3600s at $0.80/hr → $0.80
    assert metrics.estimate_gpu_cost_usd(3600.0, gpu="L4") == pytest.approx(0.80)
    assert metrics.estimate_gpu_cost_usd(0.0, gpu="L4") is None


def test_record_from_run_modal_gpu_cost(monkeypatch):
    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    monkeypatch.delenv("MODAL_GPU_USD_PER_SEC", raising=False)
    monkeypatch.delenv("MODAL_BILLED_GPU_SECONDS", raising=False)
    rec = metrics.record_from_run(
        run_id="r-modal",
        spec_hash="sh",
        task="sorter",
        profile="modal-vllm",
        model="Qwen/Qwen3-8B",
        prompt_version="code-default",
        dataset_fingerprint="fp",
        gpu="L4",
        items=[
            {
                "latency_ms": 1000,
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "ok": True,
            },
            {
                "latency_ms": 2000,
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "ok": True,
            },
        ],
    )
    assert rec["serving_kind"] == "modal"
    assert rec["gpu_seconds"] == pytest.approx(3.0)
    # 3s / 3600 * 0.80, rounded to 6 dp by estimate_gpu_cost_usd
    assert rec["estimated_gpu_cost_usd"] == pytest.approx(round(3.0 / 3600.0 * 0.80, 6))
    assert rec["gpu_cost_per_document"] == pytest.approx(rec["estimated_gpu_cost_usd"] / 2)
    assert rec["estimated_cost_usd"] is not None
    assert "cost_per_document" in rec


def test_record_from_run_billed_window_prefers_wall_over_latency_sum():
    """Under concurrency, summed latency must not drive gpu_seconds when wall is set."""
    items = [
        {"latency_ms": 5000, "ok": True, "prompt_tokens": 1, "completion_tokens": 1},
        {"latency_ms": 5000, "ok": True, "prompt_tokens": 1, "completion_tokens": 1},
    ]
    rec_wall = metrics.record_from_run(
        run_id="r-wall",
        spec_hash="sh",
        task="sorter",
        profile="modal-vllm",
        model="Qwen/Qwen3-8B",
        prompt_version="code-default",
        dataset_fingerprint="fp",
        gpu="L4",
        items=items,
        billed_window_seconds=15.0,
    )
    rec_sum = metrics.record_from_run(
        run_id="r-sum",
        spec_hash="sh",
        task="sorter",
        profile="modal-vllm",
        model="Qwen/Qwen3-8B",
        prompt_version="code-default",
        dataset_fingerprint="fp",
        gpu="L4",
        items=items,
    )
    assert rec_wall["gpu_seconds"] == pytest.approx(15.0)
    assert rec_sum["gpu_seconds"] == pytest.approx(10.0)


def test_record_from_run_billed_window_overrides_latency(monkeypatch):
    monkeypatch.setenv("MODAL_BILLED_GPU_SECONDS", "100")
    rec = metrics.record_from_run(
        run_id="r-billed",
        spec_hash="sh",
        task="sorter",
        profile="modal-vllm",
        model="Qwen/Qwen3-8B",
        prompt_version="code-default",
        dataset_fingerprint="fp",
        gpu="L4",
        items=[{"latency_ms": 10, "ok": True, "prompt_tokens": 1, "completion_tokens": 1}],
    )
    assert rec["gpu_seconds"] == pytest.approx(100.0)


def test_token_price_env_override(monkeypatch):
    monkeypatch.setenv("SANDBOX_TOKEN_PRICE_IN_PER_M", "1.0")
    monkeypatch.setenv("SANDBOX_TOKEN_PRICE_OUT_PER_M", "2.0")
    cost = metrics._estimate_cost(1_000_000, 1_000_000, "anything")
    assert cost == pytest.approx(3.0)


def test_missing_tokens_omits_cost_not_zero():
    rec = metrics.record_from_run(
        run_id="r-empty",
        spec_hash="sh",
        task="sorter",
        profile="openrouter",
        model="qwen/qwen3.7-flash",
        prompt_version="code-default",
        dataset_fingerprint="fp",
        items=[{"latency_ms": 100, "ok": True}],
        mock=False,
    )
    assert "estimated_cost_usd" not in rec
    assert "cost_per_document" not in rec


def test_compare_sorter_vs_modernbert_fixture():
    from mailroom_sandbox.datasets import load_sorter_vs_modernbert_fixtures

    fixtures = load_sorter_vs_modernbert_fixtures()
    result = metrics.compare_sorter_vs_modernbert(fixtures["sorter"], fixtures["modernbert"])
    assert result["agent"] == "sorter_vs_modernbert"
    assert result["quality"]["accuracy"]["modernbert"] == pytest.approx(0.96)
    assert result["cost"]["modernbert_cost_per_document"] == pytest.approx(1e-6)
    assert result["latency"]["sorter_e2e_s"] > result["latency"]["modernbert_e2e_s"]
    assert "Sorter vs ModernBERT" in result["markdown"]


def test_compare_includes_gpu_cost_columns():
    records = [
        _rec(
            "modal",
            "modal-vllm",
            estimated_gpu_cost_usd=0.05,
            cost_per_document=0.001,
        ),
        _rec("api", "openrouter", estimated_cost_usd=0.02, cost_per_document=0.002),
    ]
    result = metrics.compare(records)
    assert result["buckets"]["modal"]["estimated_gpu_cost_usd"] == pytest.approx(0.05)
    assert result["buckets"]["modal"]["mean_cost_per_document"] == pytest.approx(0.001)
    assert "est. GPU $" in result["markdown"]
    assert "0.001" in result["markdown"]


def test_extrapolate_cost_linear_and_industry():
    rec = {
        "n": 30,
        "cost_per_document": 0.001,
        "gpu_cost_per_document": 0.0005,
        "e2e_latency_seconds": 2.0,
        "prompt_tokens": 30_000,
        "completion_tokens": 3_000,
        "model": "Qwen/Qwen3-8B",
        "profile": "modal-vllm",
        "gpu": "L4",
        "run_id": "run-30-test",
        "gpu_seconds": 60.0,
    }
    result = metrics.extrapolate_cost(
        rec, corpus_size=3302, docs_per_day=10_000, concurrency=4
    )
    assert result["linear"]["combined_usd"] == pytest.approx(0.0015 * 3302)
    assert result["industry"]["usd_per_day"] == pytest.approx(15.0)
    assert result["with_overhead"]["combined_usd"] is not None
    assert "Cost extrapolation" in result["markdown"]
    assert result["confidence_notes"]


def test_extrapolate_refuses_silent_zero_rates():
    rates = metrics.per_document_rates({"n": 10, "profile": "modal-vllm"})
    assert rates["combined_cost_per_document"] is None
    assert rates["honest_gaps"]


def test_estimate_suite_specialist_defaults():
    """Pre-flight table for the five run-30 YAMLs (no Modal)."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    configs = [
        root / "config/runs/run-30-contracts-specialist.yaml",
        root / "config/runs/run-30-merger-specialist.yaml",
        root / "config/runs/run-30-corporate-records-specialist.yaml",
        root / "config/runs/run-30-correspondence-specialist.yaml",
        root / "config/runs/run-30-insurance-claims-specialist.yaml",
    ]
    if not all(p.is_file() for p in configs):
        import pytest

        pytest.skip("run-30 specialist YAMLs missing")
    result = metrics.estimate_suite(configs, corpus_size=3302)
    assert result["suite"]["docs"] == 150
    assert result["suite"]["runs"] == 5
    assert result["suite"]["scaledown_seconds"] == 120
    assert result["suite"]["gpu_usd"]["likely"] > 0
    assert result["suite"]["gpu_usd"]["low"] < result["suite"]["gpu_usd"]["high"]
    assert result["corpus_extrapolation"]["corpus_size"] == 3302
    assert "Pre-flight suite cost estimate" in result["markdown"]
    assert any(o["rank"] == 1 for o in result["optimizations"])
    # DMR-076: attended 120 is already the YAML pin → $0 further save-to-120
    opt2 = next(o for o in result["optimizations"] if o["rank"] == 2)
    assert opt2["expected_usd_saved"] == 0


def test_estimate_suite_override_sec_per_doc():
    result = metrics.estimate_suite(
        [
            {
                "run_id": "run-toy",
                "task": "correspondence_specialist",
                "docs": 10,
                "concurrency": 4,
                "gpu": "L4",
                "model": "Qwen/Qwen3-8B",
                "scaledown_seconds": 600,
                "max_containers": 1,
            }
        ],
        sec_per_doc_override=40.0,
        cold_start_seconds=0.0,
        scaledown_seconds=0.0,
        inter_run_gap_seconds=0.0,
        corpus_size=None,
    )
    # wall = 10 * 40 / 4 = 100 s → $ at $0.80/hr
    assert result["rows"][0]["wall_seconds"]["likely"] == pytest.approx(100.0)
    assert result["suite"]["gpu_usd"]["likely"] == pytest.approx(
        round(100.0 / 3600.0 * 0.80, 4)
    )


def test_estimate_suite_pinned_replicas_bill():
    """2×L4 MIN=MAX=2 bills 2× the per-GPU rate on shared wall."""
    result = metrics.estimate_suite(
        [
            {
                "run_id": "run-x2",
                "task": "correspondence_specialist",
                "docs": 10,
                "concurrency": 4,
                "gpu": "L4",
                "model": "Qwen/Qwen3-8B-AWQ",
                "scaledown_seconds": 120,
                "max_containers": 2,
            }
        ],
        sec_per_doc_override=40.0,
        cold_start_seconds=0.0,
        scaledown_seconds=0.0,
        inter_run_gap_seconds=0.0,
        corpus_size=None,
    )
    # wall = 10 * 40 / 4 = 100 s → 2 replicas × $0.80/hr
    assert result["rows"][0]["wall_seconds"]["likely"] == pytest.approx(100.0)
    assert result["rows"][0]["replicas"] == 2
    assert result["suite"]["gpu_usd"]["likely"] == pytest.approx(
        round(100.0 / 3600.0 * 1.60, 4)
    )


def test_usage_capture_merge_item_metrics():
    from mailroom_sandbox.job.usage_capture import merge_item_metrics, usage_from_openai_response

    merged = merge_item_metrics(
        latency_ms=12.5,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "llm_calls": 2},
        ttft_ms=3.0,
    )
    assert merged == {
        "latency_ms": 12.5,
        "ttft_ms": 3.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "llm_calls": 2,
    }
    resp = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3))
    assert usage_from_openai_response(resp) == {"prompt_tokens": 7, "completion_tokens": 3}


# ── SAND-032: replica-aware GPU cost ─────────────────────────────────────────


def test_gpu_cost_scales_with_replicas(monkeypatch):
    from mailroom_sandbox.job.metrics import estimate_gpu_cost_usd

    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    monkeypatch.delenv("MODAL_GPU_USD_PER_SEC", raising=False)
    one = estimate_gpu_cost_usd(3600, gpu="L4")
    two = estimate_gpu_cost_usd(3600, gpu="L4", replicas=2)
    assert two == round(one * 2, 6)


def test_enrich_bills_every_replica(monkeypatch):
    from mailroom_sandbox.job.metrics import enrich_serving_report

    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    monkeypatch.delenv("MODAL_GPU_USD_PER_SEC", raising=False)
    rec = {"provider": "vllm", "profile": "modal-vllm", "gpu": "L4", "n": 2}
    items = [{"ok": True, "latency_ms": 1000.0}, {"ok": True, "latency_ms": 3000.0}]
    one = enrich_serving_report(dict(rec), items=items, wall_seconds=100, gpu="L4")
    two = enrich_serving_report(dict(rec), items=items, wall_seconds=100, gpu="L4", replicas=2)
    assert two["estimated_gpu_cost_usd"] == round(one["estimated_gpu_cost_usd"] * 2, 6)
    assert two["replicas"] == 2


# ── SAND-032: p95 + billed span ──────────────────────────────────────────────


def test_p95_nearest_rank():
    from mailroom_sandbox.job.metrics import p95

    assert p95([float(i) for i in range(1, 21)]) == 19.0
    assert p95([5.0]) == 5.0


def test_p95_empty_is_loud():
    import pytest

    from mailroom_sandbox.job.metrics import p95

    with pytest.raises(ValueError):
        p95([])


def test_enrich_adds_p95_and_billed_span(monkeypatch):
    from mailroom_sandbox.job.metrics import enrich_serving_report, estimate_gpu_cost_usd

    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    monkeypatch.delenv("MODAL_GPU_USD_PER_SEC", raising=False)
    rec = {"provider": "vllm", "profile": "modal-vllm", "gpu": "L4", "n": 20}
    items = [{"ok": True, "latency_ms": float(i * 1000)} for i in range(1, 21)]
    out = enrich_serving_report(rec, items=items, wall_seconds=100, gpu="L4",
                                replicas=2, scaledown_seconds=120, cold_boot_seconds=150)
    assert out["latency_p95_seconds"] == 19.0
    # scale-to-zero: boot + wall + scaledown tail, on both replicas — a LOWER bound
    # (pre-run warm time and idle gaps are not in it; Modal usage page is truth)
    assert out["run_span_seconds_lower_bound"] == 370.0
    assert out["run_span_usd_lower_bound"] == estimate_gpu_cost_usd(370.0, gpu="L4", replicas=2)
    assert "billed_span_usd" not in out


def test_run_span_pinned_fleet_has_no_scaledown_tail(monkeypatch):
    """Review #2: MIN=MAX pinned replicas never scale down — no tail is added."""
    from mailroom_sandbox.job.metrics import enrich_serving_report

    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    rec = {"provider": "vllm", "profile": "modal-vllm", "gpu": "L4", "n": 1}
    out = enrich_serving_report(rec, items=[{"ok": True, "latency_ms": 1000.0}], wall_seconds=100,
                                gpu="L4", replicas=2, scaledown_seconds=None, cold_boot_seconds=150)
    assert out["run_span_seconds_lower_bound"] == 250.0


def test_serving_record_pinned_lock_drops_scaledown(tmp_path, monkeypatch):
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.metrics import serving_record_from_store

    monkeypatch.delenv("MODAL_BILLED_GPU_SECONDS", raising=False)
    store = RunStore(tmp_path / "r")
    store.write_lock({"task": "correspondence_specialist", "profile": "modal-vllm",
                      "engine": {"model": "Qwen/Qwen3-8B-AWQ", "modal": {
                          "gpu": "L4", "max_containers": 2, "min_containers": 2,
                          "scaledown_seconds": 120}},
                      "job": {"concurrency": 16}})
    store.append_item({"item_id": "a", "ok": True, "latency_ms": 1000.0,
                       "prompt_tokens": 10, "completion_tokens": 5})
    out = serving_record_from_store(store, wall_seconds=100, mock=False)
    assert out["replicas"] == 2
    assert out["run_span_seconds_lower_bound"] == 100.0
