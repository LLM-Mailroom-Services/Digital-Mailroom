"""Mount the operator desk on the visualizer FastAPI app."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse

from .archive import router as archive_router
from .auth import router as auth_router
from .db import db_path, ensure_bins, migrate
from .observer import observer_enabled, start_observer
from .ops import router as ops_router, set_runs_provider
from .websocket import router as ws_router

log = logging.getLogger("mailroom.operator")

OPERATOR_ENDPOINTS = [
    {"method": "POST", "path": "/v1/auth/login", "desc": "operator desk JWT login"},
    {"method": "GET", "path": "/v1/auth/me", "desc": "operator profile (Bearer)"},
    {"method": "POST", "path": "/v1/auth/logout", "desc": "discard client JWT"},
    {"method": "GET", "path": "/v1/archive/list", "desc": "archived files (operator desk)"},
    {"method": "GET", "path": "/v1/ops/health", "desc": "operator desk liveness"},
    {"method": "GET", "path": "/v1/ops/status", "desc": "ops snapshot from Langfuse runs"},
    {"method": "GET", "path": "/v1/ops/throughput", "desc": "hourly archived/failed counts (Langfuse)"},
    {"method": "GET", "path": "/v1/ops/distribution", "desc": "doc-type mix from Langfuse runs"},
    {"method": "POST", "path": "/v1/ops/events", "desc": "ingest observer events into /ws/pipeline"},
    {"method": "WS", "path": "/ws/pipeline", "desc": "operator bin-move events"},
    {"method": "GET", "path": "/desk", "desc": "optional React operator desk (build ui/ to enable)"},
]


def react_ui_dist() -> Path:
    explicit = os.environ.get("MAILROOM_UI_DIST", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    return Path(__file__).resolve().parent.parent / "ui" / "dist"


def react_ui_available() -> bool:
    return (react_ui_dist() / "index.html").is_file()


def operator_status() -> dict[str, Any]:
    from .auth import auth_required
    from .websocket import manager

    return {
        "module": "operator_desk",
        "auth": auth_required(),
        "observer": observer_enabled(),
        "db": str(db_path()),
        "pipeline_ws_clients": len(manager.active_connections),
        "react_ui": react_ui_available(),
    }


def mount_operator(
    app: FastAPI,
    *,
    runs_provider: Optional[Callable[[], list]] = None,
) -> None:
    """Attach ``/v1/auth``, ``/v1/archive``, ``/v1/ops``, ``/ws/pipeline``."""
    migrate()
    ensure_bins()
    set_runs_provider(runs_provider)
    app.include_router(auth_router)
    app.include_router(archive_router)
    app.include_router(ops_router)
    app.include_router(ws_router)
    if react_ui_available():
        dist = react_ui_dist().resolve()

        @app.get("/desk", include_in_schema=False)
        @app.get("/desk/", include_in_schema=False)
        @app.get("/desk/{spa_path:path}", include_in_schema=False)
        def optional_react_desk(spa_path: str = ""):
            index = dist / "index.html"
            if not spa_path or spa_path.endswith("/"):
                return FileResponse(index)
            target = (dist / spa_path).resolve()
            try:
                target.relative_to(dist)
            except ValueError:
                return FileResponse(index)
            if target.is_file():
                return FileResponse(target)
            return FileResponse(index)

        log.info("optional React desk mounted at /desk (%s)", dist)
    app.state.operator = operator_status()
    log.info("operator desk mounted (db=%s)", db_path())


def start_operator_observer(loop=None):
    if not observer_enabled():
        return None
    return start_observer(loop=loop)
