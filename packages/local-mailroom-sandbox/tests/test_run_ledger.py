"""Run ledger: one signed row per gated start/resume, closed with ✓ or ✗ at a terminal state."""

from __future__ import annotations

import json
import os
from pathlib import Path

from mailroom_sandbox.job import ledger
from mailroom_sandbox.job.checkpoint import RunStore

LOCK = {"run_id": "exp-a", "spec_hash": "abcdef0123456789", "job": {"api_cost_cap_usd": 1.2}}


def test_tests_never_touch_the_tracked_ledger():
    """Tests never touch the tracked ledger."""
    assert ledger.ledger_path() != Path(__file__).resolve().parents[1] / "reports" / "run-ledger.md"
    assert os.environ["SANDBOX_RUN_LEDGER"]


def test_signed_row_then_done_marks_check(tmp_path):
    """Signed row then done marks check."""
    path = tmp_path / "ledger.md"
    ledger.record_signed(LOCK, initials="AB", action="start", config="config/runs/x.yaml", rows_total=10, path=path)
    [row] = ledger.rows(path)
    assert row["initials"] == "AB" and row["run_id"] == "exp-a" and row["spec"] == "abcdef012345"
    assert row["rows"] == "10" and row["api_cap_usd"] == "1.2" and row["result"] == ""
    assert row["signed_utc"].endswith("Z")
    assert ledger.mark_result("exp-a", "abcdef0123456789", ok=True, path=path) == 1
    assert ledger.rows(path)[0]["result"] == ledger.OK
    assert path.read_text().splitlines()[-1].endswith(f"| {ledger.OK} |")
    # A closed row is never rewritten.
    assert ledger.mark_result("exp-a", "abcdef0123456789", ok=False, path=path) == 0


def test_failure_marks_x_and_other_runs_untouched(tmp_path):
    """Failure marks x and other runs untouched."""
    path = tmp_path / "ledger.md"
    ledger.record_signed(LOCK, initials="AB", action="start", path=path)
    ledger.record_signed({**LOCK, "run_id": "exp-b"}, initials="CD", action="start", path=path)
    ledger.mark_result("exp-a", LOCK["spec_hash"], ok=False, path=path)
    a, b = ledger.rows(path)
    assert a["result"] == ledger.FAILED and b["result"] == ""


def test_paused_then_resumed_rows_close_together(tmp_path):
    """Paused then resumed rows close together."""
    path = tmp_path / "ledger.md"
    ledger.record_signed(LOCK, initials="AB", action="start", path=path)
    ledger.record_signed(LOCK, initials="AB", action="resume", path=path)
    assert ledger.mark_result("exp-a", LOCK["spec_hash"], ok=True, path=path) == 2


def test_new_generation_does_not_close_old_spec(tmp_path):
    """New generation does not close old spec."""
    path = tmp_path / "ledger.md"
    ledger.record_signed(LOCK, initials="AB", action="start", path=path)
    assert ledger.mark_result("exp-a", "ffff00000000aaaa", ok=True, path=path) == 0


def test_pipes_cannot_break_the_table(tmp_path):
    """Pipes cannot break the table."""
    path = tmp_path / "ledger.md"
    ledger.record_signed({**LOCK, "run_id": "a|b"}, initials="AB", action="start", config="x|y.yaml", path=path)
    [row] = ledger.rows(path)
    assert row["run_id"] == "a/b"


def test_terminal_checkpoint_closes_the_row(tmp_path):
    """Terminal checkpoint closes the row."""
    store = RunStore(tmp_path / "runs" / "exp-a")
    store.dir.mkdir(parents=True, exist_ok=True)
    (store.dir / "spec.lock.json").write_text(json.dumps(LOCK))
    ledger.record_signed(LOCK, initials="AB", action="start")
    store.write_checkpoint(state="running", cursor=0, total=1)
    assert ledger.rows()[0]["result"] == ""
    store.write_checkpoint(state="done", cursor=1, total=1)
    assert ledger.rows()[0]["result"] == ledger.OK


def test_close_run_logs_and_continues_when_the_ledger_is_unwritable(monkeypatch, caplog):
    """A ledger write error must not fail the run's terminal checkpoint."""
    def _boom(*_args, **_kwargs):
        raise PermissionError("read-only checkout")

    monkeypatch.setattr(ledger, "mark_result", _boom)

    class _Store:
        run_id = "exp-a"

        def terminal(self):
            return True

        def state(self):
            return "done"

        def spec_hash(self):
            return "abcdef0123456789"

    with caplog.at_level("WARNING"):
        assert ledger.close_run(_Store()) == 0
    assert "run ledger not updated for exp-a" in caplog.text


def test_finalize_remote_closes_the_ledger_row(tmp_path, monkeypatch):
    """A Modal run followed with --watch closes its row when the terminal checkpoint is synced."""
    from mailroom_sandbox import cli
    from mailroom_sandbox.job import remote as job_remote

    closed = []
    monkeypatch.setattr(job_remote, "pull_run_dir", lambda store: (0, ""))
    monkeypatch.setattr(ledger, "close_run", lambda store: closed.append(store) or 1)

    class _Store:
        dir = tmp_path

    store = _Store()
    assert cli._finalize_remote(store) is True
    assert closed == [store]
