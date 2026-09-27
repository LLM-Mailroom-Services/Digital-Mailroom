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


class _FakeResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {"data": [{"id": "Qwen/Qwen3-8B"}]}

    def json(self):
        return self._payload


def test_engine_probe_url_seam_normalizes_v1_suffix(monkeypatch, tmp_path):
    """DMR-062: VLLM_BASE_URL / profile base_url carry the OpenAPI '/v1'
    seam (family contract), so the probe must NOT append '/v1/models' to an
    already-seamed base — that produced .../v1/v1/models and a live 404."""
    seen: list[str] = []

    def fake_get(url, headers=None, timeout=None):
        seen.append(url)
        return _FakeResp(200)

    monkeypatch.setattr("httpx.get", fake_get)
    monkeypatch.setenv("VLLM_API_KEY", "tok")

    # Seamed base (the documented contract: https://…-serve.modal.run/v1)
    monkeypatch.setenv(
        "VLLM_BASE_URL", "https://exios66--sandbox-vllm-serve.modal.run/v1"
    )
    spec = _run_spec(tmp_path)
    result = preflight.probe_engine(spec)
    assert result["ok"] is True
    assert seen == ["https://exios66--sandbox-vllm-serve.modal.run/v1/models"]

    # Un-seamed base (engine_base_url's modal-vllm fallback) still gets /v1
    seen.clear()
    monkeypatch.setenv("VLLM_BASE_URL", "https://exios66--sandbox-vllm-serve.modal.run")
    result = preflight.probe_engine(spec)
    assert result["ok"] is True
    assert seen == ["https://exios66--sandbox-vllm-serve.modal.run/v1/models"]

    # 401 keeps its bearer hint (DMR-048 regression)
    monkeypatch.setattr("httpx.get", lambda *a, **k: _FakeResp(401))
    result = preflight.probe_engine(spec)
    assert result["ok"] is False and "VLLM_API_KEY" in result["reason"]


def test_probe_engine_records_cold_boot_seconds(monkeypatch, tmp_path):
    """SAND-018: the live engine probe times the first successful response so a
    cold app's boot is measured, not assumed."""
    monkeypatch.setattr("httpx.get", lambda *a, **k: _FakeResp(200))
    monkeypatch.setenv("VLLM_API_KEY", "tok")
    spec = _run_spec(tmp_path)
    result = preflight.probe_engine(spec)
    assert result["ok"] is True
    assert isinstance(result["cold_boot_seconds"], float)
    assert result["cold_boot_seconds"] >= 0.0
    # non-modal profiles keep the short CI-safe probe budget
    assert result["probe_timeout_seconds"] == 10.0


def test_probe_engine_retries_empty_2xx_until_ready(monkeypatch, tmp_path):
    """SAND-018: a booting web_server can answer 2xx with an empty body before
    vLLM is ready — the probe must retry, not misreport it as the wrong API."""
    calls = {"n": 0}

    class _Empty:
        status_code = 200
        text = ""

        def json(self):
            raise ValueError("empty")

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        return _Empty() if calls["n"] == 1 else _FakeResp(200)

    monkeypatch.setattr("httpx.get", fake_get)
    monkeypatch.setenv("VLLM_API_KEY", "tok")
    monkeypatch.setenv("SANDBOX_ENGINE_PROBE_TIMEOUT_SECONDS", "5")
    spec = _run_spec(tmp_path)
    result = preflight.probe_engine(spec)
    assert result["ok"] is True
    assert calls["n"] == 2
    assert result["cold_boot_seconds"] >= 0.0


def test_probe_timeout_modal_uses_boot_budget(monkeypatch, tmp_path):
    """A scale-to-zero Modal app holds the probe open while it boots, so the
    hard 10 s timeout would misreport a booting app as unreachable."""
    monkeypatch.delenv("SANDBOX_ENGINE_PROBE_TIMEOUT_SECONDS", raising=False)
    spec = _run_spec(tmp_path)
    spec.engine.kind = "modal-vllm"
    assert preflight._probe_timeout_seconds(spec) == 1200.0
    monkeypatch.setenv("SANDBOX_ENGINE_PROBE_TIMEOUT_SECONDS", "42")
    assert preflight._probe_timeout_seconds(spec) == 42.0


def test_preflight_live_persists_cold_boot_and_record_carries_it(
    monkeypatch, tmp_path, job_data_dir
):
    """SAND-018: `preflight --live` writes cold_boot.json and the run's
    experiment-log record carries the measured boot."""
    from mailroom_sandbox.job import runner

    monkeypatch.setattr("httpx.get", lambda *a, **k: _FakeResp(200))
    monkeypatch.setenv("VLLM_API_KEY", "tok")
    spec = _run_spec(tmp_path, run_id="pf-coldboot")
    report = preflight.preflight(spec, offline=True, live=True)
    assert report["status"] == "prepared"
    assert report["cold_boot_seconds"] >= 0.0
    store = _store(report)
    boot = store.read_cold_boot()
    assert boot and boot["run_id"] == "pf-coldboot"
    assert isinstance(boot["cold_boot_seconds"], float)

    summary = runner.run_job(store, mock=True)
    assert summary["state"] == "done"
    assert summary["record"]["cold_boot_seconds"] == boot["cold_boot_seconds"]


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


def test_preflight_corrupt_lock_refuses_loud(tmp_path, job_data_dir):
    # hub#41: a corrupt spec.lock.json is a loud preflight failure naming
    # the path — never a silent run with spec_hash: null.
    spec = _run_spec(tmp_path, run_id="pf-corrupt")
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared"
    store = _store(report)
    store.lock_path.write_text("{garbage", encoding="utf-8")
    report2 = preflight.preflight(spec, offline=True)
    assert report2["status"] == "failed"
    assert report2["checks"][0]["name"] == "lock"
    assert not report2["checks"][0]["ok"]
    assert "corrupt JSON" in report2["checks"][0]["detail"]
    assert str(store.lock_path) in report2["checks"][0]["detail"]


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


def test_prompt_text_change_triggers_drift(tmp_path, job_data_dir, monkeypatch):
    """DMR-049: a local prompt FILE body change must refuse the stale lock."""
    variant_dir = tmp_path / "prompts"
    variant_dir.mkdir()
    (variant_dir / "sorter_x.txt").write_text("prompt version A", encoding="utf-8")
    monkeypatch.setattr("mailroom_sandbox.prompt_registry.prompts_dir", lambda: variant_dir)

    spec = _run_spec(tmp_path, run_id="pf-promptdrift")
    spec.prompt = {"agents": {"sorter": {"source": "local", "file": "sorter_x"}}}
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared"
    store = _store(report)
    first_sha = (store.read_lock() or {}).get("prompt_text_sha")

    (variant_dir / "sorter_x.txt").write_text("prompt version B", encoding="utf-8")
    report2 = preflight.preflight(spec, offline=True)
    assert report2["status"] == "drift_refused"

    report3 = preflight.preflight(spec, offline=True, force=True)
    assert report3["status"] == "prepared"
    assert (store.read_lock() or {}).get("prompt_text_sha") != first_sha


def test_hub_gt_absent_refuses_blind_rows(tmp_path, job_data_dir, monkeypatch):
    """DMR-049: a missing ground_truth shard must never become unlabeled rows."""
    from mailroom_sandbox.job.spec import FAMILY_HF_REVISION

    import huggingface_hub
    import pyarrow as pa
    import pyarrow.parquet as pq

    def _fake_list_repo_files(repo, revision=None, repo_type=None):
        return ["parquet/default/test/test-00000-of-00001.parquet"]

    dflt = tmp_path / "default.parquet"
    pq.write_table(
        pa.Table.from_pylist([{"filename": "f.txt", "doc_text": "t"}]),
        dflt,
    )

    monkeypatch.setattr(huggingface_hub, "list_repo_files", _fake_list_repo_files)
    monkeypatch.setattr(
        huggingface_hub,
        "hf_hub_download",
        lambda repo, filename, revision=None, repo_type=None, **kw: str(dflt),
    )

    spec = RunSpec(
        run_id="hub-blind",
        task="sorter",
        dataset=DatasetSpec(
            provider="huggingface",
            repo="Lucius-Morningstar/mailroom-dataset",
            revision=FAMILY_HF_REVISION,
            limit=1,
        ),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        job={"mock": True},
    )
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "failed"
    assert "refusing to prepare blind rows" in str(report["checks"][-1]["detail"])


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
        return [
            "parquet/default/test/test-00000-of-00001.parquet",
            "parquet/ground_truth/test/test-00000-of-00001.parquet",
        ]

    dflt = tmp_path / "default.parquet"
    gt = tmp_path / "ground_truth.parquet"
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
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "filename": "f0.txt",
                    "expected": "contract",
                    "expected_subclass": "service",
                }
            ]
        ),
        gt,
    )

    def _fake_hf_hub_download(repo, filename, revision=None, repo_type=None, **kw):
        return str(gt if "ground_truth" in filename else dflt)

    monkeypatch.setattr(huggingface_hub.HfApi, "dataset_info", _fake_dataset_info)
    monkeypatch.setattr(huggingface_hub, "list_repo_files", _fake_list_repo_files)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", _fake_hf_hub_download)

    spec = RunSpec(
        run_id="hub-lock",
        task="sorter",
        dataset=DatasetSpec(
            provider="huggingface",
            repo="Lucius-Morningstar/mailroom-dataset",
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
