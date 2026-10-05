"""Watchdog for the Tray TUI (`sandbox watch`): turns run-store + log state into alerts.

Pure functions over what the watcher already reads (items, checkpoint state,
spend, the Modal log tail), so every rule is unit-testable without a clock or
a fleet. Levels: ``critical`` (act now — the run is burning money or failing),
``warn`` (look soon), ``info`` (context). ``assess()`` also derives the live
rate, ETA and spend projection the panel shows.

Rules (thresholds are module constants so tests and operators can read them):

* AUTH      any 401 / authentication error — the SAND-038 failure class.
* BURST     the last ``BURST_N`` finished documents all failed.
* ERRORS    error share ≥ ``ERROR_RATE_WARN`` once ``ERROR_RATE_MIN_DONE`` are done.
* LENGTH    output-cap truncations (LengthFinishReasonError) — runaway decodes.
* STALL     running, but no document finished within the adaptive limit
            (``stall_limit``): ``STALL_FACTOR`` × the run's average document time
            (never under 1.5 × p95 or ``STALL_FLOOR_S``). Before the first document
            finishes it uses the run's wall budget per wave of in-flight documents, so
            slow whole-document cells (chunked merger, ~10 min/doc) don't false-alarm.
* SPEND     projected total at completion above the cap (warn) or the gate (critical).
* ENGINE    Modal log shows a traceback, CUDA OOM, or engine death since the run began.
* LOGS      running, but the Modal log stream has been silent for ``LOG_SILENT_S``.
* FAILED    the checkpoint says the run failed.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable, Mapping

BURST_N = 3
ERROR_RATE_WARN = 0.10
ERROR_RATE_MIN_DONE = 10
STALL_FLOOR_S = 180.0
STALL_FACTOR = 3.0  # × average document time
STALL_P95_FACTOR = 1.5
LOG_SILENT_S = 300.0
RATE_WINDOW = 12  # recent documents used for the live rate
SPARK_BUCKET_S = 60.0
SPARK_BUCKETS = 20
SPARK = "▁▂▃▄▅▆▇█"

_LEVEL_ORDER = {"critical": 0, "warn": 1, "info": 2}
_ENGINE_FATAL = re.compile(
    r"traceback|cuda out of memory|outofmemoryerror|engine (core )?(dead|died)|enginedeaderror|"
    r"runtimeerror|segmentation fault|killed",
    re.I,
)
_AUTH = re.compile(r"\b401\b|authenticationerror|unauthori[sz]ed|invalid api key", re.I)


def _ts(value: Any) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def error_kind(error: Any) -> str:
    """Short kind for an item error string (``LengthFinishReasonError: …`` → that name)."""
    text = str(error or "").strip()
    if not text:
        return "error"
    if _AUTH.search(text):
        return "Auth401"
    m = re.match(r"([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Timeout))\b", text)
    if m:
        return m.group(1).rsplit(".", 1)[-1]
    if "timeout" in text.lower() or "timed out" in text.lower():
        return "Timeout"
    return text.split(":", 1)[0][:32] or "error"


def error_kinds(items: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in items:
        if row.get("ok") is False:
            k = error_kind(row.get("error"))
            out[k] = out.get(k, 0) + 1
    return out


def sparkline(stamps: list[float], *, now: float, buckets: int = SPARK_BUCKETS, width_s: float = SPARK_BUCKET_S) -> str:
    """Documents finished per bucket over the last ``buckets × width_s`` seconds."""
    counts = [0] * buckets
    start = now - buckets * width_s
    for t in stamps:
        if start <= t <= now:
            counts[min(buckets - 1, int((t - start) // width_s))] += 1
    peak = max(counts)
    if peak == 0:
        return SPARK[0] * buckets
    return "".join(SPARK[min(len(SPARK) - 1, round(c / peak * (len(SPARK) - 1)))] for c in counts)


def stall_limit(
    items: Iterable[Mapping[str, Any]],
    *,
    total: int = 0,
    concurrency: int | None = None,
    max_wall_s: float | None = None,
    p95_s: float | None = None,
) -> tuple[float, str]:
    """Seconds without a finished document before STALL fires, and the basis shown to the operator.

    Tracks the run's own pace: ``STALL_FACTOR`` × the mean document latency once any
    document has finished. Before that, the wall budget per wave
    (``max_wall_s`` / ⌈total / concurrency⌉) stands in for the unknown document time.
    """
    lat = [float(r["latency_ms"]) / 1000.0 for r in items if isinstance(r.get("latency_ms"), (int, float))]
    if lat:
        avg = sum(lat) / len(lat)
        limit = max(STALL_FLOOR_S, STALL_FACTOR * avg, STALL_P95_FACTOR * float(p95_s or 0.0))
        return limit, f"{STALL_FACTOR:g}× avg doc {avg:.0f}s"
    if p95_s:
        return max(STALL_FLOOR_S, STALL_FACTOR * float(p95_s)), f"{STALL_FACTOR:g}× p95"
    if max_wall_s and total:
        waves = max(1, -(-int(total) // max(1, int(concurrency or 1))))
        budget = float(max_wall_s) / waves
        if budget > STALL_FLOOR_S:
            return budget, "wall budget per wave (no doc finished yet)"
    return STALL_FLOOR_S, "floor"


def assess(
    *,
    items: list[Mapping[str, Any]],
    state: str,
    total: int,
    spend: Mapping[str, Any],
    now: float,
    p95_s: float | None = None,
    run_started: float | None = None,
    log_lines: Iterable[str] = (),
    last_log_ts: float | None = None,
    logs_enabled: bool = True,
    concurrency: int | None = None,
    max_wall_s: float | None = None,
) -> dict[str, Any]:
    """Alerts + live rate / ETA / projection for the current run."""
    alerts: list[dict[str, str]] = []

    def alert(level: str, code: str, text: str) -> None:
        alerts.append({"level": level, "code": code, "text": text})

    state = str(state or "")
    running = state == "running"
    done = len(items)
    errs = [r for r in items if r.get("ok") is False]
    kinds = error_kinds(items)
    stamps = sorted(t for t in (_ts(r.get("ts")) for r in items) if t is not None)

    if state == "failed":
        alert("critical", "FAILED", "run failed — check the dispatch log and `sandbox run status`")
    if kinds.get("Auth401"):
        alert(
            "critical",
            "AUTH",
            f"{kinds['Auth401']} doc(s) rejected 401 — wrong key reaching the endpoint (SAND-038); cancel and fix",
        )
    recent = list(items)[-BURST_N:]
    if len(recent) == BURST_N and all(r.get("ok") is False for r in recent):
        alert("critical", "BURST", f"last {BURST_N} documents all failed ({error_kind(recent[-1].get('error'))})")
    if done >= ERROR_RATE_MIN_DONE and errs and len(errs) / done >= ERROR_RATE_WARN:
        alert("warn", "ERRORS", f"error share {len(errs) / done:.0%} ({len(errs)}/{done})")
    if kinds.get("LengthFinishReasonError"):
        alert(
            "warn" if kinds["LengthFinishReasonError"] > 1 else "info",
            "LENGTH",
            f"{kinds['LengthFinishReasonError']} output-cap truncation(s) — runaway decode at max_tokens",
        )

    # stall: time since the last finished document (or since start, before the first)
    stall_after, stall_basis = stall_limit(
        items, total=total, concurrency=concurrency, max_wall_s=max_wall_s, p95_s=p95_s
    )
    anchor = stamps[-1] if stamps else run_started
    idle_s = (now - anchor) if (running and anchor) else None
    if idle_s is not None and idle_s > stall_after and done < (total or done + 1):
        alert(
            "critical",
            "STALL",
            f"no document finished for {fmt_eta(idle_s)} (limit {fmt_eta(stall_after)}, {stall_basis}) — "
            "check endpoint health and the dispatch log",
        )

    # live rate over the recent window → ETA → spend projection
    rate = None
    if len(stamps) >= 2:
        window = stamps[-RATE_WINDOW:]
        span = max(window[-1] - window[0], 1e-6)
        if running:
            span = max(span, now - window[0])
        rate = (len(window) - 1) / span * 60.0 if len(window) > 1 else None
    remaining = max(0, int(total or 0) - done)
    eta_s = remaining / rate * 60.0 if rate and remaining and running else (0.0 if not remaining else None)
    total_usd = float(spend.get("total_usd") or 0.0)
    live_usd = float(spend.get("live_usd") or 0.0)
    cap = float(spend.get("cap_usd") or 0.0)
    gate = float(spend.get("gate_usd") or 0.0)
    projected = None
    if running and eta_s is not None and run_started:
        elapsed = max(1.0, now - run_started)
        burn = live_usd / elapsed  # $/s of the open run
        projected = total_usd + burn * eta_s
        if gate and projected > gate:
            alert("critical", "SPEND", f"projected ${projected:.2f} at completion exceeds the ${gate:.2f} gate")
        elif cap and projected > cap:
            alert("warn", "SPEND", f"projected ${projected:.2f} at completion exceeds the ${cap:.2f} cap")

    lines = list(log_lines)
    fatal = [line for line in lines if _ENGINE_FATAL.search(line)]
    if fatal:
        alert("critical", "ENGINE", f"engine fault in Modal log: {fatal[-1].strip()[:90]}")
    if logs_enabled and running and last_log_ts is not None and now - last_log_ts > LOG_SILENT_S:
        alert("warn", "LOGS", f"Modal log stream silent for {int((now - last_log_ts) // 60)}m — stream may have dropped")

    alerts.sort(key=lambda a: _LEVEL_ORDER.get(a["level"], 9))
    level = alerts[0]["level"] if alerts else "ok"
    return {
        "level": level,
        "alerts": alerts,
        "rate_dpm": round(rate, 2) if rate else None,
        "eta_s": round(eta_s) if eta_s is not None else None,
        "projected_usd": round(projected, 4) if projected is not None else None,
        "idle_s": round(idle_s) if idle_s is not None else None,
        "stall_after_s": round(stall_after),
        "stall_basis": stall_basis,
        "docs_timed": bool(stamps),
        "error_kinds": kinds,
        "spark": sparkline(stamps, now=now),
    }


def fmt_eta(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    s = int(seconds)
    return f"{s // 3600}h{(s % 3600) // 60:02d}m" if s >= 3600 else f"{s // 60}m{s % 60:02d}s"


def panel_lines(dog: Mapping[str, Any], *, on: bool, palette: Mapping[str, Any]) -> list[str]:
    """Watchdog box body: status, rate/ETA/projection, sparkline, error kinds, alerts."""
    p = palette
    level = dog.get("level") or "ok"
    status = {
        "ok": "● ALL CLEAR",
        "info": "● ALL CLEAR (notes below)",
        "warn": "▲ ATTENTION",
        "critical": "■ ACTION NEEDED",
    }[level]
    role = {"ok": "teal", "info": "teal", "warn": "gold", "critical": "warn"}[level]
    rate = dog.get("rate_dpm")
    proj = dog.get("projected_usd")
    idle = dog.get("idle_s")
    facts = (
        f"rate {'—' if rate is None else f'{rate:.1f} docs/min'} · ETA {fmt_eta(dog.get('eta_s'))}"
        f" · projected {'—' if proj is None else f'${proj:.3f}'}"
    )
    since = "last doc" if dog.get("docs_timed") else "since start"
    pace = (
        f"{since} {'—' if idle is None else fmt_eta(idle)} · stall at {fmt_eta(dog.get('stall_after_s'))}"
        f"{' (' + dog['stall_basis'] + ')' if dog.get('stall_basis') else ''}"
    )
    spark = f"docs/min, last {SPARK_BUCKETS}m  {dog.get('spark') or ''}"
    kinds = dog.get("error_kinds") or {}
    kind_txt = "errors  " + (" · ".join(f"{k} ×{v}" for k, v in sorted(kinds.items())) if kinds else "none")
    out = [
        p[role](status) if on else status,
        p["snow"](facts) if on else facts,
        p["dim"](pace) if on else pace,
        p["cyan"](spark) if on else spark,
        (p["gold"](kind_txt) if kinds else p["dim"](kind_txt)) if on else kind_txt,
    ]
    for a in dog.get("alerts") or []:
        mark = {"critical": "■", "warn": "▲", "info": "·"}.get(a["level"], "·")
        text = f"{mark} {a['code']:<7} {a['text']}"
        r = {"critical": "warn", "warn": "gold", "info": "dim"}.get(a["level"], "dim")
        out.append(p[r](text) if on else text)
    return out
