#!/usr/bin/env python3
"""Capture deterministic tray-TUI screenshots for the pretty-log docs.

Offline only: reuses the pure render functions (no Modal, no LLM, no network)
and writes dependency-free SVG screenshots + ANSI text fallbacks under
``docs/assets/watch/`` plus a ``manifest.json`` the docs gallery and the
regression test both read.

Run: ``python scripts/capture_watch_screenshots.py [--out docs/assets/watch]``
"""

from __future__ import annotations

import argparse
import io
import json
import re
import tempfile
import xml.sax.saxutils as sax
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT = REPO_ROOT / "docs" / "assets" / "watch"

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def visible_len(text: str) -> int:
    return len(strip_ansi(text))


# ── ANSI → styled segments ──────────────────────────────────────────────
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")


def parse_ansi_line(line: str) -> list[tuple[str, dict]]:
    """Split one ANSI line into (text, style) runs.

    Style keys: fg (``#rrggbb`` or None), bg, bold, dim.
    """
    runs: list[tuple[str, dict]] = []
    fg = bg = None
    bold = dim = False
    pos = 0
    for m in _SGR_RE.finditer(line):
        chunk = line[pos : m.start()]
        if chunk:
            runs.append((chunk, {"fg": fg, "bg": bg, "bold": bold, "dim": dim}))
        pos = m.end()
        codes = [int(c) for c in m.group(1).split(";") if c] or [0]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                fg = bg = None
                bold = dim = False
            elif c == 1:
                bold = True
            elif c == 2:
                dim = True
            elif c == 22:
                bold = dim = False
            elif c in (38, 48) and i + 4 < len(codes) and codes[i + 1] == 2:
                hexcol = "#%02x%02x%02x" % tuple(codes[i + 2 : i + 5])
                if c == 38:
                    fg = hexcol
                else:
                    bg = hexcol
                i += 5
                continue
            elif c == 39:
                fg = None
            elif c == 49:
                bg = None
            i += 1
    tail = line[pos:]
    if tail:
        runs.append((tail, {"fg": fg, "bg": bg, "bold": bold, "dim": dim}))
    if not runs:
        runs.append(("", {"fg": None, "bg": None, "bold": False, "dim": False}))
    return runs


# ── ANSI → SVG ──────────────────────────────────────────────────────────
_FONT = "ui-monospace, 'IBM Plex Mono', Menlo, Consolas, monospace"
_FONT_SIZE = 13
_LINE_H = 18
_CHAR_W = 7.82
_PAD = 16
_TITLE_H = 30
_BG = "#0a1628"
_PANEL_BG = "#071a2e"
_FG_DEFAULT = "#fbfcfe"


def ansi_to_svg(ansi_text: str, *, title: str) -> str:
    lines = ansi_text.splitlines() or [""]
    cols = max((visible_len(ln) for ln in lines), default=10)
    cols = max(cols, 10)
    width = int(cols * _CHAR_W + _PAD * 2)
    height = int(_TITLE_H + len(lines) * _LINE_H + _PAD * 2)
    out: list[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}" font-size="{_FONT_SIZE}">'
    )
    out.append(f"<rect width=\"{width}\" height=\"{height}\" rx=\"8\" fill=\"{_BG}\"/>")
    # title bar
    out.append(
        f'<circle cx="{_PAD}" cy="{_TITLE_H // 2}" r="5" fill="#f5c445"/>'
        f'<circle cx="{_PAD + 16}" cy="{_TITLE_H // 2}" r="5" fill="#38e0d6"/>'
        f'<circle cx="{_PAD + 32}" cy="{_TITLE_H // 2}" r="5" fill="#0e7490"/>'
        f'<text x="{_PAD + 48}" y="{_TITLE_H // 2 + 5}" fill="#5c7184" '
        f'font-size="12">{sax.escape(title)}</text>'
    )
    out.append(
        f'<rect x="{_PAD - 4}" y="{_TITLE_H}" width="{width - 2 * (_PAD - 4)}" '
        f'height="{len(lines) * _LINE_H + _PAD}" rx="6" fill="{_PANEL_BG}"/>'
    )
    y = _TITLE_H + _PAD + 13
    for line in lines:
        x = float(_PAD)
        parts = [f'<text x="{_PAD}" y="{y}">']
        for chunk, style in parse_ansi_line(line):
            fill = style["fg"] or _FG_DEFAULT
            attrs = f'fill="{fill}"'
            if style["bold"]:
                attrs += ' font-weight="bold"'
            if style["dim"]:
                attrs += ' opacity="0.62"'
            if style["bg"]:
                w = len(chunk) * _CHAR_W
                parts.append(
                    f'<rect x="{x:.1f}" y="{y - 12}" width="{w:.1f}" height="16" '
                    f'fill="{style["bg"]}"/>' if False else ""
                )
            parts.append(f'<tspan {attrs}>{sax.escape(chunk)}</tspan>')
            x += len(chunk) * _CHAR_W
        parts.append("</text>")
        out.append("".join(p for p in parts if p))
        y += _LINE_H
    out.append("</svg>")
    return "\n".join(out) + "\n"


def theme_swatch_svg(theme: dict[str, str], *, title: str) -> str:
    names = list(theme)
    cell_w, cell_h, gap = 150, 54, 10
    per_row = 4
    rows = (len(names) + per_row - 1) // per_row
    width = per_row * (cell_w + gap) + _PAD * 2 - gap
    height = _TITLE_H + rows * (cell_h + gap) + _PAD * 2 + 26
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}" font-size="{_FONT_SIZE}">',
        f"<rect width=\"{width}\" height=\"{height}\" rx=\"8\" fill=\"{_BG}\"/>",
        f'<text x="{_PAD}" y="{_TITLE_H // 2 + 5}" fill="#5c7184" font-size="12">{sax.escape(title)}</text>',
    ]
    y0 = _TITLE_H + _PAD
    for idx, name in enumerate(names):
        r, c = divmod(idx, per_row)
        x = _PAD + c * (cell_w + gap)
        y = y0 + r * (cell_h + gap)
        color = theme[name]
        out.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" rx="6" fill="{color}"/>')
        label = "#071a2e" if name in ("gold", "cyan", "cream", "snow", "sky", "amber") else "#fbfcfe"
        out.append(f'<text x="{x + 10}" y="{y + 22}" fill="{label}" font-size="12">{sax.escape(name)}</text>')
        out.append(f'<text x="{x + 10}" y="{y + 40}" fill="{label}" font-size="12" opacity="0.8">{sax.escape(color)}</text>')
    out.append(
        f'<text x="{_PAD}" y="{height - 12}" fill="#5c7184" font-size="11">'
        "Browser THEME is derived from pretty_log palette (web.py THEME); terminal and browser never drift.</text>"
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


# ── fixtures ────────────────────────────────────────────────────────────
DISPATCH_SAMPLE = [
    "=== sandbox-vllm serve config (masked) ===",
    "INFO Loading weights took 12.3 seconds",
    "INFO Available KV cache memory: 12.1 GiB",
    "GPU KV cache size: 181,344 tokens",
    "Capturing CUDA graphs (mixed prefill-decode)",
    "Avg prompt throughput: 812.3 tokens/s, Avg generation throughput: 140.1",
    "WARNING preemptions=2 length_finishes=1 on replica a1b2c3",
    "ERROR OpenAIConnectionError: engine died on DOC-0007",
    "Traceback (most recent call last): File serve.py, line 9",
    "vLLM ready on port 8000 (pid=12)",
    "INFO:     Application startup complete.",
    "some other line",
]


def _watch_imports():
    from mailroom_sandbox import watch as w  # noqa: PLC0415
    from mailroom_sandbox.tui import pretty_log as pl  # noqa: PLC0415

    return w, pl


def base_snapshot(run_id: str = "sand032-l2-marlin") -> dict:
    return {
        "run_id": run_id,
        "task": "correspondence_specialist",
        "state": "running",
        "done": 3,
        "total": 10,
        "ok": 2,
        "errors": 1,
        "replicas": 1,
        "gpu": "L4",
        "p50_s": 2.0,
        "p95_s": 3.0,
        "mean_score": 0.5,
        "last_error": "OpenAIConnectionError: x",
    }


def fake_scorecard(on: bool) -> list[str]:
    from mailroom_sandbox.tui import pretty_log as pl  # noqa: PLC0415

    def m(label: str, value: str) -> str:
        return pl._metric(label, str(value), label_w=18, total_w=96, on=on)

    return [
        m("sorted", "delivered 18 · returned 2 · of 20"),
        m("overall score", "0.2547"),
        m("schema valid", "0.94"),
        m("wall", "90.4 s"),
        m("cold boot", "161.0 s"),
        m("postmark p50/p95", "35.0s / 38.0s"),
        m("throughput", "472.1 tok/s"),
        m("tokens in/out", "40000 / 4000"),
        m("GPU $ (busy)", "$0.0556"),
        m("$/doc", "$0.00278"),
        m("run span ≥", "$0.0900 (×1 GPU)"),
    ]


def build_cases() -> list[dict]:
    w, _pl = _watch_imports()
    with tempfile.TemporaryDirectory() as tmp:
        from mailroom_sandbox.job.checkpoint import RunStore  # noqa: PLC0415

        store = RunStore(Path(tmp) / "sand032-x")
        store.write_lock(
            {
                "run_id": "sand032-x",
                "task": "correspondence_specialist",
                "engine": {"modal": {"gpu": "L4", "max_containers": 1}},
                "job": {"concurrency": 16},
            }
        )
        store.write_checkpoint(state="running", cursor=3, total=10, remote=None)
        for i, (ok, lat) in enumerate([(True, 1000.0), (True, 3000.0), (False, 500.0)]):
            store.append_item(
                {
                    "item_id": f"d{i}",
                    "ok": ok,
                    "latency_ms": lat,
                    "error": None if ok else "OpenAIConnectionError: x",
                    "score": {"overall_extraction_score": 0.5} if ok else {},
                }
            )
        live_route = w.program_lines(Path(tmp), current="sand032-l1-nothink", width=100, on=True)
        Path(tmp, "sand032-l0-baseline.times").write_text('"stopped": 1.0,\n')
        Path(tmp, "sand032-l1-nothink.times").write_text('"run_start": 1.0,\n')
        route_demo = w.program_lines(Path(tmp), current="sand032-l1-nothink", width=100, on=False)
        _ = (live_route, route_demo)

    cases: list[dict] = [
        {
            "name": "sorting-wide-color",
            "title": "SORTING — wide color (100 cols, owl open)",
            "description": "Mid-run SORTING frame: in-tray + postage side by side, dispatch log roles.",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": base_snapshot(),
            "spend": {"spent_usd": 1.2345, "live_usd": 0.01, "cap_usd": 5.0},
            "lifecycle": {"phase": "SORTING", "detail": "specialist extraction in flight", "elapsed_s": 183},
            "log_lines": DISPATCH_SAMPLE,
            "route": None,
            "scorecard": None,
        },
        {
            "name": "queued-narrow-plain",
            "title": "QUEUED — narrow plain (70 cols, NO_COLOR)",
            "description": "Waiting run in plain mode: stacked panels, no ANSI, compact hero.",
            "width": 70,
            "on": False,
            "blink": False,
            "snapshot": {**base_snapshot("sand032-l0-baseline"), "state": "waiting", "done": 0, "ok": 0, "errors": 0, "last_error": "", "p50_s": None, "p95_s": None, "mean_score": None},
            "spend": {"spent_usd": 0.0, "live_usd": 0.0, "cap_usd": 5.0},
            "lifecycle": {"phase": "QUEUED", "detail": "waiting for the driver", "elapsed_s": 0},
            "log_lines": [],
            "route": None,
            "scorecard": None,
        },
        {
            "name": "deploying",
            "title": "DEPLOYING — modal deploy",
            "description": "Driver has started the deploy; the fleet image + app are being pushed.",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": {**base_snapshot(), "state": "running", "done": 0, "ok": 0, "errors": 0, "last_error": ""},
            "spend": {"spent_usd": 0.0, "live_usd": 0.0, "cap_usd": 5.0},
            "lifecycle": {"phase": "DEPLOYING", "detail": "modal deploy · image + app", "elapsed_s": 25},
            "log_lines": ["=== sandbox-vllm serve config (masked) ==="],
            "route": None,
            "scorecard": None,
        },
        {
            "name": "preflight",
            "title": "PREFLIGHT — engine verified",
            "description": "Engine is up; the TUI has baselined /metrics before sorting starts.",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": {**base_snapshot(), "state": "running", "done": 0, "ok": 0, "errors": 0, "last_error": ""},
            "spend": {"spent_usd": 0.02, "live_usd": 0.01, "cap_usd": 5.0},
            "lifecycle": {"phase": "PREFLIGHT", "detail": "engine verified · /metrics baseline", "elapsed_s": 18},
            "log_lines": ["vLLM ready on port 8000 (pid=12)", "INFO:     Application startup complete."],
            "route": None,
            "scorecard": None,
        },
        {
            "name": "cold-boot-container-starting",
            "title": "COLD BOOT — container starting",
            "description": "First boot sub-phase: the container is up, weights not yet loading.",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": {**base_snapshot(), "state": "running", "done": 0, "ok": 0, "errors": 0, "last_error": ""},
            "spend": {"spent_usd": 0.02, "live_usd": 0.05, "cap_usd": 5.0},
            "lifecycle": {"phase": "COLD BOOT", "detail": "container starting", "elapsed_s": 12},
            "log_lines": DISPATCH_SAMPLE[:1],
            "route": None,
            "scorecard": None,
        },
        {
            "name": "cold-boot-loading-weights",
            "title": "COLD BOOT — loading weights",
            "description": "Boot sub-phase derived from Modal log markers (BOOT_MARKERS).",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": {**base_snapshot(), "state": "running", "done": 0, "ok": 0, "errors": 0, "last_error": ""},
            "spend": {"spent_usd": 0.02, "live_usd": 0.05, "cap_usd": 5.0},
            "lifecycle": {"phase": "COLD BOOT", "detail": "loading weights", "elapsed_s": 60},
            "log_lines": DISPATCH_SAMPLE[:4],
            "route": None,
            "scorecard": None,
        },
        {
            "name": "cold-boot-profiling-kv",
            "title": "COLD BOOT — profiling KV cache",
            "description": "Boot sub-phase: vLLM is sizing the KV cache pool.",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": {**base_snapshot(), "state": "running", "done": 0, "ok": 0, "errors": 0, "last_error": ""},
            "spend": {"spent_usd": 0.02, "live_usd": 0.05, "cap_usd": 5.0},
            "lifecycle": {"phase": "COLD BOOT", "detail": "profiling KV cache", "elapsed_s": 95},
            "log_lines": DISPATCH_SAMPLE[1:4],
            "route": None,
            "scorecard": None,
        },
        {
            "name": "cold-boot-cuda-graphs",
            "title": "COLD BOOT — capturing CUDA graphs",
            "description": "Boot sub-phase: engine is capturing CUDA graphs before serving.",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": {**base_snapshot(), "state": "running", "done": 0, "ok": 0, "errors": 0, "last_error": ""},
            "spend": {"spent_usd": 0.02, "live_usd": 0.05, "cap_usd": 5.0},
            "lifecycle": {"phase": "COLD BOOT", "detail": "capturing CUDA graphs", "elapsed_s": 130},
            "log_lines": DISPATCH_SAMPLE[3:6],
            "route": None,
            "scorecard": None,
        },
        {
            "name": "cold-boot-engine-ready",
            "title": "COLD BOOT — engine ready",
            "description": "Final boot sub-phase: the engine answers on its port; preflight is next.",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": {**base_snapshot(), "state": "running", "done": 0, "ok": 0, "errors": 0, "last_error": ""},
            "spend": {"spent_usd": 0.02, "live_usd": 0.05, "cap_usd": 5.0},
            "lifecycle": {"phase": "COLD BOOT", "detail": "engine ready", "elapsed_s": 161},
            "log_lines": DISPATCH_SAMPLE[9:11],
            "route": None,
            "scorecard": None,
        },
        {
            "name": "teardown-scorecard",
            "title": "TEARDOWN — scorecard",
            "description": "Post-run scorecard: quality + serving record + /metrics replica row.",
            "width": 110,
            "on": True,
            "blink": False,
            "snapshot": {**base_snapshot(), "state": "running", "done": 20, "total": 20, "ok": 18, "errors": 2},
            "spend": {"spent_usd": 0.42, "live_usd": 0.0, "cap_usd": 5.0},
            "lifecycle": {"phase": "TEARDOWN", "detail": "metrics · serving record · evidence rows · stop", "elapsed_s": 12},
            "log_lines": DISPATCH_SAMPLE,
            "route": None,
            "scorecard": fake_scorecard(True),
        },
        {
            "name": "stopped-scorecard",
            "title": "STOPPED — fleet stopped, billing ended",
            "description": "Terminal phase: the scorecard stays on screen after the fleet stops.",
            "width": 110,
            "on": True,
            "blink": False,
            "snapshot": {**base_snapshot(), "state": "running", "done": 20, "total": 20, "ok": 18, "errors": 2},
            "spend": {"spent_usd": 0.42, "live_usd": 0.0, "cap_usd": 5.0},
            "lifecycle": {"phase": "STOPPED", "detail": "fleet stopped · billing ended", "elapsed_s": 30},
            "log_lines": DISPATCH_SAMPLE,
            "route": None,
            "scorecard": fake_scorecard(True),
        },
        {
            "name": "over-gate",
            "title": "POSTAGE — over-gate warning",
            "description": "Spend past the $4.50 projected-total gate: gold warning row in postage.",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": base_snapshot(),
            "spend": {"spent_usd": 4.6, "live_usd": 0.05, "cap_usd": 5.0},
            "lifecycle": {"phase": "SORTING", "detail": "specialist extraction in flight", "elapsed_s": 400},
            "log_lines": DISPATCH_SAMPLE,
            "route": None,
            "scorecard": None,
        },
        {
            "name": "blink-owl",
            "title": "Blink frame — owl (-,-)",
            "description": "Same SORTING frame with blink=True: the owl blinks every 7th second.",
            "width": 100,
            "on": True,
            "blink": True,
            "snapshot": base_snapshot(),
            "spend": {"spent_usd": 1.2345, "live_usd": 0.01, "cap_usd": 5.0},
            "lifecycle": {"phase": "SORTING", "detail": "specialist extraction in flight", "elapsed_s": 184},
            "log_lines": DISPATCH_SAMPLE,
            "route": None,
            "scorecard": None,
        },
        {
            "name": "dispatch-roles",
            "title": "Dispatch log — every role",
            "description": "One line per classify_log_line role: error, warn, throughput, kv, ready, plain.",
            "width": 100,
            "on": True,
            "blink": False,
            "snapshot": base_snapshot(),
            "spend": {"spent_usd": 0.3, "live_usd": 0.02, "cap_usd": 5.0},
            "lifecycle": {"phase": "SORTING", "detail": "specialist extraction in flight", "elapsed_s": 90},
            "log_lines": [
                "Traceback (most recent call last): File serve.py",
                "WARNING kv cache 95% — preemptions rising",
                "Avg prompt throughput: 812.3 tokens/s",
                "GPU KV cache size: 181,344 tokens",
                "vLLM ready on port 8000 (pid=12)",
                "some other line",
                "… waiting for app (stopped between runs or booting) — will attach when it is live",
            ],
            "route": None,
            "scorecard": None,
        },
        {
            "name": "program-route",
            "title": "Program route — ladder + sweep",
            "description": "Done / live / queued marks with fleet tags across the 13-run program.",
            "width": 110,
            "on": False,
            "blink": False,
            "snapshot": base_snapshot("sand032-l1-nothink"),
            "spend": {"spent_usd": 0.3, "live_usd": 0.02, "cap_usd": 5.0},
            "lifecycle": {"phase": "SORTING", "detail": "specialist extraction in flight", "elapsed_s": 90},
            "log_lines": DISPATCH_SAMPLE,
            "route": [
                "✓ l0-baseline ×1          ▶ l1-nothink ×1           · l2-marlin ×1",
                "· l5-graphs ×1            · s2a-corr100-1rep ×1    · s2b-corr100-2rep ×2",
                "· s3-corr50 ×2            · s3-insurance50 ×2      · s3-corporate50 ×2",
                "· s3-merger50 ×2          · s3-contracts50 ×2      · s3-corr50-repeat ×2",
            ],
            "scorecard": None,
        },
    ]
    return cases


def render_board_cases() -> list[dict]:
    from mailroom_sandbox.tui import board as bmod  # noqa: PLC0415

    now_jobs = [
        {"job_id": "demo-sorter", "package": "local-mailroom-sandbox", "title": "demo · sorter n=24", "phase": "SORTING", "state": "running", "status": "running", "done": 9, "total": 24, "ok": 8, "errors": 1, "age_s": 4.0, "metrics": {"p50_s": 5.4}, "log_tail": ["DOC-demo-009 ok"]},
        {"job_id": "demo-gepa", "package": "eval-environment", "title": "demo · v2 prompt A/B", "phase": "SCORING", "state": "running", "status": "stalled", "done": 3, "total": 12, "ok": 3, "errors": 0, "age_s": 400.0, "metrics": {"delta_vs_prod": 0.036}, "log_tail": ["heartbeat lost 400s ago"]},
        {"job_id": "demo-fail", "package": "local-mailroom-sandbox", "title": "demo · failed shard", "phase": "SORTING", "state": "failed", "status": "failed", "done": 5, "total": 10, "ok": 4, "errors": 1, "age_s": 12.0, "metrics": {}, "log_tail": ["ERROR LengthFinishReasonError"]},
        {"job_id": "demo-done", "package": "local-mailroom-sandbox", "title": "demo · finished sweep", "phase": "DONE", "state": "done", "status": "done", "done": 20, "total": 20, "ok": 19, "errors": 1, "age_s": 30.0, "metrics": {"accuracy": 0.895}, "log_tail": ["accuracy 0.895"]},
    ]
    return [
        {"name": "board-terminal", "title": "Job board — running/stalled/failed/done", "description": "sandbox board --tui with one job per status; tone follows status.", "text": bmod.render_board(now_jobs, width=100, on=True)},
        {"name": "board-empty", "title": "Job board — empty in-tray", "description": "First-run hint with the Beacon publish snippet.", "text": bmod.render_board([], width=100, on=True)},
    ]


def render_session_case() -> dict:
    from mailroom_sandbox.tui import session as smod  # noqa: PLC0415

    buf = io.StringIO()
    con = smod.MailroomConsole(stream=buf, enabled=True)
    con.run_banner(run_id="sand032-l2-marlin", task="correspondence_specialist", subtitle="Qwen3-8B-AWQ · vLLM L4 eval", route="INBOX → SPECIALIST → REPORT", width=72)
    con.phase("SORTING", "specialist extraction in flight")
    con.progress(3, 10, ok=2, errors=1, state="running")
    con.cost_line(1.2345, cap_usd=5.0)
    con.operator_line("DEPLOY", "modal deploy · image + app")
    con.complete(state="done", summary="delivered 18 · returned 2 · of 20")
    return {
        "name": "session-cli",
        "title": "Session CLI — tail-friendly lines (no alt-screen)",
        "description": "sandbox run / eval / matrix output on stderr via MailroomConsole.",
        "text": buf.getvalue(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Capture watch/board/session SVG screenshots.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true", help="Verify assets exist; do not write.")
    args = ap.parse_args()

    out: Path = args.out
    cases = build_cases()
    board_cases = render_board_cases()
    session_case = render_session_case()

    from mailroom_sandbox import watch as w  # noqa: PLC0415
    from mailroom_sandbox.tui import web as web_mod  # noqa: PLC0415

    manifest_cases: list[dict] = []
    for c in cases:
        manifest_cases.append(
            {"name": c["name"], "title": c["title"], "description": c["description"], "kind": "watch", "width": c["width"], "color": bool(c["on"]), "blink": bool(c["blink"])}
        )
    for b in board_cases:
        manifest_cases.append({"name": b["name"], "title": b["title"], "description": b["description"], "kind": "board", "width": 100, "color": True, "blink": False})
    manifest_cases.append({"name": session_case["name"], "title": session_case["title"], "description": session_case["description"], "kind": "session", "width": 72, "color": True, "blink": False})
    manifest_cases.append({"name": "web-theme", "title": "Browser theme — pretty_log palette tokens", "description": "watch --web and board browser derive CSS tokens from pretty_log; terminal and browser never drift.", "kind": "web-theme", "width": 100, "color": True, "blink": False})
    manifest = {"generated_by": "scripts/sand032/capture_watch_screenshots.py", "cases": manifest_cases}

    expected = [f"{c['name']}.svg" for c in manifest_cases] + [f"{c['name']}.ansi.txt" for c in manifest_cases if c["kind"] != "web-theme"] + ["manifest.json"]
    if args.check:
        missing = [f for f in expected if not (out / f).is_file()]
        if missing:
            print("missing watch assets: " + ", ".join(missing))
            return 1
        print(f"watch assets ok: {len(expected)} files in {out}")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    for c in cases:
        frame = w.render_frame(
            snapshot=c["snapshot"],
            app="sandbox-vllm-sand032",
            log_lines=c["log_lines"],
            spend=c["spend"],
            width=c["width"],
            on=c["on"],
            blink=c["blink"],
            lifecycle=c["lifecycle"],
            scorecard=c["scorecard"],
            route=c["route"],
        )
        text = frame if c["on"] else strip_ansi(frame)
        if not c["on"]:
            text = strip_ansi(frame)
        (out / f"{c['name']}.ansi.txt").write_text(text + "\n", encoding="utf-8")
        (out / f"{c['name']}.svg").write_text(ansi_to_svg(text, title=f"{c['name']} · {c['title']}"), encoding="utf-8")
    for b in board_cases:
        (out / f"{b['name']}.ansi.txt").write_text(b["text"] + "\n", encoding="utf-8")
        (out / f"{b['name']}.svg").write_text(ansi_to_svg(b["text"], title=f"{b['name']} · {b['title']}"), encoding="utf-8")
    (out / f"{session_case['name']}.ansi.txt").write_text(session_case["text"], encoding="utf-8")
    (out / f"{session_case['name']}.svg").write_text(ansi_to_svg(session_case["text"], title=f"{session_case['name']} · {session_case['title']}"), encoding="utf-8")
    (out / "web-theme.svg").write_text(theme_swatch_svg(web_mod.THEME, title="web-theme · THEME tokens from pretty_log"), encoding="utf-8")
    (out / "web-theme.ansi.txt").write_text("\n".join(f"{k} {v}" for k, v in web_mod.THEME.items()) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest_cases)} cases to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
