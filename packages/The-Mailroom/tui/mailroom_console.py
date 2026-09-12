"""The-Mailroom TUI console — a typed-command REPL over the pipeline.

AgentLab-style banners, per-doc tables, corpus browsing, and constellation
repo access over the same display API the web UI serves (``/api/*`` on the
running server, ``MAILROOM_API_URL``), so every displayed value is still
Langfuse-derived; corpus views read the Hub through the canonical
``mailroom_ui.hf_corpus`` ladder.

The REPL: a persistent ``mailroom@floor:~$`` prompt at the bottom, output in
the scrollback above, a live status header on top.  Tab completes, arrows
recall history, Ctrl+L clears, Ctrl+C cancels the line.  Typed commands:

    help | man <cmd> | clear | history | date | echo | uname | neofetch
    floor                          live floor desk (q / quit to leave)
    review | sessions | metrics | inspect <trace> | debug | filter ...
    corpus ls|show|search|stats    browse Lucius-Morningstar/mailroom-dataset
    repos ls | repos <name> | open <name>   constellation browser

``--once --view floor|review|metrics|sessions|inspect|debug|corpus|repos``
renders a single frame for scripting.  ``--resolve`` / ``--source`` keep the
review workflow CLI (posted through the visualizer to the producer).
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import select
import sys
import termios
import threading
import time
import tty
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from typing import Any, Optional

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from tui import commands as cmds
from tui import views
from tui.corpus import CorpusClient
from tui.repos import all_repos, live_meta
from tui.views import (
    LAST_ERRORS,
    STAGE_ORDER,
    STAGE_STYLE,
    STATION_BY_STAGE,
    banner,
    corpus_detail_panels,
    corpus_stats_table,
    corpus_table,
    debug_panel,
    empty_hint,
    floor_table,
    inspect_panels,
    metrics_table,
    repo_panel,
    repos_table,
    review_table,
    runs_to_banners,
    sessions_table,
    status_header,
)

__all__ = [
    "LAST_ERRORS", "STAGE_ORDER", "STAGE_STYLE", "STATION_BY_STAGE",
    "banner", "debug_panel", "fetch_floor_runs", "fetch_list", "floor_table",
    "inspect_panels", "metrics_table", "post_json", "review_table",
    "runs_to_banners", "sessions_table", "run",
]

API_BASE = os.environ.get("MAILROOM_API_URL", "http://127.0.0.1:8001").rstrip("/")
POLL_INTERVAL = float(os.environ.get("MAILROOM_TUI_POLL", "3"))
# Same 7-day live window as the pixel console and Observatory HTTP clients.
WINDOW_S = int(os.environ.get("MAILROOM_RECENT_WINDOW", "604800"))


def _record_error(where: str, exc: BaseException) -> None:
    LAST_ERRORS.append(f"{where}: {type(exc).__name__}: {exc}")


def fetch(path: str, timeout: float = 15.0) -> Optional[dict]:
    url = f"{API_BASE}{path}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        _record_error(f"GET {path}", exc)
        try:
            LAST_ERRORS.append(f"GET {path} body: {exc.read().decode()[:300]}")
        except Exception:
            pass
        return None
    except Exception as exc:
        _record_error(f"GET {path}", exc)
        return None


def fetch_list(path: str) -> Optional[list[dict]]:
    """None = request failed (closed). [] = source reachable but empty."""
    data = fetch(path)
    if data is None:
        return None
    return data.get("runs") or []


def post_json(path: str, body: dict, timeout: float = 60.0) -> Optional[dict]:
    """POST JSON to the visualizer (review resolve). None on failure."""
    url = f"{API_BASE}{path}"
    payload = json.dumps(body).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        _record_error(f"POST {path}", exc)
        try:
            LAST_ERRORS.append(f"POST {path} body: {exc.read().decode()[:400]}")
        except Exception:
            pass
        return None
    except Exception as exc:
        _record_error(f"POST {path}", exc)
        return None


def fetch_snapshot() -> Optional[list[dict]]:
    """Full floor payloads via the same WebSocket snapshots the web floor
    uses. None = WS failed (caller should try HTTP)."""
    try:
        from websockets.sync.client import connect

        ws_url = API_BASE.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
        with connect(ws_url, open_timeout=8) as ws:
            msg = json.loads(ws.recv(timeout=8))
        if isinstance(msg, dict) and msg.get("type") == "snapshot":
            return msg.get("runs") or []
        LAST_ERRORS.append(f"WS {ws_url}: unexpected frame {type(msg).__name__}")
        return None
    except Exception as exc:
        _record_error("WS /ws", exc)
        return None


def fetch_floor_runs() -> Optional[list[dict]]:
    """None means the display API is unreachable — not an empty window."""
    snap = fetch_snapshot()
    if snap is not None:
        return snap
    return fetch_list(f"/api/traces?since={WINDOW_S}")


def probe_health() -> bool:
    h = fetch("/api/health")
    if h is None:
        return False
    return bool(h.get("ok") if h.get("ok") is not None else h.get("langfuse"))


# ---------------------------------------------------------------------------
# REPL line editor
# ---------------------------------------------------------------------------

class LineEditor:
    """Minimal raw-mode line editor: printable chars, backspace, Tab
    completion, arrows (history), Ctrl+L (clear), Ctrl+C (cancel)."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self.buf = ""
        self.history: list[str] = []
        self.history_idx: Optional[int] = None

    def text(self) -> str:
        return self.buf

    def handle(self, ch: str, pending: deque) -> bool:
        """Handle one key; True when the line was submitted (Enter)."""
        if ch == "\r" or ch == "\n":
            line = self.buf
            if line.strip():
                self.history.append(line)
            self.buf = ""
            self.history_idx = None
            return True
        if ch in ("\x7f", "\x08"):  # backspace
            self.buf = self.buf[:-1]
            return False
        if ch == "\x1b":  # ESC sequence (arrows / Esc)
            seq = ch
            while len(seq) < 3 and pending:
                seq += pending.popleft()
            if seq == "\x1b[A":  # up
                self._history_move(-1)
            elif seq == "\x1b[B":  # down
                self._history_move(1)
            else:  # bare Esc: cancel the line
                self.buf = ""
            return False
        if ch == "\t":
            self._complete()
            return False
        if ch in ("\x14", "\x0c"):  # Ctrl+L
            self.buf = ""
            return False
        if ch == "\x03":  # Ctrl+C — cancel the line
            self.buf = ""
            return False
        if ch.isprintable():
            self.buf += ch
        return False

    def _history_move(self, delta: int) -> None:
        if not self.history:
            return
        if self.history_idx is None:
            self.history_idx = len(self.history) - 1 if delta < 0 else len(self.history)
        else:
            self.history_idx = max(0, min(len(self.history), self.history_idx + delta))
        if 0 <= self.history_idx < len(self.history):
            self.buf = self.history[self.history_idx]
        elif self.history_idx >= len(self.history):
            self.history_idx = len(self.history)
            self.buf = ""

    def _complete(self) -> None:
        candidates = cmds.completion_candidates(_ctx, self.buf) if _ctx else []
        if not candidates:
            return
        prefix = self.buf.split()[-1] if self.buf.split() else ""
        matches = [c for c in candidates if c.startswith(prefix)] if prefix else candidates
        if not matches:
            return
        if len(matches) == 1:
            self._apply_completion(matches[0], prefix)
            return
        # common prefix among matches
        common = matches[0]
        for m in matches[1:]:
            while not m.startswith(common):
                common = common[:-1]
        if len(common) > len(prefix):
            self._apply_completion(common, prefix)

    def _apply_completion(self, candidate: str, prefix: str) -> None:
        head = self.buf[: len(self.buf) - len(prefix)]
        self.buf = head + candidate


_ctx: Optional[cmds.CommandContext] = None


def _key_reader(keys: "queue.Queue[str]") -> None:
    """Raw single-key reader (POSIX). Falls back to line input when the
    terminal is not usable."""
    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            while True:
                if select.select([sys.stdin], [], [], 0.2)[0]:
                    keys.put(sys.stdin.read(1))
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        while True:
            keys.put(sys.stdin.readline())


def _prompt_line(editor: LineEditor, desk: bool) -> Text:
    if desk:
        return Text("  [q]uit the floor desk — or type a command…", style="grey35")
    cursor = "█"
    return Text(f"mailroom@floor:~$ {editor.text()}{cursor}", style="bright_green")


def _dispatch(ctx: cmds.CommandContext, line: str, console: Console,
              live: Live) -> list[Any]:
    """Run a typed command; sentinels handled by the REPL loop."""
    results = cmds.run_command(ctx, line)
    out: list[Any] = []
    for result in results:
        if result is cmds.CLEAR:
            out.append(result)
        elif result is cmds.QUIT:
            out.append(result)
        elif result is cmds.DESK_FLOOR:
            out.append(result)
        else:
            out.append(result)
    return out


def render_repl_frame(ctx: cmds.CommandContext, editor: LineEditor,
                      scrollback: list[Any], desk: bool,
                      closed: bool, count: int) -> Group:
    if desk:
        filtered = cmds._print_filtered_runs(ctx)
        body = floor_table(filtered)
        lines = list(ctx.log)[-12:]
        log_panel = Panel(
            Group(*[Text(line, style="bright_cyan" if "***" in line else "grey70")
                    for line in lines]),
            title=f"LIVE LOG ({len(ctx.log)})", border_style="grey35")
        body = Group(body, log_panel)
    else:
        body = Group(*list(scrollback)[-40:])
    head = status_header(not closed, count, ctx.api_base, ctx.pipeline)
    return Group(head, body, _prompt_line(editor, desk))


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def _run_once(args: argparse.Namespace, console: Console) -> None:
    """Single-frame (scripting / CI) mode."""
    runs = fetch_floor_runs()
    log: deque[str] = deque()
    ctx = cmds.CommandContext()
    ctx.api_base = API_BASE
    ctx.window_s = WINDOW_S
    ctx.fetch = fetch
    ctx.fetch_list = fetch_list
    ctx.fetch_floor_runs = fetch_floor_runs
    ctx.corpus = CorpusClient()
    if args.view == "debug":
        bundle = fetch("/api/debug/bundle")
        if bundle:
            LAST_ERRORS.append(
                f"bundle health={bundle.get('health')} "
                f"logs={len(bundle.get('server_logs') or [])} "
                f"client_reports={len(bundle.get('client_reports') or [])}"
            )
    if runs is not None:
        ctx.runs = runs
        runs_to_banners({}, runs, log)
        ctx.pipeline = fetch("/api/pipeline") or {}
        if args.view == "floor":
            body = Group(floor_table(runs),
                         Panel(Group(*[Text(l, style="grey70") for l in list(log)[-14:]]),
                               title="LIVE LOG", border_style="grey35"))
        elif args.view == "review":
            rev = fetch_list(f"/api/review-queue?since={WINDOW_S}")
            body = review_table(rev) if rev is not None else empty_hint("review queue unavailable")
        elif args.view == "metrics":
            m = fetch(f"/api/metrics?since={WINDOW_S}")
            body = metrics_table(m) if m is not None else empty_hint("metrics unavailable")
        elif args.view == "sessions":
            payload = fetch("/api/sessions?limit=50")
            body = sessions_table(payload) if payload is not None else empty_hint("sessions unavailable")
        elif args.view == "debug":
            body = debug_panel()
        elif args.view == "corpus":
            try:
                rows = ctx.corpus.window("train", 0, 25)
                body = corpus_table(rows)
            except Exception as exc:  # noqa: BLE001
                body = empty_hint(f"corpus closed — {exc}")
        elif args.view == "repos":
            body = repos_table([
                {**r, "live_description": (live_meta(r["name"]) or {}).get("description")}
                for r in all_repos()
            ])
        elif args.view == "inspect":
            tid = args.inspect
            if not tid and runs:
                tid = runs[0].get("trace_id") or ""
            if not tid:
                body = Text("no trace to inspect", style="yellow")
            else:
                detail = fetch(f"/api/traces/{tid}")
                if detail is None or detail.get("error"):
                    body = empty_hint(f"trace {tid} unavailable")
                else:
                    body = Group(*inspect_panels(detail))
        else:
            body = Group(floor_table(runs), Panel(
                Group(*[Text(l, style="grey70") for l in list(log)[-14:]]),
                title="LIVE LOG", border_style="grey35"))
        console.print(status_header(True, len(runs), API_BASE, ctx.pipeline))
        console.print(body)
    else:
        console.print(status_header(False, 0, API_BASE))
        console.print(Panel(Text("no Langfuse connection", style="bright_red")))
        if LAST_ERRORS:
            console.print(debug_panel())


def _run_repl(args: argparse.Namespace, console: Console) -> None:
    global _ctx
    keys: "queue.Queue[str]" = queue.Queue()
    threading.Thread(target=_key_reader, args=(keys,), daemon=True).start()

    ctx = cmds.CommandContext()
    _ctx = ctx
    ctx.api_base = API_BASE
    ctx.window_s = WINDOW_S
    ctx.fetch = fetch
    ctx.fetch_list = fetch_list
    ctx.fetch_floor_runs = fetch_floor_runs
    ctx.fetch_snapshot = fetch_snapshot
    ctx.corpus = CorpusClient()

    editor = LineEditor(console)
    scrollback: list[Any] = []
    pending: deque = deque()
    desk = False
    closed = False
    last_poll = 0.0
    prev: dict[str, dict] = {}

    with Live(console=console, screen=True, auto_refresh=False) as live:
        while True:
            now = time.monotonic()
            if now - last_poll >= POLL_INTERVAL:
                last_poll = now
                fresh = fetch_floor_runs()
                if fresh is None:
                    closed = True
                    if not probe_health():
                        closed = True
                else:
                    closed = False
                    ctx.runs = fresh
                    if desk:
                        runs_to_banners(prev, fresh, ctx.log)
                    prev = {r["trace_id"]: r for r in fresh}
                    ctx.pipeline = fetch("/api/pipeline") or {}

            # Drain keys.
            while not keys.empty() or pending:
                if pending:
                    ch = pending.popleft()
                else:
                    ch = keys.get()
                if desk and ch in ("q", "Q", "\x1b"):
                    desk = False
                    continue
                if editor.handle(ch, pending):
                    line = editor.text()
                    if line.strip():
                        scrollback.append(Text(f"mailroom@floor:~$ {line}",
                                               style="dim"))
                    results = _dispatch(ctx, line, console, live)
                    for result in results:
                        if result is cmds.CLEAR:
                            scrollback.clear()
                        elif result is cmds.QUIT:
                            console.print("\nmailroom-tui closed.")
                            return
                        elif result is cmds.DESK_FLOOR:
                            desk = True
                            scrollback.append(Text("entering the floor desk — "
                                                   "q to return", style="green"))
                        else:
                            scrollback.append(result)

            live.update(render_repl_frame(ctx, editor, scrollback, desk,
                                          closed, len(ctx.runs)))
            live.refresh()
            time.sleep(0.08)


def run() -> None:
    global API_BASE, POLL_INTERVAL
    parser = argparse.ArgumentParser(description="The-Mailroom TUI console.")
    parser.add_argument("--api", default=API_BASE, help="The-Mailroom server base URL")
    parser.add_argument("--poll", type=float, default=POLL_INTERVAL, help="refresh seconds")
    parser.add_argument("--once", action="store_true",
                        help="render a single frame and exit (scripting/CI)")
    parser.add_argument("--view", default="floor",
                        choices=["floor", "review", "metrics", "sessions",
                                 "inspect", "debug", "corpus", "repos"],
                        help="which desk --once (and the live start view) shows")
    parser.add_argument("--inspect", default="",
                        help="trace id to open on the inspect desk")
    parser.add_argument("--resolve", default="",
                        help="trace id (or producer doc_id) to resolve via POST /api/review/resolve")
    parser.add_argument("--decision", default="approved",
                        choices=["approved", "rejected"],
                        help="review decision used with --resolve")
    parser.add_argument("--disposition", default="resume",
                        choices=["resume", "record", "requeue", "complete"],
                        help="resume pipeline, record-only audit, requeue to inbox, or complete with --extracted-data")
    parser.add_argument("--notes", default="",
                        help="reviewer notes stored on the producer audit chain")
    parser.add_argument("--doc-type", default="", dest="doc_type",
                        help="human class correction used with --resolve")
    parser.add_argument("--doc-subclass", default="", dest="doc_subclass",
                        help="human subtype correction used with --resolve")
    parser.add_argument("--extracted-data", default="", dest="extracted_data",
                        help="JSON object for disposition=complete (producer archives without another LLM pass)")
    parser.add_argument("--source", default="",
                        help="print parked document text via GET /api/review/source")
    args = parser.parse_args()
    API_BASE = args.api.rstrip("/")
    POLL_INTERVAL = args.poll
    console = Console()

    if args.source:
        ident = args.source.strip()
        qs = urllib.parse.urlencode(
            {"filename": ident} if "." in ident and "/" not in ident
            else {"trace_id": ident, "doc_id": ident}
        )
        payload = fetch(f"/api/review/source?{qs}")
        if payload is None:
            console.print(Panel(Text("document source failed — see debug", style="bright_red")))
            for line in LAST_ERRORS:
                console.print(Text(line, style="red"))
            raise SystemExit(1)
        if payload.get("configured") is False:
            console.print(Panel(Text(str(payload.get("error") or "producer not configured"), style="bright_yellow")))
            if not args.resolve:
                raise SystemExit(1)
        else:
            title = payload.get("filename") or ident
            extra = "  [truncated]" if payload.get("truncated") else ""
            text = payload.get("text") or payload.get("error") or ""
            console.print(Panel(Text(str(text), style="green"), title=f"DOCUMENT SOURCE — {title}{extra}"))
        if not args.resolve:
            return

    if args.resolve:
        ident = args.resolve.strip()
        body: dict[str, Any] = {
            "decision": args.decision,
            "disposition": args.disposition,
            "notes": args.notes,
        }
        if args.doc_type:
            body["doc_type"] = args.doc_type
        if args.doc_subclass:
            body["doc_subclass"] = args.doc_subclass
        if args.extracted_data:
            try:
                body["extracted_data"] = json.loads(args.extracted_data)
            except json.JSONDecodeError as exc:
                console.print(Panel(Text(f"--extracted-data is not valid JSON: {exc}", style="bright_red")))
                raise SystemExit(2)
        if "." in ident and "/" not in ident:
            body["filename"] = ident
        else:
            body["trace_id"] = ident
            body["doc_id"] = ident
        result = post_json("/api/review/resolve", body)
        if result is None:
            console.print(Panel(Text("review resolve failed — see debug", style="bright_red")))
            for line in LAST_ERRORS:
                console.print(Text(line, style="red"))
            raise SystemExit(1)
        console.print(Panel(Text(json.dumps(result, indent=2), style="green"), title="REVIEW RESOLVE"))
        return

    if args.once:
        _run_once(args, console)
        return

    _run_repl(args, console)


if __name__ == "__main__":
    run()