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
