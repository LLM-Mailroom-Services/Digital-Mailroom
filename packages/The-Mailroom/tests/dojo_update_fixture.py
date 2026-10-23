"""Manual browser fixture, never live data or a deploy entry point.

Run from the source root with the existing development Python environment:
    python -m tests.dojo_update_fixture
Open http://127.0.0.1:8765/ or /live. No credentials, Langfuse, HF, or Dojo
engine are used. A loopback fake producer exercises the real urllib bridge.
POST /__fixture/{scenario} selects example state without reloading the UI.
The raw_hostile scenario deliberately bypasses the bridge to test DOM defense.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from mailroom_ui.pipeline_ops import DOJO_RELEASE_URL, fetch_pipeline_ops
from server.poller import PollHub

ROOT = Path(__file__).resolve().parent.parent
LABEL = "DMR-095 TEST FIXTURE — EXAMPLE ADVISORY DATA ONLY — NOT LIVE / NOT PUBLISHED — NO LANGFUSE TRACES"
SCENARIOS = ("available", "current", "absent", "stale", "unknown", "unavailable",
             "disabled", "hostile", "raw_hostile", "disconnected")
scenario = "available"
CHECKED_AT = int(time.time()) - 300


def example_update():
    data = {
        "status": "update_available", "installed_version": "0.23.1",
        "latest_version": "0.24.0", "checked_at": CHECKED_AT,
        "stale": False, "source": "cache", "error": None,
        "cache_persisted": True, "release_url": DOJO_RELEASE_URL,
    }
    if scenario == "current":
        data.update(status="up_to_date", installed_version="0.24.0")
    elif scenario == "stale":
        data.update(stale=True, checked_at=CHECKED_AT - 172800, cache_persisted=False)
    elif scenario in ("unknown", "unavailable", "disabled"):
        data.update(status=scenario, latest_version=None, checked_at=None, source="none")
    elif scenario in ("hostile", "raw_hostile"):
        data.update(installed_version='<script>window.__dojoInjected=1</script>',
                    latest_version='<img src=x onerror="window.__dojoInjected=2">',
                    error='<svg onload="window.__dojoInjected=3">',
                    release_url="javascript:window.__dojoInjected=4")
    return data


class Producer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/v1/health":
            self.send_error(404)
            return
        if scenario == "disconnected":
            self.send_error(503, "TEST fixture producer disconnected")
            return
        data = {"status": "ok", "checks": {"watcher": "live", "inbox_pending": 0}}
        if scenario != "absent":
            data["dojo_update"] = example_update()
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


app = FastAPI(title=LABEL)


@app.middleware("http")
async def no_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


def page(surface):
    html = (ROOT / surface / "index.html").read_text()
    banner = (f'<aside style="position:relative;z-index:99999;background:#ffec00;color:#111;'
              f'padding:12px;font:700 14px/1.5 monospace;flex:none" role="note">{LABEL}</aside>')
    return HTMLResponse(html.replace("<title>", "<title>TEST FIXTURE · ", 1)
                        .replace("<body>", '<body style="display:block">' + banner, 1))


@app.get("/")
def pixel():
    return page("web")


@app.get("/live")
def live():
    return page("hosted")


@app.post("/__fixture/{selected}")
def select(selected: str):
    global scenario
    if selected not in SCENARIOS:
        raise HTTPException(400, "Unknown TEST scenario")
    scenario = selected
    return {"fixture": LABEL, "scenario": scenario}


@app.get("/__fixture")
def state():
    return {"fixture": LABEL, "scenario": scenario, "scenarios": SCENARIOS}


@app.get("/api/health")
def health():
    return {"ok": True, "source": "TEST fixture transport only; no live Langfuse"}


@app.get("/api/meta")
def meta():
    return {"poll_interval_s": 1, "edition": "console", "version": "TEST",
            "doc_classes": {}, "ui": {"console": "/"}}


@app.get("/api/pipeline")
def ops():
    value = fetch_pipeline_ops()
    if scenario == "raw_hostile":
        value["dojo_update"] = example_update()
    return value


@app.get("/api/traces")
@app.get("/api/review-queue")
def no_trace_rows():
    return {"runs": [], "count": 0, "source": "TEST fixture — no trace data"}


@app.get("/api/sessions")
def no_sessions():
    return {"sessions": [], "count": 0}


@app.websocket("/ws")
async def snapshots(ws: WebSocket):
    await ws.accept()
    # Use the production snapshot envelope without starting a trace-source poller.
    hub = PollHub(None, interval=1, window=60, limit=1)
    try:
        while True:
            hub.pipeline_ops = await asyncio.to_thread(ops)
            await ws.send_json(hub._snapshot_message(stale=False))
            await asyncio.sleep(.25)
    except (WebSocketDisconnect, RuntimeError):
        pass


app.mount("/static", StaticFiles(directory=ROOT / "web"))
app.mount("/live/static", StaticFiles(directory=ROOT / "hosted"))


if __name__ == "__main__":
    # Deliberate process-local test config; no .env loading or persistent edits.
    producer = ThreadingHTTPServer(("127.0.0.1", 8766), Producer)
    threading.Thread(target=producer.serve_forever, daemon=True).start()
    os.environ["MAILROOM_PIPELINE_URL"] = "http://127.0.0.1:8766"
    os.environ["MAILROOM_PIPELINE_API_PREFIX"] = "/v1"
    os.environ.pop("MAILROOM_PIPELINE_TOKEN", None)
    os.environ.pop("MAILROOM_API_TOKEN", None)
    print(LABEL, flush=True)
    try:
        uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
    finally:
        producer.shutdown()
