"""SSH tunnel lifecycle: no silent failures, no stale pidfiles, no killing the wrong process.

Before: `spawn` discarded ssh's stderr and never checked the port, so a refused key
printed "tunnel up" and recorded a pid for a dead process; `terminate` raised on a stale
pid and kept the pidfile forever; `kill <pid>` could hit an unrelated process that had
reused the pid; `status` never checked liveness. ssh is a fake shim; nothing leaves the host.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import pytest

from mailroom_sandbox import cli, tunnel
from mailroom_sandbox.overlay import load_profile
from mailroom_sandbox.tunnel import TunnelError


@pytest.fixture(autouse=True)
def _tunnel_env(monkeypatch, tmp_path):
    monkeypatch.setattr("mailroom_sandbox.tunnel.repo_root", lambda: tmp_path)
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    monkeypatch.setenv("SANDBOX_TUNNEL_HOST", "gpu.example")
    monkeypatch.setenv("SANDBOX_TUNNEL_USER", "alice")
    monkeypatch.setenv("SANDBOX_PROFILE", "vllm-remote")  # the profile that has a tunnel: block
    for name in ("SANDBOX_TUNNEL_PORT", "SANDBOX_TUNNEL_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def spec():
    return tunnel.tunnel_spec(load_profile("vllm-remote"))


@pytest.fixture
def spawned(monkeypatch):
    """Record every child `spawn` starts and make sure none outlives the test."""
    procs: list[subprocess.Popen] = []
    real = subprocess.Popen

    def spy(*a, **k):
        proc = real(*a, **k)
        procs.append(proc)
        return proc

    monkeypatch.setattr(tunnel.subprocess, "Popen", spy)
    yield procs
    for proc in procs:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)


def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def test_spawn_names_the_missing_ssh_binary(fake_bin, spec):
    with pytest.raises(TunnelError, match="ssh"):
        tunnel.spawn(spec, wait=0.5)


def test_spawn_surfaces_ssh_stderr_and_leaves_no_pidfile(fake_bin, spec, monkeypatch, tmp_path, spawned):
    fake_bin.add("ssh", stderr="alice@gpu.example: Permission denied (publickey).\n", rc=255)
    monkeypatch.setattr(tunnel, "is_up", lambda port, **k: False)
    with pytest.raises(TunnelError, match="Permission denied"):
        tunnel.spawn(spec, wait=5.0)
    assert not tunnel.pidfile(spec.profile).exists()


def test_spawn_kills_a_forward_that_never_opens_the_port(fake_bin, spec, monkeypatch, spawned):
    fake_bin.add("ssh", sleep=30)
    monkeypatch.setattr(tunnel, "is_up", lambda port, **k: False)
    started = time.monotonic()
    with pytest.raises(TunnelError, match="did not open"):
        tunnel.spawn(spec, wait=0.6)
    assert time.monotonic() - started < 10
    assert not tunnel.pidfile(spec.profile).exists()
    assert spawned and spawned[0].poll() is not None, "the stuck ssh child must be terminated"


def test_spawn_records_the_pid_once_the_port_answers(fake_bin, spec, monkeypatch, spawned):
    fake_bin.add("ssh", sleep=30)
    answers = iter([False, False, True])  # pre-check, first wait poll, then up
    monkeypatch.setattr(tunnel, "is_up", lambda port, **k: next(answers, True))
    pid = tunnel.spawn(spec, wait=5.0)
    assert pid == spawned[0].pid
    assert tunnel.read_pid(spec.profile) == pid


def test_interrupt_during_startup_reaps_child(fake_bin, spec, monkeypatch, spawned):
    fake_bin.add("ssh", sleep=30)
    monkeypatch.setattr(tunnel, "is_up", lambda port, **kw: False)

    real_sleep = time.sleep
    fired = []

    def interrupt(seconds):
        # Only the startup poll is interrupted: Popen.wait(timeout=) polls with
        # time.sleep too, and the cleanup's reap must still be able to wait.
        if not fired:
            fired.append(seconds)
            raise KeyboardInterrupt
        real_sleep(seconds)

    monkeypatch.setattr(tunnel.time, "sleep", interrupt)
    with pytest.raises(KeyboardInterrupt):
        tunnel.spawn(spec)
    assert spawned and spawned[0].poll() is not None
    assert not tunnel.pidfile(spec.profile).exists()


def test_spawn_still_refuses_to_double_forward(fake_bin, spec, monkeypatch):
    fake_bin.add("ssh")
    monkeypatch.setattr(tunnel, "is_up", lambda port, **k: True)
    with pytest.raises(TunnelError, match="already answers"):
        tunnel.spawn(spec, wait=0.5)
    assert fake_bin.calls("ssh") == []


def test_terminate_clears_a_stale_pidfile_instead_of_raising(spec):
    path = tunnel.pidfile(spec.profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{_dead_pid()}\n", encoding="utf-8")
    assert tunnel.terminate(spec) is None
    assert not path.exists()


def test_terminate_never_kills_a_live_process_that_is_not_ssh(spec):
    """A pid reused by an unrelated process must be left alone (this test process is the victim)."""
    path = tunnel.pidfile(spec.profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{os.getpid()}\n", encoding="utf-8")
    assert tunnel.terminate(spec) is None
    assert not path.exists()
    assert tunnel.is_alive(os.getpid())


def test_terminate_stops_a_live_ssh_forward(fake_bin, spec, spawned):
    shim = fake_bin.add("ssh", sleep=30)
    proc = subprocess.Popen([os.fspath(shim)], start_new_session=True)
    spawned.append(proc)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not tunnel.is_ssh_process(proc.pid):
        time.sleep(0.05)
    path = tunnel.pidfile(spec.profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{proc.pid}\n", encoding="utf-8")
    assert tunnel.terminate(spec) == proc.pid
    proc.wait(timeout=5)
    assert not path.exists()


def test_status_reports_whether_the_recorded_pid_is_alive(fake_bin, spec, capsys):
    path = tunnel.pidfile(spec.profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{_dead_pid()}\n", encoding="utf-8")
    assert cli.main(["tunnel", "status"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["pid"] is not None and report["pid_alive"] is False


def test_down_says_when_it_cleared_a_stale_pidfile(fake_bin, spec, capsys):
    path = tunnel.pidfile(spec.profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{_dead_pid()}\n", encoding="utf-8")
    assert cli.main(["tunnel", "down"]) == 0
    out = capsys.readouterr().out
    assert "stale" in out and not path.exists()


def test_up_without_ssh_is_one_error_line(fake_bin, capsys):
    assert cli.main(["tunnel", "up"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "ssh" in err and "Traceback" not in err


def test_a_non_numeric_ssh_port_is_a_tunnel_error(monkeypatch):
    monkeypatch.setenv("SANDBOX_TUNNEL_PORT", "twenty-two")
    with pytest.raises(TunnelError, match="SANDBOX_TUNNEL_PORT"):
        tunnel.tunnel_spec(load_profile("vllm-remote"))
