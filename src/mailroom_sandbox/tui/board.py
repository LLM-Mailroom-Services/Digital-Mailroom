"""`sandbox board` — one persistent mailroom display for every beacon job.

Reads ``mailroom.beacon/v1`` heartbeats (see ``tui/beacon.py``) from the beacon root
and renders them as a mailroom-themed browser page (SSE, localhost) or a live
terminal TUI built from ``pretty_log`` primitives. The board holds no job state of
its own, so it survives job restarts and can be restarted without losing anything.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mailroom_sandbox.tui import pretty_log as pl
from mailroom_sandbox.tui.beacon import BEACON_VERSION, TERMINAL_STATES, beacon_root
from mailroom_sandbox.tui.web import THEME, ansi_to_html

STALE_S = 120.0
DEFAULT_PORT = 8767  # watch --web / sandbox dev own 8765
_ORDER = {"running": 0, "stalled": 1, "failed": 2, "done": 2}
_HOST = socket.gethostname()


# ── reading ────────────────────────────────────────────────────────────────────
def _pid_alive(pid: Any) -> bool:
    try:
        os.kill(int(pid), 0)
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError):
        return False
    return True


def _tail(path: Path, n: int) -> list[str]:
    if n <= 0 or not path.is_file():
        return []
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 64 * 1024))
            lines = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    return lines[-n:]


def status_of(job: dict[str, Any], *, now: float, stale_s: float) -> str:
    state = job.get("state")
    if state in TERMINAL_STATES:
        return state
    if now - float(job.get("updated_at") or 0) > stale_s:
        return "stalled"
    if job.get("host") == _HOST and job.get("pid") and not _pid_alive(job["pid"]):
        return "stalled"
    return "running"


def list_jobs(root: Path | None = None, *, stale_s: float = STALE_S, tail: int = 8) -> list[dict[str, Any]]:
    """Every readable v1 beacon under ``root`` with derived ``status``, ``pct``, ``log_tail``."""
    root = Path(root) if root is not None else beacon_root()
    if not root.is_dir():
        return []
    now = time.time()
    jobs: list[dict[str, Any]] = []
    for path in root.glob("*.json"):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(job, dict) or job.get("schema") != BEACON_VERSION or not job.get("job_id"):
            continue
        job["status"] = status_of(job, now=now, stale_s=stale_s)
        done, total = job.get("done") or 0, job.get("total")
        job["pct"] = round(100.0 * done / total, 1) if total else None
        job["age_s"] = round(now - float(job.get("updated_at") or now), 1)
        job["log_tail"] = _tail(root / f"{job['job_id']}.log", tail)
        jobs.append(job)
    jobs.sort(key=lambda j: (_ORDER.get(j["status"], 3), -float(j.get("updated_at") or 0)))
    return jobs


# ── terminal TUI ───────────────────────────────────────────────────────────────
def _bar(done: int, total: int | None, width: int) -> str:
    if not total:
        return "·" * width
    fill = int(width * min(1.0, done / total))
    return "█" * fill + "░" * (width - fill)


def board_header(n: int, *, width: int, on: bool) -> list[str]:
    p = pl.palette(on)
    inner = width - 2
    mark = pl._wordmark_lines(inner=inner, on=on, compact=width < 90)
    sub = f"DIGITAL MAILROOM  ·  job board  ·  {n} job{'s' if n != 1 else ''}"
    route = "BEACON → BOARD → BROWSER + TERMINAL"
    if on:
        sub = p["brand"]("DIGITAL MAILROOM") + p["dim"]("  ·  ") + p["snow"]("job board") + p["dim"]("  ·  ") + p["gold"](f"{n} job{'s' if n != 1 else ''}")
        route = p["teal"](route)
    top, bot = pl.DTL + pl.DH * inner + pl.DTR, pl.DBL + pl.DH * inner + pl.DBR
    rows = [p["frame"](top) if on else top]
    rows += [pl._centered_row(line, width=width, on=on) for line in mark]
    rows += [pl._panel_row(sub, on=on, width=width), pl._panel_row(route, on=on, width=width)]
    rows.append(p["frame"](bot) if on else bot)
    return rows


def render_board(jobs: list[dict[str, Any]], *, width: int = 100, on: bool = False) -> str:
    width = max(60, min(int(width), pl.MAX_W))
    p = pl.palette(on)
    out = board_header(len(jobs), width=width, on=on)
    if not jobs:
        hint = [
            "no jobs yet — a long job publishes one line per step:",
            "  from mailroom_sandbox.tui.beacon import Beacon",
            "  with Beacon(job_id, package=...) as b: b.update(done=i, total=n)",
            f"beacon root: {beacon_root()}",
        ]
        out.append(pl._box("IN-TRAY", [p["dim"](h) if on else h for h in hint], width=width, on=on))
        return "\n".join(out)
    tone = {"running": "cyan", "stalled": "gold", "failed": "warn", "done": "teal"}
    mw = width - 4
    for j in jobs:
        status = j["status"].upper()
        done, total = int(j.get("done") or 0), j.get("total")
        count = f"{done}/{total}" if total else f"{done}"
        bar = _bar(done, total, max(10, mw - len(count) - 4))
        lines = [
            pl._metric("package", str(j.get("package")), total_w=mw, on=on),
            pl._metric("phase", f"{j.get('phase')} · {status}", total_w=mw, on=on),
            (p[tone.get(j["status"], "dim")](bar) if on else bar) + f"  {count}",
            pl._metric("sorted", f"ok {j.get('ok', 0)} · errors {j.get('errors', 0)} · updated {j['age_s']:.0f}s ago", total_w=mw, on=on),
        ]
        for k, v in list((j.get("metrics") or {}).items())[:4]:
            lines.append(pl._metric(str(k)[:12], str(v)[: mw - 14], total_w=mw, on=on))
        lines += [(p["dim"](t[: mw]) if on else t[: mw]) for t in j.get("log_tail", [])[-3:]]
        out.append(pl._box(f"{status} · {j.get('title') or j['job_id']}", lines, width=width, on=on))
    return "\n".join(out)


def run_board_tui(*, root: Path | None, stale_s: float, interval: float, once: bool) -> int:
    if once:
        sys.stdout.write(render_board(list_jobs(root, stale_s=stale_s), width=shutil.get_terminal_size((100, 40)).columns, on=pl.use_color(sys.stdout)) + "\n")
        return 0
    sys.stdout.write(pl.ALT_ENTER + pl.HIDE_CURSOR)
    try:
        while True:
            frame = render_board(list_jobs(root, stale_s=stale_s), width=shutil.get_terminal_size((100, 40)).columns, on=pl.use_color(sys.stdout))
            sys.stdout.write(pl.CURSOR_HOME + pl.CLEAR_SCREEN + frame + "\n")
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        return 0
    finally:
        sys.stdout.write(pl.SHOW_CURSOR + pl.ALT_LEAVE)
        sys.stdout.flush()


# ── browser ────────────────────────────────────────────────────────────────────
def board_page() -> bytes:
    tokens = "; ".join(f"--{k}: {v}" for k, v in THEME.items())
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>THE MAILROOM · job board</title>
<style>
:root {{ {tokens}; --frame: linear-gradient(135deg, var(--blue), var(--teal)); }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; min-height: 100vh; background: var(--navy); color: var(--snow);
  font: 13px/1.45 ui-monospace, "IBM Plex Mono", Menlo, monospace; }}
.wrap {{ max-width: 1100px; margin: 0 auto; padding: 16px; }}
.frame {{ border: 3px double var(--cyan); border-radius: 4px; padding: 2px; background: var(--frame); }}
.inner {{ background: #071a2e; padding: 16px 18px; border-radius: 2px; }}
.hero {{ margin: 0 0 10px; white-space: pre; overflow-x: auto; line-height: 1.15;
  font-size: min(12px, calc((100vw - 84px) / 60)); }}
#hero-compact {{ display: none; font-size: min(12px, calc((100vw - 84px) / 36)); }}
@media (max-width: 800px) {{ #hero {{ display: none; }} #hero-compact {{ display: block; }} }}
.bar-top {{ display: flex; flex-wrap: wrap; gap: 8px 16px; padding: 8px 10px; margin: 12px 0;
  background: rgba(36,86,214,0.25); border: 1px solid var(--teal); border-radius: 4px; font-size: 12px; }}
.bar-top .k {{ color: var(--muted); }}
.cards {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
@media (max-width: 800px) {{ .cards {{ grid-template-columns: 1fr; }} }}
.card {{ border: 1px solid var(--teal); border-radius: 6px; overflow: hidden; }}
.card h2 {{ margin: 0; padding: 6px 10px; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
  background: rgba(14,116,144,0.35); color: var(--cyan); display: flex; justify-content: space-between; gap: 8px; }}
.card .body {{ padding: 10px 12px; }}
.card.stalled {{ border-color: var(--gold); }} .card.stalled h2 {{ color: var(--gold); }}
.card.failed {{ border-color: var(--gold); }} .card.failed h2 {{ color: var(--gold); background: rgba(245,196,69,0.15); }}
.card.done {{ opacity: 0.8; }} .card.done h2 {{ color: var(--teal); }}
.metric {{ display: flex; justify-content: space-between; gap: 12px; padding: 2px 0; }}
.metric .k {{ color: var(--muted); }} .metric .v {{ text-align: right; overflow-wrap: anywhere; min-width: 0; }}
.prog {{ height: 10px; background: #050f1a; border: 1px solid var(--teal); border-radius: 3px; margin: 6px 0; }}
.prog > div {{ height: 100%; background: var(--cyan); }}
.card.stalled .prog > div, .card.failed .prog > div {{ background: var(--gold); }}
.log {{ margin-top: 6px; color: var(--muted); font-size: 11px; white-space: pre-wrap; word-break: break-all; }}
.empty {{ color: var(--cream); padding: 12px; border: 1px dashed var(--teal); border-radius: 6px; }}
.err {{ background: var(--gold); color: #1a0505; padding: 8px; border-radius: 4px; margin: 8px 0; }}
footer {{ margin-top: 16px; font-size: 11px; color: var(--muted); text-align: center; }}
</style></head><body><div class="wrap"><div class="frame"><div class="inner">
<pre class="hero" id="hero">(o,o) THE MAILROOM</pre>
<pre class="hero" id="hero-compact">(o,o) THE MAILROOM</pre>
<div id="err" class="err" hidden></div>
<div class="bar-top"><span><span class="k">jobs</span> <span id="n">—</span></span>
<span><span class="k">live</span> <span id="live">—</span></span><span><span class="k">stalled</span> <span id="stalled">—</span></span>
<span><span class="k">root</span> <span id="root">—</span></span></div>
<div class="cards" id="cards"></div>
</div></div><footer>localhost-only · SSE live · jobs publish via mailroom.beacon/v1</footer></div>
<script>
function esc(s) {{ return String(s ?? "—").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }}
function metric(k, v) {{ return `<div class="metric"><span class="k">${{esc(k)}}</span><span class="v">${{esc(v)}}</span></div>`; }}
function card(j) {{
  const count = j.total ? `${{j.done}}/${{j.total}}` : `${{j.done}}`;
  const pct = j.pct == null ? 0 : j.pct;
  const extra = Object.entries(j.metrics || {{}}).slice(0, 4).map(([k, v]) => metric(k, v)).join("");
  const log = (j.log_tail || []).slice(-3).map(l => esc(l)).join("\\n");
  return `<section class="card ${{esc(j.status)}}"><h2><span>${{esc(j.title)}}</span><span>${{esc(j.status)}}</span></h2>
<div class="body">${{metric("package", j.package)}}${{metric("phase", j.phase)}}
<div class="prog"><div style="width:${{pct}}%"></div></div>${{metric("progress", count + (j.pct == null ? "" : ` · ${{j.pct}}%`))}}
${{metric("sorted", `ok ${{j.ok}} · errors ${{j.errors}} · ${{Math.round(j.age_s)}}s ago`)}}${{extra}}
${{log ? `<div class="log">${{log}}</div>` : ""}}</div></section>`;
}}
function render(d) {{
  document.getElementById("err").hidden = true;
  if (d.hero_html) document.getElementById("hero").innerHTML = d.hero_html;
  if (d.hero_compact_html) document.getElementById("hero-compact").innerHTML = d.hero_compact_html;
  const jobs = d.jobs || [];
  document.getElementById("n").textContent = jobs.length;
  document.getElementById("live").textContent = jobs.filter(j => j.status === "running").length;
  document.getElementById("stalled").textContent = jobs.filter(j => j.status === "stalled").length;
  document.getElementById("root").textContent = d.root || "";
  document.getElementById("cards").innerHTML = jobs.length ? jobs.map(card).join("")
    : `<div class="empty">no jobs yet — long jobs publish with Beacon(job_id, package=...).update(done=i, total=n)</div>`;
}}
const es = new EventSource("/api/jobs/stream");
es.onmessage = ev => {{ try {{ render(JSON.parse(ev.data)); }} catch (e) {{ console.error(e); }} }};
es.onerror = () => {{ const e = document.getElementById("err"); e.hidden = false; e.textContent = "SSE disconnected — retrying…"; }};
</script></body></html>"""
    return page.encode("utf-8")


def board_hero(width: int) -> str:
    """Owl + amber wordmark in its double frame (job counts live in the page's own bar)."""
    rows = board_header(0, width=width, on=True)
    return ansi_to_html("\n".join(rows[:-3] + rows[-1:]))


def board_payload(root: Path, stale_s: float, heroes: dict[str, str]) -> dict[str, Any]:
    return {"root": str(root), "jobs": list_jobs(root, stale_s=stale_s), **heroes}


def make_board_server(host: str, port: int, *, root: Path | None, stale_s: float = STALE_S, interval: float = 1.0) -> ThreadingHTTPServer:
    root = Path(root) if root is not None else beacon_root()
    stop = threading.Event()
    heroes = {"hero_html": board_hero(100), "hero_compact_html": board_hero(60)}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send(self, code: int, ctype: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                return self._send(200, "text/html; charset=utf-8", board_page())
            if path == "/api/jobs":
                return self._send(200, "application/json", json.dumps(board_payload(root, stale_s, heroes)).encode())
            if path == "/api/jobs/stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                last = None
                try:
                    while not stop.is_set():
                        body = json.dumps(board_payload(root, stale_s, heroes), separators=(",", ":"))
                        if body != last:
                            self.wfile.write(f"data: {body}\n\n".encode())
                            self.wfile.flush()
                            last = body
                        stop.wait(interval)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return None
            return self._send(404, "text/plain", b"not found")

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.board_stop = stop  # type: ignore[attr-defined]
    return httpd


class DemoJobs:
    """Synthetic beacon writers for `sandbox board --demo` (dev/browser testing; no Modal)."""

    def __init__(self, root: Path, *, n: int = 24) -> None:
        from mailroom_sandbox.tui.beacon import Beacon

        self.n = n
        self._i = 0
        self.sorter = Beacon("demo-sorter", package="local-mailroom-sandbox", title="demo · sorter n=%d" % n, root=root, total=n)
        self.ab = Beacon("demo-gepa-ab", package="eval-environment", title="demo · v2 prompt A/B", root=root, total=n // 2)

    def step(self) -> None:
        self._i += 1
        i = self._i
        if i <= self.n:
            ok = i % 7 != 0
            self.sorter.update(phase="SORTING", done=i, ok=i - i // 7, errors=i // 7, metrics={"p50_s": round(5 + (i % 5) * 0.4, 1)})
            self.sorter.log(f"DOC-demo-{i:03d} {'ok' if ok else 'LengthFinishReasonError'}")
        elif i == self.n + 1:
            self.sorter.finish("done", metrics={"accuracy": 0.895})
        half = self.n // 2
        if i <= half:
            self.ab.update(phase="SCORING", done=i, ok=i, metrics={"delta_vs_prod": round(0.04 - 0.002 * (i % 3), 3)})
        elif i == half + 1:
            self.ab.finish("done")
        if i > self.n + 20:  # finished jobs stay on the board as history, then loop
            self.__init__(self.sorter.root, n=self.n)


def serve_board(
    *,
    root: Path | None,
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    open_browser: bool | None = None,
    stale_s: float = STALE_S,
    interval: float = 1.0,
    demo: bool = False,
) -> int:
    import webbrowser

    from mailroom_sandbox.tui.web import browser_url, should_open_browser

    root = Path(root) if root is not None else beacon_root()
    httpd = make_board_server(host, port, root=root, stale_s=stale_s, interval=interval)
    if demo:
        writer = DemoJobs(root)

        def _loop() -> None:
            while not httpd.board_stop.wait(interval):  # type: ignore[attr-defined]
                writer.step()

        threading.Thread(target=_loop, daemon=True).start()
    url = browser_url(*httpd.server_address[:2])
    print(f"mailroom job board at {url} (beacon root {root})", file=sys.stderr)
    if open_browser if open_browser is not None else should_open_browser():
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.board_stop.set()  # type: ignore[attr-defined]
        httpd.shutdown()
        httpd.server_close()
    return 0
