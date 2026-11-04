"""Spend caps price every Modal app a routed run keeps warm, not only the base engine.

A Modal pipeline experiment routes the judge (and optionally the specialists)
to their own apps. Pricing only the base L4 lets an L40S judge run past the cap.
"""

from __future__ import annotations

import pytest

from mailroom_sandbox.job import metrics

L4 = 0.80
L40S = 1.95

ROUTED_LOCK = {
    "engine": {"model": "Qwen/Qwen3.5-9B", "modal": {"app": "sandbox-vllm-s-9b", "gpu": "L4", "max_containers": 1}},
    "agent_routes": {
        "judge": {"provider": "modal-vllm", "model": "Qwen/Qwen3.5-27B",
                  "modal": {"app": "sandbox-vllm-s-27b", "gpu": "L40S", "max_containers": 1}},
        "contracts_specialist": {"provider": "modal-vllm", "model": "Qwen/Qwen3.5-35B-A3B",
                                 "modal": {"app": "sandbox-vllm-s-35b-a3b", "gpu": "L4:2", "max_containers": 1}},
        # Same app as above: one deployment, billed once.
        "correspondence_specialist": {"provider": "modal-vllm", "model": "Qwen/Qwen3.5-35B-A3B",
                                      "modal": {"app": "sandbox-vllm-s-35b-a3b", "gpu": "L4:2", "max_containers": 1}},
        "sorter": {"provider": "openrouter", "model": "qwen/qwen3.5-9b"},
    },
}


@pytest.fixture(autouse=True)
def _table_rates(monkeypatch):
    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    monkeypatch.delenv("MODAL_GPU_USD_PER_SEC", raising=False)


def test_fleet_lists_each_distinct_modal_app_with_its_billed_gpus():
    assert metrics.lock_gpu_fleet(ROUTED_LOCK) == [("L4", 1), ("L40S", 1), ("L4", 2)]


def test_fleet_without_routes_is_the_base_engine_alone():
    lock = {"engine": {"modal": {"gpu": "L4", "max_containers": 2}}}
    assert metrics.lock_gpu_fleet(lock) == [("L4", 2)]
    assert metrics.lock_gpu_fleet({}) == [("L4", 1)]
    # Unrouted non-Modal base: unchanged, the base entry stays.
    assert metrics.lock_gpu_fleet({"engine": {"kind": "openrouter", **lock["engine"]}}) == [("L4", 2)]
    assert metrics.routed_gpu_fleet(lock) is None


def test_fleet_drops_an_unused_base_on_a_non_modal_engine():
    lock = {**ROUTED_LOCK, "engine": {"kind": "openrouter", "modal": {"gpu": "L4", "max_containers": 1}}}
    assert metrics.lock_gpu_fleet(lock) == [("L40S", 1), ("L4", 2)]
    assert metrics.routed_gpu_fleet(lock) == [("L40S", 1), ("L4", 2)]


def test_fleet_cost_sums_every_app():
    hour = metrics.fleet_gpu_cost_usd(3600, metrics.lock_gpu_fleet(ROUTED_LOCK))
    assert hour == pytest.approx(L4 + L40S + 2 * L4)
    assert metrics.fleet_gpu_cost_usd(0, [("L4", 1)]) == 0.0


def test_run_cap_estimate_includes_route_apps(tmp_path):
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.runner import _estimate_run_gpu_usd

    store = RunStore(tmp_path / "r")
    store.write_lock(ROUTED_LOCK)
    assert _estimate_run_gpu_usd(store, 3600) == pytest.approx(L4 + L40S + 2 * L4)


def test_pipeline_job_passes_the_fleet_to_the_cap(tmp_path, monkeypatch):
    from mailroom_sandbox.eval import runners as eval_runners
    from mailroom_sandbox.job import runner
    from mailroom_sandbox.job.checkpoint import RunStore

    store = RunStore(tmp_path / "r")
    store.write_lock({**ROUTED_LOCK, "task": "pipeline", "profile": "modal-vllm", "prompt": {},
                      "job": {"cost_cap_usd": 1.0}})
    seen = {}

    def fake_pipeline(**kwargs):
        seen.update(kwargs)
        return {"task": "pipeline", "rows": [], "scores": {}}

    monkeypatch.setattr(eval_runners, "run_pipeline_eval", fake_pipeline)
    runner._run_whole_run(store, "pipeline", mock=False, model=None, profile="modal-vllm")
    # The lock is stored with sorted keys; fleet order carries no meaning.
    assert sorted(seen["gpu_fleet"]) == [("L4", 1), ("L4", 2), ("L40S", 1)]


def test_cap_guard_trips_on_the_fleet_not_the_base_gpu():
    from mailroom_sandbox.eval.runners import _estimated_gpu_usd

    # $1 cap: 30 min on the base L4 alone is $0.40, the routed fleet is $2.18.
    assert _estimated_gpu_usd(1800, gpu="L4", replicas=1, gpu_fleet=None) < 1.0
    assert _estimated_gpu_usd(1800, gpu="L4", replicas=1, gpu_fleet=metrics.lock_gpu_fleet(ROUTED_LOCK)) >= 1.0


def _serving_store(tmp_path, lock, profile="modal-vllm"):
    import json

    from mailroom_sandbox.job.checkpoint import RunStore

    store = RunStore(tmp_path / "r")
    store.write_lock({**lock, "task": "contracts_specialist", "profile": profile,
                      "job": {"mock": False, "concurrency": 4}})
    for i, ts in enumerate(("2026-01-01T00:00:00.000+00:00", "2026-01-01T00:01:00.000+00:00")):
        store.append_item({"item_id": f"d{i}", "ok": True, "latency_ms": 1000.0, "prompt_tokens": 1,
                           "completion_tokens": 1, "ts": ts})
    (store.dir / "cold_boot.json").write_text(json.dumps({"cold_boot_seconds": 30.0}), encoding="utf-8")
    return store


def test_serving_report_prices_the_routed_fleet_like_the_run_record(tmp_path, monkeypatch):
    """Dated serving reports and the runner's record agree on a routed run's GPU cost."""
    from mailroom_sandbox.eval.runners import _estimated_gpu_usd
    from mailroom_sandbox.job.runner import _lock_fleet, _lock_gpu, _lock_replicas

    monkeypatch.delenv("MODAL_BILLED_GPU_SECONDS", raising=False)
    store = _serving_store(tmp_path, ROUTED_LOCK)
    rec = metrics.serving_record_from_store(store, wall_seconds=3570.0, mock=False)
    billed = 3570.0 + 30.0  # wall + cold boot, as the runner bills it
    runner_cost = _estimated_gpu_usd(
        billed, gpu=_lock_gpu(store), replicas=_lock_replicas(store), gpu_fleet=_lock_fleet(store)
    )
    assert rec["gpu_seconds"] == pytest.approx(billed)
    assert rec["estimated_gpu_cost_usd"] == pytest.approx(runner_cost)
    assert rec["estimated_gpu_cost_usd"] == pytest.approx(L4 + L40S + 2 * L4)
    assert rec["gpu_cost_per_document"] == pytest.approx(runner_cost / 2)
    # The lower bound stays on the base engine; route apps may scale to zero.
    assert rec["run_span_usd_lower_bound"] == pytest.approx(L4)
    assert sorted((f["gpu"], f["gpus"]) for f in rec["gpu_fleet"]) == [("L4", 1), ("L4", 2), ("L40S", 1)]


def test_serving_report_keeps_the_base_gpu_formula_without_routes(tmp_path, monkeypatch):
    monkeypatch.delenv("MODAL_BILLED_GPU_SECONDS", raising=False)
    lock = {"engine": ROUTED_LOCK["engine"]}
    rec = metrics.serving_record_from_store(_serving_store(tmp_path, lock), wall_seconds=3570.0, mock=False)
    assert rec["estimated_gpu_cost_usd"] == pytest.approx(L4)
    assert "gpu_fleet" not in rec


def test_serving_report_prices_modal_routes_on_an_api_base(tmp_path, monkeypatch):
    """An API base profile with Modal routes still bills the fleet, like the runner."""
    monkeypatch.delenv("MODAL_BILLED_GPU_SECONDS", raising=False)
    # The lock keeps the default modal block on a non-Modal base; it never runs.
    engine = {"kind": "openrouter", "model": "qwen/qwen3.5-9b", "modal": {"gpu": "L4", "max_containers": 1}}
    store = _serving_store(tmp_path, {**ROUTED_LOCK, "engine": engine}, profile="openrouter")
    rec = metrics.serving_record_from_store(store, wall_seconds=3570.0, mock=False)
    assert rec["estimated_gpu_cost_usd"] == pytest.approx(L40S + 2 * L4)
    assert sorted((f["gpu"], f["gpus"]) for f in rec["gpu_fleet"]) == [("L4", 2), ("L40S", 1)]
    assert "run_span_usd_lower_bound" not in rec


def test_a_route_reusing_the_unused_base_app_name_is_still_billed():
    # The openrouter base keeps the default `sandbox-vllm` app name; it never deploys.
    lock = {"engine": {"kind": "openrouter", "modal": {"app": "sandbox-vllm", "gpu": "L4"}},
            "agent_routes": {"judge": {"provider": "modal-vllm",
                                       "modal": {"app": "sandbox-vllm", "gpu": "L40S"}}}}
    assert metrics.lock_gpu_fleet(lock) == [("L40S", 1)]
    assert metrics.routed_gpu_fleet(lock) == [("L40S", 1)]
    # On a Modal base the same name is the base app itself: billed once.
    modal_base = {**lock, "engine": {"kind": "modal-vllm", "modal": lock["engine"]["modal"]}}
    assert metrics.lock_gpu_fleet(modal_base) == [("L4", 1)]
    assert metrics.routed_gpu_fleet(modal_base) is None


def test_per_item_run_record_prices_the_routed_fleet(tmp_path, monkeypatch):
    """The per-item runner record agrees with its cost cap on a routed run."""
    from mailroom_sandbox.job.runner import _build_record, _estimate_run_gpu_usd

    monkeypatch.delenv("MODAL_BILLED_GPU_SECONDS", raising=False)
    store = _serving_store(tmp_path, ROUTED_LOCK)
    rec = _build_record(store, "contracts_specialist", None, {}, mock=False, wall_seconds=3570.0)
    assert rec["estimated_gpu_cost_usd"] == pytest.approx(_estimate_run_gpu_usd(store, 3600.0))
    assert rec["estimated_gpu_cost_usd"] == pytest.approx(L4 + L40S + 2 * L4)
