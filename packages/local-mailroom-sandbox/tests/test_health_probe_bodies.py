"""Health probes must survive any 2xx body, not only JSON.

`probe_models` used to call `resp.json()` inside a handler that only caught
`httpx.HTTPError`, so a plain-text 200 (a health endpoint that answers "OK", or a
booting gateway answering an empty body) escaped as `JSONDecodeError` and crashed
`sandbox health` with a traceback instead of a report.
"""

from __future__ import annotations

import json

import httpx
import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.health import probe_models

PROFILE = {"name": "probe", "base_url": "http://probe.invalid/v1", "health": {"models_url": "http://probe.invalid/v1/models"}}


def _reply(monkeypatch, response: httpx.Response) -> None:
    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", lambda url, **kw: response)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="OK"),
        httpx.Response(200, content=b""),
        httpx.Response(200, text="<html>gateway warming up</html>"),
        httpx.Response(200, text="{not json"),
    ],
    ids=["plain-text", "empty", "html", "truncated-json"],
)
def test_model_probe_reports_a_non_json_body_instead_of_crashing(monkeypatch, response):
    _reply(monkeypatch, response)
    result = probe_models(PROFILE)
    assert result.ok is False
    assert "non-JSON" in result.detail


def test_model_probe_still_parses_a_json_model_list(monkeypatch):
    _reply(monkeypatch, httpx.Response(200, json={"data": [{"id": "Qwen/Qwen3-8B"}, {"id": "other"}]}))
    result = probe_models(PROFILE)
    assert result.ok is True and result.models == ["Qwen/Qwen3-8B", "other"]


def test_sink_probe_treats_any_2xx_as_healthy(monkeypatch):
    """Langfuse/Phoenix health endpoints are liveness checks: the body does not matter."""
    _reply(monkeypatch, httpx.Response(200, text="OK"))
    result = probe_models(PROFILE, expect_json=False)
    assert result.ok is True and result.detail == "ok"


def test_sink_probe_still_fails_on_http_errors(monkeypatch):
    _reply(monkeypatch, httpx.Response(503, text="down"))
    assert probe_models(PROFILE, expect_json=False).ok is False


def test_health_command_survives_plain_text_sink_endpoints(monkeypatch, capsys):
    """`sandbox health` must print its report when Phoenix answers plain text."""
    monkeypatch.setattr("mailroom_sandbox.runtime.load_env_file", lambda: None)
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    for name in ("LANGFUSE_HOST", "LANGFUSE_BASE_URL", "PHOENIX_ENDPOINT", "OLLAMA_BASE_URL"):
        monkeypatch.delenv(name, raising=False)

    def fake_get(url, **kw):
        if url.endswith("/models") or url.endswith("/api/tags"):
            return httpx.Response(200, json={"data": [{"id": "m"}]})
        if url.endswith("/api/public/health"):
            return httpx.Response(200, json={"status": "OK"})
        return httpx.Response(200, text="OK")  # Phoenix /healthz

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", fake_get)
    monkeypatch.setattr(
        "mailroom_sandbox.health.httpx.post",
        lambda url, **kw: httpx.Response(200, json={"choices": []}),
    )

    assert cli.main(["health", "--profile", "ollama"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["phoenix"]["ok"] is True
    assert report["langfuse"]["ok"] is True


@pytest.mark.parametrize("status", [301, 302, 303, 307])
def test_sink_probe_does_not_call_a_redirect_healthy(monkeypatch, status):
    """httpx does not follow redirects here, so a 3xx is not a 2xx liveness answer."""
    _reply(monkeypatch, httpx.Response(status, headers={"location": "http://elsewhere.invalid/"}))
    result = probe_models(PROFILE, expect_json=False)
    assert result.ok is False and result.detail == f"HTTP {status}"


def test_model_probe_redirect_is_an_http_status_not_a_non_json_200(monkeypatch):
    """A 303 on the models URL must report its real status, not 'HTTP 200 but non-JSON'."""
    _reply(monkeypatch, httpx.Response(303, headers={"location": "http://elsewhere.invalid/"}))
    result = probe_models(PROFILE)
    assert result.ok is False and result.detail == "HTTP 303"


def test_non_json_detail_names_the_real_status(monkeypatch):
    """A 204 with no JSON must not be described as 'HTTP 200'."""
    _reply(monkeypatch, httpx.Response(204))
    result = probe_models(PROFILE)
    assert result.ok is False and result.detail == "HTTP 204 but non-JSON body"
