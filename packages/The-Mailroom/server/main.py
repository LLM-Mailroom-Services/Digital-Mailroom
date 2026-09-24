"""The-Mailroom web server: Langfuse-backed read-only API + pixel-art UI."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import deque
from typing import Any, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

# V-8: .env must be loaded BEFORE any module-level env reads (the knobs below
# were read before load_dotenv(), so MAILROOM_POLL_INTERVAL / RECENT_WINDOW /
# TRACE_LIMIT never applied from .env).
load_dotenv()

from mailroom_ui.langfuse_source import (
    LangfuseSource,
    list_recent_runs,
)
from mailroom_ui.metrics import compute_metrics
from mailroom_ui.models import PipelineRun, SessionSummary
from mailroom_ui.multi_source import MultiSource
from mailroom_ui.pipeline_ops import fetch_pipeline_ops
from mailroom_ui.review_actions import (
    ReviewActionError,
    enqueue_inbox,
    fetch_audit,
    fetch_source,
    fetch_source_download,
    pipeline_configured,
    resolve_review,
    review_context,
)
from mailroom_ui.trace_cache import (
    CACHE_SOURCE,
    cache_status,
    load_run,
    load_traces,
    persist_floor,
    persist_metrics,
    persist_run,
    snapshot_bundle,
)
from mailroom_ui.pipeline_schema import DOC_CLASSES, DOC_SUBCLASS_BY_CLASS
from mailroom_ui.phoenix_source import PhoenixSource
from mailroom_ui.producer import producer_status
from mailroom_ui.sources import TraceSourceUnavailable
from mailroom_ui.trace_interpreter import interpret_trace
from operator_desk import OPERATOR_ENDPOINTS, mount_operator, operator_status
from operator_desk.observer import start_observer
from operator_desk.observer import observer_enabled as operator_observer_enabled
from server.debug_log import DebugLog, DebugLogMiddleware
from server.poller import PollHub, floor_payload

log = logging.getLogger("mailroom.server")

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
HOSTED_DIR = Path(__file__).resolve().parent.parent / "hosted"
RECENT_WINDOW = float(os.environ.get("MAILROOM_RECENT_WINDOW", 7 * 86400))
POLL_INTERVAL = float(os.environ.get("MAILROOM_POLL_INTERVAL", "3"))
TRACE_LIMIT = int(os.environ.get("MAILROOM_TRACE_LIMIT", "200"))
_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}


def _edition() -> str:
    return os.environ.get("MAILROOM_EDITION", "console").strip().lower()


def _platform() -> str:
    """Deploy host tag for /health + /api/meta (deploy verification)."""
    if os.environ.get("RAILWAY_SERVICE_NAME") or os.environ.get("RAILWAY_DEPLOY_ID"):
        return "railway"
    if os.environ.get("RENDER_INSTANCE_ID"):
        return "render"
    if os.environ.get("FLY_APP_NAME"):
        return "fly"
    if os.environ.get("HF_SPACE_ID") or os.environ.get("SPACE_ID"):
        return "huggingface"
    return ""


def _build_sha() -> str:
    """Commit SHA baked at image build (MAILROOM_BUILD_SHA). Empty off-platform."""
    sha = (os.environ.get("MAILROOM_BUILD_SHA") or "").strip()
    return sha if sha and sha != "unknown" else ""

API_ENDPOINTS = [
    {"method": "GET", "path": "/api/health", "desc": "source reachability (Langfuse / cache)"},
    {"method": "GET", "path": "/health", "desc": "platform liveness (Railway / Fly / Docker; no Langfuse call)"},
    {"method": "GET", "path": "/api/traces", "desc": "recent runs (light); ?since=&limit=&stage=&environment="},
    {"method": "GET", "path": "/api/traces/{trace_id}", "desc": "full run detail (spans/generations/scores)"},
    {"method": "GET", "path": "/api/metrics", "desc": "window aggregates; ?since="},
    {"method": "GET", "path": "/api/sessions", "desc": "sessions / matters; /api/sessions/{session_id} for one"},
    {"method": "GET", "path": "/api/review-queue", "desc": "runs flagged for human review; ?since="},
    {"method": "GET", "path": "/api/meta", "desc": "doc classes, active sources, this endpoint index"},
    {"method": "GET", "path": "/api/debug/logs", "desc": "request ring buffer for agents; ?limit="},
    {"method": "GET", "path": "/api/debug/source", "desc": "configured sources + knobs"},
    {"method": "GET", "path": "/api/debug/bundle", "desc": "one-pull: health + source + server logs + last client dumps"},
    {"method": "GET", "path": "/api/debug/client", "desc": "last browser dumps posted by Observatory / pixel clients"},
    {"method": "POST", "path": "/api/debug/client", "desc": "store a browser debug dump for the next agent pull"},
    {"method": "GET", "path": "/api/pipeline", "desc": "producer watcher/inbox liveness (MAILROOM_PIPELINE_URL)"},
    {"method": "GET", "path": "/api/review/context", "desc": "producer catalog+audit for a review item; ?trace_id=&filename=&doc_id="},
    {"method": "POST", "path": "/api/review/resolve", "desc": "proxy approve/reject/record/requeue/complete (+ doc_type mapped to override_doc_type) to llm-mailroom /v1"},
    {"method": "GET", "path": "/api/review/source", "desc": "parked document text from producer (lookup fallback if no /documents/{id}/source); ?trace_id=&filename=&doc_id=&download=1"},
    {"method": "GET", "path": "/api/review/audit", "desc": "hash-chained producer audit; ?doc_id="},
    {"method": "POST", "path": "/api/inbox/enqueue", "desc": "proxy multipart file to producer POST /v1/upload (503 until MAILROOM_PIPELINE_URL)"},
    {"method": "GET", "path": "/api/snapshot", "desc": "Langfuse-derived JSON snapshot (cache; never fabricated)"},
    {"method": "WS", "path": "/ws", "desc": "floor snapshots (live mode only)"},
    {"method": "GET", "path": "/live", "desc": "hosted Observatory UI (modern, accessible, public)"},
]
API_ENDPOINTS = API_ENDPOINTS + list(OPERATOR_ENDPOINTS)


def _build_default_source() -> object:
    """MAILROOM_SOURCE selector: langfuse (default) | phoenix | both."""
    which = os.environ.get("MAILROOM_SOURCE", "langfuse").strip().lower()
    # List/obs TTL follows the poll interval so a just-created trace is
    # visible on the next snapshot instead of sitting behind a longer cache.
    ttl = max(0.0, POLL_INTERVAL)
    if which == "phoenix":
        return PhoenixSource(cache_ttl=ttl)
    if which in ("both", "multi", "all"):
        return MultiSource([
            LangfuseSource(cache_ttl=ttl, poll_cache_ttl=ttl),
            PhoenixSource(cache_ttl=ttl),
        ])
    return LangfuseSource(cache_ttl=ttl, poll_cache_ttl=ttl)


def create_app(source: Optional[object] = None) -> FastAPI:
    src = source or _build_default_source()
    debug_log = DebugLog()
    hub = PollHub(src, interval=POLL_INTERVAL, window=RECENT_WINDOW, limit=TRACE_LIMIT)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await hub.start()
        watcher = (
            start_observer(loop=asyncio.get_running_loop())
            if operator_observer_enabled()
            else None
        )
        yield
        if watcher is not None:
            watcher.stop()
        await hub.stop()

    app = FastAPI(title="The-Mailroom", version="0.3.0", lifespan=lifespan)

    # GH Pages edition: the static site (https://<user>.github.io/<repo>/) must
    # be able to call this API when it runs locally next to Phoenix — CORS for
    # browser fetches, read-only GETs only.
    from fastapi.middleware.cors import CORSMiddleware

    origins = [o.strip() for o in os.environ.get("MAILROOM_CORS_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(DebugLogMiddleware, recorder=debug_log)

    @app.exception_handler(TraceSourceUnavailable)
    async def langfuse_down_handler(request, exc):
        return JSONResponse(
            status_code=503,
            content={"error": "langfuse unavailable", "detail": str(exc)},
        )

    # V-18: any other server error must come back as JSON with a detail the
    # SPA can show — the old default 500 was plain text and the frontend
    # discarded it, leaving a silent blank/zeroed screen.
    @app.exception_handler(Exception)
    async def generic_error_handler(request, exc):
        from fastapi.exceptions import RequestValidationError
        from starlette.exceptions import HTTPException as StarletteHTTPException

        if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
            raise exc
        return JSONResponse(
            status_code=500,
            content={"error": "internal server error", "detail": str(exc)[:300]},
        )

    def _health_payload():
        payload = src.health()
        cache = cache_status()
        if isinstance(payload, dict):
            payload = dict(payload)
            payload["pipeline_configured"] = pipeline_configured()
            payload["mailroom"] = producer_status()
            payload["operator"] = operator_status()
            payload["cache"] = cache
            if not payload.get("ok") and cache.get("has_snapshot"):
                payload["ok"] = True
                payload["source"] = CACHE_SOURCE
                payload["cached_at"] = cache.get("cached_at")
                payload["cached_trace_count"] = cache.get("cached_trace_count")
        return payload

    @app.get("/api/health")
    def health():
        return _health_payload()

    # Platform probes (Railway / Fly / Render / Docker HEALTHCHECK) expect a
    # fast 2xx without depending on Langfuse. MAILROOM CLOSED is a valid UI
    # state — the process is still alive. Use /api/health for source status.
    @app.get("/health")
    def health_root():
        return {
            "ok": True,
            "status": "alive",
            "edition": _edition(),
            "platform": _platform(),
            "build_sha": _build_sha(),
        }

    @app.get("/api/traces")
    def traces(
        since: int = Query(86400 * 7, ge=0, le=86400 * 7, description="window seconds"),
        limit: int = Query(TRACE_LIMIT, ge=1, le=500),
        stage: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        try:
            runs = _recent(src, since, limit)
        except TraceSourceUnavailable:
            cached = load_traces()
            if cached:
                rows = list(cached.get("runs") or [])
                cutoff = _utcnow() - timedelta(seconds=since)
                rows = [r for r in rows if _cached_row_stamp(r) >= cutoff]
                if stage:
                    rows = [r for r in rows if r.get("stage") == stage]
                if environment:
                    rows = [r for r in rows if r.get("environment") == environment]
                sliced = rows[:limit]
                return {
                    "count": len(sliced),
                    "source": CACHE_SOURCE,
                    "cached_at": cached.get("cached_at"),
                    "runs": sliced,
                }
            raise
        if stage:
            runs = [r for r in runs if r.stage.value == stage]
        if environment:
            runs = [r for r in runs if r.environment == environment]
        payload_runs = [_serialize(r) for r in runs]
        persist_floor(payload_runs, source=_source_names(src))
        return {
            "count": len(payload_runs),
            "source": _source_names(src),
            "runs": payload_runs,
        }

    @app.get("/api/traces/{trace_id}")
    def trace_detail(trace_id: str):
        cached = load_run(trace_id)
        if cached and (cached.get("spans") is not None or cached.get("generations") is not None):
            return {**cached, "source": cached.get("source") or CACHE_SOURCE}
        try:
            run = src.get_run(trace_id)
        except TraceSourceUnavailable:
            if cached:
                return {**cached, "source": CACHE_SOURCE}
            raise
        if run is None:
            if cached:
                return {**cached, "source": CACHE_SOURCE}
            return JSONResponse(status_code=404, content={"error": "trace not found"})
        detail = _serialize(run, full=True)
        persist_run(trace_id, detail)
        return detail

    @app.get("/api/metrics")
    def metrics(since: int = Query(86400 * 7, ge=0, le=86400 * 7)):
        # V-3: aggregate ENRICHED runs (full observations/scores), never light
        # ones — light runs have no generations, so cost/tokens/calls were
        # permanently $0.00 / 0 tok / 0 calls.
        # Prefer the poller's already-enriched window so this desk does not
        # re-walk Langfuse (that hung the inspector for ~2 minutes).
        runs = _desk_runs(src, hub, since_seconds=since, limit=TRACE_LIMIT)
        m = compute_metrics(runs, since=_utcnow() - timedelta(seconds=since))
        payload = {"source": _source_names(src), **m.model_dump()}
        persist_metrics(payload)
        return payload

    @app.get("/api/sessions")
    def sessions(limit: int = Query(50, ge=1, le=200)):
        # V-24: group enriched runs by session in ONE list pass. The old
        # N+1 (per-session × per-trace get_run) fired up to ~1000 live
        # Langfuse calls and timed out against the real cloud.
        runs = [r for r in _desk_runs(src, hub, since_seconds=7 * 86400, limit=TRACE_LIMIT)
                if r.session_id or r.matter_id]
        grouped: dict[str, list[PipelineRun]] = {}
        for r in runs:
            grouped.setdefault(r.session_id or r.matter_id or "(no session)", []).append(r)
        out = []
        for sid, rs in grouped.items():
            rs.sort(key=_run_sort_key, reverse=True)
            stamps_c = [r.created_at for r in rs if r.created_at]
            stamps_u = [r.updated_at or r.created_at for r in rs
                        if (r.updated_at or r.created_at) is not None]
            out.append(SessionSummary(
                id=sid,
                created_at=min(stamps_c) if stamps_c else None,
                updated_at=max(stamps_u) if stamps_u else None,
                trace_count=len(rs),
                runs=rs,
            ))
        out.sort(key=lambda s: s.updated_at or UTC_MIN, reverse=True)
        return JSONResponse(
            {
                "count": len(out[:limit]),
                "source": _source_names(src),
                "sessions": [
                    {
                        **s.model_dump(mode="json", exclude={"runs"}),
                        "runs": [floor_payload(r) for r in s.runs],
                    }
                    for s in out[:limit]
                ],
            },
            headers=_NO_CACHE,
        )

    @app.get("/api/sessions/{session_id}")
    def session_detail(session_id: str):
        # Prefer the poller's already-enriched window. A 50-doc pilot used to
        # N+1 get_session_traces × get_run and time out against Langfuse.
        desk = [
            r for r in (hub.runs or [])
            if (r.session_id or r.matter_id) == session_id
        ]
        if not desk:
            cutoff = _utcnow() - timedelta(seconds=7 * 86400)
            desk = [
                r for r in list_recent_runs(src, since=cutoff, limit=TRACE_LIMIT)
                if (r.session_id or r.matter_id) == session_id
            ]
        if desk:
            desk.sort(key=_run_sort_key, reverse=True)
            return {
                "session_id": session_id,
                "count": len(desk),
                "source": _source_names(src),
                "runs": [_serialize(r) for r in desk],
            }
        runs = _session_runs(src, session_id, limit=TRACE_LIMIT)
        return {
            "session_id": session_id,
            "count": len(runs),
            "source": "langfuse",
            "runs": [_serialize(r) for r in runs],
        }

    @app.get("/api/review-queue")
    def review_queue(since: int = Query(86400 * 7, ge=0, le=86400 * 7)):
        # V-20: enriched runs (verdicts/tokens/cost on the cards, not zeros).
        # Share the poller's TRACE_LIMIT window — a second 500-trace enrich
        # starved inspector fetches against production Langfuse.
        runs = [r for r in _desk_runs(src, hub, since_seconds=since, limit=TRACE_LIMIT)
                if r.needs_human]
        return {"count": len(runs), "source": _source_names(src), "runs": [_serialize(r) for r in runs]}

    @app.get("/api/pipeline")
    def pipeline_ops():
        """Producer watcher + inbox liveness. Document display stays Langfuse."""
        ops = hub.pipeline_ops if hub.pipeline_ops.get("configured") else fetch_pipeline_ops()
        return ops

    @app.get("/api/review/context")
    def review_context_ep(
        trace_id: str = Query("", max_length=256),
        filename: str = Query("", max_length=512),
        doc_id: str = Query("", max_length=128),
    ):
        """Producer catalog lookup + audit for a REVIEW desk item.

        Tray probe: 4s cap so a slow producer does not pile threadpool waits
        behind every row (the queue can hold dozens of items).
        """
        return review_context(trace_id=trace_id, filename=filename, doc_id=doc_id, timeout=4.0)

    @app.post("/api/review/resolve")
    def review_resolve_ep(payload: dict[str, Any]):
        """Proxy a human review decision to llm-mailroom. Browser never holds the token."""
        try:
            return resolve_review(
                decision=str(payload.get("decision") or ""),
                disposition=str(payload.get("disposition") or "resume"),
                notes=str(payload.get("notes") or ""),
                trace_id=str(payload.get("trace_id") or ""),
                filename=str(payload.get("filename") or ""),
                doc_id=str(payload.get("doc_id") or ""),
                doc_type=str(payload.get("doc_type") or ""),
                doc_subclass=str(payload.get("doc_subclass") or ""),
                override_doc_type=str(payload.get("override_doc_type") or ""),
                extracted_data=payload.get("extracted_data"),
            )
        except ReviewActionError as exc:
            return JSONResponse(
                status_code=exc.status,
                content={"error": exc.message, "detail": exc.detail},
            )

    @app.get("/api/review/source")
    def review_source_ep(
        trace_id: str = Query("", max_length=256),
        filename: str = Query("", max_length=512),
        doc_id: str = Query("", max_length=128),
        download: bool = Query(False),
    ):
        """Parked document text/bytes from the producer. Browser never hits :8000."""
        try:
            if download:
                data, content_type, name = fetch_source_download(
                    trace_id=trace_id, filename=filename, doc_id=doc_id,
                )
                headers = {}
                if name:
                    headers["Content-Disposition"] = f'attachment; filename="{name}"'
                return Response(content=data, media_type=content_type, headers=headers)
            if not (trace_id or filename or doc_id):
                if not pipeline_configured():
                    return fetch_source()
                return {"configured": True, "text": None, "error": None}
            # Tray probe: 4s cap (see /api/review/context) — the queue renders
            # every parked run at once and a slow producer must not stall each.
            return fetch_source(trace_id=trace_id, filename=filename, doc_id=doc_id, timeout=4.0)
        except ReviewActionError as exc:
            if not download and exc.status == 503:
                return {
                    "configured": False,
                    "text": None,
                    "error": exc.message,
                }
            return JSONResponse(
                status_code=exc.status,
                content={"error": exc.message, "detail": exc.detail},
            )

    @app.get("/api/review/audit")
    def review_audit_ep(doc_id: str = Query(..., min_length=1, max_length=128)):
        try:
            return fetch_audit(doc_id)
        except ReviewActionError as exc:
            return JSONResponse(
                status_code=exc.status,
                content={"error": exc.message, "detail": exc.detail},
            )

    @app.post("/api/inbox/enqueue")
    async def inbox_enqueue_ep(request: Request):
        """Proxy a file to producer POST /v1/upload. No fabricated catalog row."""
        try:
            ctype = (request.headers.get("content-type") or "").lower()
            filename = ""
            matter_id = ""
            content_type = ""
            file_bytes: Optional[bytes] = None
            if "application/json" in ctype:
                payload = await request.json()
                if not isinstance(payload, dict):
                    payload = {}
                filename = str(payload.get("filename") or "")
                matter_id = str(payload.get("matter_id") or "")
                content_type = str(payload.get("content_type") or "")
                raw = payload.get("content_base64") or payload.get("content")
                if isinstance(raw, str) and raw.strip():
                    try:
                        file_bytes = base64.b64decode(raw)
                    except Exception as exc:
                        raise ReviewActionError("content_base64 is not valid base64", status=400) from exc
            else:
                form = await request.form()
                upload = form.get("file")
                matter_id = str(form.get("matter_id") or "")
                filename = str(form.get("filename") or "")
                if upload is not None and hasattr(upload, "read"):
                    file_bytes = await upload.read()
                    filename = filename or (getattr(upload, "filename", None) or "")
                    content_type = getattr(upload, "content_type", None) or ""
            result = enqueue_inbox(
                filename=filename,
                matter_id=matter_id,
                content_type=content_type,
                file_bytes=file_bytes,
            )
            status = 202 if str(result.get("status") or "").lower() == "accepted" else 200
            return JSONResponse(status_code=status, content=result)
        except ReviewActionError as exc:
            return JSONResponse(
                status_code=exc.status,
                content={"error": exc.message, "detail": exc.detail, "configured": pipeline_configured()},
            )

    @app.get("/api/snapshot")
    def snapshot_ep():
        """Download the Langfuse-derived cache bundle (same shape as export_snapshot)."""
        return snapshot_bundle()

    @app.get("/api/meta")
    def meta():
        # V-23: use PipelineSchema.load() so the MAILROOM_TAXONOMY override is
        # reflected — the module-level DOC_CLASSES constant ignored it.
        try:
            from mailroom_ui.pipeline_schema import PipelineSchema

            schema = PipelineSchema.load()
            classes = schema.doc_classes if hasattr(schema, "doc_classes") else DOC_CLASSES
        except Exception as exc:
            log.warning(
                "PipelineSchema.load() failed (%s) — serving the STALE hardcoded "
                "doc classes; the pipeline mirror is out of sync with the "
                "taxonomy it renders",
                exc,
            )
            classes = DOC_CLASSES
        subclasses = {k: list(v) for k, v in DOC_SUBCLASS_BY_CLASS.items()}
        return {
            "doc_classes": classes,
            "doc_subclasses": subclasses,
            "pipeline_configured": pipeline_configured(),
            "mailroom": producer_status(),
            "operator": operator_status(),
            "source": _source_names(src),
            "mode": "api",
            "edition": _edition(),
            "platform": _platform(),
            "build_sha": _build_sha(),
            "version": _version(),
            "ui": {
                "console": "/",
                "hosted": "/live",
                "default": "/live" if _edition() in ("hosted", "live", "observatory") else "/",
            },
            "poll_interval_s": POLL_INTERVAL,
            "recent_window_s": RECENT_WINDOW,
            "endpoints": API_ENDPOINTS,
        }

    @app.get("/api/debug/logs")
    def debug_logs(limit: int = Query(200, ge=1, le=500)):
        return {"count_limit": limit, "events": debug_log.snapshot(limit)}

    client_reports: deque[dict[str, Any]] = deque(maxlen=20)

    def _debug_source_payload() -> dict:
        info: dict = {
            "selector": os.environ.get("MAILROOM_SOURCE", "langfuse"),
            "sources": _source_names(src).split("+"),
            "debug_stdout": debug_log.verbose,
            "poll_interval_s": POLL_INTERVAL,
            "recent_window_s": RECENT_WINDOW,
            "trace_limit": TRACE_LIMIT,
            "edition": _edition(),
            "pipeline_url": bool(
                os.environ.get("MAILROOM_PIPELINE_URL")
                or os.environ.get("MAILROOM_PIPELINE_API")
            ),
            "pipeline_configured": pipeline_configured(),
            "cache": cache_status(),
        }
        info["mailroom"] = producer_status()
        info["operator"] = operator_status()
        for attr in ("project",):
            if hasattr(src, attr):
                info["phoenix_project"] = getattr(src, attr)
        return info

    @app.get("/api/debug/source")
    def debug_source():
        return _debug_source_payload()

    @app.get("/api/debug/bundle")
    def debug_bundle(limit: int = Query(200, ge=1, le=500)):
        """One pull for agents: health, source knobs, server ring, last client dumps."""
        try:
            health = src.health()
        except Exception as exc:
            health = {"ok": False, "error": str(exc)[:300]}
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "health": health,
            "source": _debug_source_payload(),
            "server_logs": debug_log.snapshot(limit),
            "client_reports": list(client_reports),
            "how_to": {
                "browser_dump": "window.__OBSERVATORY_DEBUG__.dump()",
                "browser_export": "window.__OBSERVATORY_DEBUG__.export()",
                "curl_bundle": "curl -sS $HOST/api/debug/bundle",
                "curl_logs": "curl -sS $HOST/api/debug/logs?limit=200",
                "curl_source": "curl -sS $HOST/api/debug/source",
                "view": "/live#debug or ?debug=1",
            },
        }

    @app.post("/api/debug/client")
    def debug_client_post(body: dict):
        if not isinstance(body, dict):
            return JSONResponse(status_code=400, content={"error": "expected JSON object"})
        events = body.get("events") or []
        entry = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "href": body.get("href") or body.get("location"),
            "event_count": body.get("eventCount") if body.get("eventCount") is not None else len(events),
            "last_error": body.get("lastError"),
            "report": body,
        }
        client_reports.append(entry)
        debug_log.record(
            "client-report",
            href=entry["href"],
            events=entry["event_count"],
        )
        return {"ok": True, "stored": len(client_reports)}

    @app.get("/api/debug/client")
    def debug_client_list():
        return {"count": len(client_reports), "reports": list(client_reports)}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await hub.connect(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            hub.disconnect(ws)
        except Exception:
            hub.disconnect(ws)

    def _operator_runs():
        if hub.runs:
            return list(hub.runs)
        return list_recent_runs(
            src, since=_utcnow() - timedelta(seconds=RECENT_WINDOW), limit=TRACE_LIMIT
        )

    mount_operator(app, runs_provider=_operator_runs)

    def _page(path: Path) -> FileResponse:
        return FileResponse(path, headers=_NO_CACHE)

    if HOSTED_DIR.exists():
        @app.get("/live", include_in_schema=False)
        @app.get("/live/", include_in_schema=False)
        def hosted_page():
            return _page(HOSTED_DIR / "index.html")

        app.mount("/live/static", StaticFiles(directory=HOSTED_DIR), name="hosted")

    if WEB_DIR.exists():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        @app.get("/")
        def index():
            # Hosted edition puts the public Observatory on `/`; the pixel
            # console remains at /static + this same index when edition=console.
            if _edition() in ("hosted", "live", "observatory") and HOSTED_DIR.exists():
                return _page(HOSTED_DIR / "index.html")
            return _page(WEB_DIR / "index.html")

    return app


UTC_MIN = datetime.min.replace(tzinfo=timezone.utc)


def _utcnow() -> datetime:
    """Langfuse stores UTC — every query window must be UTC-aware (a naive
    local now() shifts the window by the machine's UTC offset)."""
    return datetime.now(timezone.utc)


def _run_sort_key(run: PipelineRun) -> datetime:
    return run.updated_at or run.created_at or UTC_MIN


def _cached_row_stamp(row: dict) -> datetime:
    raw = row.get("updated_at") or row.get("created_at")
    if not raw:
        return UTC_MIN
    parsed = _dt(raw)
    return parsed if parsed is not None else UTC_MIN


def _source_names(src: object) -> str:
    if isinstance(src, MultiSource):
        return "+".join(type(s).__name__.replace("Source", "").lower() for s in src.sources)
    return type(src).__name__.replace("Source", "").lower()


def _version() -> str:
    # Dev checkout first: a stale site-packages install must not shadow the
    # working tree's version.
    try:
        text = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text()
        for line in text.splitlines():
            if line.strip().startswith("version"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    try:
        from importlib.metadata import version

        return version("the-mailroom")
    except Exception:
        return "dev"


def _recent(src: LangfuseSource, since: int, limit: int) -> list[PipelineRun]:
    since_dt = _utcnow() - timedelta(seconds=since)
    return list_recent_runs(src, since=since_dt, limit=limit)


def _desk_runs(src, hub: PollHub, *, since_seconds: int, limit: int) -> list[PipelineRun]:
    """Enriched runs for METRICS / SESSIONS / REVIEW.

    The poller already called get_run() for the live window. Reusing that
    list keeps those desks instant and leaves the inspector able to fetch
    /api/traces/{id} instead of waiting behind a sequential Langfuse walk.
    Fall back to the cheap trace-list (light runs) when the poller has not
    produced a snapshot yet — never enriched_recent_runs, which N+1s get_run
    and hung a 50-doc SESSIONS load.
    """
    cutoff = _utcnow() - timedelta(seconds=since_seconds)
    cached = [r for r in (hub.runs or [])
              if (r.updated_at or r.created_at or cutoff) >= cutoff]
    if cached:
        return cached[:limit]
    # Never N+1 Langfuse here. A 50-doc window used to hang SESSIONS/REVIEW
    # for minutes while the poller was still filling hub.runs. Light list
    # rows carry session_id / stage / needs_human; the next poller tick
    # replaces this with enriched desk runs.
    return list_recent_runs(src, since=cutoff, limit=limit)


def _session_runs(src: LangfuseSource, session_id: str, limit: int) -> list[PipelineRun]:
    """Enriched runs for one session, newest first (V-19).

    Uses the cached get_run() (observations+scores) with per-trace isolation:
    one bad trace falls back to its light interpretation instead of failing
    the whole session.
    """
    runs: list[PipelineRun] = []
    try:
        traces = src.get_session_traces(session_id, limit=limit)
    except Exception as exc:
        log.warning("session traces failed for %s: %s", session_id, exc)
        return runs
    for t in traces:
        tid = t.get("id")
        if not tid:
            continue
        try:
            full = src.get_run(tid)
            runs.append(full if full is not None else interpret_trace(t))
        except Exception as exc:
            log.warning("session run failed for %s: %s", tid, exc)
            runs.append(interpret_trace(t))
    runs.sort(key=lambda r: r.updated_at or UTC_MIN, reverse=True)
    return runs


def _serialize(run: PipelineRun, full: bool = False) -> dict:
    if not full:
        return floor_payload(run)
    return {
        **floor_payload(run),
        "spans": [s.model_dump() for s in run.spans],
        "generations": [g.model_dump() for g in run.generations],
        "scores": run.scores,
    }


def _dt(value) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def listen_port(default: int = 8001) -> int:
    """Prefer platform ``PORT`` (Railway / Fly / Render) over ``MAILROOM_PORT``.

    Hugging Face Spaces and the Observatory image bake ``MAILROOM_PORT=7860``.
    Listening on that while the edge proxies ``$PORT`` is the usual Railway
    crash-loop failure mode — same contract as llm-mailroom's API.
    """
    platform = (os.environ.get("PORT") or "").strip()
    if platform:
        return int(platform)
    configured = (os.environ.get("MAILROOM_PORT") or str(default)).strip() or str(default)
    return int(configured)


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    port = listen_port(8001)
    host = os.environ.get("MAILROOM_HOST", "127.0.0.1")
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
