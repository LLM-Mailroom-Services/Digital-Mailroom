"""OpenRouter health: the key is validated (``/key``), never echoed, and a bad key spends nothing.

OpenRouter's ``/models`` is public, so a models probe alone reports a revoked key as healthy.
"""

from __future__ import annotations

import json

import httpx
import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.health import health_check, probe_chat, probe_openrouter_key

OPENROUTER_DEFAULT = "qwen/qwen3.5-9b"  # SAND-077: the openrouter profile default

KEY = "sk-or-test-not-a-real-key"


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    for name in ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "VLLM_MODEL", "MODAL_VLLM_MODEL", "LANGFUSE_HOST", "PHOENIX_ENDPOINT"):
        monkeypatch.delenv(name, raising=False)


def _server(monkeypatch, *, key_status=200, models=(OPENROUTER_DEFAULT,), chat_status=200, limit=None, remaining=None):
    calls = []

    def get(url, headers=None, **kw):
        calls.append(("GET", url, (headers or {}).get("Authorization")))
        if url.endswith("/key"):
            if key_status != 200:
                return httpx.Response(key_status, json={"error": {"message": "No auth credentials found"}})
            return httpx.Response(200, json={"data": {"label": "sk-or-v1-abc...xyz", "usage": 17.4678, "limit": limit, "limit_remaining": remaining, "limit_reset": "weekly", "is_free_tier": False}})
        if url.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": m} for m in models]})
        return httpx.Response(200, text="ok")

    def post(url, headers=None, json=None, **kw):
        calls.append(("POST", url, json["model"]))
        return httpx.Response(chat_status, json={"choices": [{"message": {"content": '{"ok": true}'}}]})

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", get)
    monkeypatch.setattr("mailroom_sandbox.health.httpx.post", post)
    return calls


def test_key_probe_reports_label_usage_and_limit_without_the_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    calls = _server(monkeypatch)
    result = probe_openrouter_key()
    assert result.ok and result.url == "https://openrouter.ai/api/v1/key"
    assert "sk-or-v1-abc...xyz" in result.detail and "lifetime usage $17.4678" in result.detail and "no credit limit" in result.detail
    assert KEY not in json.dumps(result.as_dict())
    assert calls == [("GET", "https://openrouter.ai/api/v1/key", f"Bearer {KEY}")]


def test_weekly_limit_reports_remaining_not_lifetime_usage(monkeypatch):
    """Lifetime usage above a weekly limit is normal; only the remaining budget gates."""
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    _server(monkeypatch, limit=8, remaining=8)
    result = probe_openrouter_key()
    assert result.ok and "$8.00 of $8.00 weekly limit left" in result.detail


@pytest.mark.parametrize("body", [{"data": [1, 2]}, {"data": "ok"}, {"data": {}}, {"data": None}, {}])
def test_a_key_response_without_a_key_record_fails(monkeypatch, body):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", lambda url, headers=None, **kw: httpx.Response(200, json=body))
    result = probe_openrouter_key()
    assert not result.ok and "no key record" in result.detail


@pytest.mark.parametrize("remaining", [0, -0.5])
def test_exhausted_limit_fails_before_a_billed_chat(monkeypatch, remaining):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    calls = _server(monkeypatch, limit=8, remaining=remaining)
    report = health_check("openrouter")
    assert not report["ok"] and "credit limit exhausted" in report["key"]["detail"]
    assert "POST" not in [m for m, *_ in calls]


@pytest.mark.parametrize("status", [401, 403])
def test_rejected_key_is_a_failure_with_the_env_name(monkeypatch, status):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    _server(monkeypatch, key_status=status)
    result = probe_openrouter_key()
    assert not result.ok and "OPENROUTER_API_KEY was rejected" in result.detail


@pytest.mark.parametrize("value", [None, "", "  ", "mock-key"])
def test_missing_or_mock_key_fails_without_a_request(monkeypatch, value):
    if value is not None:
        monkeypatch.setenv("OPENROUTER_API_KEY", value)
    calls = _server(monkeypatch)
    result = probe_openrouter_key()
    assert not result.ok and "OPENROUTER_API_KEY is not set" in result.detail and calls == []


def test_base_url_override_moves_every_probe(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://proxy.example/api/v1")
    calls = _server(monkeypatch)
    report = health_check("openrouter")
    assert report["ok"]
    assert {url for _m, url, _a in calls} == {
        "https://proxy.example/api/v1/key", "https://proxy.example/api/v1/models", "https://proxy.example/api/v1/chat/completions"}


def test_bad_key_skips_models_and_chat(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    calls = _server(monkeypatch, key_status=401)
    report = health_check("openrouter")
    assert not report["ok"] and "skipped" in report["models"]["detail"] and "skipped" in report["chat"]["detail"]
    assert [m for m, *_ in calls] == ["GET"]  # no chat request is ever billed


def test_unknown_default_model_fails_before_chat(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    calls = _server(monkeypatch, models=("some/other-model",))
    report = health_check("openrouter")
    assert not report["ok"] and "not in the OpenRouter catalog" in report["models"]["detail"]
    assert "POST" not in [m for m, *_ in calls]


def test_api_chat_probe_ignores_the_hybrid_vllm_pin(monkeypatch):
    """VLLM_MODEL pins the GPU half of a hybrid run; posting it to OpenRouter would 400."""
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen3-8B-AWQ")
    calls = _server(monkeypatch)
    from mailroom_sandbox.overlay import load_profile

    assert probe_chat(load_profile("openrouter")).ok
    assert calls[-1] == ("POST", "https://openrouter.ai/api/v1/chat/completions", OPENROUTER_DEFAULT)


def test_health_cli_output_never_contains_the_key(monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    _server(monkeypatch)
    rc = cli.main(["--profile", "openrouter", "health"])
    out = capsys.readouterr().out
    assert rc == 0 and KEY not in out and json.loads(out)["key"]["ok"]


def _doctor(capsys, *args):
    rc = cli.main(["doctor", "--json", "--service", "openrouter", *args])
    return rc, json.loads(capsys.readouterr().out)["services"][0]


def test_doctor_openrouter_row_offline(monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("offline doctor must not touch the network")

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", boom)
    rc, row = _doctor(capsys, "--profile", "modal-vllm")
    assert rc == 0 and row["state"] == "skipped"
    rc, row = _doctor(capsys, "--profile", "openrouter")
    assert rc == 1 and row["state"] == "fail" and "OPENROUTER_API_KEY" in row["detail"]
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    rc, row = _doctor(capsys, "--profile", "openrouter")
    assert rc == 0 and row["state"] == "ok" and "value hidden" in row["detail"] and KEY not in json.dumps(row)


def test_doctor_openrouter_row_live(monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    _server(monkeypatch)
    rc, row = _doctor(capsys, "--profile", "openrouter", "--live")
    assert rc == 0 and row["state"] == "ok" and "key accepted" in row["detail"]
    _server(monkeypatch, key_status=401)
    rc, row = _doctor(capsys, "--profile", "modal-vllm", "--live")  # hybrid: a bad route key warns
    assert row["state"] == "warn" and "rejected" in row["detail"]


@pytest.mark.parametrize(
    ("config", "api_agents"),
    [("pipeline-openrouter", "all"), ("pipeline-modal", set()), ("pipeline-hybrid", {"judge", "boss"})],
)
def test_pipeline_examples_resolve_api_gpu_and_hybrid_transports(monkeypatch, config, api_agents):
    from mailroom_sandbox.agent_routes import describe
    from mailroom_sandbox.job.spec import load_run_spec

    monkeypatch.setenv("MODAL_WORKSPACE", "demo-ws")
    spec = load_run_spec(f"config/runs/examples/{config}.yaml")
    assert spec.task == "pipeline"
    table = describe(spec)
    on_api = {name for name, row in table.items() if row["provider"] == "openrouter"}
    assert on_api == (set(table) if api_agents == "all" else api_agents)
    assert all(row["provider"] == "vllm" for name, row in table.items() if name not in on_api)


def test_hybrid_route_without_a_key_fails_preflight(monkeypatch):
    from mailroom_sandbox.job.preflight import _engine_errors
    from mailroom_sandbox.job.spec import load_run_spec

    monkeypatch.setenv("MODAL_WORKSPACE", "demo-ws")
    errors = _engine_errors(load_run_spec("config/runs/examples/pipeline-hybrid.yaml"))
    assert any("OPENROUTER_API_KEY" in e for e in errors)
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert not any("OPENROUTER_API_KEY" in e for e in _engine_errors(load_run_spec("config/runs/examples/pipeline-hybrid.yaml")))
