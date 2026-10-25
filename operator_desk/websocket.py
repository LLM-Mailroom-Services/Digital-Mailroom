"""Operator-desk WebSocket for filesystem / observer events.

Distinct from the live-floor snapshot socket at ``/ws``. Clients subscribe
with ``{"action": "subscribe", "matter_id": "..."}``.
"""

from __future__ import annotations

import json
import logging
from typing import Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .auth import UserProfile, auth_required, decode_token

log = logging.getLogger("mailroom.operator.ws")

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self.matter_subscriptions: dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        for conns in self.matter_subscriptions.values():
            conns.discard(websocket)

    def subscribe_matter(self, websocket: WebSocket, matter_id: str) -> None:
        self.matter_subscriptions.setdefault(matter_id, set()).add(websocket)

    async def broadcast(self, message: dict) -> None:
        dead: Set[WebSocket] = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead.add(connection)
        for conn in dead:
            self.disconnect(conn)

    async def broadcast_to_matter(self, matter_id: str, message: dict) -> None:
        conns = self.matter_subscriptions.get(matter_id)
        if not conns:
            return
        dead: Set[WebSocket] = set()
        for connection in list(conns):
            try:
                await connection.send_json(message)
            except Exception:
                dead.add(connection)
        for conn in dead:
            self.disconnect(conn)


manager = ConnectionManager()


def _ws_user(websocket: WebSocket) -> Optional[UserProfile]:
    token = websocket.query_params.get("token") or ""
    if not token:
        auth = websocket.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    if not token:
        return None if auth_required() else UserProfile(username="anonymous", role="viewer")
    try:
        return decode_token(token)
    except Exception:
        return None


@router.websocket("/ws/pipeline")
async def pipeline_websocket(websocket: WebSocket):
    user = _ws_user(websocket)
    if user is None:
        await websocket.close(code=4401)
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("action") == "subscribe" and msg.get("matter_id"):
                matter_id = str(msg["matter_id"])
                manager.subscribe_matter(websocket, matter_id)
                await websocket.send_json({"type": "subscribed", "matter_id": matter_id})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


async def publish_event(event_type: str, payload: dict) -> None:
    body = dict(payload)
    body["type"] = event_type
    await manager.broadcast(body)


async def publish_matter_event(matter_id: str, event_type: str, payload: dict) -> None:
    body = dict(payload)
    body["type"] = event_type
    await manager.broadcast_to_matter(matter_id, body)
