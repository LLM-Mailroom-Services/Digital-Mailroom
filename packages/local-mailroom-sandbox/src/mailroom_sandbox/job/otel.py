"""OTLP trace-sink contract for sandbox jobs (DMR-027).

Langfuse OTLP verified 2026-09-09: ``{BASE}/api/public/otel``,
``Authorization: Basic base64(pk:sk)`` + ``x-langfuse-ingestion-version: 4``,
HTTP/JSON or HTTP/protobuf (gRPC not supported). Phoenix: ``/v1/traces``.
Generic: ``OTEL_EXPORTER_OTLP_ENDPOINT``.

``resolve_sink`` is pure (no otel import). ``configure_tracing``/``flush``
import otel lazily so the runtime venv stays lean unless the feature is used.
"""

from __future__ import annotations

import base64
import os
from contextlib import contextmanager
from typing import Any, Iterator

from pydantic import BaseModel


class SinkConfig(BaseModel):
    kind: str  # langfuse | phoenix | otlp | none
    endpoint: str | None = None
    headers: dict[str, str] = {}
    resource: dict[str, str] = {}
    active: bool = True


def _langfuse_endpoint() -> str:
    host = (
        os.environ.get("LANGFUSE_BASE_URL")
        or os.environ.get("LANGFUSE_HOST")
        or "http://localhost:3000"
    ).rstrip("/")
    return f"{host}/api/public/otel"


def _langfuse_headers() -> dict[str, str]:
    public = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    headers = {"x-langfuse-ingestion-version": "4"}
    if public and secret:
        token = base64.b64encode(f"{public}:{secret}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    return headers


def resolve_sink(
    *,
    sink: str = "langfuse",
    otlp: bool = True,
    endpoint: str | None = None,
    environment: str = "pilot",
    service_name: str = "sandbox-job",
    run_id: str | None = None,
    tags: list[str] | None = None,
    extra_resource: dict[str, str] | None = None,
) -> SinkConfig:
    """Resolve the trace sink and its OTLP export contract (pure)."""
    resource = {
        "service.name": service_name,
        "deployment.environment": environment,
    }
    if run_id:
        resource["sandbox.run_id"] = run_id
    if tags:
        resource["langfuse.trace.tags"] = ",".join(tags)
    resource.update(extra_resource or {})

    if sink == "none":
        return SinkConfig(kind="none", active=False, resource=resource)

    if not otlp:
        # Sink selected but OTLP export disabled: leave the sink for the
        # Langfuse SDK path only; no exporter is configured here.
        return SinkConfig(kind=sink, active=False, resource=resource)

    if sink == "langfuse":
        ep = endpoint or _langfuse_endpoint()
        headers = _langfuse_headers()
        if not headers.get("Authorization"):
            headers["Authorization"] = ""
        return SinkConfig(kind="langfuse", endpoint=ep, headers=headers, resource=resource)

    if sink == "phoenix":
        ep = endpoint or os.environ.get("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces").rstrip("/")
        return SinkConfig(kind="phoenix", endpoint=ep, headers={}, resource=resource)

    if sink == "otlp":
        ep = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
        return SinkConfig(kind="otlp", endpoint=ep or None, resource=resource)

    raise ValueError(f"unknown sink {sink!r}")


def configure_tracing(sink_cfg: SinkConfig) -> Any:
    """Build + activate a TracerProvider exporting to the sink (lazy imports).

    Returns a tracer, or ``None`` when the sink is inactive or otel deps are
    missing. Also returns a provider handle via ``tracer.sandbox_provider``.
    """
    if not sink_cfg.active or not sink_cfg.endpoint:
        return None
    try:
        from opentelemetry import trace as oteltrace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception:
        return None

    headers = {k: v for k, v in sink_cfg.headers.items() if v != ""}
    exporter = OTLPSpanExporter(endpoint=sink_cfg.endpoint, headers=headers)
    provider = TracerProvider(resource=Resource.create(sink_cfg.resource))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    oteltrace.set_tracer_provider(provider)
    tracer = oteltrace.get_tracer(sink_cfg.kind, "0.1.0")
    tracer.sandbox_provider = provider  # type: ignore[attr-defined]
    return tracer


def flush_tracer(tracer: Any) -> None:
    if tracer is None:
        return
    provider = getattr(tracer, "sandbox_provider", None)
    if provider is not None:
        try:
            provider.force_flush()
            provider.shutdown()
        except Exception:
            pass


@contextmanager
def job_span(tracer: Any, name: str, **attrs: str) -> Iterator[Any]:
    """A span named verb-first with string attributes (network-free no-op)."""
    if tracer is None:
        class _Noop:
            def set_attribute(self, *a, **k):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return None

        yield _Noop()
        return
    with tracer.start_as_current_span(name) as span:
        for key, value in attrs.items():
            if value is not None:
                try:
                    span.set_attribute(key, str(value))
                except Exception:
                    pass
        yield span
