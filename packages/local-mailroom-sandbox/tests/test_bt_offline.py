"""SAND-032: offline Braintrust-Experiment-shaped rows + guarded dispose."""

import json
from pathlib import Path

import pytest

from mailroom_sandbox.job.bt_offline import dispose, write_experiment
from mailroom_sandbox.job.checkpoint import RunStore


def _store(tmp_path):
    s = RunStore(tmp_path / "runs" / "sand032-x")
    s.write_lock({"run_id": "sand032-x", "engine": {
        "model": "Qwen/Qwen3-8B-AWQ", "vllm": {"kv_cache_dtype": "fp8"},
        "modal": {"gpu": "L4", "max_containers": 2}}})
    s.append_item({"item_id": "a", "ok": True, "pred": {"k": 1},
                   "score": {"overall_extraction_score": 0.4, "parse_error": False},
                   "latency_ms": 1500.0, "prompt_tokens": 100, "completion_tokens": 20})
    s.append_item({"item_id": "b", "ok": False, "error": "OpenAIConnectionError: x",
                   "pred": None, "score": {}, "latency_ms": None})
    return s


def test_write_experiment_shape(tmp_path):
    out = write_experiment(_store(tmp_path), out_root=tmp_path / "bt", git_commit="abc123")
    meta = json.loads((out / "experiment.json").read_text())
    assert meta["name"] == "sand032-x"
    assert meta["metadata"]["engine"]["vllm"]["kv_cache_dtype"] == "fp8"
    assert meta["metadata"]["git_commit"] == "abc123"
    rows = [json.loads(line) for line in (out / "rows.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    assert set(rows[0]) >= {"id", "input", "output", "expected", "scores", "metrics", "metadata"}
    assert rows[0]["scores"] == {"overall_extraction_score": 0.4}  # bools are not scores
    assert rows[0]["metrics"]["latency_seconds"] == 1.5
    assert rows[1]["metadata"] == {"ok": False, "error": "OpenAIConnectionError: x"}
    assert rows[1]["metrics"]["latency_seconds"] is None


def test_dispose_refuses_untracked_report(tmp_path):
    out = write_experiment(_store(tmp_path), out_root=tmp_path / "bt", git_commit="abc")
    with pytest.raises(RuntimeError, match="not tracked"):
        dispose("sand032-x", out_root=tmp_path / "bt", report=Path("reports/x.md"),
                is_tracked=lambda p: False)
    assert out.exists()


def test_dispose_removes_after_tracked_report(tmp_path):
    out = write_experiment(_store(tmp_path), out_root=tmp_path / "bt", git_commit="abc")
    assert dispose("sand032-x", out_root=tmp_path / "bt", report=Path("reports/x.md"),
                   is_tracked=lambda p: True) is True
    assert not out.exists()


def test_dispose_missing_dir_returns_false(tmp_path):
    assert dispose("nope", out_root=tmp_path / "bt", report=Path("r.md"),
                   is_tracked=lambda p: True) is False


def test_cli_export_then_guarded_dispose(tmp_path, monkeypatch, capsys):
    from mailroom_sandbox import paths
    from mailroom_sandbox.cli import main
    from mailroom_sandbox.job import bt_offline
    from mailroom_sandbox.job import spec as spec_mod
    from mailroom_sandbox.paths import config_dir

    cfg = config_dir() / "runs" / "run-50-correspondence-specialist-awq.yaml"
    runs = tmp_path / "runs"
    monkeypatch.setattr(spec_mod, "runs_root", lambda: runs)
    monkeypatch.setattr(paths, "runtime_dir", lambda: tmp_path)
    store = RunStore(runs / "run-50-correspondence-specialist-awq")
    store.write_lock({"run_id": "run-50-correspondence-specialist-awq", "engine": {}})
    store.append_item({"item_id": "a", "ok": True, "score": {}, "latency_ms": 1.0})

    assert main(["run", "export-bt", "--config", str(cfg)]) == 0
    out = tmp_path / "bt_experiments" / "run-50-correspondence-specialist-awq"
    assert (out / "rows.jsonl").is_file()

    monkeypatch.setattr(bt_offline, "git_tracked", lambda p: False)
    assert main(["run", "dispose", "--config", str(cfg), "--report", "reports/nope.md"]) == 1
    assert out.exists()
    monkeypatch.setattr(bt_offline, "git_tracked", lambda p: True)
    assert main(["run", "dispose", "--config", str(cfg), "--report", "reports/x.md"]) == 0
    assert not out.exists()
