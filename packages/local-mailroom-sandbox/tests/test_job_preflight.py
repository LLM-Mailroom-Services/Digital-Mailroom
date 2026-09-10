"""Preflight lock + drift tests (DMR-027) — network-free."""
from __future__ import annotations
import pytest

import json

from mailroom_sandbox.job import preflight
from mailroom_sandbox.job.spec import DatasetSpec, RunSpec, run_dir


def _run_spec(tmp_path, *, rows=2, limit=2, run_id="pf-1") -> RunSpec:
    path = tmp_path / "f.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(rows):
            cls = "contract" if i % 2 else "insurance_claim"
            fh.write(
                json.dumps(
                    {
                        "id": f"d{i}",
                        "filename": f"{i}.txt",
                        "doc_text": f"t{i}",
                        "expected": cls,
                        "expected_subclass": "service" if i % 2 else "auto",
                    }
                )
                + "\n"
            )
    return RunSpec(
        run_id=run_id,
        task="sorter",
        dataset=DatasetSpec(local_path=f"file://{path}", limit=limit),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
    )


def _store(report):
    from mailroom_sandbox.job.checkpoint import RunStore

    return RunStore(run_dir(report["run_id"]))


def test_preflight_prepares_and_locks(tmp_path):
    spec = _run_spec(tmp_path)
    report = preflight.preflight(spec, offline=True, live=False)
    assert report["status"] == "prepared"
    store = _store(report)
    lock = store.read_lock()
    assert lock and lock["spec_hash"] == spec.spec_hash()
    assert store.dataset_path.is_file()
    assert len(store.dataset_rows()) == 2
    assert store.spec_hash() == spec.spec_hash()


def test_preflight_drift_refusal_then_force(tmp_path):
    spec = _run_spec(tmp_path, limit=2)
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared"
    drifted = _run_spec(tmp_path, limit=2, run_id=spec.run_id)
    drifted.dataset = DatasetSpec(local_path=drifted.dataset.local_path, limit=1)
    assert drifted.spec_hash() != spec.spec_hash()
    report2 = preflight.preflight(drifted, offline=True)
    assert report2["status"] == "drift_refused"
    report3 = preflight.preflight(drifted, offline=True, force=True)
    assert report3["status"] == "prepared"


def test_preflight_unknown_prompt_agent_fails(tmp_path):
    spec = _run_spec(tmp_path)
    spec.prompt = {"agents": {"extract": {"source": "code-default"}}}
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "failed"
    assert any(c["name"] == "prompt" and not c["ok"] for c in report["checks"])




pytestmark = pytest.mark.usefixtures("job_data_dir")
