"""Per-agent evals, tracing contract, overlay knobs (network-free)."""

from __future__ import annotations

import json

from mailroom_sandbox.cli import main
from mailroom_sandbox.eval import agents, experiment_log, runners, tracing
from mailroom_sandbox.overlay import build_merged_taxonomy, load_profile


def _isolate_log(tmp_path, monkeypatch):
    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(log))
    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    return log


def test_eval_task_roster_covers_live_agents():
    for name in (
        "intake",
        "pdf_transcriber",
        "image_extractor",
        "sorter",
        "sorter_reviewer",
        "contracts_specialist",
        "merger_agreement_specialist",
        "corporate_records_specialist",
        "correspondence_specialist",
        "insurance_claims_specialist",
        "judge",
        "arbiter",
        "boss",
        "compile_report",
        "human_review",
        "catalog",
        "archive",
    ):
        assert name in agents.SPECS
    assert "pipeline" in agents.EVAL_TASKS
    assert "local_vs_api" in agents.EVAL_TASKS
    assert "sorter_vs_modernbert" in agents.EVAL_TASKS
    assert "court_opinions_specialist" not in agents.SPECS
    # HUB-015 reduced profile: the reporter AGENT is retired; the compile
    # stage is the procedural compile_report node (no LLM call).
    assert "reporter" not in agents.SPECS
    from mailroom_sandbox.components import is_enabled

    assert not is_enabled("agents", "reporter")
    assert is_enabled("nodes", "compile_report")


def test_procedural_reporter_makes_no_llm_call(tmp_path, monkeypatch):
    _isolate_log(tmp_path, monkeypatch)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    result = runners.run_isolated_eval("compile_report", mock=True)
    assert result["scores"]["n"] >= 1
    assert result["scores"]["exact_match"] == 1.0
    # the procedural assembler must never acquire an LLM client
    import mailroom_sandbox.eval.agents as agent_mod

    assert "get_llm" not in agent_mod._live_reporter.__code__.co_names


def test_isolated_eval_dry_run_and_mock(tmp_path, monkeypatch):
    _isolate_log(tmp_path, monkeypatch)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    plan = runners.run_isolated_eval("judge", mock=True, dry_run=True)
    assert plan["task"] == "judge"
    assert plan["observation"] == "judge-verify"
    result = runners.run_isolated_eval("judge", mock=True, experiment_name="test_judge")
    assert result["scores"]["n"] >= 1
    assert result["scores"]["exact_match"] == 1.0


def test_isolated_eval_records_latency_and_wall(tmp_path, monkeypatch):
    """SAND-018: the isolated path must capture per-row serving metrics — a
    specialist run used to report no latency/tokens at all."""
    _isolate_log(tmp_path, monkeypatch)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    result = runners.run_isolated_eval("judge", mock=True, experiment_name="t_metrics")
    rec = result["record"]
    assert rec["e2e_latency_seconds"] >= 0.0
    assert rec["latency_p50_seconds"] >= 0.0
    assert rec["latency_max_seconds"] >= 0.0
    assert rec["wall_seconds"] >= 0.0
    assert result["rows"] and all("latency_ms" in r for r in result["rows"])


def test_isolated_eval_wall_guard_aborts(tmp_path, monkeypatch):
    """SAND-018: an isolated run must honor max_wall_seconds (the whole-run
    path previously bypassed the cost/wall guards entirely)."""
    import pytest

    _isolate_log(tmp_path, monkeypatch)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="max_wall_seconds"):
        runners.run_isolated_eval("judge", mock=True, max_wall_seconds=0)


def test_isolated_eval_cost_guard_aborts(tmp_path, monkeypatch):
    import pytest

    _isolate_log(tmp_path, monkeypatch)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="cost_cap_usd"):
        runners.run_isolated_eval("judge", mock=True, cost_cap_usd=0, gpu="L4")


def test_isolated_eval_reports_progress(tmp_path, monkeypatch):
    """SAND-018: a live isolated run must report progress (it used to be silent
    until the end, so a working run looked stalled)."""
    _isolate_log(tmp_path, monkeypatch)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    calls: list[tuple[int, int, int, int]] = []
    result = runners.run_isolated_eval(
        "judge",
        mock=True,
        progress_cb=lambda done, total, ok, errors: calls.append((done, total, ok, errors)),
    )
    assert calls, "progress_cb was never invoked"
    assert calls[-1][0] == calls[-1][1] == result["scores"]["n"]


def test_run_rows_bounded_respects_window():
    """SAND-018: concurrency must be a real in-flight bound, not submit-all."""
    import threading
    import time

    results: dict[int, str] = {}
    live = {"cur": 0, "max": 0}
    lock = threading.Lock()

    def run_one(index, row):
        with lock:
            live["cur"] += 1
            live["max"] = max(live["max"], live["cur"])
        time.sleep(0.02)
        with lock:
            live["cur"] -= 1
        return f"r{index}"

    runners._run_rows_bounded(
        list(range(6)),
        workers=2,
        run_one=run_one,
        on_result=lambda i, v: results.__setitem__(i, v),
        guard=lambda: None,
    )
    assert results == {i: f"r{i}" for i in range(6)}
    assert live["max"] <= 2


def test_run_rows_bounded_guard_stops_new_submissions():
    """The cap must be checked BEFORE each new submission — a tripped guard
    stops starting work instead of draining an already-queued batch."""
    import pytest

    started: list[int] = []
    calls = {"n": 0}

    def run_one(index, row):
        started.append(index)
        return index

    def guard():
        calls["n"] += 1
        if calls["n"] > 2:
            raise RuntimeError("cap tripped")

    with pytest.raises(RuntimeError, match="cap tripped"):
        runners._run_rows_bounded(
            list(range(10)),
            workers=1,
            run_one=run_one,
            on_result=lambda i, v: None,
            guard=guard,
        )
    assert len(started) == 2


def test_gpu_cost_estimate_matches_l4_run():
    """SAND-018 cost-guard accuracy: the $0.55 cap trips at 2475s (=41.25 min)
    at L4 $0.80/hr, and the observed 2990s run prices at ~$0.664."""
    from mailroom_sandbox.job.metrics import estimate_gpu_cost_usd, gpu_usd_per_hour

    assert gpu_usd_per_hour("L4") == 0.80
    assert estimate_gpu_cost_usd(2475, gpu="L4") == 0.55
    assert estimate_gpu_cost_usd(2990, gpu="L4") == 0.664444


def test_isolated_eval_sorter_reviewer_and_arbiter(tmp_path, monkeypatch):
    _isolate_log(tmp_path, monkeypatch)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    reviewer = runners.run_isolated_eval("sorter_reviewer", mock=True, sample=1)
    assert reviewer["scores"]["exact_match"] == 1.0
    arbiter = runners.run_isolated_eval("arbiter", mock=True)
    assert arbiter["scores"]["exact_match"] == 1.0
    intake = runners.run_isolated_eval("intake", mock=True)
    assert intake["scores"]["n"] >= 1


def test_pipeline_eval_connected_scores(tmp_path, monkeypatch):
    _isolate_log(tmp_path, monkeypatch)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    result = runners.run_pipeline_eval(mock=True, sample=3, connected=True, experiment_name="test_pipe")
    scores = result["scores"]
    assert scores["class_correct"] == 1.0
    assert "stage_correct" in scores
    assert "routing_accuracy" in scores
    assert result["connected"] is True


def test_cli_agents_list(capsys):
    rc = main(["agents", "list", "--profile", "ollama"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    names = {row["agent"] for row in payload["agents"]}
    assert "sorter" in names
    assert "judge" in names
    assert "sorter" in payload["eval_tasks"]


def test_cli_eval_judge_dry_run(capsys):
    rc = main(["eval", "judge", "--mock", "--dry-run"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["task"] == "judge"


def test_cli_cutover_agent_model(capsys):
    rc = main(["cutover", "--profile", "ollama", "--agent-model", "judge=qwen3:14b"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "qwen3:14b" in out


def test_tracing_family_tags_and_public_gt():
    tags = tracing.default_tags("source-fixtures")
    assert "mailroom" in tags
    assert "sandbox" in tags
    gt = tracing.public_ground_truth(
        {
            "expected_doc_class": "contract",
            "expected_fields": {"parties": ["x"]},
            "expected_hf_class": "contract",
        }
    )
    assert "expected_fields" not in gt
    assert gt["expected_doc_class"] == "contract"
    assert tracing.observation_type_for("classify-document") == "agent"
    assert tracing.observation_type_for("judge-verify") == "evaluator"
    assert tracing.PIPELINE_TRACE == "document-pipeline"


def test_overlay_keeps_local_model_after_agent_knobs():
    taxonomy = build_merged_taxonomy(load_profile("ollama"))
    assert taxonomy["agents"]["sorter"]["model"] == "qwen3:8b"
    assert taxonomy["agents"]["sorter"]["temperature"] == 0.1
    assert taxonomy["confidence"]["high"] == 0.95
