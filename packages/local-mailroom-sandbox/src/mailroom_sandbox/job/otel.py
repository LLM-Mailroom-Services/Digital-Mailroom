"""OTLP trace-sink contract for sandbox jobs (DMR-027).

Langfuse OTLP verified 2026-09-09: ``{BASE}/api/public/otel``,
``Authorization: Basic base64(pk:sk)`` + ``x-langfuse-ingestion-version: 4``,
HTTP/JSON or HTTP/protobuf (gRPC not supported). Phoenix: ``/v1/traces``.
Generic: ``OTEL_EXPORTER_OTLP_ENDPOINT``.

``resolve_sink`` is pure (no otel import). ``configure_tracing``/``flush``
import otel lazily so the runtime venv stays lean unless the feature is used.

Local-first capture: every traced job also mirrors its spans to
``data/traces/<run_id>.spans.jsonl.gz`` (gitignored), whatever the sink, so a
run is never left without traces when Phoenix/Langfuse is down or the sink is
``none``. ``SANDBOX_TRACE_LOCAL=0`` turns the mirror off. ``trace_pack`` turns
the mirror into a Parquet zip for upload and prunes it once the copy verifies.
"""

from __future__ import annotations

import base64
import gzip
import json
import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel

_log = logging.getLogger("mailroom_sandbox.job.otel")

_OTEL_WARNED = False

LOCAL_TRACE_ENV = "SANDBOX_TRACE_LOCAL"


def local_trace_path(run_id: str) -> Path | None:
    """Where a run's local span mirror lives, or ``None`` when disabled."""
    if os.environ.get(LOCAL_TRACE_ENV, "1").strip().lower() in ("0", "false", "no", "off"):
        return None
    from mailroom_sandbox.paths import data_dir

    return data_dir() / "traces" / f"{run_id}.spans.jsonl.gz"


def span_record(span: Any) -> dict[str, Any]:
    """One finished SDK span as a flat, JSON-safe OTLP-shaped dict."""
    ctx = span.get_span_context()
    parent = span.parent
    status = span.status
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
        "parent_span_id": format(parent.span_id, "016x") if parent is not None else None,
        "name": span.name,
        "kind": getattr(span.kind, "name", str(span.kind)),
        "start_time_unix_nano": span.start_time,
        "end_time_unix_nano": span.end_time,
        "status_code": getattr(status.status_code, "name", str(status.status_code)),
        "status_description": status.description,
        "attributes": dict(span.attributes or {}),
        "events": [
            {"name": e.name, "time_unix_nano": e.timestamp, "attributes": dict(e.attributes or {})}
            for e in (span.events or ())
        ],
        "resource": dict(span.resource.attributes or {}) if span.resource is not None else {},
    }


def _jsonl_exporter(path: Path) -> Any:
    """A SpanExporter appending gzip JSONL (one span per line) to ``path``."""
    from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

    class JsonlGzSpanExporter(SpanExporter):
        def __init__(self, target: Path) -> None:
            self.path = target
            self._lock = threading.Lock()
            target.parent.mkdir(parents=True, exist_ok=True)

        def export(self, spans):  # type: ignore[override]
            lines = [json.dumps(span_record(s), separators=(",", ":"), default=str) for s in spans]
            if not lines:
                return SpanExportResult.SUCCESS
            try:
                # Each batch is its own gzip member; gzip.open reads them back as one stream.
                with self._lock, gzip.open(self.path, "at", encoding="utf-8") as fh:
                    fh.write("\n".join(lines) + "\n")
            except OSError as exc:
                _log.error("local span mirror write FAILED (%s)", self.path, exc_info=exc)
                return SpanExportResult.FAILURE
            return SpanExportResult.SUCCESS

        def shutdown(self) -> None:
            return None

    return JsonlGzSpanExporter(path)


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


def configure_tracing(sink_cfg: SinkConfig, *, local_path: Path | None = None) -> Any:
    """Build a TracerProvider exporting to the sink and/or a local mirror (lazy imports).

    Returns a tracer, or ``None`` when there is nowhere to export (inactive sink
    and no ``local_path``) or otel deps are missing. The provider handle rides
    on ``tracer.sandbox_provider``; ``tracer.sandbox_local_path`` names the mirror.
    """
    remote = bool(sink_cfg.active and sink_cfg.endpoint)
    if not remote and local_path is None:
        return None
    try:
        from opentelemetry import trace as oteltrace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception as exc:
        global _OTEL_WARNED
        if not _OTEL_WARNED:
            _OTEL_WARNED = True
            _log.warning(
                "opentelemetry deps are NOT installed — the configured %r OTLP "
                "sink (%s) and the local mirror receive NO traces; install the "
                "[observability] extra",
                sink_cfg.kind,
                sink_cfg.endpoint,
                exc_info=exc,
            )
        return None

    provider = TracerProvider(resource=Resource.create(sink_cfg.resource))
    if remote:
        headers = {k: v for k, v in sink_cfg.headers.items() if v != ""}
        exporter = OTLPSpanExporter(endpoint=sink_cfg.endpoint, headers=headers)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    if local_path is not None:
        provider.add_span_processor(BatchSpanProcessor(_jsonl_exporter(local_path)))
    if remote:
        # Keep the historical global registration for the remote-sink path;
        # the tracer itself comes from this provider so a second job in the
        # same process never silently writes to the first job's exporters.
        oteltrace.set_tracer_provider(provider)
    tracer = provider.get_tracer(sink_cfg.kind, "0.1.0")
    tracer.sandbox_provider = provider  # type: ignore[attr-defined]
    tracer.sandbox_local_path = local_path  # type: ignore[attr-defined]
    return tracer


def flush_tracer(tracer: Any) -> None:
    if tracer is None:
        return
    provider = getattr(tracer, "sandbox_provider", None)
    if provider is not None:
        try:
            provider.force_flush()
            provider.shutdown()
        except Exception as exc:
            _log.error(
                "OTLP provider force_flush/shutdown FAILED — buffered spans may "
                "be lost at the %r sink",
                getattr(tracer, "sandbox_provider", None),
                exc_info=exc,
            )


def current_context(tracer: Any) -> Any:
    """The active otel Context to hand to worker threads (``None`` without a tracer)."""
    if tracer is None:
        return None
    try:
        from opentelemetry import context as otelcontext

        return otelcontext.get_current()
    except Exception:
        return None


@contextmanager
def job_span(tracer: Any, name: str, *, parent: Any = None, **attrs: str) -> Iterator[Any]:
    """A span named verb-first with string attributes (network-free no-op).

    ``parent`` is an otel Context (see ``current_context``) for spans opened
    on worker threads, where the caller's context does not propagate.
    """
    if tracer is None:
        class _Noop:
            def set_attribute(self, *a, **k):
                return None

            def set_status(self, *a, **k):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return None

        yield _Noop()
        return
    with tracer.start_as_current_span(name, context=parent) as span:
        for key, value in attrs.items():
            if value is not None:
                try:
                    span.set_attribute(key, str(value))
                except Exception:
                    pass
        yield span
