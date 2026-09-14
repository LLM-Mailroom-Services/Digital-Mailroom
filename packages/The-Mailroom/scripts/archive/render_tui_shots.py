#!/usr/bin/env python3
"""Render TUI frames against a running Mailroom API for README screenshots.

Usage:
  MAILROOM_API_URL=http://127.0.0.1:8004 python3 scripts/render_tui_shots.py
"""
from __future__ import annotations

import os
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console

from tui import mailroom_console as tui

OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)


def _console() -> Console:
    return Console(
        record=True,
        width=120,
        force_terminal=True,
        color_system="truecolor",
        file=open(os.devnull, "w"),
    )


def save(name: str, renderable) -> Path:
    console = _console()
    console.print(renderable)
    svg = OUT / name
    console.save_svg(str(svg), title="mailroom-tui")
    return svg


def main() -> None:
    tui.API_BASE = os.environ.get("MAILROOM_API_URL", "http://127.0.0.1:8004").rstrip("/")
    runs = tui.fetch_floor_runs()
    if runs is None:
        raise SystemExit(f"API unreachable at {tui.API_BASE}")
    log: deque[str] = deque()
    tui.runs_to_banners({}, runs, log)
    save("tui-console.svg", tui.Group(tui.status_header(True, len(runs)), tui.render_floor(runs, log)))
    rev = tui.fetch_list("/api/review-queue") or []
    save("tui-review.svg", tui.Group(tui.status_header(True, len(runs)), tui.review_table(rev)))
    m = tui.fetch(f"/api/metrics?since={tui.WINDOW_S}") or {}
    save("tui-metrics.svg", tui.Group(tui.status_header(True, len(runs)), tui.metrics_table(m)))
    sessions = tui.fetch("/api/sessions?limit=50") or {}
    save("tui-sessions.svg", tui.Group(tui.status_header(True, len(runs)), tui.sessions_table(sessions)))
    print(f"wrote SVGs under {OUT}")


if __name__ == "__main__":
    main()
