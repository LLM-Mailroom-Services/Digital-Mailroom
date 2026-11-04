"""`sandbox watch [TARGET]` / `sandbox web`: target resolution, live switching, edge cases (network-free)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox import experiments as exp_mod
from mailroom_sandbox import watch_target as wt
from mailroom_sandbox.job import spec as spec_mod
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.services._exec import ServiceError
from mailroom_sandbox.tui import web as web_mod


def _run(run_id: str, *, app: str | None = "sandbox-vllm-x", concurrency: int = 4, age: float = 0.0,
         spec_hash: str | None = None) -> RunStore:
    store = RunStore(spec_mod.run_dir(run_id))
    engine = {"model": "Qwen/Qwen3-8B-AWQ", "modal": {"app": app, "gpu": "L4"} if app else None}
    lock = {"run_id": run_id, "task": "sorter", "engine": engine, "job": {"concurrency": concurrency}}
    if spec_hash:
        lock["spec_hash"] = spec_hash
    store.write_lock(lock)
    store.write_checkpoint(state="running", cursor=0, total=4, remote=None)
    if age:
        stamp = time.time() - age
        for f in [store.dir, *store.dir.iterdir()]:
            os.utime(f, (stamp, stamp))
    return store


def _spec(path: Path, run_id: str | None = "spec-run", model: str = "qwen3:8b") -> Path:
    rid = f"run_id: {run_id}\n" if run_id else ""
    path.write_text(f"schema: sandbox.run/v1\n{rid}task: sorter\nprofile: ollama\n"
                    f"engine: {{kind: vllm-local, model: '{model}', modal: null}}\n")
    return path


# ── discovery ───────────────────────────────────────────────────────────────

def test_run_dirs_orders_by_activity_and_skips_empty_and_hidden(job_data_dir):
    _run("old-run", age=300)
    _run("new-run")
    (spec_mod.runs_root() / "empty-dir").mkdir()
    (spec_mod.runs_root() / ".hidden").mkdir()
    (spec_mod.runs_root() / ".hidden" / "events.jsonl").write_text("")
    (spec_mod.runs_root() / "stray.txt").write_text("not a run")
    assert [p.name for p in wt.run_dirs()] == ["new-run", "old-run"]
    assert wt.latest_run(prefix="old").name == "old-run"
    assert wt.latest_run(prefix="nope") is None


def test_activity_in_an_old_run_makes_it_the_latest_again(job_data_dir):
    old = _run("resumed-run", age=600)
    _run("other-run", age=60)
    assert wt.latest_run().name == "other-run"
    old.append_item({"item_id": "d0", "ok": True})  # the old run resumes and writes
    assert wt.latest_run().name == "resumed-run"


def test_store_and_app_survives_a_torn_lock(job_data_dir):
    store = _run("torn-lock")
    store.lock_path.write_text("{not json")
    got, app = wt.store_and_app(store.dir)
    assert got.run_id == "torn-lock" and app == wt.DEFAULT_APP


def test_store_and_app_reads_the_modal_app_from_the_lock_unless_overridden(job_data_dir):
    store = _run("app-run", app="sandbox-vllm-qwen")
    assert wt.store_and_app(store.dir)[1] == "sandbox-vllm-qwen"
    assert wt.store_and_app(store.dir, "override")[1] == "override"
    assert wt.store_and_app(_run("no-modal", app=None).dir)[1] == wt.DEFAULT_APP


def test_store_and_app_waits_for_a_missing_directory_without_creating_it(job_data_dir):
    missing = spec_mod.runs_root() / "not-yet"
    with pytest.raises(wt.WaitingForRun):
        wt.store_and_app(missing)
    assert not missing.exists()


# ── resolve_target ──────────────────────────────────────────────────────────

def test_bare_target_follows_the_newest_run_and_switches_live(job_data_dir):
    _run("first-run", age=120)
    target = wt.resolve_target(None)
    assert target.resolve()[0].run_id == "first-run"
    _run("second-run")
    assert target.resolve()[0].run_id == "second-run"


def test_bare_target_with_no_runs_waits(job_data_dir):
    target = wt.resolve_target(None)
    with pytest.raises(wt.WaitingForRun, match="waiting for a run"):
        target.resolve()


def test_bare_target_prefers_the_sand032_current_marker(job_data_dir, tmp_path):
    _run("sand032-a", age=100)
    _run("newer-unrelated")
    marker = tmp_path / "current"
    marker.write_text("sand032-a\n")
    target = wt.resolve_target(None, sand032_current=marker)
    assert target.follow == marker and target.resolve()[0].run_id == "sand032-a"


def test_run_id_target(job_data_dir):
    _run("by-id")
    assert wt.resolve_target("by-id").resolve()[0].run_id == "by-id"


def test_unknown_run_id_lists_recent_runs(job_data_dir):
    _run("known-run")
    with pytest.raises(ServiceError, match="recent runs: known-run"):
        wt.resolve_target("unknown-run")


@pytest.mark.parametrize("bad", ["../escape", "-leading-dash", "a" * 80, "has space"])
def test_invalid_run_ids_are_rejected_not_created(job_data_dir, bad):
    with pytest.raises(ServiceError):
        wt.resolve_target(bad)
    assert not any(spec_mod.runs_root().iterdir())


def test_run_directory_target(job_data_dir):
    store = _run("dir-run")
    assert wt.resolve_target(str(store.dir)).resolve()[0].run_id == "dir-run"


def test_run_yaml_with_run_id_can_be_watched_before_it_starts(job_data_dir, tmp_path):
    cfg = _spec(tmp_path / "run.yaml", "pending-run")
    store, app = wt.resolve_target(str(cfg)).resolve()
    assert store.run_id == "pending-run" and app == wt.DEFAULT_APP and store.dir.is_dir()


def test_run_yaml_without_run_id_follows_its_newest_auto_named_run(job_data_dir, tmp_path):
    cfg = _spec(tmp_path / "auto.yaml", None, model="Qwen/Qwen3-8B")
    want = spec_mod.load_run_spec(cfg).spec_hash()
    target = wt.resolve_target(str(cfg))
    with pytest.raises(wt.WaitingForRun, match="no run_id"):
        target.resolve()
    _run("sorter-qwen3-8b-20260101T000000Z", age=90, spec_hash=want)
    _run("sorter-qwen3-8b-20260102T000000Z", age=50, spec_hash=want)
    _run("sorter-qwen3-8b-20260103T000000Z", spec_hash="0" * 64)  # same task+model, other settings
    _run("sorter-qwen3-8b-20260104T000000Z")  # not locked yet: unknown spec, never picked
    _run("pipeline-qwen3-8b-20260105T000000Z", spec_hash=want)  # other task prefix: never picked
    assert target.resolve()[0].run_id == "sorter-qwen3-8b-20260102T000000Z"
    assert target.resolve()[0].run_id == "sorter-qwen3-8b-20260102T000000Z"  # stable across frames


def test_run_yaml_without_run_id_waits_when_only_other_specs_ran(job_data_dir, tmp_path):
    cfg = _spec(tmp_path / "auto.yaml", None, model="Qwen/Qwen3-8B")
    _run("sorter-qwen3-8b-20260103T000000Z", spec_hash="f" * 64)
    with pytest.raises(wt.WaitingForRun, match="spec_hash"):
        wt.resolve_target(str(cfg)).resolve()


def test_run_yaml_without_run_id_matches_a_real_mock_run(job_data_dir, tmp_path, capsys):
    cfg = tmp_path / "noid.yaml"
    cfg.write_text("schema: sandbox.run/v1\ntask: pipeline\nprofile: ollama\n"
                   "dataset: {provider: file, local_path: data/fixtures/hf/docclass_mini.jsonl, limit: 1, sample_seed: 1}\n"
                   "engine: {kind: vllm-local, model: qwen3:8b, modal: null}\n"
                   "job: {mode: endpoint, mock: true, concurrency: 5}\ntrace: {sink: none}\n")
    other = tmp_path / "other.yaml"
    other.write_text(cfg.read_text().replace("concurrency: 5", "concurrency: 6"))
    assert cli.main(["run", "start", "--config", str(cfg), "--mock"]) == 0
    first = wt.latest_run().name
    time.sleep(1.1)  # auto-named run IDs carry a per-second UTC stamp
    assert cli.main(["run", "start", "--config", str(other), "--mock"]) == 0
    capsys.readouterr()
    assert wt.latest_run().name != first  # the other spec ran last...
    assert wt.resolve_target(str(cfg)).resolve()[0].run_id == first  # ...but cfg follows its own run


def test_malformed_run_yaml_fails_fast(job_data_dir, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("just a string")
    with pytest.raises(ServiceError, match="not a valid run YAML"):
        wt.resolve_target(str(bad))
    schema_bad = tmp_path / "schema.yaml"
    schema_bad.write_text("schema: sandbox.run/v1\nrun_id: x\ntask: not-a-task\n")
    with pytest.raises(ServiceError, match="not a valid run YAML"):
        wt.resolve_target(str(schema_bad))


def test_cli_reports_a_malformed_run_yaml_without_a_traceback(job_data_dir, tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("just a string")
    assert cli.main(["web", str(bad), "--no-browser"]) != 0
    err = capsys.readouterr().err
    assert "not a valid run YAML" in err and "Traceback" not in err


def test_a_file_that_is_neither_yaml_nor_a_run_is_rejected(job_data_dir, tmp_path):
    other = tmp_path / "notes.txt"
    other.write_text("hello")
    with pytest.raises(ServiceError, match="not a run YAML"):
        wt.resolve_target(str(other))


def test_run_name_shortcut_resolves_config_runs(job_data_dir, tmp_path, monkeypatch):
    from mailroom_sandbox import paths

    (tmp_path / "config" / "runs").mkdir(parents=True)
    _spec(tmp_path / "config" / "runs" / "my-smoke.yaml", "my-smoke-run")
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)
    _run("my-smoke-run")
    target = wt.resolve_target("my-smoke")
    assert "my-smoke.yaml" in target.describe and target.resolve()[0].run_id == "my-smoke-run"


def _fake_experiment(monkeypatch, folder: Path, run_ids: list[str]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "experiment.yaml"
    path.write_text("schema: sandbox.experiment/v1\n")
    runs = [(folder / f"{r}.yaml", SimpleNamespace(run_id=r)) for r in run_ids]
    plan = SimpleNamespace(study=folder.name, design="paired")

    def fake_load(p):
        p = Path(p).resolve()
        if p != path.resolve():
            raise ServiceError(f"unknown experiment {p}")
        return p, plan, runs

    monkeypatch.setattr(exp_mod, "_load", fake_load)
    return path


def test_experiment_target_seeds_the_marker_and_follows_it(job_data_dir, tmp_path, monkeypatch):
    path = _fake_experiment(monkeypatch, tmp_path / "study-a", ["exp-r1", "exp-r2"])
    _run("exp-r1")
    for spelled in (str(path), str(path.parent)):
        target = wt.resolve_target(spelled)
        assert target.follow == path.parent / "current-run"
        assert target.resolve()[0].run_id == "exp-r1"
        assert target.campaign("exp-r1") == path
    # The launcher advances the campaign: the watcher follows on the next frame.
    (path.parent / "current-run").write_text("exp-r2\n")
    with pytest.raises(wt.WaitingForRun):
        target.resolve()  # not started yet
    _run("exp-r2")
    assert target.resolve()[0].run_id == "exp-r2"


def test_experiment_marker_is_not_overwritten(job_data_dir, tmp_path, monkeypatch):
    path = _fake_experiment(monkeypatch, tmp_path / "study-b", ["b1", "b2"])
    (path.parent / "current-run").write_text("b2\n")
    wt.experiment_marker(path)
    assert (path.parent / "current-run").read_text() == "b2\n"


def test_follow_marker_edge_cases(job_data_dir, tmp_path):
    marker = tmp_path / "current"
    marker.write_text("")
    with pytest.raises(ServiceError, match="empty"):
        wt.resolve_target(None, follow=str(marker)).resolve()
    cfg = _spec(tmp_path / "fallback.yaml", "fallback-run")
    assert wt.resolve_target(None, follow=str(marker), config=str(cfg)).resolve()[0].run_id == "fallback-run"
    marker.write_text("../nope")
    with pytest.raises(ServiceError, match="valid run ID"):
        wt.resolve_target(None, follow=str(marker)).resolve()
    marker.unlink()
    with pytest.raises(wt.WaitingForRun, match="unreadable"):
        wt.resolve_target(None, follow=str(marker)).resolve()


def test_follow_marker_beside_an_experiment_attaches_the_campaign(job_data_dir, tmp_path):
    (tmp_path / "experiment.yaml").write_text("schema: sandbox.experiment/v1\n")
    marker = tmp_path / "current-run"
    marker.write_text("x\n")
    assert wt.resolve_target(None, follow=str(marker)).campaign("x") == tmp_path / "experiment.yaml"


def test_campaign_for_run_finds_the_study_skips_broken_ones_and_caches(tmp_path, monkeypatch):
    good, broken = tmp_path / "good", tmp_path / "broken"
    calls = []

    def fake_load(p):
        calls.append(Path(p).parent.name)
        if Path(p).parent == broken:
            raise ServiceError("malformed")
        return p, None, [(None, SimpleNamespace(run_id="hit"))]

    monkeypatch.setattr(exp_mod, "_load", fake_load)
    monkeypatch.setattr(wt, "_experiment_dirs", lambda: [broken, good])
    cache: dict = {}
    assert wt.campaign_for_run("hit", cache) == good / "experiment.yaml"
    assert wt.campaign_for_run("miss", cache) is None
    n = len(calls)
    assert wt.campaign_for_run("hit", cache) == good / "experiment.yaml" and len(calls) == n


# ── CLI wiring ──────────────────────────────────────────────────────────────

@pytest.fixture
def served(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(web_mod, "serve_watch_web", lambda **kw: seen.update(kw) or 0)
    return seen


def test_sandbox_web_is_watch_web(job_data_dir, served):
    _run("cli-run")
    assert cli.main(["web", "cli-run", "--port", "0", "--no-browser"]) == 0
    store, _ = served["resolve"]()
    assert store.run_id == "cli-run" and served["port"] == 0 and served["open_browser"] is False
    assert callable(served["campaign_path"])


def test_sandbox_web_with_no_runs_still_serves(job_data_dir, served):
    assert cli.main(["web", "--no-browser"]) == 0
    with pytest.raises(wt.WaitingForRun):
        served["resolve"]()


def test_sandbox_watch_terminal_with_no_runs_explains_and_exits(job_data_dir, capsys):
    assert cli.main(["watch", "--once"]) == 2
    assert "waiting for a run" in capsys.readouterr().err


def test_watch_positional_target_reaches_the_terminal_watcher(job_data_dir, monkeypatch):
    from mailroom_sandbox import watch as watch_mod

    _run("term-run")
    seen = {}
    monkeypatch.setattr(watch_mod, "watch", lambda **kw: seen.update(kw) or 0)
    assert cli.main(["watch", "term-run", "--once"]) == 0
    assert seen["resolve"]()[0].run_id == "term-run" and seen["once"] is True


def test_web_demo_honours_cap_usd(monkeypatch, served):
    assert cli.main(["web", "--demo", "--cap-usd", "12.5", "--no-browser"]) == 0
    assert served["cap_usd"] == 12.5


def test_terminal_watch_resolves_the_live_target_once_at_startup(job_data_dir, tmp_path, monkeypatch):
    from mailroom_sandbox import watch as watch_mod

    first = _run("startup-a")
    second = _run("startup-b")
    answers = iter([(first, "app"), (second, "app"), (second, "app")])
    calls = []

    def resolve():
        calls.append(1)
        return next(answers)

    monkeypatch.setattr(watch_mod, "start_log_streams", lambda *a, **k: None)
    monkeypatch.setattr(watch_mod, "render_frame", lambda **kw: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        watch_mod.watch(resolve=resolve, ledger=None, once=True, logs=False, serving_dir=tmp_path)
    except KeyboardInterrupt:
        pass
    assert len(calls) == 2  # one startup resolve (was two) + the first frame


def test_web_demo_routes_to_the_dev_server(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "_serve_demo", lambda args: seen.setdefault("pipeline", args.pipeline) is not None and 0)
    assert cli.main(["web", "--demo", "--pipeline", "--no-browser"]) == 0
    assert seen["pipeline"] is True


@pytest.mark.parametrize("argv, message", [
    (["web", "--pipeline"], "--pipeline requires --demo"),
    (["web", "--demo", "some-run"], "--demo cannot watch"),
    (["watch", "some-run", "--config", "x.yaml"], "not both"),
    (["watch", "--port", "1"], "sandbox web"),
    (["watch", "--web", "--once"], "--once"),
])
def test_cli_usage_errors(argv, message, capsys, job_data_dir):
    rc = cli.main(argv)
    assert rc != 0
    captured = capsys.readouterr()
    assert message in captured.err + captured.out


# ── live web session ────────────────────────────────────────────────────────

def _session(target: wt.WatchTarget, tmp_path: Path) -> web_mod.WatchWebSession:
    return web_mod.WatchWebSession(resolve=target.resolve, ledger=None, cap_usd=5.0, times_dir=None, log_path=None,
                                   serving_dir=tmp_path / "serving", interval=0.05, follow_logs=False,
                                   campaign_path=target.campaign)


def _config(state: dict) -> dict:
    return dict(line.split(": ", 1) for line in state["layout"]["configuration"] if ": " in line)


def test_web_session_tracks_new_runs_and_their_locked_configuration(job_data_dir, tmp_path):
    session = _session(wt.resolve_target(None), tmp_path)
    with pytest.raises(wt.WaitingForRun):
        session.refresh()
    session.mark_waiting("waiting for a run")
    _, state = session.snapshot()
    assert state["waiting"] and not state["ok"]

    _run("live-a", concurrency=4, age=30)
    state = session.refresh()
    assert state["snapshot"]["run_id"] == "live-a"
    assert _config(state)["job.concurrency"] == "4"

    _run("live-b", concurrency=32)
    state = session.refresh()
    assert state["snapshot"]["run_id"] == "live-b"
    assert _config(state)["job.concurrency"] == "32"


def test_web_session_picks_up_a_lock_written_after_the_watcher_started(job_data_dir, tmp_path):
    cfg = _spec(tmp_path / "late.yaml", "late-lock")
    session = _session(wt.resolve_target(str(cfg)), tmp_path)
    assert not session.refresh()["layout"]["configuration"]  # not locked yet
    store = RunStore(spec_mod.run_dir("late-lock"))
    store.write_lock({"run_id": "late-lock", "task": "sorter", "engine": {"model": "m"}, "job": {"concurrency": 8}})
    assert _config(session.refresh())["job.concurrency"] == "8"


def test_web_session_attaches_the_campaign_of_the_followed_run(job_data_dir, tmp_path, monkeypatch):
    path = _fake_experiment(monkeypatch, tmp_path / "study-live", ["camp-1"])
    monkeypatch.setattr(wt, "_experiment_dirs", lambda: [path.parent])
    session = _session(wt.resolve_target(None), tmp_path)
    _run("loose-run", age=30)
    assert session.refresh().get("campaign") is None
    _run("camp-1")
    campaign = session.refresh()["campaign"]
    assert campaign["study"] == "study-live" and campaign["current"] == "camp-1"


def test_web_refresh_loop_keeps_the_last_frame_on_a_transient_error(job_data_dir, tmp_path):
    store = _run("steady")
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("disk hiccup")
        return store, "app"

    session = _session(wt.WatchTarget(flaky, "flaky"), tmp_path)
    session.refresh()
    session.interval = 0.01
    import threading

    threading.Thread(target=session.run_refresh_loop, daemon=True).start()
    deadline = time.time() + 2
    while time.time() < deadline and session.snapshot()[1].get("ok") is not False:
        time.sleep(0.01)
    session.stop()
    state = session.snapshot()[1]
    assert state["error"] == "disk hiccup" and state["snapshot"]["run_id"] == "steady"


def test_waiting_keeps_the_last_good_frame_and_clears_on_recovery(job_data_dir, tmp_path):
    marker = tmp_path / "current"
    marker.write_text("frame-a\n")
    _run("frame-a")
    session = _session(wt.resolve_target(None, follow=str(marker)), tmp_path)
    assert session.refresh()["snapshot"]["run_id"] == "frame-a"
    marker.write_text("frame-b\n")  # the campaign advanced to a run that has not started
    with pytest.raises(wt.WaitingForRun):
        session.refresh()
    session.mark_waiting("run frame-b has not started yet")
    state = session.snapshot()[1]
    assert state["waiting"] and state["snapshot"]["run_id"] == "frame-a"  # last frame stays on screen
    _run("frame-b")
    state = session.refresh()
    assert state["snapshot"]["run_id"] == "frame-b" and state["waiting"] is False and state["ok"]


def test_serve_watch_web_starts_while_waiting(job_data_dir, tmp_path, monkeypatch, capsys):
    class FakeServer:
        server_address = ("127.0.0.1", 4321)

        def __init__(self, *_a, **_k):
            pass

        def serve_forever(self):
            raise KeyboardInterrupt

        def shutdown(self):
            pass

        def server_close(self):
            pass

    monkeypatch.setattr(web_mod, "ThreadingHTTPServer", FakeServer)
    target = wt.resolve_target(None)
    assert web_mod.serve_watch_web(resolve=target.resolve, ledger=None, serving_dir=tmp_path,
                                   open_browser=False, logs=False) == 0
    assert "127.0.0.1:4321" in capsys.readouterr().err


def test_mock_run_end_to_end_is_followed_by_a_bare_watcher(job_data_dir, tmp_path, capsys):
    """A real (mock, no inference) run started after the watcher: it appears with its locked config."""
    session = _session(wt.resolve_target(None), tmp_path)
    cfg = tmp_path / "e2e.yaml"
    cfg.write_text("schema: sandbox.run/v1\nrun_id: e2e-watch\ntask: pipeline\nprofile: ollama\n"
                   "dataset: {provider: file, local_path: data/fixtures/hf/docclass_mini.jsonl, limit: 2, sample_seed: 1}\n"
                   "engine: {kind: vllm-local, model: qwen3:8b, modal: null}\n"
                   "job: {mode: endpoint, mock: true, concurrency: 3}\ntrace: {sink: none}\n")
    assert cli.main(["run", "start", "--config", str(cfg), "--mock"]) == 0
    capsys.readouterr()
    state = session.refresh()
    assert state["snapshot"]["run_id"] == "e2e-watch"
    config = _config(state)
    assert config["job.concurrency"] == "3" and config["job.mock"] == "true"
    assert state["snapshot"]["done"] == 2
    json.dumps(state)  # still what the SSE stream sends
