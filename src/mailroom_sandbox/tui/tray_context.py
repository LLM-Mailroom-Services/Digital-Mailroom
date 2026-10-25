"""Tray TUI display context — job-aware labels for ``sandbox watch`` (terminal + web).

Resolves subtitles, routes, lifecycle, and panel titles from the locked run
manifest (``spec.lock.json``), not only SAND-032 driver stamps or suite tables.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mailroom_sandbox.job.checkpoint import RunStore, TERMINAL_STATES
from mailroom_sandbox.watch import PROGRAM, lifecycle, read_times

TRAY_PRODUCT = "Tray TUI"
BRAND = "DIGITAL MAILROOM"
DEFAULT_ROUTE = "INBOX → SPECIALIST → REPORT"

_SAND032_PROGRAM_TITLE = "PROGRAM ROUTE · 1×L4 ladder → 2×L4 scale-out + 5-specialist sweep"


def _short_model(model: str | None) -> str:
    if not model:
        return "—"
    return model.split("/")[-1] if "/" in model else model


def _engine_bits(lock: dict[str, Any]) -> tuple[str, str, str, str]:
    engine = lock.get("engine") or {}
    modal = engine.get("modal") or {}
    vllm = engine.get("vllm") or {}
    model = _short_model(engine.get("model"))
    gpu = str(modal.get("gpu") or "—")
    quant = str(vllm.get("quantization") or "").strip()
    kv = str(vllm.get("kv_cache_dtype") or "").strip()
    bits = [model]
    if quant:
        bits.append(quant)
    if kv:
        bits.append(f"kv {kv}")
    bits.append(f"vLLM {gpu}")
    subtitle = " · ".join(bits)
    app = str(modal.get("app") or "")
    return subtitle, gpu, app, model


def route_for_task(task: str | None) -> str:
    t = (task or "").strip().lower()
    if t in {"pipeline", "extract", "chained"}:
        return "INBOX → SORTER → SPECIALISTS → REPORT"
    if t == "sorter":
        return "INBOX → SORTER → TRAY"
    if t.endswith("_specialist") or t in {
        "contracts_specialist",
        "correspondence_specialist",
        "corporate_records_specialist",
        "merger_agreement_specialist",
        "insurance_claims_specialist",
    }:
        return "INBOX → SPECIALIST → REPORT"
    if t == "legalbench":
        return "INBOX → LEGALBENCH → SCORE"
    if t:
        return f"INBOX → {t.upper()} → REPORT"
    return DEFAULT_ROUTE


def stage_tag(run_id: str, *, task: str | None = None, profile: str | None = None) -> str:
    if run_id.startswith("sand032-l"):
        return "LADDER"
    if run_id.startswith("sand032-s2"):
        return "SCALE-OUT"
    if run_id.startswith("sand032-s3"):
        return "SWEEP"
    if run_id.startswith("sand032-s4"):
        return "BF16"
    prof = (profile or "").lower()
    if "modal" in prof:
        return "MODAL"
    if prof in {"vllm-local", "ollama"}:
        return "LOCAL"
    if prof == "vllm-remote":
        return "REMOTE"
    if prof == "openrouter":
        return "API"
    t = (task or "").lower()
    if t == "pipeline":
        return "PIPELINE"
    if t.endswith("_specialist"):
        return "SPECIALIST"
    return "EVAL"


def _parse_ts(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def lifecycle_from_store(
    store: RunStore,
    boot_lines: list[str],
    *,
    now: float,
) -> dict[str, Any]:
    """Lifecycle when no SAND-032 driver ``.times`` file is present."""
    from mailroom_sandbox.watch import _boot_detail

    cp = store.read_checkpoint() or {}
    state = str(cp.get("state") or "waiting")
    lock = store.read_lock() or {}
    task = str(lock.get("task") or "job")
    updated = _parse_ts(cp.get("updated_at"))
    elapsed_s = int(max(0.0, now - updated)) if updated else 0

    events = store.events()
    event_names = {str(e.get("event")) for e in events}
    cold = store.read_cold_boot()

    if state == "failed":
        raw_err = cp.get("last_error")
        if isinstance(raw_err, dict):
            detail = str(raw_err.get("message") or raw_err.get("error") or raw_err or "run failed")[:160]
        elif raw_err:
            detail = str(raw_err)[:160]
        else:
            errs = [e for e in events if str(e.get("level")) == "error"]
            detail = str((errs[-1].get("event") if errs else "") or "run failed")[:160]
        return {"phase": "FAILED", "detail": detail, "elapsed_s": elapsed_s}
    if state == "done":
        return {"phase": "COMPLETE", "detail": "run finished · serving record", "elapsed_s": elapsed_s}
    if state == "paused":
        return {"phase": "PAUSED", "detail": "checkpoint saved · resume to continue", "elapsed_s": elapsed_s}

    if boot_lines and state in {"prepared", "running", "waiting"}:
        bootish = any(
            re.search(p, line, re.I)
            for line in boot_lines[-40:]
            for p in (
                r"loading weights",
                r"kv cache",
                r"application startup",
                r"vllm ready",
            )
        )
        if bootish and state != "running":
            return {
                "phase": "COLD BOOT",
                "detail": _boot_detail(boot_lines),
                "elapsed_s": elapsed_s,
            }

    if "cold_boot" in event_names and state == "prepared":
        secs = cold.get("cold_boot_seconds") if isinstance(cold, dict) else None
        detail = f"engine probe · {secs}s cold boot" if secs else "engine probe complete"
        return {"phase": "PREFLIGHT", "detail": detail, "elapsed_s": elapsed_s}
    if "preflight_ok" in event_names and state == "prepared":
        return {"phase": "PREFLIGHT", "detail": "lock verified · dataset ready", "elapsed_s": elapsed_s}
    if "fired" in event_names and state == "running":
        return {"phase": "REMOTE", "detail": "modal job worker · state dict mirror", "elapsed_s": elapsed_s}

    if state == "running":
        job = lock.get("job") or {}
        conc = job.get("concurrency")
        conc_s = f" · concurrency {conc}" if conc else ""
        return {
            "phase": "SORTING",
            "detail": f"{task} in flight{conc_s}",
            "elapsed_s": elapsed_s,
        }
    if state == "prepared":
        return {"phase": "QUEUED", "detail": "prepared · waiting for start", "elapsed_s": elapsed_s}
    return {"phase": "QUEUED", "detail": "waiting for run state", "elapsed_s": elapsed_s}


def resolve_times_file(store: RunStore, times_dir: Path | None) -> Path | None:
    if times_dir is not None:
        candidate = times_dir / f"{store.run_id}.times"
        if candidate.is_file():
            return candidate
    run_local = store.dir / "watch.times"
    return run_local if run_local.is_file() else None


def resolve_watch_paths(
    store: RunStore,
    *,
    sand032_root: Path | None,
) -> tuple[Path | None, Path]:
    """Return ``(times_dir, modal_log_path)`` for this run."""
    if sand032_root is not None:
        sand_logs = sand032_root / "logs"
        if (sand_logs / f"{store.run_id}.times").is_file():
            return sand_logs, sand_logs / "modal-app.log"
    return None, store.dir / "modal-app.log"


WORKER_APP = "sandbox-job"


def dispatch_source(store: RunStore, cli_app: str | None = None) -> dict[str, Any]:
    """Per-job dispatch source: serve app + optional Modal worker app.

    ``cli_app`` (--app) always wins for the serve stream. When
    ``job.mode == "modal"`` the ``sandbox-job`` worker container is a second
    stream; otherwise only the serve app is tailed.
    """
    lock = store.read_lock() or {}
    job = lock.get("job") or {}
    engine = lock.get("engine") or {}
    modal = engine.get("modal") or {}
    serve_app = cli_app or str(modal.get("app") or "sandbox-vllm")
    job_mode = str(job.get("mode") or "endpoint")
    streams = [serve_app]
    worker_app: str | None = None
    if job_mode == "modal":
        worker_app = WORKER_APP
        if worker_app not in streams:
            streams.append(worker_app)
    return {
        "serve_app": serve_app,
        "worker_app": worker_app,
        "job_mode": job_mode,
        "streams": streams,
    }


def job_event_lines(store: RunStore, *, limit: int = 8) -> list[dict[str, str]]:
    """Recent ``events.jsonl`` rows as dispatch feed entries with roles."""
    rows = store.events()[-limit:] if limit else store.events()
    out: list[dict[str, str]] = []
    for e in rows:
        level = str(e.get("level") or "info").lower()
        role = "error" if level == "error" else ("warn" if level == "warn" else "plain")
        event = str(e.get("event") or "event")
        detail = e.get("detail")
        if isinstance(detail, dict):
            bits = " ".join(f"{k}={v}" for k, v in list(detail.items())[:3])
            text = f"job:{event} {bits}".strip()
        elif detail:
            text = f"job:{event} {detail}"
        else:
            text = f"job:{event}"
        out.append({"text": text[:300], "role": role})
    return out


def program_route_lines(times_dir: Path, *, current: str, width: int = 100) -> list[str] | None:
    if not any((times_dir / f"{rid}.times").is_file() for rid, _ in PROGRAM):
        if current not in {rid for rid, _ in PROGRAM}:
            return None
    from mailroom_sandbox.watch import program_lines

    return program_lines(times_dir, current=current, width=width, on=False)


def job_context_lines(store: RunStore, *, app: str) -> list[str]:
    lock = store.read_lock() or {}
    job = lock.get("job") or {}
    engine = lock.get("engine") or {}
    profile = str(lock.get("profile") or "—")
    mode = str(job.get("mode") or "endpoint")
    task = str(lock.get("task") or "—")
    model = _short_model(engine.get("model"))
    modal = engine.get("modal") or {}
    gpu = str(modal.get("gpu") or "—")
    replicas = max(1, int(modal.get("max_containers") or 1))
    conc = job.get("concurrency")
    lines = [
        f"▶ {store.run_id} · {task} · profile {profile} · job {mode}",
        f"  engine {model} · ×{replicas} {gpu} · modal app {app}",
    ]
    if conc is not None:
        lines.append(f"  concurrency {conc}")
    trace = lock.get("trace") or {}
    sink = trace.get("sink")
    if sink:
        lines.append(f"  trace {sink}")
    return lines


def build_tray_layout(
    store: RunStore,
    *,
    app: str,
    times_dir: Path | None,
    cap_usd: float,
    gate_usd: float,
    width: int = 100,
) -> dict[str, Any]:
    lock = store.read_lock() or {}
    task = str(lock.get("task") or "?")
    profile = str(lock.get("profile") or "")
    job = lock.get("job") or {}
    job_mode = str(job.get("mode") or "endpoint")
    subtitle, gpu, _modal_app, _model = _engine_bits(lock)
    route_label = route_for_task(task)
    stage = stage_tag(store.run_id, task=task, profile=profile)

    times_file = resolve_times_file(store, times_dir)
    times = read_times(times_file) if times_file else {}

    program: list[str] | None = None
    program_title: str | None = None
    if times_dir is not None:
        program = program_route_lines(times_dir, current=store.run_id, width=width)
        if program:
            program_title = _SAND032_PROGRAM_TITLE

    job_route: list[str] | None = None
    if not program:
        job_route = job_context_lines(store, app=app)

    cost_cap = job.get("cost_cap_usd")
    if cost_cap is not None:
        try:
            cap_usd = float(cost_cap)
        except (TypeError, ValueError):
            pass

    src = dispatch_source(store, cli_app=app)
    streams = src["streams"]
    if len(streams) > 1:
        dispatch_title = f"Dispatch log · {' + '.join(f'modal app logs {a}' for a in streams)}"
    else:
        dispatch_title = f"Dispatch log · modal app logs {app}"
    tray_title = f"{TRAY_PRODUCT} · In-tray"
    postage_title = "Postage ($)"
    scorecard_title = f"Scorecard · {store.run_id}"
    window_title = f"{TRAY_PRODUCT} · THE MAILROOM · live watch"
    watcher_label = f"Tray TUI watcher · {profile or 'sandbox'} · {job_mode}"

    return {
        "product": TRAY_PRODUCT,
        "brand": BRAND,
        "subtitle": subtitle,
        "route_label": route_label,
        "stage": stage,
        "task": task,
        "profile": profile,
        "job_mode": job_mode,
        "gpu": gpu,
        "app": app,
        "cap_usd": cap_usd,
        "gate_usd": gate_usd,
        "panels": {
            "window_title": window_title,
            "tray": tray_title,
            "postage": postage_title,
            "dispatch": dispatch_title,
            "lifecycle": "Lifecycle",
            "scorecard": scorecard_title,
            "program": program_title,
        },
        "route": program,
        "job_route": job_route,
        "times_path": str(times_file) if times_file else None,
        "watcher_label": watcher_label,
        "dispatch": src,
    }


def resolve_lifecycle(
    store: RunStore,
    times: dict[str, float],
    boot_lines: list[str],
    *,
    now: float,
) -> dict[str, Any] | None:
    # A leftover driver ``.times`` ``deploy_done`` (no ``run_start``) used to
    # pin COLD BOOT forever after the endpoint job was already scoring.
    cp = store.read_checkpoint() or {}
    state = str(cp.get("state") or "")
    store_life = lifecycle_from_store(store, boot_lines, now=now)
    if state == "running":
        return store_life
    if times:
        life = lifecycle(times, boot_lines, now=now)
        if life.get("phase") != "QUEUED" or times:
            return life
    if cp.get("state") in TERMINAL_STATES and store_life.get("phase") == "QUEUED":
        return store_life
    if not times and store_life.get("phase") == "QUEUED" and not cp:
        return None
    return store_life


def show_scorecard(
    lifecycle_phase: str | None,
    checkpoint_state: str | None,
) -> bool:
    if lifecycle_phase in ("TEARDOWN", "STOPPED", "COMPLETE"):
        return True
    return str(checkpoint_state or "") in ("done", "failed")
