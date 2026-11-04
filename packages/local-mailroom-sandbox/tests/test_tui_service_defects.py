"""Regression tests for the TUI-facing defects found while wiring services into the board.

Each test was written against the unfixed code first (see the PR description for the
failure output): D9 `beacon update --finish` left the phase untouched, T1 a paused/limited
run was stamped terminal "done", T2 the Modal log follower leaked its `modal app logs -f`
child when asked to stop, T3 a busy board port escaped as a traceback.
"""

from __future__ import annotations

import json
import socket
import threading
import time

import pytest

from mailroom_sandbox import cli


@pytest.fixture(autouse=True)
def _beacon_root(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BEACON_DIR", str(tmp_path / "beacons"))
    return tmp_path / "beacons"


def _beacon(root, job):
    return json.loads((root / f"{job}.json").read_text(encoding="utf-8"))


# D9 ------------------------------------------------------------------------------------


@pytest.mark.parametrize(("finish", "phase"), [("done", "DONE"), ("failed", "FAILED")])
def test_beacon_update_finish_sets_the_terminal_phase(_beacon_root, finish, phase):
    """`beacon update --finish X` used to pass phase=None, so `setdefault` never applied."""
    assert cli.main(["beacon", "update", "--job", "j1", "--package", "p", "--phase", "SORTING", "--done", "3"]) == 0
    assert cli.main(["beacon", "update", "--job", "j1", "--package", "p", "--finish", finish]) == 0
    row = _beacon(_beacon_root, "j1")
    assert row["state"] == finish and row["phase"] == phase


def test_beacon_update_finish_keeps_an_explicit_phase(_beacon_root):
    assert cli.main(["beacon", "update", "--job", "j2", "--package", "p", "--phase", "SCORED", "--finish", "done"]) == 0
    assert _beacon(_beacon_root, "j2")["phase"] == "SCORED"


# T1 ------------------------------------------------------------------------------------


@pytest.mark.parametrize("state", ["paused", "running"])
def test_a_paused_or_limited_run_is_not_published_as_done(_beacon_root, state):
    """`run start --max-items N` returns `running`, a cancelled run `paused`: neither is finished."""
    from mailroom_sandbox.job.runner import _beacon_hook

    _wrapped, finish = _beacon_hook("r-paused", task="sorter")
    finish({"state": state, "cursor": 3, "total": 10})
    row = _beacon(_beacon_root, "r-paused")
    assert row["state"] not in ("done", "failed")
    assert row["phase"] == state.upper()
    assert (row["done"], row["total"]) == (3, 10)


@pytest.mark.parametrize(("state", "beacon_state"), [("done", "done"), ("failed", "failed"), ("cancelled", "failed")])
def test_terminal_run_states_still_finish_the_beacon(_beacon_root, state, beacon_state):
    from mailroom_sandbox.job.runner import _beacon_hook

    _wrapped, finish = _beacon_hook("r-end", task="sorter")
    finish({"state": state, "cursor": 10, "total": 10})
    assert _beacon(_beacon_root, "r-end")["state"] == beacon_state


# T2 ------------------------------------------------------------------------------------


def test_stopping_the_log_follower_terminates_the_modal_child(fake_bin):
    """The follower blocked reading a quiet `modal app logs -f` and never noticed `stop`."""
    from mailroom_sandbox import watch

    fake_bin.add("modal", sleep=30)
    stop = threading.Event()
    sink: list[str] = []
    thread = threading.Thread(target=watch._stream_logs, args=("sandbox-vllm", sink, stop), daemon=True)
    thread.start()
    deadline = time.time() + 5
    while not fake_bin.calls("modal") and time.time() < deadline:
        time.sleep(0.05)
    assert fake_bin.calls("modal"), "follower never started modal"
    stop.set()
    thread.join(timeout=5)
    assert not thread.is_alive(), "log follower thread did not end after stop"


# T3 ------------------------------------------------------------------------------------


@pytest.fixture
def busy_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    yield sock.getsockname()[1]
    sock.close()


def test_board_on_a_busy_port_is_one_error_line(busy_port, capsys):
    assert cli.main(["board", "--port", str(busy_port), "--no-browser"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "already in use" in err and "Traceback" not in err
