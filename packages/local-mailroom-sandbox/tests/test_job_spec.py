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
    VLLMSpec()  # defaults valid
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