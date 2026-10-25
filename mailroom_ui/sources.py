"""Shared trace-source contract for The-Mailroom.

Langfuse is THE source of truth for llm-mailroom runs; Phoenix (Arize,
typically a local instance) is an ADDITIONAL read-only source so a locally
running pipeline that traces into Phoenix can be debugged on the same
console. Both adapters duck-type this interface:

    health() -> {"ok": bool, "source": str, ...}
    list_traces(*, since=None, limit=200, tags=None, environments=None,
                name=None) -> list[dict]           # trace-shaped dicts
    get_trace(trace_id) -> Optional[dict]
    get_observations(trace_id) -> list[dict]        # span/generation-shaped
    get_scores(trace_id) -> list[dict]              # {name, value, ...}
    get_score_configs() -> {name: {"data_type", "categories"}}
    get_run(trace_id) -> Optional[PipelineRun]
    list_sessions(limit=100) -> list[dict]
    get_session_traces(session_id, limit=100) -> list[dict]

Nothing here ever fabricates data: an unreachable source raises
TraceSourceUnavailable (the server turns it into a 503 the SPA displays as
"MAILROOM CLOSED").
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from .models import PipelineRun


class TraceSourceUnavailable(RuntimeError):
    """A configured trace backend is unreachable / misconfigured."""


@runtime_checkable
class TraceSource(Protocol):
    """Structural type satisfied by LangfuseSource and PhoenixSource."""

    def health(self) -> dict[str, Any]: ...

    def list_traces(
        self,
        *,
        since: Optional[Any] = None,
        limit: int = 200,
        tags: Optional[list[str]] = None,
        environments: Optional[list[str]] = None,
        name: Optional[str] = None,
    ) -> list[dict[str, Any]]: ...

    def get_trace(self, trace_id: str) -> Optional[dict[str, Any]]: ...

    def get_observations(self, trace_id: str) -> list[dict[str, Any]]: ...

    def get_scores(self, trace_id: str) -> list[dict[str, Any]]: ...

    def get_score_configs(self) -> dict[str, dict[str, Any]]: ...

    def get_run(self, trace_id: str) -> Optional[PipelineRun]: ...

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]: ...

    def get_session_traces(
        self, session_id: str, limit: int = 100
    ) -> list[dict[str, Any]]: ...
