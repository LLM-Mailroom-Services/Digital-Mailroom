"""Railway deploy contract: IaC file, listen port, /health, deploy metadata.

Railway retired Config as Code (railway.json) — 2026-08-28 for new projects,
hard cutoff 2026-12-01. The repo ships Infrastructure as Code instead:
`.railway/railway.py` (railway_sdk, authoring-only) + the Dockerfile.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from server.main import _build_sha, _platform, create_app, listen_port
from tests.fake_langfuse import FakeClient, make_trace
from mailroom_ui.langfuse_source import LangfuseSource

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_listen_port_prefers_platform_port(monkeypatch):
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("MAILROOM_PORT", "7860")
    assert listen_port() == 8080


def test_listen_port_falls_back_to_mailroom_port(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("MAILROOM_PORT", "9001")
    assert listen_port() == 9001


def test_listen_port_default(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("MAILROOM_PORT", raising=False)
    assert listen_port(8001) == 8001


def test_health_root_is_platform_liveness_without_source():
    """Railway / Docker probes must not wait on Langfuse."""

    class HangingSrc:
        def health(self):
            raise AssertionError("platform /health must not call src.health()")

    with TestClient(create_app(HangingSrc())) as c:
        root = c.get("/health")
        assert root.status_code == 200
        body = root.json()
        assert body["ok"] is True
        assert body["status"] == "alive"
        assert "edition" in body
        assert "platform" in body
        assert "build_sha" in body


def test_api_health_still_reports_source():
    src = LangfuseSource(client=FakeClient([make_trace("t-health")]))
    with TestClient(create_app(src)) as c:
        api = c.get("/api/health")
        assert api.status_code == 200
        assert api.json()["ok"] is True
        assert "mailroom" in api.json()


def test_platform_detection(monkeypatch):
    for envs, expect in [
        ({"RAILWAY_SERVICE_NAME": "mailroom"}, "railway"),
        ({"RAILWAY_DEPLOY_ID": "d-1"}, "railway"),
        ({"RENDER_INSTANCE_ID": "srv-1"}, "render"),
        ({"FLY_APP_NAME": "mailroom"}, "fly"),
        ({"HF_SPACE_ID": "user/mailroom"}, "huggingface"),
        ({}, ""),
    ]:
        for k in ("RAILWAY_SERVICE_NAME", "RAILWAY_DEPLOY_ID", "RENDER_INSTANCE_ID", "FLY_APP_NAME", "HF_SPACE_ID"):
            monkeypatch.delenv(k, raising=False)
        for k, v in envs.items():
            monkeypatch.setenv(k, v)
        assert _platform() == expect


def test_build_sha_reads_baked_env(monkeypatch):
    monkeypatch.setenv("MAILROOM_BUILD_SHA", "abc123")
    assert _build_sha() == "abc123"
    monkeypatch.setenv("MAILROOM_BUILD_SHA", "unknown")
    assert _build_sha() == ""
    monkeypatch.delenv("MAILROOM_BUILD_SHA", raising=False)
    assert _build_sha() == ""


def test_health_and_meta_surface_platform_and_sha(monkeypatch):
    monkeypatch.setenv("RAILWAY_SERVICE_NAME", "mailroom")
    monkeypatch.setenv("MAILROOM_BUILD_SHA", "abc123")
    src = LangfuseSource(client=FakeClient([make_trace("t-meta")]))
    with TestClient(create_app(src)) as c:
        root = c.get("/health").json()
        assert root["platform"] == "railway"
        assert root["build_sha"] == "abc123"
        meta = c.get("/api/meta").json()
        assert meta["platform"] == "railway"
        assert meta["build_sha"] == "abc123"


def test_railway_iac_replaces_deprecated_railway_json():
    """railway.json (Config as Code) is gone — IaC owns the service now."""
    assert not (REPO_ROOT / "railway.json").exists()
    text = (REPO_ROOT / ".railway" / "railway.py").read_text(encoding="utf-8")
    assert "service(" in text
    assert 'start="python -m server.hosted"' in text
    assert 'healthcheck="/health"' in text
    assert "MAILROOM_EDITION" in text
    assert "MAILROOM_HOST" in text
    assert "preserve()" in text
    assert "RAILWAY_GIT_COMMIT_SHA" not in text


def test_dockerfile_healthcheck_prefers_platform_port():
    text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "HEALTHCHECK" in text
    assert "os.environ.get('PORT')" in text
    assert "/health" in text
    assert "server.hosted" in text
    assert "ARG RAILWAY_GIT_COMMIT_SHA" in text
    assert "MAILROOM_BUILD_SHA" in text


def test_nixpacks_fallback_binds_hosted():
    text = (REPO_ROOT / "nixpacks.toml").read_text(encoding="utf-8")
    assert "MAILROOM_HOST=0.0.0.0" in text
    assert "python -m server.hosted" in text