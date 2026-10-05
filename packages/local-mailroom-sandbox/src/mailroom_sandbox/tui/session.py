"""Mailroom-themed terminal output for long sandbox CLI jobs (SAND-033).

Wraps vendored ``pretty_log`` primitives. Alt-screen TUI stays in
``mailroom_sandbox.watch``; this module is tail-friendly lines on stderr.

Plain mode when ``NO_COLOR`` is set, stderr is not a TTY, or
``SANDBOX_PLAIN_LOGS=1``.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, TextIO

from mailroom_sandbox.tui import pretty_log as pl

# Double-line frame chars (match pretty_log / watch)
_DTL, _DH, _DTR = pl.DTL, pl.DH, pl.DTR
_DBL, _DBR = pl.DBL, pl.DBR


def stream_is_tty(stream: TextIO | None = None) -> bool:
    fh = stream or sys.stderr
    return hasattr(fh, "isatty") and bool(fh.isatty())


def mailroom_style_enabled(*, stream: TextIO | None = None) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("SANDBOX_PLAIN_LOGS", "").strip().lower() in ("1", "true", "yes"):
        return False
    return stream_is_tty(stream)


def item_progress_bar(done: int, total: int, *, width: int = 24) -> str:
    """Eval/job bar (█ / ░), same glyphs as ``watch.progress_bar``."""
    frac = 0.0 if total <= 0 else min(1.0, max(0.0, done / total))
    filled = int(round(frac * width))
    return "█" * filled + "░" * (width - filled)


class MailroomConsole:
    """One-line and compact-banner mailroom output for operator CLIs."""

    def __init__(self, *, stream: TextIO | None = None, enabled: bool | None = None) -> None:
        self.stream = stream or sys.stderr
        self.on = mailroom_style_enabled(stream=self.stream) if enabled is None else bool(enabled)
        self._last_progress_key: tuple[int, int] | None = None

    def emit(self, line: str) -> None:
        print(line, file=self.stream, flush=True)

    def run_banner(
        self,
        *,
        run_id: str,
        task: str = "",
        subtitle: str = "",
        route: str | None = None,
        width: int = 72,
    ) -> None:
        """Run start: compact double-line frame or plain one-liner."""
        tag = run_id
        sub = subtitle or (f"task · {task}" if task else "")
        route_line = route or pl.mailroom_route_banner()
        if not self.on:
            bits = [f"[mailroom] {tag}"]
            if sub:
                bits.append(sub)
            self.emit(" · ".join(bits))
            return
        w = max(48, min(width, 100))
        inner = w - 2
        p = pl.palette(True)
        top = p["frame"](_DTL + _DH * inner + _DTR)
        bot = p["frame"](_DBL + _DH * inner + _DBR)
        mark = pl._wordmark_lines(inner=inner, on=True, compact=w < 90)
        self.emit(top)
        for ol in mark:
            self.emit(pl._centered_row(ol, width=w, on=True))
        if sub:
            self.emit(pl._panel_row(p["brand"](sub), on=False, sides=True, width=w))
        self.emit(pl._panel_row(p["teal"](route_line), on=False, sides=True, width=w))
        self.emit(bot)

    def phase(self, phase: str, detail: str = "") -> None:
        """Structured phase change (preflight → deploy → eval …)."""
        phase = phase.strip().upper()
        detail = detail.strip()
        if not self.on:
            self.emit(f"[{phase}] {detail}" if detail else f"[{phase}]")
            return
        p = pl.palette(True)
        face = pl.owl_emoticon(blink=False, on=True)
        stamp = p["stamp"](f"▸{phase}◂")
        body = f"{face}  {stamp}"
        if detail:
            body += p["dim"](f"  ·  {detail}")
        self.emit(body)

    def progress(
        self,
        done: int,
        total: int,
        *,
        ok: int | None = None,
        errors: int | None = None,
        label: str = "items",
        state: str = "",
    ) -> None:
        """In-tray progress; skips duplicate (done, total) in plain throttle mode."""
        key = (done, total)
        if not self.on and key == self._last_progress_key:
            return
        self._last_progress_key = key
        bar = item_progress_bar(done, total)
        pct = (100.0 * done / total) if total else 0.0
        if not self.on:
            extra = ""
            if ok is not None:
                extra = f" ok={ok}"
            if errors is not None:
                extra += f" errors={errors}"
            if state:
                extra += f" {state}"
            self.emit(f"[progress] {done}/{total}{extra}")
            return
        p = pl.palette(True)
        counts = f"{done}/{total}"
        if ok is not None:
            counts += f"  delivered {ok}"
        if errors is not None:
            counts += p["warn"](f"  returned {errors}")
        line = (
            p["dim"]("IN-TRAY  ")
            + p["accent"](bar)
            + p["dim"](f"  {pct:5.1f}%  ")
            + p["snow"](counts)
        )
        if state:
            line += p["dim"](f"  ·  {state}")
        self.emit(line)

    def cost_line(self, spent_usd: float | None, *, cap_usd: float | None = None, label: str = "POSTAGE") -> None:
        if spent_usd is None and cap_usd is None:
            return
        spent = "—" if spent_usd is None else f"${spent_usd:.4f}"
        cap = "" if cap_usd is None else f" / cap ${cap_usd:.2f}"
        if not self.on:
            self.emit(f"[{label.lower()}] {spent}{cap}")
            return
        p = pl.palette(True)
        warn = cap_usd is not None and spent_usd is not None and spent_usd >= 0.9 * cap_usd
        val = p["warn"](spent + cap) if warn else p["gold"](spent + cap)
        self.emit(p["dim"](f"{label}  ") + val)

    def operator_line(self, phase: str, message: str) -> None:
        """Deploy / Modal scripts: one stamped line (remote logs stay plain)."""
        if not self.on:
            self.emit(message)
            return
        p = pl.palette(True)
        self.emit(p["stamp"](f"▸{phase.upper()}◂") + p["dim"]("  ") + p["snow"](message))

    def complete(self, *, state: str, summary: str = "") -> None:
        state = state.strip().lower()
        if not self.on:
            self.emit(f"[done] {state}" + (f" — {summary}" if summary else ""))
            return
        p = pl.palette(True)
        role = "teal" if state in {"done", "ok", "prepared"} else "warn"
        face = pl.owl_emoticon(blink=False, on=True)
        head = p[role](state.upper())
        tail = p["dim"](f"  ·  {summary}") if summary else ""
        self.emit(f"{face}  {head}{tail}")

    def json_fallback(self, payload: Any) -> None:
        """When styled banners are off, callers still use structured _print."""
        if not self.on:
            return
        # Styled runs prefer human lines; JSON summaries go to stdout via _print elsewhere.
        return


def run_event_handler(console: MailroomConsole) -> Callable[[dict[str, Any]], None]:
    """``on_event`` hook for ``runner.run_job`` / ``--watch`` without alt-screen TUI."""

    def _on_event(ev: dict[str, Any]) -> None:
        console.progress(
            int(ev.get("cursor") or 0),
            int(ev.get("total") or 0),
            ok=ev.get("ok") if ev.get("ok") is not None else None,
            errors=ev.get("errors") if ev.get("errors") is not None else None,
            state=str(ev.get("state") or ""),
        )

    return _on_event


def operator_emit(message: str, *, phase: str = "DEPLOY", stream: TextIO | None = None) -> None:
    """Modal/deploy local entrypoints (stdout); remote container logs stay plain."""
    MailroomConsole(stream=stream or sys.stdout).operator_line(phase, message)


def remote_progress_line(console: MailroomConsole, run_id: str, progress: dict[str, Any] | None) -> None:
    """One update line for ``sandbox run status --watch`` (modal job mode)."""
    prog = progress or {}
    state = str(prog.get("state") or "unknown")
    cursor = int(prog.get("cursor") or prog.get("done") or 0)
    total = int(prog.get("total") or 0)
    ok = prog.get("ok")
    errors = prog.get("errors")
    if console.on and total > 0:
        console.progress(cursor, total, ok=int(ok) if ok is not None else None,
                         errors=int(errors) if errors is not None else None, state=state)
    elif console.on:
        console.phase(state, run_id)
    else:
        console.emit(f"{run_id} {state} {prog}")
