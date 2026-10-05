"""Server debug ring buffer — machine-readable request telemetry for agents.

Always records (cheap, capped); verbose stdout logging activates with
MAILROOM_DEBUG=1. Exposed via GET /api/debug/logs so a human or an automated
agent can read exactly what the API served without shell access.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("mailroom.debug")

MAX_EVENTS = 500


class DebugLog:
    """Thread-safe capped event log."""

    def __init__(self, max_events: int = MAX_EVENTS) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self.verbose = os.environ.get("MAILROOM_DEBUG", "").strip().lower() in ("1", "true", "yes")

    def record(self, kind: str, **fields: Any) -> None:
        event = {
            "t": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            **fields,
        }
        with self._lock:
            self._events.append(event)
        if self.verbose:
            log.info("debug %s %s", kind, fields)

    def snapshot(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        with self._lock:
            events = list(self._events)
        return events[-limit:] if limit else events


class DebugLogMiddleware:
    """Pure-ASGI request logger (method/path/status/duration per request)."""

    def __init__(self, app: Any, recorder: DebugLog) -> None:
        self.app = app
        self.recorder = recorder

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status_holder: dict[str, int] = {}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            self.recorder.record(
                "http",
                method=scope.get("method"),
                path=scope.get("path"),
                query=scope.get("query_string", b"").decode("utf-8", "replace")[:200],
                status=status_holder.get("status"),
                ms=round((time.perf_counter() - start) * 1000, 1),
                client=_client_tag((scope.get("client") or ("?",))[0]),
            )


_CLIENT_SALT = os.urandom(8).hex()


def _client_tag(addr: str) -> str:
    """Per-process pseudonym for a client address.

    /api/debug/logs is readable by anyone on the hosted edition; raw IPs
    leaked every visitor's address to every other visitor. The salted hash
    still groups one client's requests for debugging.
    """
    if not addr or addr == "?":
        return "?"
    return "c-" + hashlib.sha256(f"{_CLIENT_SALT}:{addr}".encode()).hexdigest()[:10]
