"""Run-spec model tests (DMR-027)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from mailroom_sandbox.job.spec import (
    DatasetSpec,
    ModalSpec,
    PromptRef,
    RunSpec,
    VLLMSpec,
    load_run_spec,
    resolve_run_id,
    spec_core,
    spec_hash,
)


def _spec(**overrides) -> RunSpec:
    base = dict(
        task="sorter",
        dataset=DatasetSpec(local_path="file:///tmp/x.jsonl"),
        engine={"kind": "vllm-local", "modal": None},
    )
    base.update(overrides)
    return RunSpec(**base)


def test_spec_hash_stable_across_instances():
    assert _spec().spec_hash() == _spec().spec_hash()


def test_spec_hash_changes_with_dataset():
    a = _spec(dataset=DatasetSpec(local_path="file:///tmp/a.jsonl"))
    b = _spec(dataset=DatasetSpec(local_path="file:///tmp/b.jsonl"))
    assert a.spec_hash() != b.spec_hash()


def test_spec_hash_ignores_run_id_and_artifacts():
    a = RunSpec(run_id="run-a", dataset=DatasetSpec(local_path="file:///tmp/x.jsonl"))
    b = RunSpec(run_id="run-b", dataset=DatasetSpec(local_path="file:///tmp/x.jsonl"))
    assert a.spec_hash() == b.spec_hash()


def test_spec_core_is_behavioral_and_json_serializable():
    core = spec_core(_spec())
    assert "run_id" not in json.dumps(json.loads(json.dumps(core)))


def test_vllm_range_validation():
    # DMR-056 pin: the DEFAULT max_model_len is 16384 (boot-valid for L4-bf16
    # 8B-class rows on v0.28.0 — 32768 RAISES at the KV admission check), not
    # the pre-DMR-056 32768; AWQ/FP8 rows opt up explicitly.
    assert VLLMSpec().max_model_len == 16384
    VLLMSpec(max_model_len=32768)  # explicit opt-up stays valid
    with pytest.raises(ValidationError):
        VLLMSpec(gpu_memory_utilization=1.5)
    with pytest.raises(ValidationError):
        VLLMSpec(max_num_seqs=0)
    with pytest.raises(ValidationError):
        VLLMSpec(quantization="nope")


def test_modal_gpu_and_pin_validation():
    with pytest.raises(ValidationError):
        RunSpec(engine={"kind": "modal-vllm", "modal": {"gpu": "Voodoo"}})
    with pytest.raises(ValidationError):
        RunSpec(engine={"kind": "modal-vllm", "modal": {"image_tag": "latest"}})


def test_job_concurrency_validation():
    # Modal vLLM throughput alignment: bounded concurrent per-item runs.
    # Default stays 1 (serial, deterministic); validated [1, 64] so a runaway
    # spec value is rejected at preflight, not discovered as a cost spike.
    from mailroom_sandbox.job.spec import JobSpec

    assert JobSpec().concurrency == 1
    assert JobSpec(concurrency=16).concurrency == 16
    with pytest.raises(ValidationError):
        JobSpec(concurrency=0)
    with pytest.raises(ValidationError):
        JobSpec(concurrency=65)
    # Behavioral knob: it must be covered by the spec hash like the others.
    assert spec_hash(_spec(job={"concurrency": 4})) != spec_hash(_spec(job={"concurrency": 8}))


def test_prompt_ref_invariants():
    with pytest.raises(ValidationError):
        PromptRef(source="langfuse", name="x", version=1, label="production")  # xor
    with pytest.raises(ValidationError):
        PromptRef(source="local")  # needs file
    PromptRef(source="code-default")  # ok


def test_run_id_regex_enforced():
    with pytest.raises(Exception):
        resolve_run_id(RunSpec(run_id="bad id with spaces"))


def test_yaml_load_roundtrip(tmp_path):
    import yaml

    path = tmp_path / "run.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "run_id": "example",
                "task": "sorter",
                "dataset": {"provider": "file", "local_path": "file:///tmp/x.jsonl"},
                "engine": {"kind": "vllm-local", "modal": None},
                "prompt": {"agents": {"judge": {"source": "local", "file": "judge_local_v0"}}},
            }
        ),
        encoding="utf-8",
    )
    spec = load_run_spec(path)
    assert spec.run_id == "example"
    assert spec.prompt["agents"]["judge"]["file"] == "judge_local_v0"
    assert spec_hash(spec)