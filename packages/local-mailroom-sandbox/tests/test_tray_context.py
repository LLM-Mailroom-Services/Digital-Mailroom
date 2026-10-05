"""Tray TUI job-aware layout (network-free)."""

from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.tui import tray_context as tc
from mailroom_sandbox.watch import compose_watch_state, LogBuffer


def _generic_store(tmp_path) -> RunStore:
    s = RunStore(tmp_path / "run-20-correspondence-awq")
    s.write_lock(
        {
            "run_id": "run-20-correspondence-awq",
            "task": "correspondence_specialist",
            "profile": "modal-vllm",
            "engine": {
                "model": "Qwen/Qwen3-8B-AWQ",
                "vllm": {"quantization": "awq", "kv_cache_dtype": "fp8"},
                "modal": {"gpu": "L4", "max_containers": 1, "app": "sandbox-vllm"},
            },
            "job": {"mode": "endpoint", "concurrency": 8, "cost_cap_usd": 0.55},
        }
    )
    s.write_checkpoint(state="running", cursor=4, total=20, remote=None)
    s.append_event("preflight_ok", "info")
    return s


def test_build_layout_uses_lock_not_sand032_defaults(tmp_path):
    store = _generic_store(tmp_path)
    layout = tc.build_tray_layout(
        store, app="sandbox-vllm", times_dir=None, cap_usd=5.0, gate_usd=4.5
    )
    assert layout["profile"] == "modal-vllm"
    assert layout["job_mode"] == "endpoint"
    assert "Qwen3-8B-AWQ" in layout["subtitle"]
    assert layout["route_label"] == "INBOX → SPECIALIST → REPORT"
    assert layout["job_route"] is not None
    assert layout["route"] is None
    assert layout["panels"]["tray"].startswith("Tray TUI")
    assert layout["cap_usd"] == 0.55


def test_running_checkpoint_beats_stale_times_cold_boot(tmp_path):
    """Operator bug: .times deploy_done pinned COLD BOOT while items scored."""
    import time

    store = _generic_store(tmp_path)
    times_dir = tmp_path / "logs"
    times_dir.mkdir()
    (times_dir / f"{store.run_id}.times").write_text(
        f'"deploy_done": {time.time() - 315},\n', encoding="utf-8"
    )
    life = tc.resolve_lifecycle(
        store,
        {"deploy_done": time.time() - 315},
        ["vLLM ready on port 8000"],
        now=time.time(),
    )
    assert life["phase"] == "SORTING"
    assert "in flight" in life["detail"]

    state = compose_watch_state(
        store=store,
        app="sandbox-vllm",
        sink=LogBuffer(None),
        ledger=None,
        cap_usd=5.0,
        times_dir=times_dir,
        serving_dir=tmp_path / "serving",
        started=time.time(),
        boot_mark={},
    )
    assert state["lifecycle"]["phase"] == "SORTING"
    assert state["stage"] == "SORTING"


def test_lifecycle_from_checkpoint_when_no_driver_times(tmp_path):
    store = _generic_store(tmp_path)
    life = tc.lifecycle_from_store(store, [], now=__import__("time").time())
    assert life["phase"] == "SORTING"
    assert "correspondence_specialist" in life["detail"]


def test_compose_state_includes_layout_and_job_route(tmp_path):
    store = _generic_store(tmp_path)
    state = compose_watch_state(
        store=store,
        app="sandbox-vllm",
        sink=LogBuffer(None),
        ledger=None,
        cap_usd=5.0,
        times_dir=None,
        serving_dir=tmp_path / "serving",
        started=__import__("time").time(),
        boot_mark={},
    )
    assert state["layout"]["profile"] == "modal-vllm"
    assert state["job_route"]
    assert state["watcher_label"].startswith("Tray TUI watcher")
    assert "animate_lifecycle" in state


def test_resolve_watch_paths_prefers_run_dir_log(tmp_path):
    store = _generic_store(tmp_path)
    td, log_path = tc.resolve_watch_paths(store, sand032_root=tmp_path / "sand032")
    assert td is None
    assert log_path == store.dir / "modal-app.log"


def test_dispatch_source_endpoint_vs_modal_worker(tmp_path):
    store = _generic_store(tmp_path)
    src = tc.dispatch_source(store, cli_app="sandbox-vllm")
    assert src["serve_app"] == "sandbox-vllm"
    assert src["worker_app"] is None
    assert src["streams"] == ["sandbox-vllm"]

    store2 = _generic_store(tmp_path / "sub")
    lock = store2.read_lock() or {}
    lock["job"]["mode"] = "modal"
    import json

    store2.lock_path.write_text(json.dumps(lock))
    src2 = tc.dispatch_source(store2, cli_app=None)
    assert src2["serve_app"] == "sandbox-vllm"
    assert src2["worker_app"] == "sandbox-job"
    assert src2["streams"] == ["sandbox-vllm", "sandbox-job"]


def test_job_event_lines_carry_roles(tmp_path):
    store = _generic_store(tmp_path)
    store.append_event("failed", "error", message="boom")
    store.append_event("paused", "warn", cursor=3)
    lines = tc.job_event_lines(store, limit=2)
    assert lines[0]["role"] == "error" and lines[0]["text"].startswith("job:failed")
    assert lines[1]["role"] == "warn"


def test_compose_state_merges_job_events_and_source_tags(tmp_path):
    import time

    store = _generic_store(tmp_path)
    store.append_event("preflight_ok", "info")
    sink = LogBuffer(None)
    sink.append("vLLM ready on port 8000")
    state = compose_watch_state(
        store=store,
        app="sandbox-vllm",
        sink=sink,
        ledger=None,
        cap_usd=5.0,
        times_dir=None,
        serving_dir=tmp_path / "serving",
        started=time.time(),
        boot_mark={},
    )
    assert any(e["source"] == "job" for e in state["logs"])
    assert any(e["source"] == "modal" for e in state["logs"])
    assert state["lifecycle_role"] in {"gold", "cyan", "teal", "warn", "dim"}
    assert state["animate_lifecycle"] is True  # SORTING animates
    assert "sandbox-job" not in state["layout"]["panels"]["dispatch"]


def test_failed_state_detail_and_no_animation(tmp_path):
    import time

    store = _generic_store(tmp_path)
    store.write_checkpoint(state="failed", cursor=4, total=20, remote=None, last_error="GPU OOM")
    state = compose_watch_state(
        store=store,
        app="sandbox-vllm",
        sink=LogBuffer(None),
        ledger=None,
        cap_usd=5.0,
        times_dir=None,
        serving_dir=tmp_path / "serving",
        started=time.time(),
        boot_mark={},
    )
    assert state["lifecycle"]["phase"] == "FAILED"
    assert "OOM" in state["lifecycle"]["detail"]
    assert state["animate_lifecycle"] is False
    assert state["scorecard"] is not None or True  # scorecard path is best-effort offline
