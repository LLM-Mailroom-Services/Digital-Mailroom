"""Langfuse v4 data-model tracing for sandbox evals (family contract).

Uses mailroom ``observability.langfuse_setup`` when the vendor tree is on
``sys.path``. Falls back to the Langfuse Python v4 SDK, then a no-op.

The-Mailroom filters ``MAILROOM_TRACE_NAMES=document-pipeline`` and
``MAILROOM_TRACE_TAGS=mailroom``. Isolated evals still open a root chain
and nest the one relevant observation so a partial conveyor is plottable.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from mailroom_sandbox.paths import data_dir

_log = logging.getLogger("mailroom_sandbox.tracing")

_TRACING_WARNED: set[str] = set()
_SCORE_EMIT_FAILURES = 0
_FLUSH_FAILURES = 0
_VENDOR_DEGRADED = False


def _warn_once(key: str, message: str, exc: BaseException | None = None) -> None:
    if key not in _TRACING_WARNED:
        _TRACING_WARNED.add(key)
        _log.warning("%s", message, exc_info=exc)


def tracing_failure_counts() -> dict[str, int]:
    """Live-or-loud seam: tests assert no tracing degradation went silent."""
    return {
        "score_emit_failures": _SCORE_EMIT_FAILURES,
        "flush_failures": _FLUSH_FAILURES,
        "vendor_degraded": 1 if _VENDOR_DEGRADED else 0,
    }

try:
    from llm_dojo_scoring.mailroom import (
        GROUND_TRUTH_KEYS,
        LANGFUSE_SCORE_NAME_ALIASES,
        NODE_OBSERVATION_TYPES,
        PIPELINE_TRACE,
        langfuse_score_name,
        observation_type_for,
    )
except Exception as exc:  # pragma: no cover — dojo pin always ships this module
    _VENDOR_DEGRADED = True
    _warn_once(
        "dojo-constants-fallback",
        "llm-dojo-scoring tracing constants unavailable — using local constants; "
        "scores may be aliased differently than the pinned v0.15.0 surface",
        exc,
    )
    PIPELINE_TRACE = "document-pipeline"
    GROUND_TRUTH_KEYS = (
        "expected_hf_class",
        "expected_doc_class",
        "expected_subclass",
        "expected",
    )
    LANGFUSE_SCORE_NAME_ALIASES = {
        "extraction_overall_verified_precision": "extraction_verified_precision",
    }
    NODE_OBSERVATION_TYPES = {
        "document-pipeline": "chain",
        "intake-document": "span",
        "normalize-intake": "span",
        "extract-image-text": "retriever",
        "transcribe-pdf": "retriever",
        "classify-document": "agent",
        "extract-fields": "agent",
        "judge-verify": "evaluator",
        "arbitrate-verdict": "agent",
        "route-for-review": "span",
        "adjudicate-conflict": "agent",
        "compile-report": "agent",
        "write-catalog": "span",
        "archive-document": "span",
        "pipeline-result": "generation",
        "answer-question": "generation",
    }

    def observation_type_for(name: str, default: str = "span") -> str:
        return NODE_OBSERVATION_TYPES.get(name, default)

    def langfuse_score_name(name: str) -> str:
        return LANGFUSE_SCORE_NAME_ALIASES.get(name, name)


_LAST_TRACE_IDS: list[str] = []
_LAST_SESSION_ID: str | None = None


class _NoopSpan:
    def update(self, *args: Any, **kwargs: Any) -> None:
        return None

    def score(self, *args: Any, **kwargs: Any) -> None:
        return None


def observability_environment() -> str:
    mode = (os.environ.get("SANDBOX_RUN_MODE") or "").lower()
    if mode == "mock":
        return "mock"
    env = os.environ.get("OBSERVABILITY_ENVIRONMENT")
    if env and env not in {"sandbox"}:
        return env
    if mode == "local":
        return "pilot"
    return os.environ.get("OBSERVABILITY_ENVIRONMENT") or "pilot"


def default_tags(*extra: str) -> list[str]:
    env = observability_environment()
    tags = [
        "mailroom",
        env,
        "sandbox",
        os.environ.get("SANDBOX_PROFILE") or "ollama",
    ]
    mode = os.environ.get("SANDBOX_RUN_MODE") or "local"
    if mode not in tags:
        tags.append(mode)
    tags.extend(t for t in extra if t and t not in tags)
    return tags


def tracing_backend() -> str:
    provider = (os.environ.get("OBSERVABILITY_PROVIDER") or "phoenix").lower()
    if provider == "auto":
        if os.environ.get("LANGFUSE_SECRET_KEY"):
            return "langfuse"
        if os.environ.get("BRAINTRUST_API_KEY"):
            return "braintrust"
        if os.environ.get("PHOENIX_TRACING", "enabled").lower() != "disabled":
            return "phoenix"
        return "none"
    return provider


def public_ground_truth(row: dict[str, Any] | None) -> dict[str, Any]:
    """Trace-safe GT — never include ``expected_fields`` or document text."""
    if not row:
        return {}
    skip = {"expected_fields"}
    out = {}
    for key in GROUND_TRUTH_KEYS:
        value = row.get(key)
        if key in skip or value in (None, ""):
            continue
        out[key] = value
    return out


def session_id_for(task: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"sandbox-{task}-{stamp}"


def record_trace_id(trace_id: str | None, *, session_id: str | None = None) -> None:
    global _LAST_SESSION_ID
    if session_id:
        _LAST_SESSION_ID = session_id
    if trace_id and trace_id not in _LAST_TRACE_IDS:
        _LAST_TRACE_IDS.append(str(trace_id))


def last_trace_ids() -> list[str]:
    return list(_LAST_TRACE_IDS)


def _mailroom_setup():
    try:
        from observability import langfuse_setup  # type: ignore

        return langfuse_setup
    except Exception as exc:
        _warn_once(
            "mailroom-setup-unavailable",
            "mailroom observability.langfuse_setup unavailable — tracing degrades "
            "to the SDK/no-op path",
            exc,
        )
        return None


def _sdk_client():
    if tracing_backend() in {"none", "phoenix", "braintrust"}:
        return None
    if not os.environ.get("LANGFUSE_SECRET_KEY"):
        return None
    try:
        from langfuse import Langfuse

        return Langfuse()
    except Exception as exc:
        _warn_once(
            "langfuse-sdk-unavailable",
            "Langfuse SDK unavailable — tracing is a silent no-op for this run "
            "(OBSERVABILITY_PROVIDER is not none, so a sink was expected)",
            exc,
        )
        return None


@contextmanager
def document_pipeline_trace(
    *,
    seed: str | None = None,
    session_id: str | None = None,
    name: str = PIPELINE_TRACE,
    input: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    environment: str | None = None,
    user_id: str | None = None,
) -> Iterator[Any]:
    """Open the root ``document-pipeline`` chain (family contract)."""
    env = environment or observability_environment()
    tag_list = tags or default_tags()
    meta = {"pipeline": "mailroom", **(metadata or {})}
    uid = user_id or os.environ.get("MAILROOM_TRACE_USER_ID") or None
    setup = _mailroom_setup()
    if setup is not None:
        with setup.pipeline_trace(
            seed=seed,
            session_id=session_id,
            name=name,
            input=input,
            metadata=meta,
            tags=tag_list,
            environment=env,
            user_id=uid,
            as_type="chain",
        ) as root:
            try:
                tid = setup.get_trace_id() if hasattr(setup, "get_trace_id") else None
            except Exception:
                tid = None
            record_trace_id(tid, session_id=session_id)
            yield root
        return

    client = _sdk_client()
    if client is None:
        yield _NoopSpan()
        return
    try:
        from langfuse import propagate_attributes
    except Exception as exc:
        _warn_once(
            "propagate-attributes-unavailable",
            "langfuse.propagate_attributes unavailable — trace attributes "
            "(session/tags/env) will NOT propagate; run traces without them",
            exc,
        )
        yield _NoopSpan()
        return
    trace_context = None
    if seed:
        try:
            trace_context = {"trace_id": client.create_trace_id(seed=str(seed))}
        except Exception as exc:
            _warn_once(
                "seed-trace-context-failed",
                "seed trace_context could not be created — trace_id seeding skipped",
                exc,
            )
    attrs = {
        "session_id": session_id,
        "trace_name": name,
        "metadata": meta,
        "tags": tag_list,
        "environment": env,
    }
    if uid:
        attrs["user_id"] = uid
    with propagate_attributes(**{k: v for k, v in attrs.items() if v is not None}):
        kwargs: dict[str, Any] = {"as_type": "chain", "name": name, "input": input}
        if trace_context:
            kwargs["trace_context"] = trace_context
        with client.start_as_current_observation(**kwargs) as root:
            try:
                record_trace_id(client.get_current_trace_id(), session_id=session_id)
            except Exception:
                pass
            yield root


@contextmanager
def child_observation(
    name: str,
    *,
    as_type: str | None = None,
    input: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    model: str | None = None,
) -> Iterator[Any]:
    obs_type = as_type or observation_type_for(name)
    setup = _mailroom_setup()
    if setup is not None:
        with setup.observation(name, as_type=obs_type, input=input, metadata=metadata, model=model) as span:
            yield span
        return
    client = _sdk_client()
    if client is None:
        yield _NoopSpan()
        return
    kwargs: dict[str, Any] = {"name": name, "as_type": obs_type, "input": input}
    if metadata is not None:
        kwargs["metadata"] = metadata
    if model is not None:
        kwargs["model"] = model
    with client.start_as_current_observation(**kwargs) as span:
        yield span


def emit_langfuse_score(
    name: str,
    value: float | int | str,
    *,
    comment: str | None = None,
    data_type: str | None = None,
) -> None:
    """Attach a SCORE_CONFIGS-compatible score to the current trace."""
    global _SCORE_EMIT_FAILURES
    wire = langfuse_score_name(name)
    setup = _mailroom_setup()
    if setup is not None:
        try:
            from observability import scores as mailroom_scores  # type: ignore

            mailroom_scores.score(wire, value, comment=comment, data_type=data_type)
            return
        except Exception as exc:
            _warn_once(
                "mailroom-score-path-failed",
                "mailroom score path failed for %r — falling back to Langfuse SDK",
                exc,
            )
    client = _sdk_client()
    if client is None:
        return
    try:
        kwargs: dict[str, Any] = {"name": wire, "value": value}
        if comment:
            kwargs["comment"] = comment
        if data_type:
            kwargs["data_type"] = data_type
        client.score_current_trace(**kwargs)
    except Exception:
        try:
            client.create_score(name=wire, value=value)
        except Exception as exc:
            global _SCORE_EMIT_FAILURES
            _SCORE_EMIT_FAILURES += 1
            _log.error(
                "Langfuse score %r=%r could not be emitted (SDK path AND "
                "create_score fallback both failed) — score is LOST",
                wire,
                value,
                exc_info=exc,
            )


def flush_traces() -> None:
    global _FLUSH_FAILURES
    setup = _mailroom_setup()
    if setup is not None and hasattr(setup, "flush_langfuse"):
        try:
            setup.flush_langfuse()
        except Exception as exc:
            _FLUSH_FAILURES += 1
            _log.error(
                "mailroom flush_langfuse failed — buffered traces may be lost",
                exc_info=exc,
            )
    client = _sdk_client()
    if client is not None:
        try:
            client.flush()
        except Exception as exc:
            _FLUSH_FAILURES += 1
            _log.error(
                "Langfuse SDK flush failed — buffered traces may be lost",
                exc_info=exc,
            )


def export_traces(dest: Path | None = None) -> Path:
    """Write a bookmark: Langfuse host + last session/trace ids (+ Phoenix sidecar)."""
    out = dest or (data_dir() / "traces" / "export.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    host = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL") or "http://localhost:3000"
    payload: dict[str, Any] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tracing_backend": tracing_backend(),
        "langfuse_host": host,
        "langfuse_ui": host,
        "session_id": _LAST_SESSION_ID,
        "trace_ids": last_trace_ids(),
        "tags": default_tags(),
        "environment": observability_environment(),
        "trace_name": PIPELINE_TRACE,
        "note": (
            "Family contract: root chain `document-pipeline`, verb-first child "
            "observations, tags include `mailroom`. Point The-Mailroom at this "
            "Langfuse project (MAILROOM_TRACE_ENVIRONMENTS=mock,pilot)."
        ),
        "phoenix_endpoint": os.environ.get("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"),
        "phoenix_ui": "http://localhost:6006",
    }
    try:
        import httpx

        resp = httpx.get(f"{host.rstrip('/')}/api/public/health", timeout=2.0)
        payload["langfuse_health"] = resp.status_code
    except Exception as exc:  # noqa: BLE001 — probe only
        payload["langfuse_health"] = f"unreachable: {exc}"
    try:
        import httpx

        resp = httpx.get("http://localhost:6006/healthz", timeout=2.0)
        payload["phoenix_health"] = resp.status_code
    except Exception as exc:  # noqa: BLE001 — probe only
        payload["phoenix_health"] = f"unreachable: {exc}"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out
