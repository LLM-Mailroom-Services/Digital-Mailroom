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
    """`run status` without --run-id or --config exits instead of guessing."""
    with pytest.raises(SystemExit):
        main(["run", "status"])


def test_run_resume_passes_resolved_config_path(tmp_path, monkeypatch):
    """Resume preflight receives the resolved --config path, not the raw string."""
    from argparse import Namespace
    from pathlib import Path
    from types import SimpleNamespace

    from mailroom_sandbox import cli
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    nested = tmp_path / "nested"
    nested.mkdir()
    cfg = nested / "run.yaml"
    cfg.write_text("schema: sandbox.run/v1\n", encoding="utf-8")
    store = RunStore(run_dir("cli-resume"))
    store.write_lock({"run_id": "cli-resume", "spec_hash": "s1"})

    spec = SimpleNamespace(
        profile="ollama",
        run_id="cli-resume",
        engine=None,
        job=SimpleNamespace(mock=True),
    )
    seen: dict[str, object] = {}

    monkeypatch.chdir(nested)
    monkeypatch.setattr(cli, "activate", lambda *a, **k: None)
    monkeypatch.setattr("mailroom_sandbox.job.spec.load_run_spec", lambda path: spec)

    def fake_preflight(loaded, *, run_id="", config_path=None, **kwargs):
        """Record the config_path passed into preflight."""
        seen["config_path"] = config_path
        return {"status": "prepared", "run_id": run_id, "checks": []}

    monkeypatch.setattr("mailroom_sandbox.job.preflight.preflight", fake_preflight)
    monkeypatch.setattr(cli, "_job_mode", lambda store: "endpoint")
    monkeypatch.setattr(cli, "_run_endpoint", lambda store, args: {"state": "done"})

    rc = cli._cmd_run_resume(
        Namespace(
            config="run.yaml",
            run_id="cli-resume",
            force=False,
            watch=False,
            model=None,
            agent_models=[],
        )
    )
    assert rc == 0
    assert seen["config_path"] == cfg.resolve()
    assert Path(seen["config_path"]).is_absolute()


def test_run_resume_stops_when_preflight_fails(tmp_path, monkeypatch):
    """A failed resume preflight must not start endpoint execution."""
    from argparse import Namespace
    from types import SimpleNamespace

    from mailroom_sandbox import cli
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    cfg = tmp_path / "run.yaml"
    cfg.write_text("schema: sandbox.run/v1\n", encoding="utf-8")
    store = RunStore(run_dir("cli-resume-fail"))
    store.write_lock({"run_id": "cli-resume-fail", "spec_hash": "s1"})
    spec = SimpleNamespace(
        profile="ollama",
        run_id="cli-resume-fail",
        engine=None,
        job=SimpleNamespace(mock=True),
    )
    ran = {"endpoint": False}

    monkeypatch.setattr(cli, "activate", lambda *a, **k: None)
    monkeypatch.setattr("mailroom_sandbox.job.spec.load_run_spec", lambda path: spec)
    monkeypatch.setattr(
        "mailroom_sandbox.job.preflight.preflight",
        lambda *a, **k: {"status": "failed", "run_id": "cli-resume-fail", "checks": []},
    )
    monkeypatch.setattr(cli, "_job_mode", lambda store: "endpoint")
    monkeypatch.setattr(cli, "_run_endpoint", lambda store, args: ran.__setitem__("endpoint", True) or {"state": "done"})

    rc = cli._cmd_run_resume(
        Namespace(
            config=str(cfg),
            run_id="cli-resume-fail",
            force=False,
            watch=False,
            model=None,
            agent_models=[],
        )
    )
    assert rc == 1
    assert ran["endpoint"] is False


def test_watch_remote_stalls_out_after_deadline(tmp_path, monkeypatch, capsys):
    """A dead worker with no heartbeat must fail the watch instead of polling forever."""
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
