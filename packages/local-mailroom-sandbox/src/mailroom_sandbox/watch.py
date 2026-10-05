"""Tray TUI (`sandbox watch`) — mailroom-themed live view of a sandbox job run.

One terminal pane that combines:
  * the run's in-tray (checkpoint cursor/total, delivered vs returned docs,
    postmark latency p50/p95, mean score) read from the local run store;
  * postage — spend so far (ledger) + the live run's GPU estimate vs the cap;
  * the dispatch log — `modal app logs <app>` streamed from the dedicated
    Modal app, colour-coded (errors, warnings, vLLM throughput, KV pool).

Stdlib only (ANSI escapes); render functions are pure and unit-tested.
"""

from __future__ import annotations

import json
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.tui import pretty_log as pl

_ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
GATE_USD = 4.50
# Legacy defaults when no lock is present (demo / empty store).
SUBTITLE_PATH = "sandbox job · vLLM eval"
ROUTE = "INBOX → SPECIALIST → REPORT"


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


def progress_bar(done: int, total: int, *, width: int = 30) -> str:
    """mailroom-ml bar glyphs (█ filled / ░ empty), clamped to [0, total]."""
    frac = 0.0 if total <= 0 else min(1.0, max(0.0, done / total))
    filled = int(round(frac * width))
    return "█" * filled + "░" * (width - filled)


def classify_log_line(line: str) -> str:
    low = line.lower()
    if low.startswith("job:"):
        if "fail" in low or "error" in low:
            return "error"
        if "warn" in low or "pause" in low or "drift" in low:
            return "warn"
        if "cold boot" in low or "ready" in low or "done" in low:
            return "ready"
        return "plain"
    if "traceback" in low or re.search(r"\berror\b", low) or "exception" in low:
        return "error"
    if re.search(r"\bwarn(ing)?\b", low):
        return "warn"
    if "throughput" in low:
        return "throughput"
    if "kv cache" in low:
        return "kv"
    if "ready on port" in low or "application startup complete" in low:
        return "ready"
    return "plain"


# lifecycle phase -> palette role (terminal) / CSS token (browser)
_LIFECYCLE_ROLE = {
    "FAILED": "warn",
    "COMPLETE": "teal",
    "STOPPED": "teal",
    "TEARDOWN": "teal",
    "PAUSED": "gold",
    "REMOTE": "cyan",
    "SORTING": "gold",
    "COLD BOOT": "gold",
    "DEPLOYING": "gold",
    "PREFLIGHT": "cyan",
    "QUEUED": "dim",
}

# phases with a pulsing lifecycle animation (terminal blink + browser pulse)
ANIMATED_PHASES = ("DEPLOYING", "COLD BOOT", "PREFLIGHT", "REMOTE", "SORTING")


# log class -> mailroom-ml palette role
_LOG_ROLE = {"error": "warn", "warn": "gold", "throughput": "cyan", "kv": "mint",
             "ready": "teal", "plain": "dim"}


def run_snapshot(store: RunStore) -> dict[str, Any]:
    """Everything the in-tray panel needs, read from the local run store."""
    lock = (store.read_lock() if store.lock_path.is_file() else None) or {}
    cp = (store.read_checkpoint() if store.checkpoint_path.is_file() else None) or {}
    items = store.load_items()
    modal = ((lock.get("engine") or {}).get("modal") or {}) if isinstance(lock, dict) else {}
    ok = [i for i in items if i.get("ok", True) is not False]
    errs = [i for i in items if i.get("ok") is False]
    lat = sorted(float(i["latency_ms"]) / 1000.0 for i in ok if i.get("latency_ms") is not None)
    scores = [
        float((i.get("score") or {}).get("overall_extraction_score"))
        for i in ok
        if isinstance((i.get("score") or {}).get("overall_extraction_score"), (int, float))
    ]
    p95 = lat[max(0, int(0.95 * len(lat) + 0.999999) - 1)] if lat else None
    prompt_tokens = _sum_int_field(items, "prompt_tokens")
    completion_tokens = _sum_int_field(items, "completion_tokens")
    return {
        "run_id": lock.get("run_id") or store.dir.name,
        "task": lock.get("task") or "?",
        "state": cp.get("state") or ("waiting" if not items else "running"),
        "done": max(int(cp.get("cursor") or 0), len(items)),
        "total": int(cp.get("total") or 0),
        "ok": len(ok),
        "errors": len(errs),
        "replicas": max(1, int(modal.get("max_containers") or 1)),
        "gpu": str(modal.get("gpu") or "L4"),
        "p50_s": round(statistics.median(lat), 3) if lat else None,
        "p95_s": round(p95, 3) if p95 is not None else None,
        "mean_score": round(statistics.mean(scores), 4) if scores else None,
        "last_error": (errs[-1].get("error") or "") if errs else "",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def _sum_int_field(items: list[dict[str, Any]], key: str) -> int:
    total = 0
    for row in items:
        value = row.get(key)
        if isinstance(value, (int, float)):
            total += int(value)
    return total


def _fmt(v: Any, suffix: str = "") -> str:
    return "—" if v is None else f"{v}{suffix}"


def _stage_for(run_id: str) -> str:
    if run_id.startswith("sand032-l"):
        return "LADDER"
    if run_id.startswith("sand032-s2"):
        return "SCALE-OUT"
    if run_id.startswith("sand032-s3"):
        return "SWEEP"
    if run_id.startswith("sand032-s4"):
        return "BF16"
    return "EVAL"


def _header(
    run_id: str,
    *,
    width: int,
    on: bool,
    subtitle: str | None = None,
    route_label: str | None = None,
    brand: str = "DIGITAL MAILROOM",
) -> list[str]:
    """mailroom-ml double-line frame + owl/amber THE MAILROOM, job subtitle."""
    p = pl.palette(on)
    inner = width - 2
    mark = pl._wordmark_lines(inner=inner, on=on, compact=width < 90)
    tag = run_id if len(run_id) <= 28 else run_id[:27] + "…"
    sub_path = subtitle or SUBTITLE_PATH
    route_txt = route_label or ROUTE
    if on:
        sub = p["brand"](brand) + p["dim"]("  ·  ") + p["snow"](sub_path) + p["dim"]("  ·  ") + p["gold"](tag)
        route = p["teal"](route_txt)
    else:
        sub = f"{brand}  ·  {sub_path}  ·  {tag}"
        route = route_txt
    top = pl.DTL + pl.DH * inner + pl.DTR
    bot = pl.DBL + pl.DH * inner + pl.DBR
    rows = [p["frame"](top) if on else top]
    rows += [pl._centered_row(line, width=width, on=on) for line in mark]
    rows += [pl._panel_row(sub, on=on, width=width), pl._panel_row(route, on=on, width=width)]
    rows.append(p["frame"](bot) if on else bot)
    return rows


# ── lifecycle (driver stamps + Modal boot log markers) ─────────────────────
BOOT_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("container starting", re.compile(r"sandbox-vllm serve config|launching vllm subprocess|secrets check", re.I)),
    ("loading weights", re.compile(r"loading weights|load(ing)? model|safetensors|model loading took|downloading", re.I)),
    ("profiling KV cache", re.compile(r"kv cache|memory profiling|# gpu blocks", re.I)),
    ("capturing CUDA graphs", re.compile(r"captur(e|ing) cuda graph|cudagraph|torch\.compile|compil(ing|ation)", re.I)),
    ("engine ready", re.compile(r"application startup complete|vllm ready on port", re.I)),
)
TEARDOWN_PHASES = ("TEARDOWN", "STOPPED")


def read_times(path: Path) -> dict[str, float]:
    """Parse the driver's ``"key": epoch,`` stamp lines (scripts/sand032/run_one.sh)."""
    out: dict[str, float] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*"([a-z_]+)":\s*([0-9.]+)', line)
        if m:
            out[m.group(1)] = float(m.group(2))
    return out


def _boot_detail(boot_lines: list[str]) -> str:
    detail = "container starting"
    for line in boot_lines:
        for name, pat in BOOT_MARKERS:
            if pat.search(line):
                detail = name
    return detail


def lifecycle(times: dict[str, float], boot_lines: list[str], *, now: float) -> dict[str, Any]:
    """Current phase of a run from its driver stamps; COLD BOOT sub-phase from logs."""
    def since(key: str) -> int:
        return int(max(0.0, now - times[key]))

    if "stopped" in times:
        return {"phase": "STOPPED", "detail": "fleet stopped · billing ended", "elapsed_s": since("stopped")}
    if "run_end" in times:
        return {"phase": "TEARDOWN", "detail": "metrics · serving record · evidence rows · stop", "elapsed_s": since("run_end")}
    if "run_start" in times:
        return {"phase": "SORTING", "detail": "specialist extraction in flight", "elapsed_s": since("run_start")}
    if "ready" in times:
        return {"phase": "PREFLIGHT", "detail": "engine verified · /metrics baseline", "elapsed_s": since("ready")}
    if "deploy_done" in times:
        return {"phase": "COLD BOOT", "detail": _boot_detail(boot_lines), "elapsed_s": since("deploy_done")}
    if "deploy_start" in times:
        return {"phase": "DEPLOYING", "detail": "modal deploy · image + app", "elapsed_s": since("deploy_start")}
    return {"phase": "QUEUED", "detail": "waiting for the driver", "elapsed_s": 0}


# ── persistent dispatch log ─────────────────────────────────────────────────
class LogBuffer:
    """Thread-safe tail of streamed Modal logs, mirrored to disk so history
    survives TUI restarts and run switches (never cleared between runs)."""

    def __init__(self, path: Path | None, *, maxlen: int = 2000) -> None:
        self._lines: deque[str] = deque(maxlen=maxlen)
        self._count = 0
        self.last_ts: float | None = None  # wall time of the last streamed line (watchdog LOGS rule)
        self.changed = threading.Event()  # set on every append; the render loop wakes on it
        self._lock = threading.Lock()
        self._path = path
        self._writer = False
        if path is not None:
            # One writer per log file: the first TUI instance takes an exclusive
            # lock; later instances display the stream but never append.
            import fcntl

            path.parent.mkdir(parents=True, exist_ok=True)
            self._lockfh = open(str(path) + ".lock", "a")
            try:
                fcntl.flock(self._lockfh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._writer = True
            except OSError:
                self._writer = False
        if path is not None and path.is_file():
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-maxlen:]:
                self._lines.append(line)
                self._count += 1

    def append(self, line: str) -> None:
        with self._lock:
            self._lines.append(line)
            self._count += 1
            self.last_ts = time.time()
            self.changed.set()
            if self._path is not None and self._writer:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")

    def mark(self) -> int:
        return self._count

    def since(self, mark: int) -> list[str]:
        with self._lock:
            n = max(0, min(self._count - mark, len(self._lines)))
            return list(self._lines)[-n:] if n else []

    def tail(self, n: int) -> list[str]:
        with self._lock:
            return list(self._lines)[-n:]

    def last(self) -> str | None:
        with self._lock:
            return self._lines[-1] if self._lines else None


# SAND-032 program route: (run_id, replicas) in execution order.
PROGRAM: tuple[tuple[str, int], ...] = (
    ("sand032-l0-baseline", 1), ("sand032-l1-nothink", 1), ("sand032-l2-marlin", 1),
    # L3/L4 folded into L5: warm flow boots the frozen config ONCE (engine
    # args are fixed at boot, so per-knob rungs would each cost a restart).
    ("sand032-l5-graphs", 1),
    ("sand032-s2a-corr100-1rep", 1), ("sand032-s2b-corr100-2rep", 2),
    ("sand032-s3-corr50", 2), ("sand032-s3-insurance50", 2), ("sand032-s3-corporate50", 2),
    ("sand032-s3-merger50", 2), ("sand032-s3-contracts50", 2), ("sand032-s3-corr50-repeat", 2),
    ("sand032-s4-corr20-bf16", 1),
)


def program_lines(times_dir: Path, *, current: str, width: int = 100, on: bool = False) -> list[str]:
    """✓ done · ▶ live · · queued — every run with its fleet (×1 / ×2 L4)."""
    p = pl.palette(on)
    cells = []
    for rid, rep in PROGRAM:
        t = read_times(times_dir / f"{rid}.times")
        done = "stopped" in t or ("run_end" in t and rid != current)
        mark = "✓" if done else ("▶" if rid == current or t else "·")
        text = f"{mark} {rid.removeprefix('sand032-')} ×{rep}"
        role = {"✓": "teal", "▶": "gold", "·": "dim"}[mark]
        cells.append((text, p[role](text) if on else text))
    col = max(len(t) for t, _ in cells) + 2
    per_row = max(1, (width - 4) // col)
    rows = []
    for i in range(0, len(cells), per_row):
        chunk = cells[i : i + per_row]
        rows.append("".join(styled + " " * (col - len(plain)) for plain, styled in chunk).rstrip())
    return rows


NOISE = re.compile(r'"GET /(metrics|v1/models|health)|GET /(metrics|v1/models|health) ->')


def display_tail(buf: "LogBuffer", n: int) -> list[str]:
    """On-screen tail without our own /metrics + probe chatter (file keeps all)."""
    return [line for line in buf.tail(n * 20) if not NOISE.search(line)][-n:]


# ── scorecard ───────────────────────────────────────────────────────────────
def scorecard_lines(store: RunStore, *, serving_dir: Path, width: int = 100, on: bool = False) -> list[str]:
    """Post-run scorecard: items (quality) + serving record (speed/cost) + /metrics."""
    p = pl.palette(on)
    snap = run_snapshot(store)
    mw = max(40, width - 4)
    items = store.load_items()
    schema = [
        (i.get("score") or {}).get("parse_error") is False
        for i in items
        if "parse_error" in (i.get("score") or {})
    ]
    rec: dict[str, Any] = {}
    path = serving_dir / f"{snap['run_id']}.serving.json"
    if not path.is_file():
        matches = sorted(serving_dir.rglob(path.name))
        if len(matches) == 1:
            path = matches[0]
    if path.is_file():
        try:
            rec = json.loads(path.read_text())
        except ValueError:
            rec = {}
    scores = rec.get("scores") or {}
    score = scores.get("overall_extraction_score", snap["mean_score"])
    valid = scores.get("schema_valid_rate", round(sum(schema) / len(schema), 4) if schema else None)
    n = int(rec.get("n") or snap["done"] or 0)
    tokens = (rec.get("prompt_tokens") or 0, rec.get("completion_tokens") or 0)

    def m(label: str, value: Any) -> str:
        return pl._metric(label, str(value), label_w=18, total_w=mw, on=on)

    lines = [
        m("sorted", f"delivered {snap['ok']} · returned {snap['errors']} · of {snap['total'] or n}"),
        m("overall score", _fmt(score)),
        m("schema valid", _fmt(valid)),
    ]
    if rec:
        per_doc = rec.get("gpu_cost_per_document")
        lines += [
            m("wall", _fmt(rec.get("wall_seconds"), " s")),
            m("cold boot", _fmt(rec.get("cold_boot_seconds"), " s")),
            m("postmark p50/p95", f"{_fmt(rec.get('latency_p50_seconds'), 's')} / {_fmt(rec.get('latency_p95_seconds'), 's')}"),
            m("throughput", _fmt(rec.get("tokens_per_second"), " tok/s")),
            m("tokens in/out", f"{tokens[0]} / {tokens[1]}"),
            m("GPU $ (busy)", f"${rec.get('estimated_gpu_cost_usd', 0):.4f}"),
            m("$/doc", "—" if per_doc is None else f"${per_doc:.5f}"),
            m("run span ≥", f"${rec.get('run_span_usd_lower_bound', 0):.4f} (×{rec.get('replicas', 1)} GPU)"),
        ]
    else:
        lines.append(p["dim"]("serving record pending …") if on else "serving record pending …")
    mpath = store.dir / "vllm_metrics_after.json"
    if mpath.is_file():
        try:
            met = json.loads(mpath.read_text())
        except ValueError:
            met = {}
        lines.append(m("/metrics", met.get("coverage", "—")))
        for key, rep in sorted((met.get("replicas") or {}).items()):
            hit = rep.get("prefix_cache_hit_rate")
            lines.append(
                m(
                    f"replica {key[-6:]}",
                    f"ttft {_fmt(rep.get('ttft_mean_seconds'), 's')} · prefix "
                    f"{'—' if hit is None else f'{100 * hit:.1f}%'} · preempt {_fmt(rep.get('preemptions'))}"
                    f" · len-cut {_fmt(rep.get('length_finishes'))}",
                )
            )
    return lines


def render_frame(
    *,
    snapshot: dict[str, Any],
    app: str,
    log_lines: list[str],
    spend: dict[str, float],
    width: int = 100,
    on: bool = False,
    blink: bool = False,
    lifecycle: dict[str, Any] | None = None,
    scorecard: list[str] | None = None,
    route: list[str] | None = None,
    job_route: list[str] | None = None,
    layout: dict[str, Any] | None = None,
    watchdog: Mapping[str, Any] | None = None,
    log_rows: int = 14,
) -> str:
    width = max(60, min(int(width), pl.MAX_W))
    p = pl.palette(on)
    s = snapshot
    lay = layout or {}
    panels = lay.get("panels") or {}
    stage_tag = lay.get("stage") or _stage_for(s["run_id"])
    out: list[str] = _header(
        s["run_id"],
        width=width,
        on=on,
        subtitle=lay.get("subtitle"),
        route_label=lay.get("route_label"),
        brand=str(lay.get("brand") or "DIGITAL MAILROOM"),
    )
    watcher = lay.get("watcher_label") or f"Tray TUI watcher · app {app}"
    out.append(
        pl.render_status_bar(
            timestamp=time.strftime("%H:%M:%S") + f" · {watcher}",
            stage=(lifecycle or {}).get("phase") or stage_tag,
            on=on,
            width=width,
            blink=blink,
        )
    )

    if lifecycle:
        el = int(lifecycle.get("elapsed_s") or 0)
        phase = f"▸{lifecycle['phase']}◂  {lifecycle.get('detail', '')}  ·  {el // 60}m{el % 60:02d}s  ·  {stage_tag}"
        life_title = panels.get("lifecycle") or "Lifecycle"
        role = _LIFECYCLE_ROLE.get(str(lifecycle.get("phase") or ""), "gold")
        out.append(pl._box(life_title, [p[role](phase) if on else phase], width=width, on=on))

    if watchdog:
        from mailroom_sandbox.tui import watchdog as wd

        level = watchdog.get("level") or "ok"
        dog_title = {"critical": "■ WATCHDOG · ACTION NEEDED", "warn": "▲ WATCHDOG"}.get(level, "WATCHDOG")
        out.append(pl._box(dog_title, wd.panel_lines(watchdog, on=on, palette=p), width=width, on=on))

    if route:
        title = panels.get("program") or "Program route"
        out.append(pl._box(title, route, width=width, on=on))
    elif job_route:
        out.append(pl._box("JOB · run manifest", job_route, width=width, on=on))

    wide = width >= 100
    box_w = (width - 2) // 2 if wide else width
    mw = box_w - 4
    bar = progress_bar(s["done"], s["total"], width=max(10, mw - 14))
    tray = [
        pl._metric("run", s["run_id"], total_w=mw, on=on),
        pl._metric("specialist", s["task"], total_w=mw, on=on),
        pl._metric("fleet", f"×{s['replicas']} {s['gpu']} · {s['state']}", total_w=mw, on=on),
        (p["cyan"](bar) if on else bar) + f"  {s['done']}/{s['total']}",
        pl._metric("sorted", f"delivered {s['ok']} · returned {s['errors']}", total_w=mw, on=on),
        pl._metric("postmark", f"p50 {_fmt(s['p50_s'], 's')} · p95 {_fmt(s['p95_s'], 's')}", total_w=mw, on=on),
        pl._metric("score", _fmt(s["mean_score"]), total_w=mw, on=on),
    ]
    if s.get("last_error"):
        err = f"last return: {s['last_error']}"
        tray.append(p["warn"](err) if on else err)
    tray_title = panels.get("tray") or f"{pl.owl_emoticon(on=False)} IN-TRAY"
    tray_box = pl._box(tray_title, tray, width=box_w, on=on)

    spent = float(spend.get("spent_usd") or 0.0)
    live = float(spend.get("live_usd") or 0.0)
    cap = float(spend.get("cap_usd") or 5.0)
    # compose_watch_state binds ledger and live to the same run when there is no ledger; its
    # total_usd is authoritative (spent + live would count the open run twice).
    total = float(spend["total_usd"]) if spend.get("total_usd") is not None else spent + live
    pbar = progress_bar(int(total * 100), int(cap * 100), width=max(10, mw - 14))
    postage = [
        pl._metric("sorted", f"delivered {s['ok']} · returned {s['errors']}", total_w=mw, on=on),
        pl._metric("docs", f"{s['done']}/{s['total']}", total_w=mw, on=on),
        pl._metric(
            "tokens",
            f"{int(s.get('prompt_tokens') or 0)} in · {int(s.get('completion_tokens') or 0)} out",
            total_w=mw,
            on=on,
        ),
        pl._metric("ledger", f"${spent:.4f}", total_w=mw, on=on),
        pl._metric("live run", f"${live:.4f}", total_w=mw, on=on),
        pl._metric("total", f"${total:.4f} / ${cap:.2f}", total_w=mw, on=on),
        (p["gold"](pbar) if on else pbar) + f"  {100 * total / cap:.0f}%",
        pl._metric("gate", f"${GATE_USD:.2f} projected-total stop", total_w=mw, on=on),
    ]
    if total > GATE_USD:
        warn = f"⚠ OVER ${GATE_USD:.2f} GATE — stop and reconcile"
        postage.append(p["warn"](warn) if on else warn)
    postage_title = panels.get("postage") or "POSTAGE ($)"
    postage_box = pl._box(postage_title, postage, width=box_w, on=on)
    if wide:
        out.append(pl._side_by_side(tray_box, postage_box, gap=2))
    else:
        out += [tray_box, postage_box]

    show_sc = scorecard and (
        not lifecycle
        or lifecycle.get("phase") in TEARDOWN_PHASES
        or lifecycle.get("phase") in ("COMPLETE", "STOPPED", "FAILED")
    )
    if show_sc:
        sc_title = panels.get("scorecard") or f"📊 SCORECARD · {s['run_id']}"
        out.append(pl._box(sc_title, scorecard, width=width, on=on))

    tail = log_lines[-max(4, int(log_rows)):]
    log = [
        (p[_LOG_ROLE[classify_log_line(line)]](line) if on else line) for line in tail
    ] or [p["dim"]("(waiting on modal app logs …)") if on else "(waiting on modal app logs …)"]
    dispatch_title = panels.get("dispatch") or f"DISPATCH LOG · modal app logs {app}"
    out.append(pl._box(dispatch_title, log, width=width, on=on))
    return "\n".join(out)


RECONNECT_NOTE = "… waiting for app (stopped between runs or booting) — will attach when it is live"


def log_command(app: str) -> list[str]:
    """`modal app logs <app>` fetches 100 lines and exits — `-f` streams live."""
    return ["modal", "app", "logs", "-f", app]


def note_reconnect(sink: Any) -> None:
    last = sink.last() if isinstance(sink, LogBuffer) else (sink[-1] if sink else None)
    if last != RECONNECT_NOTE:
        sink.append(RECONNECT_NOTE)


def _stream_logs(app: str, sink: Any, stop: threading.Event, *, prefix: str = "") -> None:
    """Follow `modal app logs <app>` into ``sink``; restart if the stream drops."""
    while not stop.is_set():
        try:
            proc = subprocess.Popen(
                log_command(app),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            sink.append("ERROR modal CLI not found on PATH — logs unavailable")
            return
        assert proc.stdout is not None
        for raw in proc.stdout:
            if stop.is_set():
                break
            line = raw.rstrip()
            if line:
                sink.append(f"{prefix}{line}" if prefix else line)
        proc.terminate()
        if not stop.is_set():
            note_reconnect(sink)
            stop.wait(10)


def start_log_streams(store: RunStore, app: str, sink: Any, stop: threading.Event) -> list[threading.Thread]:
    """Start one Modal stream per dispatch source; worker lines get a tag."""
    from mailroom_sandbox.tui import tray_context as tc

    src = tc.dispatch_source(store, cli_app=app)
    threads: list[threading.Thread] = []
    serve = src["serve_app"]
    t = threading.Thread(target=_stream_logs, args=(serve, sink, stop), daemon=True)
    t.start()
    threads.append(t)
    worker = src.get("worker_app")
    if worker and worker != serve:
        tw = threading.Thread(
            target=_stream_logs, args=(worker, sink, stop), kwargs={"prefix": "[worker] "}, daemon=True
        )
        tw.start()
        threads.append(tw)
    return threads


def read_ledger(ledger: Path | None) -> tuple[float, bool]:
    """(spent_usd, includes_live). ``includes_live`` = the ledger already counts
    the open fleet's time, so the TUI must not add its own live estimate."""
    if ledger is None or not ledger.is_file():
        return 0.0, False
    try:
        data = json.loads(ledger.read_text())
        return float(data.get("spent_usd") or 0.0), bool(data.get("includes_live"))
    except (ValueError, OSError):
        return 0.0, False


def _live_run_usd(store: RunStore, snap: Mapping[str, Any], started: float) -> float:
    """GPU $ for the open job. Running cells extend first-item ts → now so $ ticks."""
    from mailroom_sandbox.job.metrics import _parse_item_ts, estimate_gpu_cost_usd

    now = time.time()
    watch_wall = max(0.0, now - started)
    stamps: list[float] = []
    for row in store.load_items():
        ts = _parse_item_ts(row.get("ts"))
        if ts is not None:
            stamps.append(ts)
    for ev in store.events():
        ts = _parse_item_ts(ev.get("ts"))
        if ts is not None:
            stamps.append(ts)
    if stamps:
        span = (now - min(stamps)) if str(snap.get("state")) == "running" else (max(stamps) - min(stamps))
        wall = max(watch_wall, span)
    else:
        wall = watch_wall
    if wall <= 0:
        return 0.0
    return float(
        estimate_gpu_cost_usd(wall, gpu=snap.get("gpu"), replicas=int(snap.get("replicas") or 1))
        or 0.0
    )


def compose_watch_state(
    *,
    store: RunStore,
    app: str,
    sink: LogBuffer,
    ledger: Path | None,
    cap_usd: float,
    times_dir: Path | None,
    serving_dir: Path,
    started: float,
    boot_mark: dict[str, int],
    width: int = 100,
    blink: bool = False,
    log_rows: int = 14,
) -> dict[str, Any]:
    """JSON-serializable Tray TUI snapshot (terminal + browser)."""
    from mailroom_sandbox.tui import tray_context as tc

    snap = run_snapshot(store)
    layout = tc.build_tray_layout(
        store, app=app, times_dir=times_dir, cap_usd=cap_usd, gate_usd=GATE_USD, width=width
    )
    cap_usd = float(layout.get("cap_usd") or cap_usd)
    times_file = tc.resolve_times_file(store, times_dir)
    times = read_times(times_file) if times_file else {}
    key = f"{snap['run_id']}@{times.get('deploy_done', times.get('ready', 0))}"
    boot_mark.setdefault(key, sink.mark())
    boot_lines = sink.since(boot_mark[key])
    life = tc.resolve_lifecycle(store, times, boot_lines, now=time.time())
    cp_state = snap.get("state")
    # Belt: even if a times-file race returns COLD BOOT, in-flight docs are SORTING.
    if str(cp_state) == "running" and (life or {}).get("phase") in {
        "COLD BOOT",
        "DEPLOYING",
        "QUEUED",
        "PREFLIGHT",
    }:
        life = tc.lifecycle_from_store(store, boot_lines, now=time.time())
    card = (
        scorecard_lines(store, serving_dir=serving_dir, width=width, on=False)
        if tc.show_scorecard((life or {}).get("phase"), cp_state)
        else None
    )
    spent, includes_live = read_ledger(ledger)
    run_usd = _live_run_usd(store, snap, started)
    if includes_live:
        live = 0.0
        total = spent
    elif spent <= 0.0:
        # No suite spend.json — the Postage "ledger" row used to sit at $0.0000
        # forever while only "live run" ticked. Bind both to the current job.
        spent = run_usd
        live = run_usd
        total = run_usd
    else:
        live = run_usd
        total = spent + live
    spend = {
        "spent_usd": spent,
        "live_usd": live,
        "cap_usd": cap_usd,
        "gate_usd": GATE_USD,
        "ok": snap["ok"],
        "errors": snap["errors"],
        "done": snap["done"],
        "n": snap["total"],
        "prompt_tokens": snap.get("prompt_tokens") or 0,
        "completion_tokens": snap.get("completion_tokens") or 0,
        "total_tokens": snap.get("total_tokens") or 0,
    }
    spend["total_usd"] = total
    spend["pct_of_cap"] = round(100 * total / cap_usd, 1) if cap_usd else 0.0
    spend["over_gate"] = total > GATE_USD
    spend["bar"] = progress_bar(int(total * 100), int(cap_usd * 100), width=30)
    from mailroom_sandbox.tui import watchdog as wd

    items = store.load_items()
    run_started = None
    for ev in store.events():
        t = wd._ts(ev.get("ts"))
        if t is not None and ev.get("event") in ("preflight_ok", "cold_boot", "start", "resume"):
            run_started = t  # latest (re)start of this run
    if run_started is None and items:
        run_started = wd._ts(items[0].get("ts"))
    lock = (store.read_lock() if store.lock_path.is_file() else None) or {}
    job_knobs = (lock.get("job") or {}) if isinstance(lock, dict) else {}
    dog = wd.assess(
        items=items,
        state=str(cp_state or ""),
        total=int(snap.get("total") or 0),
        spend=spend,
        now=time.time(),
        p95_s=snap.get("p95_s"),
        run_started=run_started,
        log_lines=boot_lines,
        last_log_ts=sink.last_ts,
        logs_enabled=sink.last_ts is not None,
        concurrency=job_knobs.get("concurrency"),
        max_wall_s=job_knobs.get("max_wall_seconds"),
    )
    log_src = display_tail(sink, max(14, int(log_rows)))
    logs = [{"text": line, "role": classify_log_line(line), "source": "modal"} for line in log_src]
    for entry in tc.job_event_lines(store, limit=4):
        logs.append(
            {"text": entry["text"], "role": entry["role"], "source": "job"}
        )
    logs = logs[-max(14, int(log_rows)):]
    # Alerts lead the dispatch feed too, so the browser view (`--web`) carries them.
    logs = [
        {"text": f"{a['code']}: {a['text']}", "role": "error" if a["level"] == "critical" else "warn", "source": "watchdog"}
        for a in dog["alerts"]
        if a["level"] != "info"
    ] + logs
    route = layout.get("route")
    job_route = layout.get("job_route")
    phase = (life or {}).get("phase") or layout.get("stage") or _stage_for(snap["run_id"])
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "app": app,
        "snapshot": snap,
        "spend": spend,
        "lifecycle": life,
        "scorecard": card,
        "route": route,
        "job_route": job_route,
        "layout": layout,
        "logs": logs,
        "subtitle": layout.get("subtitle") or SUBTITLE_PATH,
        "route_label": layout.get("route_label") or ROUTE,
        "stage": phase,
        "watcher_label": layout.get("watcher_label"),
        "profile": layout.get("profile"),
        "job_mode": layout.get("job_mode"),
        "progress": {
            "done": snap["done"],
            "total": snap["total"],
            "bar": progress_bar(snap["done"], snap["total"], width=30),
        },
        "blink": blink and phase in ANIMATED_PHASES,
        "animate_lifecycle": phase in ANIMATED_PHASES,
        "lifecycle_role": _LIFECYCLE_ROLE.get(phase, "gold"),
        "watchdog": dog,
    }


def _watch_paths(
    store: RunStore,
    *,
    times_dir: Path | None,
    sand032_root: Path | None,
    log_path: Path | None,
) -> tuple[Path | None, Path]:
    from mailroom_sandbox.tui import tray_context as tc

    if log_path is not None:
        resolved_log = log_path
    else:
        _, resolved_log = tc.resolve_watch_paths(store, sand032_root=sand032_root)
    if times_dir is not None:
        return times_dir, resolved_log
    td, _ = tc.resolve_watch_paths(store, sand032_root=sand032_root)
    return td, resolved_log


SYNC_BEGIN = "\033[?2026h"  # synchronized update: the terminal paints the frame at once (no tearing)
SYNC_END = "\033[?2026l"
ERASE_EOL = "\033[K"
ERASE_BELOW = "\033[J"
BELL = "\a"
FRAME_TICK_S = 0.25  # how often the loop checks for new logs / run-store changes


def paint(frame: str, rows: int | None = None) -> str:
    """Repaint in place: home, each line + erase-to-EOL, erase below — no full-screen clear (no flicker)."""
    lines = frame.split("\n")
    if rows:
        lines = lines[: max(1, rows - 1)]
    return SYNC_BEGIN + pl.CURSOR_HOME + (ERASE_EOL + "\n").join(lines) + ERASE_EOL + "\n" + ERASE_BELOW + SYNC_END


def log_rows_for(rows: int) -> int:
    """Dispatch-log height that fills the terminal below the fixed panels."""
    return max(6, min(60, rows - 44))


def _store_sig(store: RunStore) -> tuple:
    sig = []
    for path in (store.checkpoint_path, store.dir / "items.jsonl", store.dir / "events.jsonl"):
        try:
            st = path.stat()
            sig.append((st.st_mtime_ns, st.st_size))
        except OSError:
            sig.append(None)
    return tuple(sig)


def new_critical(dog: Mapping[str, Any] | None, seen: set[str]) -> list[str]:
    """Critical alert codes not yet announced (the bell rings once per code)."""
    codes = [a["code"] for a in (dog or {}).get("alerts") or [] if a["level"] == "critical"]
    fresh = [c for c in codes if c not in seen]
    seen.update(codes)
    return fresh


def watch(
    *,
    resolve: Callable[[], tuple[RunStore, str]],
    ledger: Path | None,
    cap_usd: float = 5.0,
    once: bool = False,
    logs: bool = True,
    interval: float = 1.0,
    times_dir: Path | None = None,
    sand032_root: Path | None = None,
    log_path: Path | None = None,
    serving_dir: Path | None = None,
    bell: bool = True,
) -> int:
    """Live Tray TUI. Redraws when a log line lands or the run store changes, and at
    least every ``interval`` seconds (clocks, spend), painting in place without clearing."""
    from mailroom_sandbox.paths import reports_dir

    serving_dir = serving_dir or (reports_dir() / "serving")
    store, _app = resolve()
    _td, resolved_log = _watch_paths(
        store, times_dir=times_dir, sand032_root=sand032_root, log_path=log_path
    )
    sink = LogBuffer(resolved_log)
    stop = threading.Event()
    store, app = resolve()
    if not once:
        sys.stdout.write(pl.ALT_ENTER + pl.HIDE_CURSOR + pl.CLEAR_SCREEN)
    if logs and not once:
        start_log_streams(store, app, sink, stop)
    started = time.time()
    boot_mark: dict[str, int] = {}
    announced: set[str] = set()
    last_frame = ""
    last_sig: tuple | None = None
    last_paint = 0.0
    last_size: tuple[int, int] | None = None
    interval = max(0.25, float(interval or 1.0))
    try:
        while True:
            store, app = resolve()  # --follow: the current run can change between frames
            size = shutil.get_terminal_size((100, 40))
            sig = (store.dir, _store_sig(store))
            due = (
                once
                or sink.changed.is_set()
                or sig != last_sig
                or (size.columns, size.lines) != last_size
                or time.time() - last_paint >= interval
            )
            if not due:
                stop.wait(FRAME_TICK_S)
                continue
            sink.changed.clear()
            last_sig, last_size = sig, (size.columns, size.lines)
            frame_times_dir, _ = _watch_paths(
                store, times_dir=times_dir, sand032_root=sand032_root, log_path=log_path
            )
            width = size.columns
            rows = log_rows_for(size.lines)
            blink = int(time.time()) % 7 == 0
            state = compose_watch_state(
                store=store,
                app=app,
                sink=sink,
                ledger=ledger,
                cap_usd=cap_usd,
                times_dir=frame_times_dir,
                serving_dir=serving_dir,
                started=started,
                boot_mark=boot_mark,
                width=width,
                blink=blink,
                log_rows=rows,
            )
            frame = render_frame(
                snapshot=state["snapshot"],
                app=app,
                log_lines=[e["text"] for e in state["logs"]],
                spend=state["spend"],
                width=width,
                on=pl.use_color(sys.stdout),
                blink=blink,
                lifecycle=state["lifecycle"],
                scorecard=state["scorecard"],
                route=state["route"],
                job_route=state.get("job_route"),
                layout=state.get("layout"),
                watchdog=state.get("watchdog"),
                log_rows=rows,
            )
            if once:
                sys.stdout.write(frame + "\n")
                return 0
            last_paint = time.time()
            ring = bell and new_critical(state.get("watchdog"), announced)
            if frame != last_frame or ring:
                sys.stdout.write(paint(frame, size.lines) + (BELL if ring else ""))
                sys.stdout.flush()
                last_frame = frame
    except KeyboardInterrupt:
        return 0
    finally:
        stop.set()
        if not once:
            sys.stdout.write(pl.SHOW_CURSOR + pl.ALT_LEAVE)
            sys.stdout.flush()


def print_scorecard(store: RunStore, *, serving_dir: Path, width: int | None = None) -> int:
    """`sandbox scorecard --run <id>`: one-shot mailroom scorecard for a finished run."""
    width = max(60, min(width or shutil.get_terminal_size((100, 40)).columns, pl.MAX_W))
    on = pl.use_color(sys.stdout)
    snap = run_snapshot(store)
    from mailroom_sandbox.tui import tray_context as tc

    layout = tc.build_tray_layout(store, app="—", times_dir=None, cap_usd=5.0, gate_usd=GATE_USD, width=width)
    out = _header(
        snap["run_id"],
        width=width,
        on=on,
        subtitle=layout.get("subtitle"),
        route_label=layout.get("route_label"),
    )
    out.append(pl._box(f"📊 SCORECARD · {snap['run_id']}", scorecard_lines(store, serving_dir=serving_dir, width=width, on=on), width=width, on=on))
    sys.stdout.write("\n".join(out) + "\n")
    return 0
