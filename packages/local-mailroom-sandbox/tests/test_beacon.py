"""mailroom.beacon/v1 writer: atomic heartbeats that never break the job."""

import json
import os

import pytest

from mailroom_sandbox.tui import beacon as bmod


def _read(root, job):
    return json.loads((root / f"{job}.json").read_text())


def test_update_writes_an_atomic_heartbeat(tmp_path):
    b = bmod.Beacon("job-1", package="local-mailroom-sandbox", title="corr n=100", root=tmp_path)
    b.update(phase="SORTING", done=3, total=10, ok=2, errors=1, metrics={"p50_s": 6.8})
    d = _read(tmp_path, "job-1")
    assert d["schema"] == "mailroom.beacon/v1"
    assert (d["job_id"], d["package"], d["title"], d["state"]) == ("job-1", "local-mailroom-sandbox", "corr n=100", "running")
    assert (d["done"], d["total"], d["ok"], d["errors"], d["phase"]) == (3, 10, 2, 1, "SORTING")
    assert d["metrics"] == {"p50_s": 6.8} and d["pid"] == os.getpid() and d["host"]
    assert d["started_at"] <= d["updated_at"] and d["finished_at"] is None
    assert not list(tmp_path.glob("*.tmp"))  # tmp+rename leaves no partials


def test_metrics_merge_across_updates(tmp_path):
    b = bmod.Beacon("j", package="p", root=tmp_path)
    b.update(metrics={"a": 1})
    b.update(metrics={"b": 2})
    assert _read(tmp_path, "j")["metrics"] == {"a": 1, "b": 2}


def test_log_appends_lines(tmp_path):
    b = bmod.Beacon("j", package="p", root=tmp_path)
    b.log("first")
    b.log("second\n")
    assert (tmp_path / "j.log").read_text().splitlines() == ["first", "second"]


def test_finish_marks_terminal_state(tmp_path):
    b = bmod.Beacon("j", package="p", root=tmp_path)
    b.finish("done")
    d = _read(tmp_path, "j")
    assert d["state"] == "done" and d["finished_at"] is not None


def test_context_manager_marks_failed_and_reraises(tmp_path):
    with pytest.raises(ValueError):
        with bmod.Beacon("j", package="p", root=tmp_path) as b:
            b.update(done=1, total=2)
            raise ValueError("boom")
    d = _read(tmp_path, "j")
    assert d["state"] == "failed" and "ValueError: boom" in d["metrics"]["error"]


def test_context_manager_marks_done_on_success(tmp_path):
    with bmod.Beacon("j", package="p", root=tmp_path) as b:
        b.update(done=2, total=2)
    assert _read(tmp_path, "j")["state"] == "done"


def test_beacon_never_raises_into_the_job(tmp_path):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("file where the beacon dir should be")
    b = bmod.Beacon("j", package="p", root=blocker)  # unwritable root
    b.update(done=1)
    b.log("x")
    b.finish("done")  # all silently no-op


def test_root_defaults_to_env_then_home(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BEACON_DIR", str(tmp_path / "env"))
    assert bmod.beacon_root() == tmp_path / "env"
    monkeypatch.delenv("MAILROOM_BEACON_DIR")
    assert bmod.beacon_root().parts[-2:] == (".mailroom", "jobs")


def test_job_ids_are_sanitized_to_safe_filenames(tmp_path):
    b = bmod.Beacon("../../etc/passwd run 1", package="p", root=tmp_path)
    b.update(done=1)
    files = [p.name for p in tmp_path.iterdir()]
    assert files == [f"{b.job_id}.json"] and "/" not in b.job_id and ".." not in b.job_id


def test_finish_sets_a_terminal_phase_unless_given(tmp_path):
    b = bmod.Beacon("j", package="p", root=tmp_path)
    b.update(phase="SCORING")
    b.finish("done")
    assert _read(tmp_path, "j")["phase"] == "DONE"
    b2 = bmod.Beacon("k", package="p", root=tmp_path)
    b2.finish("failed", phase="PREFLIGHT")
    assert _read(tmp_path, "k")["phase"] == "PREFLIGHT"
