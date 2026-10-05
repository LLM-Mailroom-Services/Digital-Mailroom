"""Multi-source aggregator: serve several trace sources through one facade.

`MAILROOM_SOURCE=both` wraps Langfuse + Phoenix so the floor shows runs from
either backend. Reads fan out with per-trace isolation (a dead source
degrades to empty results from that side, never fabricated data); drill-downs
delegate to whichever source actually holds the trace.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from .models import PipelineRun
from .sources import TraceSourceUnavailable

log = logging.getLogger("mailroom.multi_source")


class MultiSource:
    """Duck-types TraceSource over an ordered list of concrete sources."""

    def __init__(self, sources: list[Any]) -> None:
        if not sources:
            raise ValueError("MultiSource needs at least one source")
        self.sources = sources
        self.primary = sources[0]

    # ------------------------------------------------------------- helpers

    def _merge(self, lists: list[list[dict[str, Any]]], limit: int) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for lst in lists:  # primary first: it wins id collisions
            for t in lst:
                tid = t.get("id")
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                out.append(t)
        return out[:limit]

    def _fanout(self, method: str, /, default: Any, **kw) -> list[Any]:
        """Per-source isolation — but if EVERY source failed, raise.

        Swallowing a total outage returned [] (an empty, healthy-looking
        floor) instead of the MAILROOM CLOSED state.
        """
        batches = []
        errors: list[str] = []
        for src in self.sources:
            try:
                batches.append(getattr(src, method)(**kw))
            except Exception as exc:
                log.warning("%s failed on %s: %s", method, type(src).__name__, exc)
                errors.append(f"{type(src).__name__}: {exc}")
                batches.append([])
        if errors and len(errors) == len(self.sources):
            raise TraceSourceUnavailable(f"{method}: all sources failed ({'; '.join(errors)})"[:400])
        return batches

    def _first(self, method: str, trace_id: str):
        failures = 0
        for src in self.sources:
            try:
                result = getattr(src, method)(trace_id)
            except Exception as exc:
                log.warning("%s(%s) failed on %s: %s", method, trace_id, type(src).__name__, exc)
                failures += 1
                continue
            if result is not None and (not isinstance(result, list) or result):
                return result
        if failures == len(self.sources):
            raise TraceSourceUnavailable(f"{method}({trace_id}): all sources failed")
        return None if method != "get_observations" and method != "get_scores" else []

    # -------------------------------------------------------------- traces

    def list_traces(
        self,
        *,
        since: Optional[datetime] = None,
        limit: int = 200,
        tags: Optional[list[str]] = None,
        environments: Optional[list[str]] = None,
        name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        batches = self._fanout(
            "list_traces", [], since=since, limit=limit, tags=tags,
            environments=environments, name=name,
        )
        return self._merge(batches, limit)

    def get_trace(self, trace_id: str) -> Optional[dict[str, Any]]:
        return self._first("get_trace", trace_id)

    def get_observations(self, trace_id: str) -> list[dict[str, Any]]:
        return self._first("get_observations", trace_id)

    def get_scores(self, trace_id: str) -> list[dict[str, Any]]:
        return self._first("get_scores", trace_id)

    def get_score_configs(self) -> dict[str, dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for src in self.sources:
            try:
                merged.update(src.get_score_configs() or {})
            except Exception as exc:
                log.warning("score_configs failed on %s: %s", type(src).__name__, exc)
        return merged

    def get_run(self, trace_id: str, *, force_refresh: bool = False) -> Optional[PipelineRun]:
        failures = 0
        for src in self.sources:
            try:
                if force_refresh and hasattr(src, "invalidate_run"):
                    src.invalidate_run(trace_id)
                run = src.get_run(trace_id, force_refresh=force_refresh) if force_refresh else src.get_run(trace_id)
            except TypeError:
                try:
                    run = src.get_run(trace_id)
                except Exception as exc:
                    log.warning("get_run(%s) failed on %s: %s", trace_id, type(src).__name__, exc)
                    failures += 1
                    continue
            except Exception as exc:
                log.warning("get_run(%s) failed on %s: %s", trace_id, type(src).__name__, exc)
                failures += 1
                continue
            if run is not None:
                return run
        if failures == len(self.sources):
            raise TraceSourceUnavailable(f"get_run({trace_id}): all sources failed")
        return None

    def invalidate_run(self, trace_id: str) -> None:
        for src in self.sources:
            fn = getattr(src, "invalidate_run", None)
            if callable(fn):
                try:
                    fn(trace_id)
                except Exception as exc:
                    log.warning("invalidate_run(%s) failed on %s: %s", trace_id, type(src).__name__, exc)

    # ------------------------------------------------------------ sessions

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for batch in self._fanout("list_sessions", [], limit=limit * len(self.sources)):
            for s in batch:
                sid = s.get("id")
                if sid and sid not in seen:
                    seen.add(sid)
                    out.append(s)
        return out[:limit]

    def get_session_traces(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        batches = self._fanout("get_session_traces", [], session_id=session_id, limit=limit)
        return self._merge(batches, limit)

    # -------------------------------------------------------------- health

    def health(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        names: list[str] = []
        ok_any = False
        for src in self.sources:
            # One probe per source (it used to call health() twice, the
            # first time outside any try).
            try:
                h = src.health()
            except Exception as exc:
                log.warning("health failed on %s: %s", type(src).__name__, exc)
                h = {}
            key = h.get("source") or type(src).__name__.lower()
            names.append(str(key))
            ok = bool(h.get("ok"))
            ok_any = ok_any or ok
            out[key] = ok
        # "langfuse"/"phoenix" keys carry their own truth; "ok" is the
        # source-agnostic lamp signal the SPA renders.
        out["ok"] = ok_any
        return {"source": "+".join(names), **out}
