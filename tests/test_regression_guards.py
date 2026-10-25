"""Meta regression guards — fail closed when shipped capabilities go missing.

These tests complement the behavioral suites (watch web, agents, vendor, eval)
by asserting wiring that PR #63–#65 (unified themed logging + watch --web +
sandbox dev) and HUB-015 (reduced profile) depend on, and that CI actually
runs the network-free pytest suite.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest
import yaml

from mailroom_sandbox.eval import agents, runners
from mailroom_sandbox.paths import repo_root

ROOT = repo_root()
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

# Files that must exist — deleting them should fail CI, not silently drop coverage.
REGRESSION_TEST_MODULES = (
    "tests/test_vendor.py",
    "tests/test_vendor_drift.py",
    "tests/test_agents.py",
    "tests/test_eval.py",
    "tests/test_watch.py",
    "tests/test_watch_web.py",
    "tests/test_watch_demo.py",
    "tests/test_mailroom_session.py",
    "tests/test_board.py",
    "tests/test_eval_environment_lineage.py",
    "tests/test_job_preflight.py",
    "tests/test_serving_parity.py",
    "tests/test_requirements.py",
    "tests/test_subagents.py",
    "tests/test_governance_sand.py",
)


@pytest.mark.parametrize("rel", REGRESSION_TEST_MODULES)
def test_regression_guard_module_exists(rel):
    path = ROOT / rel
    assert path.is_file(), f"missing regression module {rel}"


def test_ci_workflow_runs_network_free_pytest():
    """The sandbox CI must not be a no-op stub (regression of DMR-057 guardrails)."""
    assert CI_WORKFLOW.is_file()
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["network-free"]["steps"]
    joined = "\n".join(
        step.get("run", "") for step in steps if isinstance(step.get("run"), str)
    )
    assert "pytest" in joined
    assert "local_llm" in joined
    assert "echo ok" not in joined


def test_reduced_profile_reporter_retired_in_components():
    from mailroom_sandbox.components import is_enabled

    text = (ROOT / "config" / "components.yaml").read_text(encoding="utf-8")
    assert "reporter" in text
    assert "retired_agents" in text
    assert not is_enabled("agents", "reporter")
    assert is_enabled("nodes", "compile_report")
    assert "reporter" not in agents.SPECS


def test_five_live_specialists_stay_enabled():
    """HUB-015 / AGENTS.md: one specialist agent per live doc class."""
    from mailroom_sandbox.components import is_enabled

    live = (
        "contracts_specialist",
        "merger_agreement_specialist",
        "corporate_records_specialist",
        "correspondence_specialist",
        "insurance_claims_specialist",
    )
    for name in live:
        assert is_enabled("agents", name), name
    overlay = yaml.safe_load((ROOT / "config" / "taxonomy.overlay.yaml").read_text(encoding="utf-8"))
    for name in live:
        assert name in (overlay.get("agents") or {}), f"{name} missing from taxonomy overlay"


def test_unified_mailroom_logging_surface():
    """PR #63/#65: pretty_log palette drives browser theme; dev == watch --web --demo."""
    web = importlib.import_module("mailroom_sandbox.tui.web")
    pl = importlib.import_module("mailroom_sandbox.tui.pretty_log")
    assert callable(getattr(web, "serve_watch_web", None))
    assert callable(getattr(web, "_html_page", None))
    page = web._html_page().decode()
    assert "THE MAILROOM" in page
    assert web.THEME["blue"] == "#%02x%02x%02x" % pl.BLUE
    cli_src = (ROOT / "src" / "mailroom_sandbox" / "cli.py").read_text(encoding="utf-8")
    assert re.search(r'add_parser\s*\(\s*["\']dev["\']', cli_src)
    assert "--web" in cli_src and "--demo" in cli_src


@pytest.mark.parametrize(
    "task",
    ["sorter", "judge", "pipeline", "local_vs_api", "compile_report"],
)
def test_mock_eval_tasks_remain_registered(task):
    if task == "compile_report":
        assert task in agents.SPECS
    else:
        assert task in agents.EVAL_TASKS


def test_compile_report_mock_eval_never_touches_llm(tmp_path, monkeypatch):
    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(log))
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    from mailroom_sandbox.eval import experiment_log

    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    result = runners.run_isolated_eval("compile_report", mock=True)
    assert result["scores"]["exact_match"] == 1.0
    assert "get_llm" not in agents._live_reporter.__code__.co_names
