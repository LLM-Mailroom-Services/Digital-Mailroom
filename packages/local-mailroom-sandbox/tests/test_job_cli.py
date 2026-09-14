"""CLI wiring tests (DMR-027) — network-free."""

from __future__ import annotations

import json

import pytest

from mailroom_sandbox.cli import main


def _write_run_yaml(tmp_path) -> str:
    import yaml

    path = tmp_path / "run.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "run_id": "cli-smoke",
                "task": "sorter",
                "dataset": {
                    "provider": "file",
                    "local_path": "file:///tmp/does-not-matter.jsonl",
                    "limit": 2,
                },
                "engine": {"kind": "vllm-local", "modal": None},
                "job": {"mock": True},
                "trace": {"sink": "none"},
            }
        ),
        encoding="utf-8",
    )
    return str(path)


def test_prompts_list(capsys):
    rc = main(["prompts", "list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "sorter" in out


def test_metrics_compare_requires_runs(capsys):
    with pytest.raises(SystemExit):
        main(["metrics", "compare"])


def test_run_parser_has_lifecycle(tmp_path, capsys):
    import json as _json

    # A config pointing at a non-existent dataset fails harmlessly under dry-run.
    path = tmp_path / "run.yaml"
    import yaml

    path.write_text(
        yaml.safe_dump(
            {
                "run_id": "cli-pf",
                "dataset": {"provider": "file", "local_path": "file:///tmp/nope.jsonl"},
                "engine": {"kind": "vllm-local", "modal": None},
                "trace": {"sink": "none"},
            }
        ),
        encoding="utf-8",
    )
    rc = main(["run", "preflight", "--config", str(path), "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"status": "prepared"' in out

def test_run_status_resolves_run_id_from_config(tmp_path, capsys):
    # status/resume/cancel accept --config <run.yaml> alone: the embedded
    # run_id is resolved from the spec (DMR-058).
    rc = main(["run", "status", "--config", _write_run_yaml(tmp_path)])
    assert rc == 1  # no lock yet, but the run_id resolved (not SystemExit)
    out = capsys.readouterr().out
    assert '"run_id": "cli-smoke"' in out
    assert "no locked run found" in out


def test_run_status_still_requires_some_id(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["run", "status"])


def test_watch_remote_stalls_out_after_deadline(tmp_path, monkeypatch, capsys):
    # hub#41: a worker that dies before its first state_dict.put must not
    # leave the watch polling 'running' forever — no heartbeat + a call that
    # is provably not alive fails the watch with exit 1.
    from mailroom_sandbox import cli
    from mailroom_sandbox.job import remote as job_remote
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    store = RunStore(run_dir("run-watch"))
    store.write_lock({"spec_hash": "s1"})
    store.write_checkpoint(
        state="running", cursor=0, total=2, remote={"call_id": "call-x", "app": "a", "fn": "f"}
    )

    clock = {"t": 0.0}
    monkeypatch.setattr("time.monotonic", lambda: clock["t"])
    monkeypatch.setattr("time.sleep", lambda s: clock.__setitem__("t", clock["t"] + s))
    monkeypatch.setattr(job_remote, "read_progress", lambda store: {"state": "running"})
    monkeypatch.setattr(job_remote, "is_alive", lambda store: False)
    rc = cli._watch_remote(store, None)
    assert rc == 1
    out = capsys.readouterr().out
    assert "stalled" in out


pytestmark = pytest.mark.usefixtures("job_data_dir")
