"""Job runner checkpoint/resume tests (DMR-027) — network-free (mock)."""
from __future__ import annotations
import pytest

import json

from mailroom_sandbox.job import preflight
from mailroom_sandbox.job import runner
from mailroom_sandbox.job.spec import DatasetSpec, RunSpec


def _prepped_store(tmp_path, rows=4, run_id="run-r1", job=None):
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
        job=job or {"mock": True},
    )
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    return RunStore(run_dir(report["run_id"]))


def _append_item(store, index, predicted, expected, ok=True, error=None):
    store.append_item(
        {
            "item_id": f"d{index}",
            "index": index,
            "expected": expected,
            "predicted": predicted,
            "ok": ok,
            "error": error,
            "latency_ms": 1.0,
            "trace_id": "",
            "ts": "2026-01-01T00:00:00.000+00:00",
        }
    )


def test_run_job_mock_completes(tmp_path):
    store = _prepped_store(tmp_path, rows=3)
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    assert summary["cursor"] == 3 and summary["ok"] == 3
    items = store.load_items()
    assert sorted(i["index"] for i in items) == [0, 1, 2]
    assert summary["scores"]["exact_match"] == 1.0


def test_successful_run_fires_report_writers(tmp_path, monkeypatch):
    """A completed job invokes the dated-report and grid-card writers once."""
    store = _prepped_store(tmp_path, rows=1)
    report_calls = []
    card_calls = []

    def record_report(target, **kwargs):
        """Capture dated-report writer arguments."""
        report_calls.append((target, kwargs))

    def record_card(target, **kwargs):
        """Capture grid-card writer arguments."""
        card_calls.append((target, kwargs))

    monkeypatch.setattr("mailroom_sandbox.job.dated_reports.maybe_write_run_reports", record_report)
    monkeypatch.setattr("mailroom_sandbox.job.grid_cards.maybe_write_card", record_card)

    summary = runner.run_job(store, mock=None)

    assert summary["state"] == "done"
    assert len(report_calls) == len(card_calls) == 1
    for target, kwargs in (report_calls[0], card_calls[0]):
        assert target is store
        assert kwargs["scores"] == summary["scores"]
        assert isinstance(kwargs["wall_seconds"], float)


def test_whole_run_forwards_report_group_to_scoring_runner(tmp_path, monkeypatch):
    """Isolated eval receives the lock's report_group as score_metadata."""
    from mailroom_sandbox.eval import runners as eval_runners
    from mailroom_sandbox.job.checkpoint import RunStore

    store = RunStore(tmp_path / "agent-run")
    store.write_lock(
        {
            "run_id": store.run_id,
            "task": "judge",
            "profile": "ollama",
            "engine": {"model": "test-model", "modal": None},
            "job": {"mock": True, "concurrency": 1},
            "dataset": {},
            "report_group": "SAND-123",
        }
    )
    captured = {}

    def fake_isolated_eval(task, **kwargs):
        """Record isolated-eval kwargs without running the suite."""
        captured["task"] = task
        captured["kwargs"] = kwargs
        return {"n": 0, "scores": {"n": 0}}

    monkeypatch.setattr(runner, "_agent_task_names", lambda: {"judge"})
    monkeypatch.setattr(eval_runners, "run_isolated_eval", fake_isolated_eval)

    summary = runner._run_whole_run(store, "judge", mock=True, model=None, profile="ollama")

    assert summary["state"] == "done"
    assert captured["task"] == "judge"
    assert captured["kwargs"]["score_metadata"] == {"report_group": "SAND-123"}


def test_whole_run_local_vs_api_forwards_score_metadata(tmp_path, monkeypatch):
    """local_vs_api whole-run scoring receives the lock's report_group."""
    from mailroom_sandbox.eval import runners as eval_runners
    from mailroom_sandbox.job.checkpoint import RunStore

    store = RunStore(tmp_path / "lva-run")
    store.write_lock(
        {
            "run_id": store.run_id,
            "task": "local_vs_api",
            "profile": "ollama",
            "engine": {"model": "test-model", "modal": None},
            "job": {"mock": True, "concurrency": 1},
            "dataset": {},
            "report_group": "SAND-123",
        }
    )
    captured = {}

    def fake_local_vs_api_eval(**kwargs):
        """Record local-vs-API eval kwargs without running the suite."""
        captured["kwargs"] = kwargs
        return {"n": 0, "scores": {"n": 0}}

    monkeypatch.setattr(eval_runners, "run_local_vs_api_eval", fake_local_vs_api_eval)

    summary = runner._run_whole_run(
        store, "local_vs_api", mock=True, model=None, profile="ollama"
    )

    assert summary["state"] == "done"
    assert captured["kwargs"]["score_metadata"] == {"report_group": "SAND-123"}


def test_run_job_all_items_failed_writes_failed_not_done(tmp_path, monkeypatch):
    """hub#39: a run where EVERY item errored must write state=failed with a
    last_error, exit 1 (CLI maps state != done), and never append a 'done'
    record — a dead engine is loud, not silent."""
    store = _prepped_store(tmp_path, rows=3, job={"mock": False, "max_retries": 0})

    def _dead_engine(task, row, *, mock, model, run_id=None):
        raise ConnectionError("engine unreachable")

    monkeypatch.setattr(runner, "_predict_row", _dead_engine)
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "failed"
    assert summary["ok"] == 0 and summary["errors"] == 3
    assert "engine unreachable" in str(summary.get("last_error") or {})
    cp = store.read_checkpoint() or {}
    assert cp["state"] == "failed"
    assert "engine unreachable" in str(cp.get("last_error") or {})
    events = store.events()
    assert not any(e["event"] == "done" for e in events)
    assert any(e["event"] == "failed" for e in events)
    items = store.load_items()
    assert len(items) == 3 and all(i["ok"] is False for i in items)


def test_run_job_resume_all_failed_stays_failed(tmp_path, monkeypatch):
    """hub#39: resumed rows where earlier rows already failed must also land
    in state=failed (the guard reads per-row ok truth, not this invocation's
    error counter)."""
    store = _prepped_store(tmp_path, rows=3, job={"mock": False, "max_retries": 0})
    _append_item(store, index=0, predicted="", expected="contract", ok=False, error="boom")
    store.write_checkpoint(state="running", cursor=1, total=3)

    def _dead_engine(task, row, *, mock, model, run_id=None):
        raise ConnectionError("engine unreachable")

    monkeypatch.setattr(runner, "_predict_row", _dead_engine)
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "failed"
    cp = store.read_checkpoint() or {}
    assert cp["state"] == "failed"
    events = store.events()
    assert not any(e["event"] == "done" for e in events)


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


# ── Concurrency (Modal vLLM throughput alignment) ────────────────────────────


def test_run_job_concurrent_completes_all_rows_once(tmp_path):
    store = _prepped_store(tmp_path, rows=8, job={"mock": True, "concurrency": 4})
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    assert summary["ok"] == 8 and summary["errors"] == 0
    assert summary["cursor"] == 8
    items = store.load_items()
    assert sorted(i["index"] for i in items) == list(range(8))
    assert summary["scores"]["exact_match"] == 1.0


def test_run_job_concurrent_max_items_leaves_running_and_resumes(tmp_path):
    store = _prepped_store(tmp_path, rows=6, job={"mock": True, "concurrency": 3})
    first = runner.run_job(store, mock=None, max_items=4)
    assert first["state"] == "running"
    assert first["cursor"] == 4
    assert len({i["index"] for i in store.load_items()}) == 4

    second = runner.run_job(store, mock=None)
    assert second["state"] == "done"
    assert second["cursor"] == 6
    items = store.load_items()
    assert sorted(i["index"] for i in items) == list(range(6))


def test_run_job_concurrent_resume_skips_completed_by_index(tmp_path):
    """Resume must skip by completed INDEX, not a contiguous cursor: after a
    concurrent pass an item with a high index can complete before lower ones,
    so a cursor-style skip would silently drop rows (the DMR-027 regression
    this guards against)."""
    store = _prepped_store(tmp_path, rows=4, job={"mock": True, "concurrency": 2})
    runner.run_job(store, mock=None, max_items=1)  # index 0 completed
    _append_item(store, index=2, expected="contract", predicted="contract")  # index 2 done
    store.write_checkpoint(state="running", cursor=len(store.load_items()), total=4)

    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    items = store.load_items()
    assert sorted(i["index"] for i in items) == [0, 1, 2, 3]
    # The seeded index-2 row must NOT have been re-run (its predicted value
    # survives; a re-run would have produced the deterministic mock value).
    seeded = next(i for i in items if i["index"] == 2)
    assert seeded["predicted"] == "contract"
    assert seeded["ok"] is True


def test_run_job_concurrent_fail_fast_stops_scheduling(tmp_path, monkeypatch):
    store = _prepped_store(
        tmp_path, rows=4, job={"mock": True, "concurrency": 2, "fail_fast": True, "max_retries": 0}
    )

    def _boom_predict(task, row, *, mock, model, run_id=None):
        if row.get("id") == "d0":
            raise RuntimeError("boom")
        cls = "contract" if str(row.get("id")) in {"d1", "d3"} else "insurance_claim"
        return cls, {}

    monkeypatch.setattr(runner, "_predict_row", _boom_predict)
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "failed"
    assert "boom" in str(summary.get("last_error") or {})
    items = store.load_items()
    failed = [i for i in items if i["index"] == 0]
    assert failed and "boom" in failed[0]["error"]
    # fail_fast stops SCHEDULING new rows: at most the two in-flight rows ran.
    assert len(items) <= 2


def test_build_record_bills_wall_not_latency_sum_under_concurrency(tmp_path, monkeypatch):
    """Issue #37: gpu_seconds must track wall+cold boot, not sum(latency)/conc."""
    from mailroom_sandbox.job.checkpoint import RunStore

    monkeypatch.delenv("MODAL_BILLED_GPU_SECONDS", raising=False)
    store = RunStore(tmp_path / "run-bill")
    store.write_lock(
        {
            "run_id": store.run_id,
            "task": "sorter",
            "profile": "modal-vllm",
            "spec_hash": "abc",
            "engine": {"model": "Qwen/Qwen3-8B", "modal": {"gpu": "L4"}},
            "job": {"mock": False, "concurrency": 8},
        }
    )
    for i in range(4):
        store.append_item(
            {
                "item_id": f"d{i}",
                "index": i,
                "ok": True,
                "latency_ms": 10_000.0,
                "prompt_tokens": 1,
                "completion_tokens": 1,
            }
        )
    store.write_cold_boot({"cold_boot_seconds": 5.0})
    rec = runner._build_record(store, "sorter", None, {}, mock=False, wall_seconds=12.0)
    assert rec["gpu_seconds"] == pytest.approx(17.0)
    assert rec["gpu_seconds"] != pytest.approx(40.0 + 5.0)


def test_build_record_modalt_billed_env_override(tmp_path, monkeypatch):
    from mailroom_sandbox.job.checkpoint import RunStore

    monkeypatch.setenv("MODAL_BILLED_GPU_SECONDS", "99")
    store = RunStore(tmp_path / "run-env")
    store.write_lock(
        {
            "run_id": store.run_id,
            "task": "sorter",
            "profile": "modal-vllm",
            "spec_hash": "abc",
            "engine": {"model": "Qwen/Qwen3-8B", "modal": {"gpu": "L4"}},
            "job": {"mock": False},
        }
    )
    store.append_item({"item_id": "d0", "index": 0, "ok": True, "latency_ms": 1000.0})
    rec = runner._build_record(store, "sorter", None, {}, mock=False, wall_seconds=1.0)
    assert rec["gpu_seconds"] == pytest.approx(99.0)


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
    store3 = RunStore(tmp_path / "run-src3")
    store3.write_lock(
        {
            "task": "correspondence_specialist",
            "prompt": {
                "default": {"source": "code-default"},
                "agents": {
                    "correspondence_specialist": {
                        "source": "local",
                        "file": "correspondence_specialist_simplified",
                    }
                },
            },
        }
    )
    assert runner._lock_prompt_variant(store3) == "correspondence_specialist_simplified"


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


def test_whole_run_agent_task_carries_cold_boot(tmp_path):
    """SAND-018: the measured engine cold boot (preflight --live) lands in the
    whole-run experiment-log record, not just the per-item path."""
    store = _whole_run_store(tmp_path, task="judge")
    store.write_cold_boot({"cold_boot_seconds": 178.25, "run_id": store.run_id})
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    assert summary["result"]["record"]["cold_boot_seconds"] == 178.25


def test_whole_run_record_bills_cold_boot(tmp_path):
    """SAND-018 cost accuracy: the pipeline record's GPU-seconds span the warm
    interval (cold boot + busy), so the reported cost matches the Modal charge."""
    store = _whole_run_store(tmp_path, task="pipeline")
    store.write_cold_boot({"cold_boot_seconds": 178.0, "run_id": store.run_id})
    store.items_path.write_text(
        json.dumps({"id": "d0", "ok": True, "latency_ms": 2400.0}) + "\n",
        encoding="utf-8",
    )
    rec = runner._build_record(store, "pipeline", None, {"n": 1}, mock=True)
    assert rec["cold_boot_seconds"] == 178.0
    assert rec["gpu_seconds"] >= 178.0
    assert "estimated_gpu_cost_usd" in rec


def test_whole_run_emits_progress_events(monkeypatch, tmp_path):
    """SAND-018: a delegated whole-run must forward per-item progress so
    `sandbox run status` / --watch track a live run instead of showing nothing."""
    from mailroom_sandbox.eval import runners as eval_runners

    def _fake_isolated(task, **kwargs):
        cb = kwargs.get("progress_cb")
        if cb is not None:
            cb(1, 3, 1, 0)
            cb(2, 3, 2, 0)
            cb(3, 3, 3, 0)
        return {"n": 3, "scores": {"exact_match": 1.0}, "record": {"ok": True}, "rows": []}

    monkeypatch.setattr(eval_runners, "run_isolated_eval", _fake_isolated)
    store = _whole_run_store(tmp_path, task="judge")
    events: list[dict] = []
    summary = runner.run_job(store, mock=True, on_event=events.append)
    assert summary["state"] == "done"
    assert [e["cursor"] for e in events] == [1, 2, 3]
    assert all(e["state"] == "running" for e in events)


def test_whole_run_agent_task_passes_concurrency_and_caps(monkeypatch, tmp_path):
    """SAND-018: job.concurrency / cost_cap / max_wall reach the isolated
    runner — the isolated path used to be serial and unguarded."""
    from mailroom_sandbox.eval import runners as eval_runners

    captured: dict = {}

    def _fake_isolated(task, **kwargs):
        captured.update(kwargs)
        captured["_task"] = task
        return {"n": 1, "scores": {"exact_match": 1.0}, "record": {"ok": True}, "rows": []}

    monkeypatch.setattr(eval_runners, "run_isolated_eval", _fake_isolated)
    store = _whole_run_store(tmp_path, task="judge")
    runner.run_job(store, mock=True)
    assert captured["_task"] == "judge"
    assert captured["concurrency"] >= 1
    assert "max_wall_seconds" in captured
    assert "cost_cap_usd" in captured
    assert "gpu" in captured


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


# --- DMR-072: live sorter dead-path guards (silent-fallback trap) ---------

def test_live_sorter_without_runtime_activation_raises(tmp_path, monkeypatch):
    """The unactivated graph returns doc_type='unknown' without any LLM call —
    _predict_row must refuse to score it as ok=True."""
    import mailroom_sandbox.runtime as runtime_mod

    monkeypatch.setattr(runtime_mod, "_ACTIVE", None)  # isolation: test_eval activates globally
    store = _prepped_store(tmp_path, rows=1, job={"mock": False, "max_retries": 0})
    row = store.dataset_rows()[0]
    with pytest.raises(RuntimeError, match="profile not activated"):
        runner._predict_row("sorter", row, mock=False, model=None, run_id="x")


def test_live_sorter_unknown_doc_type_raises(tmp_path, monkeypatch):
    """Even WITH an activated runtime, a graph that falls through to the
    'unknown' default is a dead path — hard-fail, never ok=True with 0.0."""
    store = _prepped_store(tmp_path, rows=1, job={"mock": False, "max_retries": 0})
    row = store.dataset_rows()[0]

    import mailroom_sandbox.runtime as runtime_mod
    import mailroom_sandbox.eval.runners as eval_runners

    monkeypatch.setattr(runtime_mod, "_ACTIVE", object())
    monkeypatch.setattr(
        eval_runners, "_run_pipeline_doc",
        lambda row, *, mock, run_id=None: {"doc_type": "unknown"},
    )
    with pytest.raises(RuntimeError, match="no real doc_type"):
        runner._predict_row("sorter", row, mock=False, model=None, run_id="x")


# ── SAND-032: replica-aware live caps ────────────────────────────────────────


def test_lock_replicas_reads_max_containers(tmp_path):
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.runner import _lock_replicas

    two = RunStore(tmp_path / "two")
    two.write_lock({"engine": {"modal": {"gpu": "L4", "max_containers": 2}}})
    assert _lock_replicas(two) == 2
    one = RunStore(tmp_path / "one")  # locks are write-once — separate store
    one.write_lock({"engine": {"modal": {"gpu": "L4"}}})
    assert _lock_replicas(one) == 1


def test_run_gpu_estimate_scales_by_lock_replicas(tmp_path, monkeypatch):
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.runner import _estimate_run_gpu_usd

    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    monkeypatch.delenv("MODAL_GPU_USD_PER_SEC", raising=False)
    one = RunStore(tmp_path / "one")
    one.write_lock({"engine": {"modal": {"gpu": "L4", "max_containers": 1}}})
    two = RunStore(tmp_path / "two")
    two.write_lock({"engine": {"modal": {"gpu": "L4", "max_containers": 2}}})
    import pytest

    assert _estimate_run_gpu_usd(two, 300) == pytest.approx(2 * _estimate_run_gpu_usd(one, 300), abs=2e-6)


def test_isolated_guard_scales_by_replicas(monkeypatch):
    """A $0.10 cap trips at 450 s on one L4 but 225 s on two ($0.80/hr)."""
    from mailroom_sandbox.job import metrics

    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    monkeypatch.delenv("MODAL_GPU_USD_PER_SEC", raising=False)
    assert metrics.estimate_gpu_cost_usd(300, gpu="L4") < 0.10
    assert metrics.estimate_gpu_cost_usd(300, gpu="L4", replicas=2) >= 0.10


# ── SAND-032: isolated runs persist per-doc items ────────────────────────────


def test_persist_isolated_items_writes_items_jsonl(tmp_path):
    import json

    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.runner import _persist_isolated_items

    store = RunStore(tmp_path / "r")
    rows = [
        {"id": "a", "pred": {"x": 1}, "score": {"overall_extraction_score": 0.5},
         "error": None, "latency_ms": 1200.0, "prompt_tokens": 10, "completion_tokens": 5},
        {"id": "b", "pred": None, "score": {}, "error": "OpenAIConnectionError: x",
         "latency_ms": 900.0, "prompt_tokens": 0, "completion_tokens": 0},
    ]
    assert _persist_isolated_items(store, rows) == 2
    lines = [json.loads(line) for line in store.items_path.read_text().splitlines()]
    assert [line["item_id"] for line in lines] == ["a", "b"]
    assert lines[0]["ok"] is True and lines[1]["ok"] is False
    assert lines[1]["error"].startswith("OpenAIConnectionError")
    assert lines[0]["prompt_tokens"] == 10


def test_persist_isolated_items_is_idempotent(tmp_path):
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.runner import _persist_isolated_items

    store = RunStore(tmp_path / "r")
    rows = [{"id": "a", "score": {}, "error": None, "latency_ms": 1.0}]
    _persist_isolated_items(store, rows)
    assert _persist_isolated_items(store, rows) == 0
    assert len(store.items_path.read_text().splitlines()) == 1


def test_persist_isolated_items_none_is_noop(tmp_path):
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.runner import _persist_isolated_items

    assert _persist_isolated_items(RunStore(tmp_path / "r"), None) == 0


def test_aborted_isolated_run_keeps_completed_items(tmp_path, monkeypatch):
    """SAND-032 review #3: a cost-cap abort mid-run must not drop the rows
    already paid for (items.jsonl feeds reports + offline BT rows)."""
    from mailroom_sandbox.eval import runners as eval_runners
    from mailroom_sandbox.job import runner
    from mailroom_sandbox.job.checkpoint import RunStore

    store = RunStore(tmp_path / "r")
    store.write_lock({"task": "judge", "profile": "modal-vllm", "prompt": {},
                      "engine": {"model": "m", "modal": {"gpu": "L4", "max_containers": 2}},
                      "job": {"concurrency": 2}})

    def fake_isolated(task, *, row_cb=None, **kwargs):
        for i in range(2):
            row_cb({"id": f"d{i}", "score": {}, "error": None, "latency_ms": 10.0})
        raise RuntimeError("isolated eval aborted: cost_cap_usd=0.1 exceeded")

    monkeypatch.setattr(eval_runners, "run_isolated_eval", fake_isolated)
    out = runner._run_whole_run(store, "judge", mock=False, model=None, profile="modal-vllm")
    assert out["state"] == "failed"
    assert [i["item_id"] for i in store.load_items()] == ["d0", "d1"]
