"""DMR-078 specialist posture — Qwen L4 context fit + per-doc-type guards."""

from __future__ import annotations

from pathlib import Path

from mailroom_sandbox.job.benchmark_check import (
    SPECIALIST_LOCAL_PROMPTS,
    check_benchmark_posture,
)
from mailroom_sandbox.job.spec import load_run_spec
from mailroom_sandbox.job.specialist_posture import (
    SPECIALIST_LIMIT_BY_RUN,
    SPECIALIST_POSTURE,
    context_fit_ok,
    expected_concurrency,
    expected_limit,
    validate_mapping,
)


def _stub_modal(monkeypatch):
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check.active_modal_profile_name",
        lambda: "hermes-agent-jjb",
    )
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check._modal_cli_ok",
        lambda: {"ok": True, "version": "modal stub"},
    )


def test_posture_context_fit_and_invariants():
    assert validate_mapping() == []
    for run_id, row in SPECIALIST_POSTURE.items():
        window = int(row.get("max_model_len", 16384))
        assert context_fit_ok(row["max_tokens"], row["max_input_chars"], window), run_id
        assert 2 <= row["concurrency"] <= 8


def test_run_20_contracts_single_class_posture():
    """SAND-018: the 20-contract single-class variant is a first-class posture."""
    row = SPECIALIST_POSTURE["run-20-contracts-specialist"]
    assert row["task"] == "contracts_specialist"
    assert row["doc_class"] == "contract"
    assert row["prompt_file"] == "contracts_specialist_v33_simplified"
    assert expected_limit("run-20-contracts-specialist") == 20
    # No posture row may rely on the silent default limit (coverage honesty).
    assert set(SPECIALIST_POSTURE) <= set(SPECIALIST_LIMIT_BY_RUN)
    assert expected_limit("run-30-contracts-specialist") == 30


def test_run_20_yaml_full_corpus_logged_sample():
    root = Path(__file__).resolve().parents[1] / "config" / "runs"
    spec = load_run_spec(root / "run-20-contracts-specialist.yaml")
    assert spec.dataset.split == "all"
    assert spec.dataset.limit == 20
    assert spec.dataset.sample_seed == 42
    assert spec.dataset.strata["buckets"] == [{"doc_class": "contract", "count": 20}]
    assert spec.effective_revision() == "46a4d3c240a36671cde0182fff4960f6b8b73aca"
    assert spec.job.cost_cap_usd == 0.55
    assert spec.job.max_wall_seconds == 3200
    agents = spec.prompt.get("agents") or {}
    assert agents["contracts_specialist"]["file"] == "contracts_specialist_v33_simplified"


def test_run_20_contracts_awq_c8_posture():
    """SAND-019: the corrected 8-concurrency AWQ contracts variant."""
    row = SPECIALIST_POSTURE["run-20-contracts-awq-c8"]
    assert row["task"] == "contracts_specialist"
    assert row["concurrency"] == 8
    assert row["max_model_len"] == 32768
    assert row["max_tokens"] == 8192          # > 4096, clears the length error
    assert row["prompt_file"] == "contracts_specialist_v33_simplified"
    assert expected_limit("run-20-contracts-awq-c8") == 20
    assert context_fit_ok(row["max_tokens"], row["max_input_chars"], 32768)


def test_run_20_correspondence_c8_posture():
    """SAND-019: the 8-concurrency correspondence variant is first-class."""
    row = SPECIALIST_POSTURE["run-20-correspondence-awq-c8"]
    assert row["task"] == "correspondence_specialist"
    assert row["concurrency"] == 8
    assert row["prompt_file"] == "correspondence_specialist_simplified"
    assert expected_limit("run-20-correspondence-awq-c8") == 20


def test_run_20_correspondence_fp16_c8_posture():
    """issue #21: FP16 twin is first-class posture, not an ad-hoc YAML."""
    row = SPECIALIST_POSTURE["run-20-correspondence-fp16-c8"]
    assert row["task"] == "correspondence_specialist"
    assert row["concurrency"] == 8
    # Isolation vs the already-scored AWQ c8 run (production prompt). SAND-026
    # retargeted the AWQ YAML to `*_simplified`; do not silently retarget this
    # twin — that is an experiment-design choice (see PR notes).
    assert row["prompt_file"] == "correspondence_specialist_production"
    assert expected_limit("run-20-correspondence-fp16-c8") == 20
    spec = load_run_spec(
        Path(__file__).resolve().parents[1]
        / "config"
        / "runs"
        / "run-20-correspondence-fp16-c8.yaml"
    )
    assert spec.engine.model == "Qwen/Qwen3-8B"
    assert spec.engine.vllm.quantization in ("", None)
    assert spec.engine.vllm.max_model_len == 16384
    assert spec.dataset.sample_seed == 42
    assert spec.dataset.limit == 20
    assert spec.job.concurrency == 8


def test_run_20_gate_enforces_limit_20(monkeypatch):
    """The loud gate must cover run-20 too — a wrong limit cannot pass green."""
    _stub_modal(monkeypatch)
    root = Path(__file__).resolve().parents[1] / "config" / "runs"
    spec = load_run_spec(root / "run-20-contracts-specialist.yaml")
    report = check_benchmark_posture(spec=spec, require_hermes=True)
    assert report["ok"], report["errors"]
    assert report["checks"]["spec"]["limit"] == 20
    assert report["checks"]["spec"]["local_prompts"] == {
        "contracts_specialist": "contracts_specialist_v33_simplified"
    }
    bad = spec.model_copy(
        update={"dataset": spec.dataset.model_copy(update={"limit": 30})}
    )
    bad_report = check_benchmark_posture(spec=bad, require_hermes=True)
    assert bad_report["ok"] is False
    assert any("dataset.limit" in e for e in bad_report["errors"])


def test_merger_is_dedicated_specialist():
    row = SPECIALIST_POSTURE["run-30-merger-specialist"]
    assert row["task"] == "merger_agreement_specialist"
    assert row["agent"] == "merger_agreement_specialist"
    assert SPECIALIST_LOCAL_PROMPTS["run-30-merger-specialist"] == {
        "merger_agreement_specialist": "merger_agreement_specialist_simplified"
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
        # SAND-018/019: AWQ variants (incl. the -awq-c8 suffix) run the quantized
        # checkpoint; every other specialist run stays on the bf16 default.
        if "-awq" in run_id:
            assert spec.engine.model == "Qwen/Qwen3-8B-AWQ"
            assert spec.engine.vllm.quantization == "awq"
        else:
            assert spec.engine.model == "Qwen/Qwen3-8B"
        report = check_benchmark_posture(spec=spec, require_hermes=True)
        assert report["ok"], (run_id, report["errors"])
