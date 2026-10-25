"""OTEL sink resolution tests (DMR-027) — network-free."""

from __future__ import annotations

import base64

from mailroom_sandbox.job import otel


def test_langfuse_sink_endpoint_and_auth(monkeypatch):
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    cfg = otel.resolve_sink(sink="langfuse", otlp=True, environment="pilot", run_id="r1", tags=["sandbox", "job"])
    assert cfg.endpoint == "https://us.cloud.langfuse.com/api/public/otel"
    assert cfg.headers["x-langfuse-ingestion-version"] == "4"
    expect = base64.b64encode(b"pk-test:sk-test").decode()
    assert cfg.headers["Authorization"] == f"Basic {expect}"
    assert cfg.resource["langfuse.trace.tags"] == "sandbox,job"
    assert cfg.resource["sandbox.run_id"] == "r1"


def test_langfuse_local_default():
    cfg = otel.resolve_sink(sink="langfuse", otlp=True)
    assert cfg.endpoint.endswith("/api/public/otel")


def test_none_inactive():
    cfg = otel.resolve_sink(sink="none", otlp=True)
    assert not cfg.active


def test_phoenix_default_endpoint():
    cfg = otel.resolve_sink(sink="phoenix", otlp=True)
    assert "6006" in cfg.endpoint


def test_otlp_generic_env(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://collector:4318")
    cfg = otel.resolve_sink(sink="otlp", otlp=True)
    assert cfg.endpoint == "https://collector:4318"


def test_otlp_disabled_no_exporter():
    cfg = otel.resolve_sink(sink="langfuse", otlp=False)
    assert not cfg.active


def test_configure_tracing_none_is_noop():
    assert otel.configure_tracing(otel.resolve_sink(sink="none")) is None