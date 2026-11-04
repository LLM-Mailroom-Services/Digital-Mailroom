"""Service commands publish `mailroom.beacon/v1` jobs so the board shows what they are doing."""

from __future__ import annotations

import json

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.services._exec import ServiceError
from mailroom_sandbox.services.beacon import service_job
from mailroom_sandbox.tui.beacon import beacon_root


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    for name in ("MODAL_WORKSPACE", "VLLM_BASE_URL", "MODAL_VLLM_APP_NAME", "HF_HOME", "HF_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("mailroom_sandbox.services.modal_cli.VERIFY_DELAY", 0.0)


def _job(name):
    return json.loads((beacon_root() / f"svc-{name}.json").read_text(encoding="utf-8"))


def _log(name):
    return (beacon_root() / f"svc-{name}.log").read_text(encoding="utf-8").splitlines()


def test_service_job_publishes_running_then_done():
    with service_job("demo", title="demo job") as job:
        job.update(phase="WORKING")
        assert _job("demo")["state"] == "running" and _job("demo")["phase"] == "WORKING"
    row = _job("demo")
    assert row["state"] == "done" and row["package"] == "local-mailroom-sandbox"
    assert row["title"] == "demo job"


def test_service_job_records_a_failure_and_still_raises():
    with pytest.raises(ServiceError):
        with service_job("boom"):
            raise ServiceError("tool exploded")
    row = _job("boom")
    assert row["state"] == "failed" and "tool exploded" in row["metrics"]["error"]


def test_modal_deploy_publishes_a_job_with_the_tool_output(fake_bin, monkeypatch):
    fake_bin.add(
        "modal",
        stdout="building image\nready\n",
        rules=[{"prefix": ["--version"], "stdout": "modal client version: 1.6.2\n"}],
    )
    monkeypatch.setenv("MODAL_WORKSPACE", "ws")
    assert cli.main(["modal", "deploy"]) == 0
    assert _job("modal-deploy")["state"] == "done"
    assert "building image" in _log("modal-deploy")


def test_a_failed_deploy_publishes_a_failed_job(fake_bin):
    fake_bin.add(
        "modal",
        rc=2,
        rules=[{"prefix": ["--version"], "stdout": "modal client version: 1.6.2\n"}],
    )
    assert cli.main(["modal", "deploy"]) == 1
    assert _job("modal-deploy")["state"] == "failed"


def test_dry_run_publishes_nothing(fake_bin):
    assert cli.main(["modal", "deploy", "--dry-run"]) == 0
    assert cli.main(["hf", "download", "--dry-run"]) == 0
    assert not list(beacon_root().glob("svc-*.json")) if beacon_root().exists() else True


def test_prewarm_and_stop_publish_jobs(fake_bin):
    fake_bin.add(
        "modal",
        rules=[
            {"prefix": ["--version"], "stdout": "modal client version: 1.6.2\n"},
            {"prefix": ["app", "list"], "stdout": "[]"},
        ],
    )
    assert cli.main(["modal", "prewarm"]) == 0
    assert cli.main(["modal", "stop"]) == 0
    assert _job("modal-prewarm")["state"] == "done"
    assert _job("modal-stop")["state"] == "done"


def test_hf_download_publishes_a_job(fake_bin):
    fake_bin.add("hf", stdout="Fetching 3 files\n")
    assert cli.main(["hf", "download"]) == 0
    assert _job("hf-download")["state"] == "done"
    assert "Fetching 3 files" in _log("hf-download")


def test_tunnel_up_publishes_a_job(monkeypatch):
    monkeypatch.setenv("SANDBOX_PROFILE", "vllm-remote")
    monkeypatch.setenv("SANDBOX_TUNNEL_HOST", "h")
    monkeypatch.setenv("SANDBOX_TUNNEL_USER", "u")
    monkeypatch.setattr("mailroom_sandbox.tunnel.spawn", lambda spec, **kw: 4242)
    assert cli.main(["tunnel", "up"]) == 0
    assert _job("tunnel-up")["state"] == "done"


def test_datasets_pull_publishes_a_job(monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.datasets.pull_hf_dataset", lambda *a, **k: None)
    assert cli.main(["datasets", "pull"]) == 0
    assert _job("datasets-pull")["state"] == "done"


def test_doctor_beacon_records_failed_checks(fake_bin):
    assert cli.main(['doctor', '--profile', 'modal-vllm', '--service', 'provider']) == 1
    assert _job('doctor')['state'] == 'failed'


def test_doctor_beacon_records_a_success(fake_bin):
    assert cli.main(['doctor', '--service', 'git']) == 0
    assert _job('doctor')['state'] == 'done'


def test_compose_start_beacon_tracks_tool_failure(fake_bin):
    fake_bin.add('docker', rc=1)
    assert cli.main(['up', '-d']) == 1
    assert _job('up')['state'] == 'failed'


@pytest.mark.parametrize('rc', [0, 1])
def test_pull_models_beacon_tracks_return_code(monkeypatch, rc):
    monkeypatch.setattr('mailroom_sandbox.compose.pull_ollama_models', lambda models: rc)
    assert cli.main(['pull-models', '--profile', 'ollama']) == rc
    assert _job('pull-models')['state'] == ('failed' if rc else 'done')


def test_modal_pull_models_guidance_does_not_claim_a_download():
    assert cli.main(['pull-models', '--profile', 'modal-vllm']) == 0
    assert not (beacon_root() / 'svc-pull-models.json').exists()
