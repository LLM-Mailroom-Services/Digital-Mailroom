"""DMR-078 specialist posture — Qwen L4 context fit + per-doc-type guards."""

from __future__ import annotations

from pathlib import Path

from mailroom_sandbox.job.benchmark_check import (
    SPECIALIST_LOCAL_PROMPTS,
    check_benchmark_posture,
)
from mailroom_sandbox.job.spec import load_run_spec
from mailroom_sandbox.job.specialist_posture import (
    SPECIALIST_POSTURE,
    context_fit_ok,
    expected_concurrency,
    validate_mapping,
)


def test_posture_context_fit_and_invariants():
    assert validate_mapping() == []
    for run_id, row in SPECIALIST_POSTURE.items():
        assert context_fit_ok(row["max_tokens"], row["max_input_chars"]), run_id
        assert 2 <= row["concurrency"] <= 6


def test_merger_is_dedicated_specialist():
    row = SPECIALIST_POSTURE["run-30-merger-specialist"]
    assert row["task"] == "merger_agreement_specialist"
    assert row["agent"] == "merger_agreement_specialist"
    assert SPECIALIST_LOCAL_PROMPTS["run-30-merger-specialist"] == {
        "merger_agreement_specialist": "merger_agreement_specialist_production"
    }


def test_run_yamls_match_posture(monkeypatch):
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check.active_modal_profile_name",
        lambda: "hermes-agent-jjb",
    )
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check._modal_cli_ok",
        lambda: {"ok": True, "version": "modal stub"},
    )
    root = Path(__file__).resolve().parents[1] / "config" / "runs"
    for run_id, row in SPECIALIST_POSTURE.items():
        spec = load_run_spec(root / f"{run_id}.yaml")
        assert spec.task == row["task"]
        assert spec.job.concurrency == expected_concurrency(run_id)
        assert float(spec.job.cost_cap_usd) == float(row["cost_cap_usd"])
        assert int(spec.job.max_wall_seconds) == int(row["max_wall_seconds"])
        assert spec.engine.model == "Qwen/Qwen3-8B"
        report = check_benchmark_posture(spec=spec, require_hermes=True)
        assert report["ok"], (run_id, report["errors"])
