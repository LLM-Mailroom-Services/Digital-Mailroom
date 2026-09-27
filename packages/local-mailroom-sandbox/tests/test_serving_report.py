"""Serving JSON export (issue #36 / SAND-028-1) — network-free."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from mailroom_sandbox.job import metrics
from mailroom_sandbox.job.checkpoint import RunStore


def _synthetic_items(n: int, latency_s: float, *, spread_s: float = 0.0) -> list[dict]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    items = []
    for i in range(n):
        ts = (start + timedelta(seconds=i * spread_s)).isoformat(timespec="milliseconds")
        items.append(
            {
                "item_id": f"d{i}",
                "index": i,
                "ok": True,
                "latency_ms": latency_s * 1000.0,
                "prompt_tokens": 1000,
                "completion_tokens": 100,
                "ts": ts,
            }
        )
    return items


def test_enrich_serving_report_idle_block_and_throughput():
    items = _synthetic_items(4, 30.0, spread_s=5.0)
    wall = 90.401
    base = metrics.record_from_run(
        run_id="run-toy",
        spec_hash="sh",
        task="correspondence_specialist",
        profile="modal-vllm",
        model="Qwen/Qwen3-8B-AWQ",
        prompt_version="correspondence_specialist_production",
        dataset_fingerprint="fp",
        items=items,
        gpu="L4",
        mock=False,
    )
    rec = metrics.enrich_serving_report(
        base,
        items=items,
        wall_seconds=wall,
        concurrency=8,
        cold_boot_seconds=159.887,
        gpu="L4",
    )
    assert rec["wall_seconds"] == pytest.approx(90.401)
    assert rec["concurrency"] == 8
    assert rec["latency_sum_seconds"] == pytest.approx(120.0)
    assert rec["latency_sum_over_wall"] == pytest.approx(round(120.0 / wall, 2))
    assert rec["tokens_per_second"] == pytest.approx(round(4400 / wall, 2))
    assert rec["ttft_note"] == metrics.TTFT_NEVER_INFERRED_NOTE
    assert rec["gpu_seconds"] == pytest.approx(round(wall + 159.887, 3))
    busy = 120.0 / 8
    assert rec["busy_slot_seconds"] == pytest.approx(round(busy, 3))
    assert rec["slot_utilization"] == pytest.approx(round(busy / wall, 4))
    assert rec["idle_container_seconds"] == pytest.approx(round(wall - busy, 3))
    assert rec["idle_estimated_usd"] == pytest.approx(
        metrics.estimate_gpu_cost_usd(wall - busy, gpu="L4")
    )
    assert rec["boot_estimated_usd"] == pytest.approx(
        metrics.estimate_gpu_cost_usd(159.887, gpu="L4")
    )


def test_write_serving_json_from_store(tmp_path):
    store = RunStore(tmp_path / "run-export")
    store.write_lock(
        {
            "run_id": store.run_id,
            "task": "sorter",
            "profile": "modal-vllm",
            "spec_hash": "abc",
            "engine": {"model": "Qwen/Qwen3-8B", "modal": {"gpu": "L4"}},
            "job": {"mock": True, "concurrency": 4},
            "prompt": {"default": {"source": "local", "file": "sorter_local_v0"}},
        }
    )
    store.append_item(
        {
            "item_id": "d0",
            "index": 0,
            "ok": True,
            "latency_ms": 100.0,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "ts": "2026-01-01T00:00:00.000+00:00",
        }
    )
    store.append_item(
        {
            "item_id": "d1",
            "index": 1,
            "ok": True,
            "latency_ms": 200.0,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "ts": "2026-01-01T00:01:30.500+00:00",
        }
    )
    out = tmp_path / "out.serving.json"
    path = metrics.write_serving_json(store, out, wall_seconds=90.5)
    assert path == out
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["run_id"] == store.run_id
    assert payload["prompt_version"] == "sorter_local_v0"
    assert payload["wall_seconds"] == pytest.approx(90.5)
    assert payload["latency_sum_seconds"] == pytest.approx(0.3)
    assert "busy_slot_seconds" in payload


def test_infer_wall_from_item_timestamps():
    items = [
        {"ts": "2026-01-01T00:00:00.000+00:00", "ok": True},
        {"ts": "2026-01-01T00:01:30.500+00:00", "ok": True},
    ]
    assert metrics.infer_wall_seconds_from_items(items) == pytest.approx(90.5)
