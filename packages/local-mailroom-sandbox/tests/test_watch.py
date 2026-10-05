"""SAND-032: `sandbox watch` — mailroom-themed live view (pure render functions)."""

import json
import re
import time

from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.watch import (
    classify_log_line,
    progress_bar,
    render_frame,
    run_snapshot,
    strip_ansi,
)


def test_progress_bar_uses_mailroom_glyphs_and_clamps():
    assert progress_bar(5, 10, width=10) == "█████░░░░░"
    assert progress_bar(0, 0, width=4) == "░░░░"
    assert progress_bar(12, 10, width=4) == "████"


def test_vendored_pretty_log_is_pinned():
    import hashlib
    from pathlib import Path

    from mailroom_sandbox import tui

    path = Path(tui.__file__).with_name("pretty_log.py")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == tui.PRETTY_LOG_SHA256
    assert "mailroom-ml@" in tui.PRETTY_LOG_UPSTREAM
    assert "training/pretty_log.py" in tui.PRETTY_LOG_UPSTREAM


def test_header_is_mailroom_frame_with_eval_subtitle(tmp_path):
    store = _store(tmp_path)
    from mailroom_sandbox.tui.tray_context import build_tray_layout

    layout = build_tray_layout(
        store, app="sandbox-vllm-sand032", times_dir=None, cap_usd=5.0, gate_usd=4.5, width=100
    )
    frame = strip_ansi(
        render_frame(
            snapshot=run_snapshot(store),
            app="sandbox-vllm-sand032",
            log_lines=[],
            spend={"spent_usd": 0, "cap_usd": 5.0},
            width=100,
            layout=layout,
        )
    )
    lines = frame.splitlines()
    assert lines[0].startswith("╔") and "(o,o)" in frame
    assert "DIGITAL MAILROOM" in frame and "Qwen3-8B-AWQ" in frame
    assert "INBOX → SPECIALIST → REPORT" in frame
    assert "╭" in frame and "Tray TUI" in frame and "Postage" in frame and "Dispatch log" in frame


def test_classify_log_line():
    assert classify_log_line("ERROR vLLM engine died") == "error"
    assert classify_log_line("Traceback (most recent call last):") == "error"
    assert classify_log_line("WARNING kv cache 95%") == "warn"
    assert classify_log_line("Avg prompt throughput: 812.3 tokens/s, Avg generation throughput: 140.1") == "throughput"
    assert classify_log_line("GPU KV cache size: 181,344 tokens") == "kv"
    assert classify_log_line("vLLM ready on port 8000 (pid=12)") == "ready"
    assert classify_log_line("some other line") == "plain"


def _store(tmp_path, *, replicas=2):
    s = RunStore(tmp_path / "sand032-x")
    s.write_lock({"run_id": "sand032-x", "task": "correspondence_specialist",
                  "engine": {"model": "Qwen/Qwen3-8B-AWQ",
                             "vllm": {"kv_cache_dtype": "fp8"},
                             "modal": {"gpu": "L4", "max_containers": replicas,
                                       "min_containers": replicas}},
                  "job": {"concurrency": 16}})
    s.write_checkpoint(state="running", cursor=3, total=10, remote=None)
    for i, (ok, lat) in enumerate([(True, 1000.0), (True, 3000.0), (False, 500.0)]):
        s.append_item({"item_id": f"d{i}", "ok": ok, "latency_ms": lat,
                       "error": None if ok else "OpenAIConnectionError: x",
                       "score": {"overall_extraction_score": 0.5} if ok else {},
                       "prompt_tokens": 100 + i, "completion_tokens": 10 + i})
    return s


def test_run_snapshot_counts_and_latency(tmp_path):
    snap = run_snapshot(_store(tmp_path))
    assert snap["run_id"] == "sand032-x"
    assert (snap["done"], snap["total"], snap["ok"], snap["errors"]) == (3, 10, 2, 1)
    assert snap["state"] == "running"
    assert snap["replicas"] == 2
    assert snap["p50_s"] == 2.0 and snap["mean_score"] == 0.5
    assert snap["last_error"].startswith("OpenAIConnectionError")
    assert (snap["prompt_tokens"], snap["completion_tokens"], snap["total_tokens"]) == (303, 33, 336)


def test_run_snapshot_missing_store_is_waiting(tmp_path):
    snap = run_snapshot(RunStore(tmp_path / "nope"))
    assert snap["state"] == "waiting" and snap["done"] == 0


def test_render_frame_has_mailroom_sections_and_fits_width(tmp_path):
    frame = render_frame(
        snapshot=run_snapshot(_store(tmp_path)),
        app="sandbox-vllm-sand032",
        log_lines=["vLLM ready on port 8000 (pid=12)", "ERROR boom"],
        spend={"spent_usd": 1.2345, "cap_usd": 5.0, "live_usd": 0.01},
        width=100,
    )
    plain = strip_ansi(frame)
    for needle in ("MAILROOM", "sandbox-vllm-sand032", "sand032-x", "3/10",
                   "delivered 2", "returned 1", "$1.2345", "$5.00", "ERROR boom", "×2 L4"):
        assert needle in plain, needle
    assert all(len(line) <= 100 for line in plain.splitlines())


def test_render_frame_warns_near_budget(tmp_path):
    frame = render_frame(snapshot=run_snapshot(_store(tmp_path)), app="a", log_lines=[],
                         spend={"spent_usd": 4.6, "cap_usd": 5.0, "live_usd": 0.0}, width=80)
    assert "OVER $4.50 GATE" in strip_ansi(frame)


def test_strip_ansi():
    assert strip_ansi("\x1b[31mred\x1b[0m") == "red"
    assert not re.search(r"\x1b", strip_ansi("\x1b[1;36mx\x1b[0m"))


def test_cli_watch_once_renders_single_frame(tmp_path, monkeypatch, capsys):
    from mailroom_sandbox.cli import main
    from mailroom_sandbox.job import spec as spec_mod
    from mailroom_sandbox.paths import config_dir

    monkeypatch.setattr(spec_mod, "runs_root", lambda: tmp_path)
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"spent_usd": 0.42}))
    rc = main(["watch", "--config", str(config_dir() / "runs" / "sand032-l0-baseline.yaml"),
               "--once", "--no-logs", "--ledger", str(ledger)])
    out = strip_ansi(capsys.readouterr().out)
    assert rc == 0
    assert "sandbox-vllm-sand032" in out and "sand032-l0-baseline" in out and "$0.4200" in out


def test_cli_watch_follow_file_tracks_current_config(tmp_path, monkeypatch, capsys):
    """One terminal pane follows whichever SAND-032 run is current."""
    from mailroom_sandbox.cli import main
    from mailroom_sandbox.job import spec as spec_mod
    from mailroom_sandbox.paths import config_dir

    monkeypatch.setattr(spec_mod, "runs_root", lambda: tmp_path)
    follow = tmp_path / "current"
    follow.write_text(str(config_dir() / "runs" / "sand032-s3-merger50.yaml") + "\n")
    rc = main(["watch", "--follow", str(follow), "--once", "--no-logs"])
    out = strip_ansi(capsys.readouterr().out)
    assert rc == 0 and "sand032-s3-merger50" in out and "SWEEP" in out


def test_cli_watch_requires_config_or_follow(tmp_path, monkeypatch, capsys):
    from mailroom_sandbox import paths
    from mailroom_sandbox.cli import main

    monkeypatch.setattr(paths, "runtime_dir", lambda: tmp_path)  # no SAND-032 run in flight
    assert main(["watch", "--once", "--no-logs"]) == 2


def test_live_run_usd_keeps_ticking_between_docs(tmp_path):
    from datetime import datetime, timedelta, timezone

    from mailroom_sandbox.watch import _live_run_usd, run_snapshot

    store = _store(tmp_path)
    items = store.load_items()
    start = datetime.now(timezone.utc) - timedelta(seconds=180)
    for i, row in enumerate(items):
        row["ts"] = (start + timedelta(seconds=i)).isoformat()
    store.items_path.write_text("".join(json.dumps(r) + "\n" for r in items))
    snap = run_snapshot(store)
    a = _live_run_usd(store, snap, started=time.time())
    time.sleep(0.2)
    b = _live_run_usd(store, snap, started=time.time())
    assert a > 0 and b >= a


def test_ledger_with_live_fleet_is_not_double_counted(tmp_path):
    from mailroom_sandbox.watch import read_ledger

    p = tmp_path / "l.json"
    p.write_text(json.dumps({"spent_usd": 1.5, "includes_live": True}))
    assert read_ledger(p) == (1.5, True)
    p.write_text(json.dumps({"spent_usd": 0.5}))
    assert read_ledger(p) == (0.5, False)
    assert read_ledger(tmp_path / "missing.json") == (0.0, False)


def test_log_stream_follows_instead_of_refetching():
    """`modal app logs <app>` fetches 100 lines and EXITS; -f streams."""
    from mailroom_sandbox.watch import log_command

    assert log_command("sandbox-vllm-sand032") == ["modal", "app", "logs", "-f", "sandbox-vllm-sand032"]


def test_reconnect_notice_is_not_repeated():
    from collections import deque

    from mailroom_sandbox.watch import note_reconnect

    sink = deque(["a"])
    note_reconnect(sink)
    note_reconnect(sink)
    assert list(sink).count(sink[-1]) == 1 and "waiting for app" in sink[-1]


# ── lifecycle / scorecard / persistent logs (SAND-032 TUI v2) ──────────────


def test_read_times_parses_driver_stamps(tmp_path):
    from mailroom_sandbox.watch import read_times

    p = tmp_path / "r.times"
    p.write_text('"deploy_start": 100.5,\n"deploy_done": 102.0,\n')
    assert read_times(p) == {"deploy_start": 100.5, "deploy_done": 102.0}
    assert read_times(tmp_path / "missing.times") == {}


def test_lifecycle_phases_follow_driver_stamps():
    from mailroom_sandbox.watch import lifecycle

    assert lifecycle({}, [], now=10)["phase"] == "QUEUED"
    assert lifecycle({"deploy_start": 0}, [], now=10)["phase"] == "DEPLOYING"
    boot = lifecycle({"deploy_start": 0, "deploy_done": 2}, [], now=62)
    assert boot["phase"] == "COLD BOOT" and boot["detail"] == "container starting" and boot["elapsed_s"] == 60
    t = {"deploy_start": 0, "deploy_done": 2, "ready": 150}
    assert lifecycle(t, [], now=160)["phase"] == "PREFLIGHT"
    t["run_start"] = 170
    assert lifecycle(t, [], now=200)["phase"] == "SORTING"
    t["run_end"] = 300
    assert lifecycle(t, [], now=310)["phase"] == "TEARDOWN"
    t["stopped"] = 320
    assert lifecycle(t, [], now=330)["phase"] == "STOPPED"


def test_warm_run_skips_deploy_phases():
    from mailroom_sandbox.watch import lifecycle

    assert lifecycle({"ready": 5}, [], now=6)["phase"] == "PREFLIGHT"


def test_cold_boot_subphases_from_modal_logs():
    from mailroom_sandbox.watch import lifecycle

    t = {"deploy_start": 0, "deploy_done": 1}
    def sub(lines):
        return lifecycle(t, lines, now=50)["detail"]
    assert sub(["=== sandbox-vllm serve config (masked) ==="]) == "container starting"
    assert sub(["INFO Loading weights took 12.3 seconds"]) == "loading weights"
    assert sub(["Loading safetensors checkpoint shards: 50%"]) == "loading weights"
    assert sub(["INFO Loading weights took 12.3 seconds",
                "INFO Available KV cache memory: 12.1 GiB", "GPU KV cache size: 181,344 tokens"]) == "profiling KV cache"
    assert sub(["GPU KV cache size: 1 tokens", "Capturing CUDA graphs (mixed prefill-decode)"]) == "capturing CUDA graphs"
    assert sub(["Capturing CUDA graphs", "INFO:     Application startup complete."]) == "engine ready"


def test_log_buffer_persists_and_tracks_since(tmp_path):
    from mailroom_sandbox.watch import LogBuffer

    path = tmp_path / "app.log"
    buf = LogBuffer(path, maxlen=50)
    buf.append("a")
    mark = buf.mark()
    buf.append("b")
    buf.append("c")
    assert buf.tail(2) == ["b", "c"] and buf.since(mark) == ["b", "c"]
    again = LogBuffer(path, maxlen=50)  # TUI restart: history reloads from disk
    assert again.tail(3) == ["a", "b", "c"]


def _serving(tmp_path, rid="sand032-x"):
    d = tmp_path / "serving"
    d.mkdir(exist_ok=True)
    (d / f"{rid}.serving.json").write_text(json.dumps({
        "wall_seconds": 90.4, "cold_boot_seconds": 161.0, "tokens_per_second": 472.1,
        "latency_p50_seconds": 35.0, "latency_p95_seconds": 38.0, "gpu_cost_per_document": 0.00278,
        "estimated_gpu_cost_usd": 0.0556, "run_span_usd_lower_bound": 0.09, "replicas": 1,
        "prompt_tokens": 40000, "completion_tokens": 4000, "n": 20,
        "scores": {"overall_extraction_score": 0.2547, "schema_valid_rate": 0.94}}))
    return d


def test_scorecard_combines_serving_record_metrics_and_items(tmp_path):
    from mailroom_sandbox.watch import scorecard_lines

    store = _store(tmp_path)
    (store.dir / "vllm_metrics_after.json").write_text(json.dumps({
        "coverage": "replicas observed: 1 of 1",
        "replicas": {"1000.0": {"ttft_mean_seconds": 0.42, "prefix_cache_hit_rate": 0.61,
                                "preemptions": 0.0, "length_finishes": 0.0, "kv_cache_usage_perc": 0.3}}}))
    plain = "\n".join(strip_ansi(x) for x in scorecard_lines(store, serving_dir=_serving(tmp_path), width=90))
    for needle in ("0.2547", "0.94", "90.4", "161.0", "472.1", "$0.00278", "$0.0556", "0.42", "61.0%",
                   "replicas observed: 1 of 1", "delivered 2"):
        assert needle in plain, needle


def test_scorecard_pending_serving_record(tmp_path):
    from mailroom_sandbox.watch import scorecard_lines

    plain = "\n".join(strip_ansi(x) for x in scorecard_lines(_store(tmp_path), serving_dir=tmp_path / "none", width=90))
    assert "serving record pending" in plain and "delivered 2" in plain


def test_frame_shows_lifecycle_and_scorecard_on_teardown(tmp_path):
    frame = strip_ansi(render_frame(
        snapshot=run_snapshot(_store(tmp_path)), app="a", log_lines=[], spend={"cap_usd": 5.0}, width=110,
        lifecycle={"phase": "TEARDOWN", "detail": "stopping fleet", "elapsed_s": 12},
        scorecard=["overall score 0.2547"]))
    assert "TEARDOWN" in frame and "stopping fleet" in frame and "SCORECARD" in frame and "0.2547" in frame


def test_frame_hides_scorecard_while_sorting(tmp_path):
    frame = strip_ansi(render_frame(
        snapshot=run_snapshot(_store(tmp_path)), app="a", log_lines=[], spend={"cap_usd": 5.0}, width=110,
        lifecycle={"phase": "SORTING", "detail": "", "elapsed_s": 3}, scorecard=["x"]))
    assert "SORTING" in frame and "SCORECARD" not in frame


def test_cli_scorecard_command(tmp_path, monkeypatch, capsys):
    from mailroom_sandbox.cli import main
    from mailroom_sandbox.job import spec as spec_mod

    monkeypatch.setattr(spec_mod, "runs_root", lambda: tmp_path)
    _store(tmp_path)
    rc = main(["scorecard", "--run", "sand032-x", "--serving-dir", str(_serving(tmp_path))])
    out = strip_ansi(capsys.readouterr().out)
    assert rc == 0 and "SCORECARD" in out and "0.2547" in out


def test_cli_watch_defaults_to_sand032_follow(tmp_path, monkeypatch, capsys):
    """Bare `sandbox watch` follows the current SAND-032 run — no flags needed."""
    from mailroom_sandbox import paths
    from mailroom_sandbox.cli import main
    from mailroom_sandbox.job import spec as spec_mod
    from mailroom_sandbox.paths import config_dir

    monkeypatch.setattr(spec_mod, "runs_root", lambda: tmp_path / "runs")
    monkeypatch.setattr(paths, "runtime_dir", lambda: tmp_path)
    (tmp_path / "sand032").mkdir()
    (tmp_path / "sand032" / "current").write_text(str(config_dir() / "runs" / "sand032-l2-marlin.yaml"))
    rc = main(["watch", "--once", "--no-logs"])
    assert rc == 0 and "sand032-l2-marlin" in strip_ansi(capsys.readouterr().out)


def test_display_tail_hides_scrape_noise_but_file_keeps_it(tmp_path):
    from mailroom_sandbox.watch import LogBuffer, display_tail

    buf = LogBuffer(tmp_path / "app.log")
    for line in ['(APIServer pid=4) INFO:     1.2.3.4:1 - "GET /metrics HTTP/1.1" 200 OK',
                 "    GET /metrics -> 200 OK  (duration: 225.0 ms, execution: 136.1 ms)",
                 '(APIServer pid=4) INFO:     1.2.3.4:2 - "GET /v1/models HTTP/1.1" 200 OK',
                 "Avg prompt throughput: 812.3 tokens/s"]:
        buf.append(line)
    assert display_tail(buf, 5) == ["Avg prompt throughput: 812.3 tokens/s"]
    assert len((tmp_path / "app.log").read_text().splitlines()) == 4


def test_program_route_shows_every_run_with_fleet_and_status(tmp_path):
    from mailroom_sandbox.watch import PROGRAM, program_lines

    assert len(PROGRAM) == 13  # L3/L4 folded into the single-boot L5 (warm flow)
    assert sum(1 for _, rep in PROGRAM if rep == 2) == 7  # s2b + six Stage-3 runs
    assert "sand032-l3-fp8kv" not in dict(PROGRAM)
    (tmp_path / "sand032-l0-baseline.times").write_text('"stopped": 1.0,\n')
    (tmp_path / "sand032-l1-nothink.times").write_text('"run_start": 1.0,\n')
    plain = "\n".join(strip_ansi(x) for x in program_lines(tmp_path, current="sand032-l1-nothink", width=110))
    assert "✓ l0-baseline ×1" in plain
    assert "▶ l1-nothink ×1" in plain
    assert "· s3-merger50 ×2" in plain and "· s2b-corr100-2rep ×2" in plain


def test_program_route_warm_runs_done_after_run_end(tmp_path):
    """Warm-flow runs never get their own `stopped` stamp — run_end + not current = done."""
    from mailroom_sandbox.watch import program_lines

    (tmp_path / "sand032-s2a-corr100-1rep.times").write_text('"ready": 1.0,\n"run_end": 2.0,\n')
    (tmp_path / "sand032-s2b-corr100-2rep.times").write_text('"ready": 3.0,\n')
    plain = "\n".join(strip_ansi(x) for x in program_lines(tmp_path, current="sand032-s2b-corr100-2rep", width=110))
    assert "✓ s2a-corr100-1rep ×1" in plain and "▶ s2b-corr100-2rep ×2" in plain


def test_only_one_tui_instance_writes_the_persistent_log(tmp_path):
    """Two TUI tabs must not double every line in modal-app.log."""
    from mailroom_sandbox.watch import LogBuffer

    path = tmp_path / "app.log"
    a, b = LogBuffer(path), LogBuffer(path)
    a.append("x")
    b.append("x")
    assert path.read_text().splitlines() == ["x"]
    assert a.tail(1) == ["x"] and b.tail(1) == ["x"]  # both still display it
