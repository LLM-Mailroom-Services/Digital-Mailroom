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


def test_force_relock_archives_old_generation(tmp_path, job_data_dir):
    """DMR-049: --force must move the old lock/items aside, not leave them."""
    from pathlib import Path

    spec = _run_spec(tmp_path, limit=2, run_id="pf-archive")
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared"
    store = _store(report)
    old_hash = store.spec_hash()
    drifted = _run_spec(tmp_path, limit=2, run_id=spec.run_id)
    drifted.dataset = DatasetSpec(local_path=drifted.dataset.local_path, limit=1)
    report2 = preflight.preflight(drifted, offline=True, force=True)
    assert report2["status"] == "prepared"
    archived = Path(report2["archived"])
    assert archived.is_dir()
    archived_lock = (archived / "spec.lock.json").read_text(encoding="utf-8")
    assert old_hash in archived_lock
    assert store.spec_hash() == drifted.spec_hash() != old_hash


def test_run_job_refuses_drifted_dataset(tmp_path, job_data_dir):
    """DMR-049: a dataset that changed under the lock must never be scored."""
    from mailroom_sandbox.job import runner

    spec = _run_spec(tmp_path, limit=2, run_id="pf-drift")
    report = preflight.preflight(spec, offline=True)
    store = _store(report)
    store.dataset_path.write_text('{"id": "x", "doc_text": "mutated"}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed since the lock"):
        runner.run_job(store, mock=None)


def test_preflight_unknown_prompt_agent_fails(tmp_path):
    spec = _run_spec(tmp_path)
    spec.prompt = {"agents": {"extract": {"source": "code-default"}}}
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "failed"
    assert any(c["name"] == "prompt" and not c["ok"] for c in report["checks"])


def test_preflight_hub_spec_locks_pinned_revision(tmp_path, monkeypatch):
    """DMR-042: a Hub-spec preflight must lock the pinned sha, not float."""
    from mailroom_sandbox.job.spec import FAMILY_HF_REVISION

    # Stub the corpus Hub path so preflight's dataset check is network-free.
    import huggingface_hub

    class _FakeInfo:
        sha = FAMILY_HF_REVISION

    def _fake_dataset_info(repo, revision=None):
        return _FakeInfo()

    def _fake_list_repo_files(repo, revision=None, repo_type=None):
        return ["parquet/default/test/test-00000-of-00001.parquet"]

    dflt = tmp_path / "default.parquet"
    import pyarrow as pa
    import pyarrow.parquet as pq

    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "filename": "f0.txt",
                    "doc_text": "hub text 0",
                    "prompt": "",
                    "metadata": {"source": "test"},
                }
            ]
        ),
        dflt,
    )

    def _fake_hf_hub_download(repo, filename, revision=None, repo_type=None, **kw):
        return str(dflt)

    monkeypatch.setattr(huggingface_hub.HfApi, "dataset_info", _fake_dataset_info)
    monkeypatch.setattr(huggingface_hub, "list_repo_files", _fake_list_repo_files)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", _fake_hf_hub_download)

    spec = RunSpec(
        run_id="hub-lock",
        task="sorter",
        dataset=DatasetSpec(
            provider="huggingface",
            repo="Lucius-Morningstar/mailroom-corpus",
            revision=FAMILY_HF_REVISION,
            limit=1,
        ),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        job={"mock": True},
    )
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    store = _store(report)
    lock = store.read_lock() or {}
    assert lock["dataset"]["revision"] == FAMILY_HF_REVISION
    assert lock["dataset"]["rows"] == 1


pytestmark = pytest.mark.usefixtures("job_data_dir")
