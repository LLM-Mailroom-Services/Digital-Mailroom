"""Job runner checkpoint/resume tests (DMR-027) — network-free (mock)."""
from __future__ import annotations
import pytest

import json

from mailroom_sandbox.job import preflight
from mailroom_sandbox.job import runner
from mailroom_sandbox.job.spec import DatasetSpec, RunSpec


def _prepped_store(tmp_path, rows=4, run_id="run-r1"):
    path = tmp_path / "f.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(rows):
            fh.write(json.dumps({"id": f"d{i}", "filename": f"{i}.txt", "doc_text": f"t{i}", "expected": "contract" if i % 2 else "insurance_claim", "expected_subclass": "service" if i % 2 else "auto"}) + "\n")
    spec = RunSpec(
        run_id=run_id,
        task="sorter",
        dataset=DatasetSpec(local_path=f"file://{path}", limit=rows),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        job={"mock": True},
    )
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    return RunStore(run_dir(report["run_id"]))


def test_run_job_mock_completes(tmp_path):
    store = _prepped_store(tmp_path, rows=3)
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    assert summary["cursor"] == 3 and summary["ok"] == 3
    items = store.load_items()
    assert [i["index"] for i in items] == [0, 1, 2]
    assert summary["scores"]["exact_match"] == 1.0


def test_run_job_resumes_from_checkpoint(tmp_path):
    store = _prepped_store(tmp_path, rows=4)
    first = runner.run_job(store, mock=None, max_items=2)
    assert first["state"] == "running"
    assert first["cursor"] == 2

    second = runner.run_job(store, mock=None)
    assert second["state"] == "done"
    assert second["cursor"] == 4
    items = store.load_items()
    assert len(items) == 4  # resume never re-runs completed rows


def test_run_record_lands_in_experiment_log(tmp_path):
    store = _prepped_store(tmp_path, rows=2)
    runner.run_job(store, mock=None)
    from mailroom_sandbox.eval.experiment_log import jsonl_path

    log = jsonl_path()
    assert log.is_file()
    text = log.read_text(encoding="utf-8")
    assert store.run_id in text or "sandbox_sorter" in text


# ── DMR-053: whole-run delegation links records to the lock ──────────────────


def test_lock_prompt_source_reads_lock_default(tmp_path):
    from mailroom_sandbox.job.checkpoint import RunStore

    store = RunStore(tmp_path / "run-src")
    store.write_lock({"prompt": {"default": {"source": "local", "file": "sorter_x"}}})
    assert runner._lock_prompt_source(store) == "local"
    assert runner._lock_prompt_variant(store) == "sorter_x"
    store2 = RunStore(tmp_path / "run-src2")
    store2.write_lock({"prompt": {"default": {"source": "code-default"}}})
    assert runner._lock_prompt_source(store2) == "code-default"
    assert runner._lock_prompt_variant(store2) is None


def test_whole_run_delegation_links_record_to_lock(tmp_path, monkeypatch):
    """The delegated runner's record must carry the lock's prompt source,
    spec_hash, and dataset fingerprint (was 'mailroom-default' + unlinked)."""
    from mailroom_sandbox.eval import runners as eval_runners

    captured: dict = {}

    def _fake_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "n": 2,
            "scores": {"exact_match": 0.5},
            "record": {"experiment_name": "sandbox_pipeline_run-x", "scores": {"exact_match": 0.5}},
        }

    monkeypatch.setattr(eval_runners, "run_pipeline_eval", _fake_pipeline)
    store = _prepped_store(tmp_path, rows=2, run_id="run-link")
    result = runner._run_whole_run(store, "pipeline", mock=True, model=None, profile="ollama")
    # code-default lock -> no local variant stem for the runner (overrides are
    # applied in-process); the STAMPED record still names the lock's source.
    assert captured["prompt_version"] is None
    assert result["state"] == "done"
    record = result["result"]["record"]
    assert record["spec_hash"] == store.spec_hash()
    assert record["run_id"] == store.run_id
    assert record["prompt_version"] == "code-default"
    assert record["dataset_fingerprint"] == result["dataset_fingerprint"]
    assert len(record["dataset_fingerprint"]) == 12


# ── Whole-run task delegation (DMR-041) ───────────────────────────────────────

def _whole_run_store(tmp_path, *, task="pipeline", run_id="run-wholerun") -> object:
    path = tmp_path / "f.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(3):
            cls = "insurance_claim" if i % 2 == 0 else "contract"
            fh.write(
                json.dumps(
                    {
                        "id": f"d{i}",
                        "filename": f"{i}.txt",
                        "doc_text": f"t{i}",
                        "expected": cls,
                        "expected_subclass": "auto" if cls == "insurance_claim" else "service",
                    }
                )
                + "\n"
            )
    spec = RunSpec(
        run_id=run_id,
        task=task,
        dataset=DatasetSpec(local_path=f"file://{path}", limit=3),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        job={"mock": True},
    )
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    return RunStore(run_dir(report["run_id"]))


def test_whole_run_pipeline_delegates_and_done(tmp_path):
    store = _whole_run_store(tmp_path, task="pipeline")
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    assert summary["task"] == "pipeline"
    assert summary["scores"]["class_correct"] == 1.0
    assert "stage_correct" in summary["scores"]
    cp = store.read_checkpoint() or {}
    assert cp["state"] == "done"
    assert cp["cursor"] >= 1


def test_whole_run_local_vs_api_delegates(tmp_path):
    store = _whole_run_store(tmp_path, task="local_vs_api")
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    assert summary["task"] == "local_vs_api"
    assert "scores" in summary


def test_whole_run_unknown_task_rejected(tmp_path):
    import pytest

    # DMR-056: validation now lives at spec parse (known_tasks) — a bogus
    # task dies at RunSpec construction, never "locks prepared then dies".
    with pytest.raises(ValueError, match="unknown task"):
        RunSpec(task="bogus")


def test_whole_run_agent_task_delegates(tmp_path):
    # DMR-056: any registered AgentSpec name is a whole-run job task —
    # `task: judge` dispatches to run_isolated_eval without code changes.
    store = _whole_run_store(tmp_path, task="judge")
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    assert summary["task"] == "judge"
    assert "scores" in summary
    cp = store.read_checkpoint() or {}
    assert cp["state"] == "done"


def test_whole_run_pipeline_receives_locked_rows(tmp_path, monkeypatch):
    # DMR-056: whole-run tasks score the LOCKED live dataset (3 rows here),
    # not the 10-row fixture manifest — the live-data integration contract.
    captured: dict = {}

    def spy(**kwargs):
        captured["rows"] = kwargs.get("rows")
        captured["n"] = len(kwargs.get("rows") or [])
        return {"scores": {"class_correct": 1.0, "n": captured["n"]}, "n": captured["n"]}

    monkeypatch.setattr(runner.eval_runners, "run_pipeline_eval", spy)
    store = _whole_run_store(tmp_path, task="pipeline")
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    assert captured["n"] == 3, "whole-run pipeline must score the locked rows"


def test_registering_new_agent_spec_is_the_extension_point(tmp_path, monkeypatch):
    # THE DMR-056 extension-point contract: registering ONE AgentSpec is the
    # one-file change; the new task then passes spec validation, is a whole-run
    # job task, and dispatches — no enum, no dispatch table, no spec field.
    from mailroom_sandbox.eval import agents as agents_mod
    from mailroom_sandbox.eval.agents import AgentSpec
    from mailroom_sandbox.job.spec import known_tasks

    spec = AgentSpec(
        name="dummy_agent",
        observation="classify-document",
        mock_predict=lambda row: {"doc_type": "contract"},
        score_one=lambda row, pred: {"match": 1.0},
    )
    agents_mod.SPECS["dummy_agent"] = spec
    try:
        assert "dummy_agent" in known_tasks()  # validation accepts it
        assert "dummy_agent" in runner._agent_task_names()  # dispatch accepts it
        store = _whole_run_store(tmp_path, task="dummy_agent")
        summary = runner.run_job(store, mock=None)
        assert summary["state"] == "done"
        assert summary["task"] == "dummy_agent"
    finally:
        agents_mod.SPECS.pop("dummy_agent", None)


def test_whole_run_failure_writes_failed_checkpoint(tmp_path, monkeypatch):
    store = _whole_run_store(tmp_path, task="pipeline")

    def _boom(*a, **kw):
        raise RuntimeError("delegated runner exploded")

    monkeypatch.setattr(runner.eval_runners, "run_pipeline_eval", _boom)
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "failed"
    assert "delegated runner exploded" in summary["error"]
    cp = store.read_checkpoint() or {}
    assert cp["state"] == "failed"


pytestmark = pytest.mark.usefixtures("job_data_dir")
