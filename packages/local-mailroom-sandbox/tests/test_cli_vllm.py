"""`sandbox vllm …`: probe a vLLM endpoint, print/serve the ``vllm serve`` command, scrape metrics.

Network-free: ``httpx`` is stubbed and ``vllm`` is a fake binary. ``command`` builds the argv
from ``deploy/modal_vllm.py::build_vllm_command`` itself (the Modal SDK is not needed), so the
printed command can never drift from what the Modal app actually launches.
"""

from __future__ import annotations

import hashlib
import json

import httpx
import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.job.spec import DEFAULT_ENGINE_MODEL

BASE = "http://vllm.test/v1"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    # The probe/metrics default profile is read from SANDBOX_PROFILE; another test can leave it
    # pointing at ollama, which would send these tests to localhost:11434.
    monkeypatch.setenv("SANDBOX_PROFILE", "modal-vllm")
    for name in (
        "MODAL_WORKSPACE", "VLLM_BASE_URL", "VLLM_API_KEY", "MODAL_VLLM_API_TOKEN",
        "MODAL_VLLM_MODEL", "MODAL_VLLM_GPU", "VLLM_MODEL", "MODAL_VLLM_APP_NAME",
    ):
        monkeypatch.delenv(name, raising=False)


def _serve(monkeypatch, *, models=(DEFAULT_ENGINE_MODEL,), health=200, metrics=200, down=False, seen=None):
    """Answer the four endpoints a vLLM server exposes."""

    def get(url, **kw):
        if seen is not None:
            seen.append((url, kw.get("headers", {})))
        if down:
            raise httpx.ConnectError("refused")
        if url.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": m} for m in models]})
        if url.endswith("/health"):
            return httpx.Response(health, text="")
        if url.endswith("/metrics"):
            return httpx.Response(metrics, text="# HELP\nvllm:request_success_total 3\n")
        return httpx.Response(404)

    def post(url, **kw):
        if down:
            raise httpx.ConnectError("refused")
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", get)
    monkeypatch.setattr("mailroom_sandbox.health.httpx.post", post)


# --------------------------------------------------------------------------- probe


def test_probe_without_an_endpoint_fails_with_the_deploy_hint_and_probes_nothing(monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("must not touch the network for an unresolved modal-vllm endpoint")

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", boom)
    assert cli.main(["vllm", "probe"]) == 1
    err = capsys.readouterr().err
    assert "VLLM_BASE_URL" in err and "localhost" not in err


def test_probe_reports_models_chat_health_and_metrics(monkeypatch, capsys):
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    _serve(monkeypatch)
    assert cli.main(["vllm", "probe"]) == 0
    out = capsys.readouterr().out
    for word in ("models", "chat", "health", "metrics"):
        assert word in out
    assert DEFAULT_ENGINE_MODEL in out


def test_probe_json_shape(monkeypatch, capsys):
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    _serve(monkeypatch)
    assert cli.main(["vllm", "probe", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert {"models", "chat", "health", "metrics", "served_model_ok"} <= set(report)
    assert report["health"]["url"] == "http://vllm.test/health"
    assert report["metrics"]["url"] == "http://vllm.test/metrics"


def test_probe_sends_the_bearer_token_to_every_endpoint(monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    monkeypatch.setenv("VLLM_API_KEY", "tok123")
    seen: list = []
    _serve(monkeypatch, seen=seen)
    assert cli.main(["vllm", "probe"]) == 0
    assert seen and all(h.get("Authorization") == "Bearer tok123" for _, h in seen)


def test_probe_fails_when_the_served_model_is_not_the_one_the_run_will_ask_for(monkeypatch, capsys):
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    monkeypatch.setenv("MODAL_VLLM_MODEL", "Qwen/Qwen3-8B-AWQ")
    _serve(monkeypatch, models=("Qwen/Qwen3-8B",))
    assert cli.main(["vllm", "probe"]) == 1
    err = capsys.readouterr().err
    assert "Qwen/Qwen3-8B-AWQ" in err and "serves" in err


def test_probe_unreachable_server_is_a_failure_with_chat_skipped(monkeypatch, capsys):
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    _serve(monkeypatch, down=True)
    assert cli.main(["vllm", "probe", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False and report["models"]["ok"] is False
    assert "skipped" in report["chat"]["detail"]


def test_probe_metrics_unavailable_is_informational_not_a_failure(monkeypatch, capsys):
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    _serve(monkeypatch, metrics=404, health=503)
    assert cli.main(["vllm", "probe", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["metrics"]["ok"] is False and report["health"]["ok"] is False and report["ok"] is True


def test_probe_warns_that_a_modal_endpoint_may_wake_a_billed_gpu(monkeypatch, capsys):
    monkeypatch.setenv("VLLM_BASE_URL", "https://ws--sandbox-vllm-serve.modal.run/v1")
    _serve(monkeypatch)
    cli.main(["vllm", "probe"])
    assert "cold-start" in capsys.readouterr().err


# --------------------------------------------------------------------------- command


def test_command_prints_the_exact_vllm_serve_line_the_modal_app_uses(capsys):
    assert cli.main(["vllm", "command"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith(f"vllm serve {DEFAULT_ENGINE_MODEL} ")
    assert "--host 0.0.0.0" in out and "--port 8000" in out and "--max-model-len" in out
    # SAND-077: the default serves online fp8, text-only (no vision memory reserve).
    assert "--quantization fp8" in out and """--limit-mm-per-prompt '{"image":0,"video":0,"audio":0}'""" in out


def test_command_for_the_frozen_qwen3_8b_row_keeps_bf16_and_no_mm_limits(capsys):
    assert cli.main(["vllm", "command", "--model", "Qwen/Qwen3-8B"]) == 0
    out = capsys.readouterr().out
    assert "--quantization" not in out and "--limit-mm-per-prompt" not in out


def test_command_follows_the_matrix_row_for_the_model(capsys):
    assert cli.main(["vllm", "command", "--model", "Qwen/Qwen3-8B-AWQ"]) == 0
    out = capsys.readouterr().out
    assert "vllm serve Qwen/Qwen3-8B-AWQ" in out and "--quantization awq" in out


def test_command_gpu_override_sets_tensor_parallel_size(capsys):
    assert cli.main(["vllm", "command", "--gpu", "A100-40GB:2"]) == 0
    assert "--tensor-parallel-size 2" in capsys.readouterr().out


def test_command_json_lists_the_argv(capsys):
    assert cli.main(["vllm", "command", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["argv"][:3] == ["vllm", "serve", DEFAULT_ENGINE_MODEL]
    assert payload["model"] == DEFAULT_ENGINE_MODEL


def test_command_unknown_model_is_a_clean_error(capsys):
    assert cli.main(["vllm", "command", "--model", "nope/none"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "nope/none" in err


def test_command_does_not_leak_matrix_env_into_the_process(monkeypatch):
    cli.main(["vllm", "command", "--model", "Qwen/Qwen3-8B-AWQ"])
    import os

    assert "MODAL_VLLM_MODEL" not in os.environ


# --------------------------------------------------------------------------- serve


def test_serve_without_vllm_points_at_compose_and_modal(fake_bin, capsys):
    assert cli.main(["vllm", "serve"]) == 1
    err = capsys.readouterr().err
    assert "`vllm` not found" in err and "--profile vllm" in err and "sandbox modal deploy" in err


def test_serve_dry_run_binds_loopback_not_all_interfaces(capsys):
    assert cli.main(["vllm", "serve", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "--host 127.0.0.1" in out and "0.0.0.0" not in out


def test_serve_runs_vllm_with_extra_arguments_appended(fake_bin):
    fake_bin.add("vllm")
    fake_bin.add("nvidia-smi")
    assert cli.main(["vllm", "serve", "--", "--max-num-seqs", "2"]) == 0
    argv = fake_bin.calls("vllm")[0]
    assert argv[:3] == ["serve", DEFAULT_ENGINE_MODEL, "--host"] and argv[3] == "127.0.0.1"
    assert argv[-2:] == ["--max-num-seqs", "2"]


def test_serve_exports_the_gateway_token_as_vllm_api_key(fake_bin, monkeypatch):
    monkeypatch.setenv("MODAL_VLLM_API_TOKEN", "tok")
    fake_bin.add("vllm")
    fake_bin.add("nvidia-smi")
    assert cli.main(["vllm", "serve"]) == 0
    assert fake_bin.envs("vllm")[0]["VLLM_API_KEY"] == "sha256:" + hashlib.sha256(b"tok").hexdigest()


def test_serve_warns_when_there_is_no_nvidia_gpu(fake_bin, capsys):
    fake_bin.add("vllm")
    assert cli.main(["vllm", "serve"]) == 0
    assert "nvidia-smi" in capsys.readouterr().err


def test_serve_failure_mirrors_into_one_error_line(fake_bin, capsys):
    fake_bin.add("vllm", rc=3)
    fake_bin.add("nvidia-smi")
    assert cli.main(["vllm", "serve"]) == 1
    assert "rc=3" in capsys.readouterr().err


# --------------------------------------------------------------------------- metrics


def test_metrics_scrapes_once_by_default_and_prints_the_summary(monkeypatch, capsys):
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    monkeypatch.setenv("VLLM_API_KEY", "tok")
    calls = []

    def scrape(base_url, api_key, *, attempts=12, expected=1):
        calls.append((base_url, api_key, attempts))
        return {"coverage": "replicas observed: 1 of 1", "replicas": {"1.0": {"requests": 3.0}}, "raw": {"1.0": "x"}, "errors": []}

    monkeypatch.setattr("mailroom_sandbox.job.vllm_metrics.scrape", scrape)
    assert cli.main(["vllm", "metrics"]) == 0
    assert calls == [(BASE, "tok", 1)]
    out = capsys.readouterr().out
    assert "replicas observed: 1 of 1" in out and "requests" in out


def test_metrics_attempts_and_json(monkeypatch, capsys):
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    seen = []
    monkeypatch.setattr(
        "mailroom_sandbox.job.vllm_metrics.scrape",
        lambda b, k, *, attempts=12, expected=1: seen.append(attempts) or {"coverage": "c", "replicas": {"1": {"requests": 1.0}}, "raw": {}, "errors": []},
    )
    assert cli.main(["vllm", "metrics", "--attempts", "3", "--json"]) == 0
    assert seen == [3]
    assert json.loads(capsys.readouterr().out)["coverage"] == "c"


def test_metrics_scrape_errors_fail_the_command(monkeypatch, capsys):
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    monkeypatch.setattr(
        "mailroom_sandbox.job.vllm_metrics.scrape",
        lambda b, k, **kw: {"coverage": "replicas observed: 0 of 1", "replicas": {}, "raw": {}, "errors": ["ConnectError: refused"]},
    )
    assert cli.main(["vllm", "metrics"]) == 1
    assert "ConnectError" in capsys.readouterr().err


def test_metrics_without_an_endpoint_is_the_deploy_hint(capsys):
    assert cli.main(["vllm", "metrics"]) == 1
    assert "VLLM_BASE_URL" in capsys.readouterr().err


def test_bare_vllm_group_prints_usage(capsys):
    assert cli.main(["vllm"]) == 0
    out = capsys.readouterr().out
    assert "probe" in out and "command" in out and "serve" in out and "metrics" in out


def test_metrics_with_no_replica_and_no_error_still_fails(monkeypatch, capsys):
    """A scrape that observed nothing must not read as success."""
    monkeypatch.setenv("VLLM_BASE_URL", BASE)
    monkeypatch.setattr(
        "mailroom_sandbox.job.vllm_metrics.scrape",
        lambda b, k, **kw: {"coverage": "replicas observed: 0 of 1", "replicas": {}, "raw": {}, "errors": []},
    )
    assert cli.main(["vllm", "metrics"]) == 1
    assert "no replica answered" in capsys.readouterr().err
