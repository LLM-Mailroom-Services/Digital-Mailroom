"""Arize Phoenix adapter — an ADDITIONAL local trace source.

Reads a locally running Phoenix instance (default http://localhost:6006) via
the official `arize-phoenix-client` REST wrapper and reshapes its
OpenTelemetry/OpenInference spans into the Langfuse-shaped dicts that
`interpret_trace` already consumes. llm-mailroom span names map through the
existing SPAN_STAGE_MAP; anything unmapped degrades to the `unknown`/inbox
stage — the same breakage-map philosophy as the Langfuse path. No data is
ever fabricated: if Phoenix is unreachable, callers get TraceSourceUnavailable
and the UI shows MAILROOM CLOSED.

Mapping (Phoenix -> Mailroom):
    root span (parent_id None)      -> trace dict
        context.trace_id            -> id
        start_time                  -> timestamp
        attributes["session.id"]    -> session_id / matter_id
        attributes["mailroom.tags"] -> tags (comma list or JSON list)
        attributes["mailroom.environment"] -> environment
        input.value / output.value  -> input/output ({...} when JSON)
    child span                      -> observation dict
        span_kind "LLM"             -> type GENERATION (+model, usage, cost)
        known mailroom names        -> NODE_OBSERVATION_TYPES (AGENT /
                                       EVALUATOR / RETRIEVER / CHAIN / SPAN)
        anything else               -> type SPAN
        name                        -> name (verb-first node names pass through)
        status_code ERROR + events  -> error message
    span annotations                -> scores ({name, value})

Config (env): PHOENIX_ENDPOINT, PHOENIX_API_KEY, PHOENIX_CLIENT_HEADERS,
MAILROOM_PHOENIX_PROJECT (default project "default").
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .models import PipelineRun
from .pipeline_schema import (
    RELOADED_ROOT_SPAN,
    RELOADED_STATUS_STAGES,
    observation_type_for,
)
from .sources import TraceSourceUnavailable
from .trace_interpreter import interpret_trace

log = logging.getLogger("mailroom.phoenix_source")

try:  # optional dependency: only needed when this source is selected
    from phoenix.client import Client as _PhoenixClient

    HAS_PHOENIX_CLIENT = True
except ImportError:  # pragma: no cover - exercised via env matrix in CI-less dev
    _PhoenixClient = None
    HAS_PHOENIX_CLIENT = False


class PhoenixUnavailable(TraceSourceUnavailable):
    pass


def _to_dict(obj: Any) -> Any:
    """SDK models -> plain dict; dicts pass through."""
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    return obj


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    return str(value)


def _seconds(start: Any, end: Any) -> Optional[float]:
    try:
        s = datetime.fromisoformat(str(_iso(start)).replace("Z", "+00:00"))
        e = datetime.fromisoformat(str(_iso(end)).replace("Z", "+00:00"))
        return max(0.0, (e - s).total_seconds())
    except (TypeError, ValueError):
        return None


def _attr(span: dict[str, Any], key: str) -> Any:
    attrs = span.get("attributes")
    return attrs.get(key) if isinstance(attrs, dict) else None


def _parse_io(value: Any) -> Any:
    """`input.value`/`output.value`: JSON when parseable, else {"value": str}."""
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except (TypeError, ValueError):
        return {"value": text}


def _error_from_events(span: dict[str, Any]) -> Optional[str]:
    for ev in span.get("events") or []:
        ev = _to_dict(ev)
        attrs = ev.get("attributes") or {}
        msg = attrs.get("exception.message") or attrs.get("exception.type")
        if msg:
            return str(msg)[:300]
    return None


class PhoenixSource:
    """Read-only gateway to one Phoenix project."""

    MAX_PAGES = 20

    def __init__(
        self,
        client: Any = None,
        *,
        cache_ttl: float = 5.0,
        run_cache_ttl: float = 30.0,
    ) -> None:
        self.project = os.environ.get("MAILROOM_PHOENIX_PROJECT", "default")
        self.client = client if client is not None else self._build_client()
        self.available = self.client is not None
        # Local Phoenix has no cloud rate limits; short TTLs keep the floor live.
        from .langfuse_source import TTLCache

        self.cache = TTLCache()
        self.cache_ttl = cache_ttl
        self.run_cache_ttl = run_cache_ttl

    @staticmethod
    def _build_client() -> Any:
        if not HAS_PHOENIX_CLIENT:
            log.warning("arize-phoenix-client not installed; Phoenix source disabled")
            return None
        endpoint = os.environ.get(
            "PHOENIX_ENDPOINT", "http://localhost:6006"
        )
        api_key = os.environ.get("PHOENIX_API_KEY")
        headers = {}
        raw = os.environ.get("PHOENIX_CLIENT_HEADERS", "")
        for pair in raw.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                headers[k.strip()] = v.strip()
        try:
            return _PhoenixClient(base_url=endpoint, api_key=api_key, headers=headers or None)
        except TypeError:
            # Older clients without the headers kwarg
            try:
                return _PhoenixClient(base_url=endpoint, api_key=api_key)
            except Exception:
                return None
        except Exception:
            return None

    def _guarded(self, label: str, fn) -> Any:
        if not self.available:
            raise PhoenixUnavailable(f"{label}: no Phoenix client (is Phoenix running at PHOENIX_ENDPOINT?)")
        try:
            return fn()
        except TraceSourceUnavailable:
            raise
        except Exception as exc:
            raise PhoenixUnavailable(f"{label}: {str(exc)[:200]}") from exc

    def _spans(self, label: str, **kw) -> list[dict[str, Any]]:
        """get_spans with pagination tolerance across client versions."""
        spans_api = getattr(self.client, "spans", None)
        if spans_api is None or not hasattr(spans_api, "get_spans"):
            raise PhoenixUnavailable(f"{label}: client.spans.get_spans unavailable")
        out: list[dict[str, Any]] = []
        cursor = kw.pop("cursor", None)
        for _page in range(self.MAX_PAGES):
            resp = self._guarded(label, lambda c=cursor: self._get_spans_page(spans_api, c, **kw))
            batch, next_cursor = self._page_spans(resp)
            out.extend(batch)
            if not next_cursor or not batch:
                break
            cursor = next_cursor
        return [_to_dict(s) for s in out]

    @staticmethod
    def _get_spans_page(spans_api: Any, cursor: Optional[str], **kw) -> Any:
        if cursor is None:
            return spans_api.get_spans(**kw)
        try:
            return spans_api.get_spans(cursor=cursor, **kw)
        except TypeError:
            # Client without cursor pagination: serve the first page only.
            return spans_api.get_spans(**kw)

    @staticmethod
    def _page_spans(resp: Any) -> tuple[list[Any], Optional[str]]:
        if isinstance(resp, dict):
            data = resp.get("data")
            if data is None and "spans" in resp:
                data = resp.get("spans")
            return list(data or []), resp.get("next_cursor") or resp.get("nextCursor")
        if isinstance(resp, tuple) and len(resp) == 2:
            return list(resp[0] or []), resp[1]
        if isinstance(resp, list):
            return resp, None
        data = getattr(resp, "data", None)
        if isinstance(data, list):
            return data, getattr(resp, "next_cursor", None)
        return [], None

    # ------------------------------------------------------------- shaping

    def _trace_dict(self, root: dict[str, Any]) -> dict[str, Any]:
        ctx = _to_dict(root.get("context")) or {}
        trace_id = ctx.get("trace_id") or root.get("trace_id")
        tags = _attr(root, "mailroom.tags") or []
        if isinstance(tags, str):
            text = tags.strip()
            try:
                parsed = json.loads(text)
                tags = [str(t) for t in parsed] if isinstance(parsed, list) else [t.strip() for t in text.split(",") if t.strip()]
            except ValueError:
                tags = [t.strip() for t in text.split(",") if t.strip()]
        start = _iso(root.get("start_time"))
        end = _iso(root.get("end_time"))
        t_input = _parse_io(_attr(root, "input.value"))
        t_output = _parse_io(_attr(root, "output.value"))
        session_id = _attr(root, "session.id")
        if root.get("name") == RELOADED_ROOT_SPAN:
            t_input, t_output, session_id = self._reloaded_io(
                root, t_input, t_output, session_id
            )
        return {
            "id": str(trace_id or ""),
            "name": root.get("name") or "phoenix-trace",
            "timestamp": start,
            "updated_at": end or start,
            "latency": _seconds(root.get("start_time"), root.get("end_time")),
            "session_id": session_id,
            "environment": _attr(root, "mailroom.environment"),
            "tags": tags,
            "metadata": {"project": self.project},
            "input": t_input,
            "output": t_output,
        }

    @staticmethod
    def _reloaded_io(
        root: dict[str, Any],
        t_input: Any,
        t_output: Any,
        session_id: Any,
    ) -> tuple[Any, Any, Any]:
        """Fill a mailroom-reloaded ``mailroom.document`` root's trace input,
        output and session from its ``mailroom.*`` attributes.

        Only attributes the pipeline really set are lifted; explicit
        ``input.value`` / ``output.value`` always win. ``mailroom.status``
        maps through RELOADED_STATUS_STAGES (parked -> review).
        """
        t_input = dict(t_input or {})
        for key, attr in (
            ("doc_id", "mailroom.doc_id"),
            ("filename", "mailroom.filename"),
            ("run_id", "mailroom.run_id"),
        ):
            value = _attr(root, attr)
            if value is not None:
                t_input.setdefault(key, value)
        t_output = dict(t_output or {})
        status = _attr(root, "mailroom.status")
        if status is not None:
            t_output.setdefault(
                "stage", RELOADED_STATUS_STAGES.get(str(status).lower(), "processing")
            )
        doc_type = _attr(root, "mailroom.doc_type")
        if doc_type is not None:
            t_output.setdefault("doc_type", doc_type)
        if session_id is None:
            session_id = _attr(root, "mailroom.run_id")
        return (t_input or None), (t_output or None), session_id

    @staticmethod
    def _observation_dict(span: dict[str, Any]) -> dict[str, Any]:
        kind = str(span.get("span_kind") or _attr(span, "openinference.span.kind") or "").upper()
        is_llm = kind == "LLM"
        name = span.get("name") or ""
        if is_llm:
            o_type = "GENERATION"
        else:
            o_type = observation_type_for(name).upper()
        obs_id = (_to_dict(span.get("context")) or {}).get("span_id") or span.get("span_id")
        obs = {
            "id": str(obs_id or ""),
            "type": o_type,
            "name": span.get("name"),
            "start_time": _iso(span.get("start_time")),
            "end_time": _iso(span.get("end_time")),
            "latency": _seconds(span.get("start_time"), span.get("end_time")),
            "input": _parse_io(_attr(span, "input.value")),
            "output": _parse_io(_attr(span, "output.value")),
        }
        status = str(span.get("status_code") or "").upper()
        if status == "ERROR":
            obs["level"] = "ERROR"
            err = _error_from_events(span)
            if err:
                obs["error"] = err
        if is_llm:
            model = _attr(span, "llm.model_name")
            if model is not None:
                obs["model"] = model
            usage = {
                "total": _attr(span, "llm.token_count.total"),
                "input": _attr(span, "llm.token_count.prompt"),
                "output": _attr(span, "llm.token_count.completion"),
            }
            if any(v is not None for v in usage.values()):
                obs["usage"] = usage
            cost_total = _attr(span, "llm.cost.total")
            if cost_total is None:
                p, c = _attr(span, "llm.cost.prompt"), _attr(span, "llm.cost.completion")
                if p is not None or c is not None:
                    try:
                        cost_total = float(p or 0) + float(c or 0)
                    except (TypeError, ValueError):
                        cost_total = None
            if cost_total is not None:
                obs["totalCost"] = cost_total
        return obs

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
        since = since or (datetime.now(timezone.utc) - timedelta(hours=6))
        bucket = int(since.timestamp() // 30)  # 30s cache bucket like LangfuseSource
        key = f"list:{self.project}:{bucket}:{limit}"
        cached = self.cache.get(key)
        if cached is not None:
            traces = cached
        else:
            roots = [
                s for s in self._spans(
                    "spans.list",
                    project_identifier=self.project,
                    start_time=since,
                    limit=max(limit * 3, 100),
                )
                if not s.get("parent_id")
            ]
            traces = [self._trace_dict(r) for r in roots]
            self.cache.set(key, traces, self.cache_ttl)
            for t in traces:
                self.cache.set(f"trace:{t['id']}", t, self.cache_ttl)
        out = []
        for t in traces:
            if name and t.get("name") != name:
                continue
            if tags and not set(tags) <= set(t.get("tags") or []):
                continue
            if environments and t.get("environment") not in environments:
                continue
            out.append(t)
        return out[:limit]

    def get_trace(self, trace_id: str) -> Optional[dict[str, Any]]:
        key = f"trace:{trace_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        roots = [
            s for s in self._spans(
                f"spans.trace:{trace_id}",
                project_identifier=self.project,
                trace_ids=[trace_id],
                limit=1000,
            )
            if not s.get("parent_id")
        ]
        if not roots:
            return None
        out = self._trace_dict(roots[0])
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_observations(self, trace_id: str) -> list[dict[str, Any]]:
        key = f"obs:{trace_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        spans = self._spans(
            f"spans.trace-children:{trace_id}",
            project_identifier=self.project,
            trace_ids=[trace_id],
            limit=1000,
        )
        out = [self._observation_dict(s) for s in spans if s.get("parent_id")]
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_scores(self, trace_id: str) -> list[dict[str, Any]]:
        """Scores from Phoenix span annotations + mailroom.score.* attributes."""
        key = f"scores:{trace_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        out: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        def add(name: str, value: Any, span_id: str = "") -> None:
            if name is None or value is None or (name, span_id) in seen:
                return
            seen.add((name, span_id))
            out.append({"name": name, "value": value, "data_type": "CATEGORICAL" if isinstance(value, str) else "NUMERIC"})

        spans = self._spans(
            f"spans.scores:{trace_id}",
            project_identifier=self.project,
            trace_ids=[trace_id],
            limit=1000,
        )
        for s in spans:
            sid = (_to_dict(s.get("context")) or {}).get("span_id") or ""
            attrs = s.get("attributes")
            if not isinstance(attrs, dict):
                continue
            for akey, avalue in attrs.items():
                if akey.startswith("mailroom.score.") and avalue is not None:
                    add(akey.split(".", 2)[2], avalue, sid)
        try:
            anns_api = getattr(self.client.spans, "get_span_annotations", None)
            if anns_api is not None:
                span_ids = [
                    (_to_dict(s.get("context")) or {}).get("span_id")
                    for s in spans
                    if (_to_dict(s.get("context")) or {}).get("span_id")
                ]
                for i in range(0, len(span_ids), 100):
                    chunk = span_ids[i:i + 100]
                    resp = self._guarded(
                        "spans.annotations",
                        lambda ch=chunk: anns_api(
                            span_ids=ch, project_identifier=self.project
                        ),
                    )
                    for ann in resp if isinstance(resp, list) else []:
                        ann = _to_dict(ann)
                        add(ann.get("name"), ann.get("label", ann.get("score")), ann.get("span_id") or "")
        except PhoenixUnavailable as exc:
            log.warning("annotation fetch degraded: %s", exc)
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_score_configs(self) -> dict[str, dict[str, Any]]:
        """Phoenix carries no categorical configs; labels are stored directly."""
        return {}

    def invalidate_run(self, trace_id: str) -> None:
        if not trace_id:
            return
        for prefix in ("run:", "obs:", "scores:"):
            self.cache.delete(f"{prefix}{trace_id}")

    def get_run(self, trace_id: str, *, force_refresh: bool = False) -> Optional[PipelineRun]:
        key = f"run:{trace_id}"
        if force_refresh:
            self.invalidate_run(trace_id)
        else:
            cached = self.cache.get(key)
            if cached is not None:
                return cached
        trace = self.get_trace(trace_id)
        if trace is None:
            return None
        run = interpret_trace(trace, self.get_observations(trace_id), self.get_scores(trace_id))
        self.cache.set(key, run, self.run_cache_ttl)
        return run

    # ------------------------------------------------------------ sessions

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        sessions: dict[str, dict[str, Any]] = {}
        for t in self.list_traces(limit=500):
            sid = t.get("session_id")
            if not sid:
                continue
            entry = sessions.setdefault(sid, {
                "id": sid, "created_at": t.get("timestamp"), "updated_at": t.get("updated_at"),
            })
            entry["updated_at"] = max(entry["updated_at"] or "", t.get("updated_at") or "") or None
        return list(sessions.values())[:limit]

    def get_session_traces(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return [
            t for t in self.list_traces(limit=500)
            if t.get("session_id") == session_id
        ][:limit]

    # -------------------------------------------------------------- health

    def health(self) -> dict[str, Any]:
        try:
            n = len(self.list_traces(limit=1))
            ok = True
        except Exception:
            ok = False
            n = None
        return {"ok": ok, "phoenix": ok, "source": "phoenix", "project": self.project}
