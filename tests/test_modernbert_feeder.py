"""ModernBERT feeder path resolution + benchmark gate (network-free)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mailroom_sandbox.job.benchmark_check import (
    HERMES_MODAL_PROFILE,
    check_benchmark_posture,
)
from mailroom_sandbox.job.spec import FAMILY_CLASS_COUNTS, FAMILY_CORPUS_SIZE, load_run_spec
from mailroom_sandbox.modernbert import (
    feeder_status,
    resolve_mailroom_ml_src,
    resolve_modernbert_model_path,
    serving_record_from_eval,
)


def test_family_corpus_size_constant():
    assert FAMILY_CORPUS_SIZE == 3302
    assert sum(FAMILY_CLASS_COUNTS.values()) == FAMILY_CORPUS_SIZE
    assert FAMILY_CLASS_COUNTS["merger_agreement"] == 152


def _fake_mailroom_ml(root: Path, *, with_eval_cli: bool = True) -> Path:
    """Build a minimal mailroom-ml checkout (src pkg, eval CLI, published bundle)."""
    (root / "src" / "mailroom_ml").mkdir(parents=True)
    (root / "src" / "mailroom_ml" / "__init__.py").write_text("", encoding="utf-8")
    if with_eval_cli:
        (root / "training").mkdir()
        (root / "training" / "eval_modernbert.py").write_text("", encoding="utf-8")
    bundle = root / "artifacts" / "run2-published"
    bundle.mkdir(parents=True)
    (bundle / "labels.json").write_text("{}", encoding="utf-8")
    return root


def _clear_model_env(monkeypatch):
    monkeypatch.delenv("MODERNBERT_MODEL_PATH", raising=False)
    monkeypatch.delenv("ML_MODEL_DIR", raising=False)


def test_modernbert_feeder_resolves_ml_checkout(tmp_path, monkeypatch):
    # Hermetic: never depends on a mailroom-ml checkout on the developer's machine.
    ml = _fake_mailroom_ml(tmp_path / "mailroom-ml")
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("MAILROOM_ML_SRC", str(ml))

    assert resolve_mailroom_ml_src() == ml.resolve()
    assert resolve_modernbert_model_path() == (ml / "artifacts" / "run2-published").resolve()
    status = feeder_status()
    assert status["ok"] is True
    assert status["mailroom_ml_src"] == str(ml.resolve())
    assert status["modernbert_model_path"] == str((ml / "artifacts" / "run2-published").resolve())
    assert status["eval_entrypoint"] == str((ml / "training" / "eval_modernbert.py").resolve())


def test_modernbert_feeder_status_not_ok_without_eval_entrypoint(tmp_path, monkeypatch):
    # A checkout with weights but no eval CLI must report not-ok, loudly.
    ml = _fake_mailroom_ml(tmp_path / "mailroom-ml", with_eval_cli=False)
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("MAILROOM_ML_SRC", str(ml))

    status = feeder_status()
    assert status["ok"] is False
    assert status["eval_entrypoint"] is None
    assert status["modernbert_model_path"] is not None


def test_modernbert_env_override(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "labels.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("MODERNBERT_MODEL_PATH", str(bundle))
    assert resolve_modernbert_model_path() == bundle.resolve()


def test_serving_record_from_eval():
    report = {
        "n_docs": 10,
        "seed": 42,
        "doc_type_accuracy": 0.9,
        "subclass_accuracy_conditional": 0.8,
        "model_kind": "onnx-fp32",
        "artifact_sha": "abc",
        "_sandbox_wall_seconds": 5.0,
        "_checkpoint": "/tmp/ckpt",
    }
    rec = serving_record_from_eval(report)
    assert rec["n"] == 10
    assert rec["serving_kind"] == "modernbert"
    assert rec["e2e_latency_seconds"] == pytest.approx(0.5)
    assert rec["scores"]["doc_type_accuracy"] == 0.9


def test_benchmark_check_contracts_spec(monkeypatch):
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check.active_modal_profile_name",
        lambda: HERMES_MODAL_PROFILE,
    )
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check._modal_cli_ok",
        lambda: {"ok": True, "version": "modal-stub"},
    )
    spec = load_run_spec(
        Path(__file__).resolve().parents[1]
        / "config"
        / "runs"
        / "legacy"
        / "run-30-contracts-specialist.yaml"
    )
    report = check_benchmark_posture(spec=spec, require_hermes=True)
    assert report["ok"] is True, report["errors"]
    assert report["checks"]["spec"]["concurrency"] == 4
    assert report["checks"]["spec"]["gpu"] == "L4"
    assert report["checks"]["spec"]["scaledown_seconds"] == 120
    assert report["checks"]["spec"]["min_containers"] == 0
    assert report["checks"]["spec"]["max_containers"] == 1
    assert report["checks"]["spec"]["limit"] == 30
    assert report["checks"]["spec"]["local_prompts"] == {
        "contracts_specialist": "contracts_specialist_v33_simplified"
    }
    assert report["checks"]["expected"]["scaledown_seconds"] == 120
    assert report["checks"]["spend_posture"]["warm_app_once"] is True


def test_benchmark_check_merger_spec_uses_dedicated_specialist(monkeypatch):
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check.active_modal_profile_name",
        lambda: HERMES_MODAL_PROFILE,
    )
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check._modal_cli_ok",
        lambda: {"ok": True, "version": "modal-stub"},
    )
    spec = load_run_spec(
        Path(__file__).resolve().parents[1]
        / "config"
        / "runs"
        / "legacy"
        / "run-30-merger-specialist.yaml"
    )
    assert spec.task == "merger_agreement_specialist"
    report = check_benchmark_posture(spec=spec, require_hermes=True)
    assert report["ok"] is True, report["errors"]
    assert report["checks"]["spec"]["local_prompts"] == {
        "merger_agreement_specialist": "merger_agreement_specialist_simplified"
    }


def test_benchmark_check_scaledown_drift_fails(monkeypatch):
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check.active_modal_profile_name",
        lambda: HERMES_MODAL_PROFILE,
    )
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check._modal_cli_ok",
        lambda: {"ok": True, "version": "modal-stub"},
    )
    spec = load_run_spec(
        Path(__file__).resolve().parents[1]
        / "config"
        / "runs"
        / "legacy"
        / "run-30-contracts-specialist.yaml"
    )
    bad = spec.model_copy(
        update={
            "engine": spec.engine.model_copy(
                update={
                    "modal": spec.engine.modal.model_copy(update={"scaledown_seconds": 600})
                }
            )
        }
    )
    report = check_benchmark_posture(spec=bad, require_hermes=True)
    assert report["ok"] is False
    assert any("scaledown_seconds" in e for e in report["errors"])


def test_benchmark_check_fails_wrong_profile(monkeypatch):
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check.active_modal_profile_name",
        lambda: "exios66",
    )
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check._modal_cli_ok",
        lambda: {"ok": True, "version": "modal-stub"},
    )
    report = check_benchmark_posture(spec=None, require_hermes=True)
    assert report["ok"] is False
    assert any("hermes-agent-jjb" in e for e in report["errors"])


def test_modal_matrix_default_and_awq():
    from mailroom_sandbox.modal_matrix import (
        DEFAULT_MODAL_MODEL,
        env_exports,
        list_modal_models,
        resolve_modal_row,
    )

    rows = list_modal_models()
    assert any(r["default"] and r["model"] == DEFAULT_MODAL_MODEL for r in rows)
    default = resolve_modal_row()
    assert default["model"] == "Qwen/Qwen3.5-9B"  # SAND-077
    assert default["quantization"] == "fp8"
    assert default["gpu"] == "L4"
    assert default["is_default"] is True
    awq = resolve_modal_row("Qwen/Qwen3-8B-AWQ")
    assert awq["quantization"] == "awq"
    assert awq["max_model_len"] == 32768
    assert "MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ" in env_exports("Qwen/Qwen3-8B-AWQ")
    overridden = resolve_modal_row("Qwen/Qwen3-8B", gpu_override="A100-80GB:2")
    assert overridden["gpu"] == "A100-80GB:2"
    assert overridden["tp_size"] == 2
