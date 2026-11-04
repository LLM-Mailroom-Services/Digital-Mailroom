"""The two primary tasks and their two levels: ``specialist [TARGET]`` and ``pipeline [--class]``.

Offline: every run is ``--mock``; legacy tasks stay runnable but hidden from help and menus.
"""

from __future__ import annotations

import json

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.eval import primary
from mailroom_sandbox.job.spec import RunSpec, spec_hash
from mailroom_sandbox.tui.shell import command_catalog, render_menu


@pytest.mark.parametrize(("spelling", "cls"), [
    ("contract", "contract"), ("contracts", "contract"), ("contracts_specialist", "contract"),
    ("merger", "merger_agreement"), ("merger-agreement", "merger_agreement"),
    ("corporate_records", "corporate_record"), ("Insurance_Claims_Specialist", "insurance_claim"),
    ("correspondence", "correspondence"),
])
def test_one_target_vocabulary_for_both_levels(spelling, cls):
    assert primary.resolve_class(spelling) == cls
    assert primary.specialists_for(spelling) == [primary.SPECIALISTS[cls]]


@pytest.mark.parametrize("bad", ["sorter", "judge", "contractz", "legalbench"])
def test_unknown_targets_name_the_valid_ones(bad):
    with pytest.raises(ValueError, match="contract, merger_agreement"):
        primary.resolve_class(bad)


def test_no_target_means_every_specialist_in_live_class_order():
    assert primary.resolve_class(None) is None and primary.resolve_class(" ") is None
    assert primary.specialists_for(None) == [
        "contracts_specialist", "merger_agreement_specialist", "corporate_records_specialist",
        "correspondence_specialist", "insurance_claims_specialist"]


def test_rows_for_class_filters_and_refuses_an_empty_class():
    rows = [{"id": "a", "expected_doc_class": "contract"}, {"id": "b", "doc_type": "correspondence"}]
    assert [r["id"] for r in primary.rows_for_class(rows, "contracts")] == ["a"]
    assert primary.rows_for_class(rows, None) is rows
    with pytest.raises(ValueError, match="no insurance_claim documents"):
        primary.rows_for_class(rows, "insurance_claim")


def test_eval_help_lists_only_the_primary_tasks(capsys):
    with pytest.raises(SystemExit):
        cli.main(["eval", "--help"])
    out = capsys.readouterr().out
    assert "{specialist,pipeline}" in out and "--all-tasks" in out
    assert "sorter_vs_modernbert" not in out and "judge" not in out


def test_bare_eval_prints_both_levels_and_all_tasks_adds_the_rest(capsys):
    assert cli.main(["eval"]) == 0
    out = capsys.readouterr().out
    assert "specialist TARGET" in out and "pipeline --class C" in out and "judge" not in out
    assert cli.main(["eval", "--all-tasks"]) == 0
    out = capsys.readouterr().out
    assert "judge" in out and "sorter_vs_modernbert" in out and "legalbench" not in out


@pytest.mark.parametrize("legacy", ["sorter", "judge", "contracts_specialist", "extract", "local_vs_api"])
def test_legacy_tasks_still_parse(legacy):
    args = cli.build_parser().parse_args(["eval", legacy, "--mock"])
    assert args.task == legacy and args.handler is cli._cmd_eval


def test_level_two_flags_parse_and_normalize():
    parser = cli.build_parser()
    assert parser.parse_args(["eval", "specialist", "contracts", "--mock"]).target == "contract"
    assert parser.parse_args(["eval", "specialist", "--mock"]).target is None
    assert parser.parse_args(["eval", "pipeline", "--class", "merger", "--mock"]).doc_class == "merger_agreement"
    assert parser.parse_args(["--profile", "ollama", "eval", "specialist", "contract"]).profile == "ollama"


@pytest.mark.parametrize("argv", [
    ["eval", "specialist", "nope"], ["eval", "pipeline", "--class", "sorter"],
    ["eval", "specialist", "--class", "contract"],  # --class belongs to pipeline
    ["eval", "specialist", "--from-log"],  # comparison flags belong to the legacy comparison tasks
])
def test_level_two_misuse_is_a_usage_error(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args([*argv, "--mock"])
    assert exc.value.code == 2


def _json(out: str) -> dict:
    return json.loads(out[out.index("{"):])


def test_specialist_sweep_and_single_target_dry_run(capsys):
    assert cli.main(["eval", "specialist", "--mock", "--dry-run"]) == 0
    sweep = _json(capsys.readouterr().out)
    assert sweep["task"] == "specialist" and sweep["targets"] == primary.specialists_for(None)
    assert set(sweep["results"]) == set(sweep["targets"])
    assert cli.main(["eval", "specialist", "contract", "--mock", "--dry-run"]) == 0
    one = _json(capsys.readouterr().out)
    assert one["task"] == "contracts_specialist"  # same shape as `eval contracts_specialist`


def test_single_target_keeps_the_specialist_log_identity(monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "_print", lambda result: None)
    monkeypatch.setattr("mailroom_sandbox.eval.runners.run_isolated_eval", lambda agent, **kw: seen.append((agent, kw["experiment_name"])) or {})
    assert cli.main(["eval", "specialist", "merger", "--mock"]) == 0
    assert seen == [("merger_agreement_specialist", "sandbox_merger_agreement_specialist")]
    seen.clear()
    assert cli.main(["eval", "specialist", "--mock", "--name", "sweep"]) == 0
    assert [name for _a, name in seen] == [f"sweep_{a}" for a in primary.specialists_for(None)]


def test_pipeline_class_narrows_the_documents(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "_print", lambda result: None)
    monkeypatch.setattr("mailroom_sandbox.eval.runners.run_pipeline_eval", lambda **kw: seen.update(kw) or {})
    assert cli.main(["eval", "pipeline", "--class", "correspondence", "--mock"]) == 0
    assert seen["rows"] and {primary.row_class(r) for r in seen["rows"]} == {"correspondence"}
    assert seen["experiment_name"] == "sandbox_pipeline_correspondence" and seen["connected"] is True
    seen.clear()
    assert cli.main(["eval", "pipeline", "--mock"]) == 0
    assert seen["rows"] is None  # every class: the runner's own fixture default


def test_menus_show_level_one_then_level_two_and_hide_legacy():
    catalog = command_catalog(cli.build_parser())
    node = {tuple(r["path"]): r for r in catalog}
    assert node[("eval",)]["children"] == ["specialist", "pipeline"]
    assert ("eval", "judge") not in node
    spec_menu = render_menu(node[("eval", "specialist")])
    assert "1. all five specialists  eval specialist" in spec_menu and "eval specialist insurance_claim" in spec_menu
    assert "eval pipeline --class merger_agreement" in render_menu(node[("eval", "pipeline")])


def _spec(**kw) -> RunSpec:
    return RunSpec(run_id="t", dataset={"provider": "file", "local_path": "data/fixtures/hf/docclass_mini.jsonl"},
                   engine={"kind": "vllm-local", "model": "m", "modal": None}, profile="ollama", **kw)


def test_run_spec_target_validation_and_hash_stability():
    assert _spec(task="specialist", target="contracts_specialist").target == "contract"
    assert _spec(task="pipeline", target="merger").target == "merger_agreement"
    with pytest.raises(ValueError, match="only applies to task specialist or pipeline"):
        _spec(task="sorter", target="contract")
    with pytest.raises(ValueError, match="unknown target"):
        _spec(task="pipeline", target="judge")
    # Unset target is not hashed: every pre-existing run YAML keeps its spec_hash.
    plain = _spec(task="pipeline")
    assert spec_hash(plain) != spec_hash(_spec(task="pipeline", target="contract"))
    from mailroom_sandbox.job.spec import spec_core

    assert "target" not in spec_core(plain)


def _run(tmp_path, capsys, *, task, target=None):
    config = tmp_path / "run.yaml"
    config.write_text(
        f"schema: sandbox.run/v1\nrun_id: primary-{task}-{target or 'all'}-{tmp_path.name[-8:]}\ntask: {task}\nprofile: ollama\n"
        "dataset: {provider: file, local_path: data/fixtures/hf/docclass_mini.jsonl, limit: 8, sample_seed: 1}\n"
        "engine: {kind: vllm-local, model: qwen3:8b, modal: null}\njob: {mode: endpoint, mock: true, concurrency: 1}\n"
        "trace: {sink: none}\n")
    argv = ["run", "start", "--config", str(config), "--mock", *(["--target", target] if target else [])]
    rc = cli.main(argv)
    return rc, _json(capsys.readouterr().out)


@pytest.fixture
def runs(job_data_dir, monkeypatch):
    from mailroom_sandbox.eval import experiment_log

    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: job_data_dir / "log.jsonl")
    monkeypatch.setattr(experiment_log, "md_path", lambda: job_data_dir / "log.md")
    return job_data_dir


def test_run_specialist_sweep_scores_each_class_once(runs, capsys):
    rc, out = _run(runs, capsys, task="specialist")
    assert rc == 0 and out["state"] == "done" and out["cursor"] == out["total"] > 0


@pytest.mark.parametrize(("task", "target"), [("specialist", "contract"), ("pipeline", "insurance_claim")])
def test_run_target_narrows_the_locked_rows(runs, capsys, task, target):
    rc, out = _run(runs, capsys, task=task, target=target)
    assert rc == 0 and out["state"] == "done"
    rows = [json.loads(line) for line in open("data/fixtures/hf/docclass_mini.jsonl") if line.strip()]
    expected = sum(1 for r in rows if primary.row_class(r) == target)
    assert out["total"] == expected and 0 < expected < len(rows)


def test_run_target_flag_on_a_non_primary_task_is_a_usage_error(capsys):
    assert cli.main(["run", "preflight", "--config", "config/runs/examples/example.yaml", "--target", "contract", "--dry-run"]) == 2
    assert "--target: target only applies to task specialist or pipeline" in capsys.readouterr().err


@pytest.mark.parametrize(("task", "target", "route"), [
    ("specialist", None, "INBOX → ALL FIVE SPECIALISTS → REPORT"),
    ("specialist", "contract", "INBOX → CONTRACTS_SPECIALIST → REPORT"),
    ("pipeline", None, "INBOX → SORTER → SPECIALISTS → REPORT"),
    ("pipeline", "merger_agreement", "INBOX → SORTER → MERGER_AGREEMENT → REPORT  (full pipeline · merger_agreement only)"),
])
def test_watch_route_names_both_levels(task, target, route):
    from mailroom_sandbox.tui.tray_context import route_for_task

    assert route_for_task(task, target) == route
