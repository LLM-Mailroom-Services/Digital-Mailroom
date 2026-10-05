"""Browser-hosted Tray TUI (`sandbox watch --web`).

Stdlib HTTP + SSE; reuses ``mailroom_sandbox.watch.compose_watch_state``.
Binds ``127.0.0.1`` by default — not a public dashboard (see operator docs).
"""

from __future__ import annotations

import html as _html
import json
import os
import re
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.tui import pretty_log as pl
from mailroom_sandbox.watch import _LOG_ROLE, LogBuffer, _header, _stream_logs, compose_watch_state

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


# Mailroom brand — derived from pretty_log so the browser and terminal never drift.
THEME = {
    "blue": _hex(pl.BLUE),
    "teal": _hex(pl.TEAL),
    "cyan": _hex(pl.CYAN),
    "navy": _hex(pl.NAVY),
    "gold": _hex(pl.GOLD),
    "cream": _hex(pl.CREAM),
    "snow": _hex(pl.SNOW),
    "muted": _hex(pl.MUTED),
    "sky": _hex(pl.SKY),
    "amber": _hex(pl.AMBER_FACE),
    "extrude": _hex(pl.AMBER_EXTRUDE),
}
# terminal palette role → THEME token (pretty_log: warn=gold, mint=sky, dim=faint)
_ROLE_TOKEN = {"warn": "gold", "gold": "gold", "cyan": "cyan", "mint": "sky", "teal": "teal", "dim": "muted"}

# lifecycle phase → THEME token (mirrors watch._LIFECYCLE_ROLE palette roles)
_STATE_TOKEN = {
    "FAILED": "gold",
    "COMPLETE": "teal",
    "STOPPED": "teal",
    "TEARDOWN": "teal",
    "PAUSED": "gold",
    "REMOTE": "cyan",
    "SORTING": "gold",
    "COLD BOOT": "gold",
    "DEPLOYING": "gold",
    "PREFLIGHT": "cyan",
    "QUEUED": "muted",
}

_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")


def ansi_to_html(text: str) -> str:
    """Truecolor SGR (pretty_log output) → escaped HTML spans; other codes dropped."""
    out: list[str] = []
    open_span = False
    pos = 0
    for m in _SGR_RE.finditer(text):
        out.append(_html.escape(text[pos:m.start()], quote=False))
        pos = m.end()
        codes = [int(c) for c in m.group(1).split(";") if c] or [0]
        style: list[str] = []
        i = 0
        while i < len(codes):
            c = codes[i]
            if c in (38, 48) and i + 4 < len(codes) and codes[i + 1] == 2:
                prop = "color" if c == 38 else "background"
                style.append(f"{prop}:{_hex(tuple(codes[i + 2:i + 5]))}")
                i += 5
                continue
            if c == 1:
                style.append("font-weight:bold")
            elif c == 2:
                style.append("opacity:0.6")
            i += 1
        if open_span:
            out.append("</span>")
            open_span = False
        if style:
            # color first, then weight — stable order for callers/tests
            style.sort(key=lambda d: (not d.startswith(("color", "background")), d))
            out.append(f'<span style="{";".join(style)}">')
            open_span = True
    out.append(_html.escape(text[pos:], quote=False))
    if open_span:
        out.append("</span>")
    return "".join(out)


def should_open_browser(*, stream: Any = None) -> bool:
    if os.environ.get("NO_BROWSER", "").strip().lower() in ("1", "true", "yes"):
        return False
    fh = stream or sys.stderr
    return hasattr(fh, "isatty") and bool(fh.isatty())


def browser_url(host: str, port: int) -> str:
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    return f"http://{display_host}:{port}/"


class WatchWebSession:
    """Shared state for SSE clients and the background refresh loop."""

    def __init__(
        self,
        *,
        resolve: Callable[[], tuple[RunStore, str]],
        ledger: Path | None,
        cap_usd: float,
        times_dir: Path | None,
        sand032_root: Path | None = None,
        log_path: Path | None = None,
        serving_dir: Path,
        interval: float,
        follow_logs: bool,
        tick: Callable[[LogBuffer], None] | None = None,
    ) -> None:
        self.resolve = resolve
        self.tick = tick  # dev-server hook: advance a synthetic run before each refresh
        self.ledger = ledger
        self.cap_usd = cap_usd
        self.times_dir = times_dir
        self.sand032_root = sand032_root
        self.serving_dir = serving_dir
        self.interval = interval
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {"ok": False, "error": "initializing"}
        self._version = 0
        self._stop = threading.Event()
        self._log_path_override = log_path
        self.sink = LogBuffer(None)
        self._started = time.time()
        self._last_run_id: str | None = None
        self._boot_mark: dict[str, int] = {}
        self._log_stop = threading.Event()
        if follow_logs:
            from mailroom_sandbox.watch import _watch_paths, start_log_streams

            store, app = resolve()
            _td, resolved_log = _watch_paths(
                store, times_dir=times_dir, sand032_root=sand032_root, log_path=log_path
            )
            self.sink = LogBuffer(resolved_log)
            start_log_streams(store, app, self.sink, self._log_stop)

    def refresh(self) -> dict[str, Any]:
        if self.tick is not None:
            self.tick(self.sink)
        from mailroom_sandbox.watch import _watch_paths

        store, app = self.resolve()
        rid = store.run_id
        if self._last_run_id != rid:
            self._started = time.time()
            self._boot_mark = {}
            self._last_run_id = rid
        frame_times_dir, _ = _watch_paths(
            store,
            times_dir=self.times_dir,
            sand032_root=self.sand032_root,
            log_path=None,
        )
        state = compose_watch_state(
            store=store,
            app=app,
            sink=self.sink,
            ledger=self.ledger,
            cap_usd=self.cap_usd,
            times_dir=frame_times_dir,
            serving_dir=self.serving_dir,
            started=self._started,
            boot_mark=self._boot_mark,
            width=100,
            blink=int(time.time()) % 7 == 0,
        )
        layout = state.get("layout") or {}
        rid = state["snapshot"]["run_id"]
        hero_kw = dict(
            subtitle=layout.get("subtitle"),
            route_label=layout.get("route_label"),
            brand=str(layout.get("brand") or "DIGITAL MAILROOM"),
        )
        state["hero_html"] = ansi_to_html("\n".join(_header(rid, width=100, on=True, **hero_kw)))
        state["hero_compact_html"] = ansi_to_html(
            "\n".join(_header(rid, width=60, on=True, **hero_kw))
        )
        state["ok"] = True
        with self._lock:
            self._version += 1
            state["ui_version"] = self._version
            self._state = state
        return state

    def snapshot(self) -> tuple[int, dict[str, Any]]:
        with self._lock:
            return self._version, dict(self._state)

    def run_refresh_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.refresh()
            except Exception as exc:  # noqa: BLE001 — surface to UI
                with self._lock:
                    self._state = {"ok": False, "error": str(exc)}
                    self._version += 1
            self._stop.wait(self.interval)

    def stop(self) -> None:
        self._stop.set()
        self._log_stop.set()


def _theme_css() -> tuple[str, str]:
    tokens = "; ".join(f"--{k}: {v}" for k, v in THEME.items())
    roles = "\n".join(
        f".log-line.{role} {{ color: var(--{_ROLE_TOKEN.get(tone, 'muted')}); }}" for role, tone in _LOG_ROLE.items()
    )
    states = "\n".join(
        f".stage-{phase.lower().replace(' ', '-')} {{ color: var(--{token}); }}"
        for phase, token in _STATE_TOKEN.items()
    )
    return tokens, roles + "\n" + states


def _html_page() -> bytes:
    tokens, roles = _theme_css()
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tray TUI · THE MAILROOM · live watch</title>
<style>
:root {{
  {tokens};
  --frame: linear-gradient(135deg, var(--blue), var(--teal));
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; min-height: 100vh; font-family: ui-monospace, "IBM Plex Mono", Menlo, monospace;
  background: var(--navy); color: var(--snow); font-size: 13px; line-height: 1.45;
}}
.wrap {{ max-width: 1100px; margin: 0 auto; padding: 16px; }}
.frame {{
  border: 3px double var(--cyan); border-radius: 4px; padding: 2px;
  background: var(--frame);
}}
.inner {{ background: #071a2e; padding: 16px 18px; border-radius: 2px; }}
header h1 {{
  margin: 0 0 4px; font-size: 22px; letter-spacing: 0.08em;
  color: var(--gold); text-shadow: 0 1px 0 #8a5a12;
}}
header .sub {{ color: var(--cream); font-size: 12px; margin-bottom: 8px; }}
header .route {{ color: var(--cyan); font-size: 11px; letter-spacing: 0.06em; }}
.status {{
  display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center;
  padding: 8px 10px; margin: 12px 0; background: rgba(36,86,214,0.25);
  border: 1px solid var(--teal); border-radius: 4px; font-size: 12px;
}}
.status .stage {{ color: var(--gold); font-weight: 600; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
@media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
.panel {{
  border: 1px solid var(--teal); border-radius: 6px; overflow: hidden;
}}
.panel h2 {{
  margin: 0; padding: 6px 10px; font-size: 11px; letter-spacing: 0.1em;
  background: rgba(14,116,144,0.35); color: var(--cyan); text-transform: uppercase;
}}
.panel .body {{ padding: 10px 12px; }}
.metric {{ display: flex; justify-content: space-between; gap: 12px; padding: 2px 0; }}
.metric .k {{ color: var(--muted); }}
.metric .v {{ color: var(--snow); text-align: right; overflow-wrap: anywhere; min-width: 0; }}
.bar {{
  font-family: inherit; letter-spacing: 1px; color: var(--cyan);
  margin: 6px 0; white-space: nowrap; overflow: hidden;
}}
.lifecycle {{
  margin: 12px 0; padding: 10px 12px; border-left: 3px solid var(--gold);
  background: rgba(245,196,69,0.08); color: var(--cream);
}}
.lifecycle.live {{ animation: lifecycle-pulse 2.2s ease-in-out infinite; }}
@keyframes lifecycle-pulse {{ 50% {{ border-left-color: var(--cyan); opacity: 0.92; }} }}
.route-lines {{ white-space: pre-wrap; color: var(--muted); font-size: 11px; line-height: 1.5; }}
.log {{
  margin-top: 12px; max-height: 280px; overflow-y: auto;
  border: 1px solid var(--teal); border-radius: 6px; background: #050f1a;
}}
.log h2 {{ position: sticky; top: 0; }}
.log-line {{ padding: 2px 10px; border-bottom: 1px solid rgba(14,116,144,0.2); word-break: break-all; }}
.log-line .src {{ color: var(--muted); opacity: 0.7; font-size: 10px; text-transform: uppercase; margin-right: 6px; }}
{roles}
.log-line.error {{ font-weight: 600; }}
.log-line.dim {{ color: var(--muted); opacity: 0.7; }}
#hero {{ font-size: min(12px, calc((100vw - 84px) / 60)); }}
#hero-compact {{ display: none; font-size: min(12px, calc((100vw - 84px) / 36)); }}
@media (max-width: 800px) {{ #hero {{ display: none; }} #hero-compact {{ display: block; }} }}
.hero {{
  margin: 0 0 10px; line-height: 1.15; font-family: ui-monospace, "IBM Plex Mono", Menlo, monospace;
  white-space: pre; overflow-x: auto; color: var(--snow);
}}
.err-banner {{ background: var(--gold); color: #1a0505; padding: 10px; border-radius: 4px; margin-bottom: 12px; }}
.blink .stage {{ animation: pulse 1s ease-in-out infinite; }}
@keyframes pulse {{ 50% {{ opacity: 0.55; }} }}
footer {{ margin-top: 16px; font-size: 11px; color: var(--muted); text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="frame"><div class="inner">
    <header>
      <pre class="hero" id="hero" aria-label="THE MAILROOM">(o,o) THE MAILROOM</pre>
      <pre class="hero" id="hero-compact" aria-label="THE MAILROOM">(o,o) THE MAILROOM</pre>
      <div class="sub" id="brand-sub" hidden>DIGITAL MAILROOM</div>
      <div class="route" id="route-label" hidden>INBOX → SPECIALIST → REPORT</div>
    </header>
    <div id="error" class="err-banner" hidden></div>
    <div class="status" id="status-bar">
      <span class="stage" id="stage">—</span>
      <span id="ts">—</span>
      <span id="app-line">—</span>
    </div>
    <div class="lifecycle" id="lifecycle" hidden></div>
    <div class="route-lines" id="program-route" hidden></div>
    <div class="grid">
      <section class="panel">
        <h2 id="tray-heading">Tray TUI · In-tray</h2>
        <div class="body" id="intray"></div>
      </section>
      <section class="panel">
        <h2 id="postage-heading">Postage ($)</h2>
        <div class="body" id="postage"></div>
      </section>
    </div>
    <section class="panel log" id="scorecard-wrap" hidden>
      <h2 id="scorecard-heading">Scorecard</h2>
      <div class="body" id="scorecard"></div>
    </section>
    <section class="panel log">
      <h2 id="dispatch-heading">Dispatch log</h2>
      <div id="logs"></div>
    </section>
  </div></div>
  <footer id="footer-line">Tray TUI · localhost-only · SSE + poll · hard-refresh after a watch restart</footer>
</div>
<script>
const LOG_CLASS = {{ error: "error", warn: "warn", throughput: "throughput", kv: "kv", ready: "ready", plain: "plain" }};  // = watch._LOG_ROLE keys

function metric(k, v) {{
  return `<div class="metric"><span class="k">${{k}}</span><span class="v">${{esc(v)}}</span></div>`;
}}
function esc(s) {{
  return String(s ?? "—").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}}

function render(state) {{
  if (!state || (state.ok === false && !state.snapshot)) {{
    document.getElementById("error").hidden = false;
    document.getElementById("error").textContent = (state && state.error) || "unknown error";
    return;
  }}
  if (state.ok === false) {{
    document.getElementById("error").hidden = false;
    document.getElementById("error").textContent = state.error || "unknown error";
  }} else {{
    document.getElementById("error").hidden = true;
  }}
  if (state.hero_html) document.getElementById("hero").innerHTML = state.hero_html;
  if (state.hero_compact_html) document.getElementById("hero-compact").innerHTML = state.hero_compact_html;
  const s = state.snapshot || {{}};
  const sp = state.spend || {{}};
  const layout = state.layout || {{}};
  const panels = layout.panels || {{}};
  document.title = panels.window_title || "Tray TUI · THE MAILROOM · live watch";
  document.getElementById("brand-sub").hidden = false;
  document.getElementById("route-label").hidden = false;
  document.getElementById("brand-sub").textContent =
    (layout.brand || "DIGITAL MAILROOM") + "  ·  " + (state.subtitle || "") + "  ·  " + (s.run_id || "");
  document.getElementById("route-label").textContent = state.route_label || "";
  if (panels.tray) document.getElementById("tray-heading").textContent = panels.tray;
  if (panels.postage) document.getElementById("postage-heading").textContent = panels.postage;
  if (panels.dispatch) document.getElementById("dispatch-heading").textContent = panels.dispatch;
  if (panels.scorecard) document.getElementById("scorecard-heading").textContent = panels.scorecard;
  const bar = document.getElementById("status-bar");
  bar.classList.toggle("blink", !!state.blink && !!state.animate_lifecycle);
  const L = state.lifecycle || {{}};
  let phase = L.phase || state.stage || "—";
  let detail = L.detail || "";
  // In-flight docs are never COLD BOOT — first SSE frame used to stick here.
  if (s.state === "running" && (phase === "COLD BOOT" || phase === "DEPLOYING" || phase === "QUEUED")) {{
    phase = "SORTING";
    detail = detail && !/engine ready|container starting|loading weights/i.test(detail)
      ? detail
      : ((s.task || "specialist") + " in flight");
  }}
  const stageEl = document.getElementById("stage");
  stageEl.textContent = phase;
  stageEl.className = "stage-" + String(phase || "unknown").toLowerCase().replace(/\\s+/g, "-");
  document.getElementById("ts").textContent = state.ts || "";
  const watcher = state.watcher_label || ("Tray TUI watcher · app " + (state.app || "—"));
  document.getElementById("app-line").textContent = watcher;

  const life = document.getElementById("lifecycle");
  if (state.lifecycle || s.state === "running") {{
    life.hidden = false;
    life.classList.toggle("live", phase === "SORTING" || !!state.animate_lifecycle);
    const el = L.elapsed_s || 0;
    const tag = layout.stage || "";
    life.textContent = `▸${{phase}}◂  ${{detail}}  ·  ${{Math.floor(el/60)}}m${{String(el%60).padStart(2,"0")}}s` + (tag ? `  ·  ${{tag}}` : "");
  }} else {{ life.hidden = true; life.classList.remove("live"); }}

  const route = document.getElementById("program-route");
  if (state.route && state.route.length) {{
    route.hidden = false;
    route.textContent = state.route.join("\\n");
  }} else if (state.job_route && state.job_route.length) {{
    route.hidden = false;
    route.textContent = state.job_route.join("\\n");
  }} else route.hidden = true;

  const prog = state.progress || {{}};
  document.getElementById("intray").innerHTML =
    metric("run", s.run_id) +
    metric("specialist", s.task) +
    metric("fleet", `×${{s.replicas}} ${{s.gpu}} · ${{s.state}}`) +
    `<div class="bar">${{esc(prog.bar)}}  ${{prog.done}}/${{prog.total}}</div>` +
    metric("sorted", `delivered ${{s.ok}} · returned ${{s.errors}}`) +
    metric("postmark", `p50 ${{s.p50_s ?? "—"}}s · p95 ${{s.p95_s ?? "—"}}s`) +
    metric("score", s.mean_score) +
    (s.last_error ? `<div class="metric"><span class="k">last return</span><span class="v" style="color:var(--gold)">${{esc(s.last_error)}}</span></div>` : "");

  const pct = sp.pct_of_cap != null ? sp.pct_of_cap + "%" : "";
  const tokIn = Number(s.prompt_tokens ?? sp.prompt_tokens ?? 0);
  const tokOut = Number(s.completion_tokens ?? sp.completion_tokens ?? 0);
  document.getElementById("postage").innerHTML =
    metric("sorted", `delivered ${{s.ok ?? sp.ok ?? 0}} · returned ${{s.errors ?? sp.errors ?? 0}}`) +
    metric("docs", `${{prog.done ?? s.done ?? 0}}/${{prog.total ?? s.total ?? 0}}`) +
    metric("tokens", `${{tokIn}} in · ${{tokOut}} out`) +
    metric("ledger", "$" + Number(sp.spent_usd || 0).toFixed(4)) +
    metric("live run", "$" + Number(sp.live_usd || 0).toFixed(4)) +
    metric("total", `$${{Number(sp.total_usd || 0).toFixed(4)}} / $${{Number(sp.cap_usd || 0).toFixed(2)}}`) +
    `<div class="bar">${{esc(sp.bar || "")}}  ${{pct}}</div>` +
    metric("gate", `$${{Number(sp.gate_usd || 4.5).toFixed(2)}} projected-total stop`) +
    (sp.over_gate ? `<div class="metric"><span class="v" style="color:var(--gold)">⚠ OVER GATE</span></div>` : "");
  const foot = document.getElementById("footer-line");
  if (foot) {{
    foot.textContent = `Tray TUI · ${{s.run_id || "—"}} · ${{prog.done ?? 0}}/${{prog.total ?? 0}} · $${{Number(sp.total_usd || 0).toFixed(4)}} · v${{state.ui_version || "—"}}`;
  }}

  const sc = document.getElementById("scorecard-wrap");
  if (state.scorecard && state.scorecard.length) {{
    sc.hidden = false;
    document.getElementById("scorecard").innerHTML = state.scorecard.map(l => `<div>${{esc(l)}}</div>`).join("");
  }} else sc.hidden = true;

  const logs = document.getElementById("logs");
  const lines = state.logs || [];
  const dispatchName = (panels.dispatch || "Dispatch log").replace(/^Dispatch log · /, "");
  logs.innerHTML = lines.length
    ? lines.map(e => `<div class="log-line ${{LOG_CLASS[e.role] || "plain"}}"><span class="src">${{esc(e.source || "modal")}}</span> ${{esc(e.text)}}</div>`).join("")
    : `<div class="log-line dim">(waiting on ${{esc(dispatchName)}} · job events appear here)…</div>`;
  const pane = logs.parentElement;  // the .log panel owns overflow-y
  pane.scrollTop = pane.scrollHeight;
}}

function pullState() {{
  fetch("/api/state?t=" + Date.now(), {{ cache: "no-store" }})
    .then((r) => r.json())
    .then(render)
    .catch(() => {{}});
}}
pullState();
setInterval(pullState, 2000);
const es = new EventSource("/api/stream?t=" + Date.now());
es.onmessage = (ev) => {{
  try {{ render(JSON.parse(ev.data)); }} catch (e) {{ console.error(e); }}
}};
es.onerror = () => {{
  document.getElementById("error").hidden = false;
  document.getElementById("error").textContent = "SSE disconnected — polling /api/state…";
}};
</script>
</body>
</html>"""
    return page.encode("utf-8")


def make_handler(session: WatchWebSession) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return  # quiet localhost server

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                body = _html_page()
                self._send(200, "text/html; charset=utf-8", body)
                return
            if path == "/api/state":
                _, state = session.snapshot()
                self._send_json(state)
                return
            if path == "/api/stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.send_header("Connection", "keep-alive")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()
                last_ver = -1
                try:
                    while not session._stop.is_set():
                        ver, state = session.snapshot()
                        if ver != last_ver:
                            payload = json.dumps(state, separators=(",", ":"))
                            self.wfile.write(f"data: {payload}\n\n".encode())
                            self.wfile.flush()
                            last_ver = ver
                        session._stop.wait(session.interval)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            self._send(404, "text/plain", b"not found")

        def _send(self, code: int, ctype: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, obj: dict[str, Any]) -> None:
            self._send(200, "application/json", json.dumps(obj).encode())

    return Handler


def serve_watch_web(
    *,
    resolve: Callable[[], tuple[RunStore, str]],
    ledger: Path | None,
    cap_usd: float = 5.0,
    logs: bool = True,
    interval: float = 2.0,
    times_dir: Path | None = None,
    sand032_root: Path | None = None,
    log_path: Path | None = None,
    serving_dir: Path | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    open_browser: bool | None = None,
    tick: Callable[[LogBuffer], None] | None = None,
) -> int:
    from mailroom_sandbox.paths import reports_dir

    serving_dir = serving_dir or (reports_dir() / "serving")
    session = WatchWebSession(
        resolve=resolve,
        ledger=ledger,
        cap_usd=cap_usd,
        times_dir=times_dir,
        sand032_root=sand032_root,
        log_path=log_path,
        serving_dir=serving_dir,
        interval=interval,
        follow_logs=logs,
        tick=tick,
    )
    session.refresh()
    threading.Thread(target=session.run_refresh_loop, daemon=True).start()

    handler = make_handler(session)
    httpd = ThreadingHTTPServer((host, port), handler)
    bound_host, bound_port = httpd.server_address[0], httpd.server_address[1]
    url = browser_url(bound_host, bound_port)
    print(f"Tray TUI watch (browser) at {url}", file=sys.stderr)
    if open_browser if open_browser is not None else should_open_browser():
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        session.stop()
        httpd.shutdown()
        httpd.server_close()
    return 0
