"""Background poller: Langfuse -> compact run snapshots -> WebSocket clients."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import WebSocket

from mailroom_ui.classification import archive_name_from_run, classification_from_run
from mailroom_ui.langfuse_source import LangfuseSource, list_recent_runs
from mailroom_ui.models import PipelineRun, Stage
from mailroom_ui.pipeline_ops import fetch_pipeline_ops
from mailroom_ui.trace_cache import persist_floor, persist_run

log = logging.getLogger("mailroom.poller")

_TERMINAL_STAGES = {Stage.ARCHIVED.value, Stage.FAILED.value}
_PARKED_STAGES = {Stage.HUMAN_REVIEW.value}


def floor_payload(run: PipelineRun) -> dict[str, Any]:
    """Compact serialization for the floor view (list-level data only)."""
    return {
        "trace_id": run.trace_id,
        "filename": run.filename,
        "doc_id": run.doc_id,
        "matter_id": run.matter_id,
        "session_id": run.session_id,
        "environment": run.environment,
        "user_id": run.user_id,
        "release": run.release,
        "tags": run.tags,
        "attempt": run.attempt,
        "stage": run.stage.value,
        "phase": run.phase.value,
        "doc_type": run.doc_type,
        "doc_subclass": run.doc_subclass,
        "contract_subtype": run.contract_subtype,
        "expected_hf_class": run.expected_hf_class,
        "expected_subclass": run.expected_subclass,
        "intake_messy": run.intake_messy,
        "intake_changed": run.intake_changed,
        "intake_method": run.intake_method,
        "intake_chars": run.intake_chars,
        "intake_bert": run.intake_bert,
        "classification_confidence": run.classification_confidence,
        "extraction_confidence": run.extraction_confidence,
        "review_decision": run.review_decision,
        "escalation_reason": run.escalation_reason,
        "review_causes": run.review_causes,
        "needs_reconsideration": run.needs_reconsideration,
        "error_message": run.error_message,
        "run_aborted": run.run_aborted,
        "failure_class": run.failure_class,
        "verdict": run.verdict,
        "quality": run.quality,
        "latency": run.latency,
        "llm_call_count": run.llm_call_count,
        "total_tokens": run.total_tokens,
        "cost_usd": run.cost_usd,
        "retried": run.retried,
        "needs_human": run.needs_human,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "routing_path": run.routing_path,
        **classification_from_run(run),
        "archive_name": archive_name_from_run(run),
    }


def run_fingerprint(run: PipelineRun) -> tuple[Any, ...]:
    """Light-run identity used to decide whether cached detail is stale."""
    updated = run.updated_at.isoformat() if run.updated_at else None
    stage = run.stage.value if run.stage else None
    try:
        latency = round(float(run.latency or 0), 2)
    except (TypeError, ValueError):
        latency = 0.0
    # Session is part of identity: llm-mailroom reuses deterministic trace
    # ids across pilots, so a new session_id means a new run on the same id.
    return (updated, stage, latency, run.error_message, run.session_id)


def apply_light_identity(full: PipelineRun, light: PipelineRun) -> PipelineRun:
    """Prefer fresh list-payload identity over a cached get_run.

    Reused Langfuse trace ids keep first-write session_id / output on the
    cached full run even after a later pilot retags the list row. Desk
    grouping (SESSIONS / REVIEW) keys off session_id, so overlay the light
    list fields whenever they are present.
    """
    updates: dict[str, Any] = {}
    if light.session_id:
        updates["session_id"] = light.session_id
    if light.matter_id:
        updates["matter_id"] = light.matter_id
    if light.environment:
        updates["environment"] = light.environment
    if light.tags:
        updates["tags"] = list(light.tags)
    if light.filename:
        updates["filename"] = light.filename
    if light.user_id:
        updates["user_id"] = light.user_id
    if light.release:
        updates["release"] = light.release
    if light.failure_class:
        updates["failure_class"] = light.failure_class
    if light.run_aborted:
        updates["run_aborted"] = True
    session_moved = bool(
        light.session_id and full.session_id and light.session_id != full.session_id
    )
    # Span progress lives on get_run observations. Overlay stage from the
    # light list only when the trace id was reused for a new session —
    # otherwise a cached list row would pin an in-flight envelope to INGEST.
    if session_moved:
        if light.stage:
            updates["stage"] = light.stage
            updates["phase"] = light.phase
        if light.doc_type:
            updates["doc_type"] = light.doc_type
        if light.doc_subclass:
            updates["doc_subclass"] = light.doc_subclass
        if light.review_causes:
            updates["review_causes"] = list(light.review_causes)
        if light.updated_at:
            updates["updated_at"] = light.updated_at
        updates["error_message"] = light.error_message
    if not updates:
        return full
    return full.model_copy(update=updates)


def poll_enrich_mode() -> str:
    """``all`` = legacy N+1 get_run; ``inflight`` (default) = hot runs only."""
    raw = (os.environ.get("MAILROOM_POLL_ENRICH") or "inflight").strip().lower()
    if raw in {"1", "true", "yes", "all", "on"}:
        return "all"
    if raw in {"0", "false", "no", "off", "none"}:
        return "none"
    return "inflight"


def is_conveyor_hot(run: PipelineRun) -> bool:
    """True when the envelope is still moving and must be re-enriched often."""
    st = run.stage.value if run.stage else "unknown"
    return st not in _TERMINAL_STAGES and st not in _PARKED_STAGES


class PollHub:
    """One poll loop broadcasting snapshots to all connected clients."""

    def __init__(
        self,
        source: LangfuseSource,
        *,
        interval: float = 3.0,
        window: float = 7 * 86400,
        limit: int = 100,
        detail_ttl: float = 60.0,
        inflight_ttl: float = 0.0,
        review_ttl: float = 15.0,
    ) -> None:
        self.source = source
        self.interval = interval
        self.window = window
        self.limit = limit
        self.detail_ttl = detail_ttl
        # 0 = re-enrich every poll so a just-flushed node moves the envelope
        # on the next tick instead of sitting on the previous station.
        self.inflight_ttl = inflight_ttl
        self.review_ttl = review_ttl
        self.clients: set[WebSocket] = set()
        self.snapshot: list[dict[str, Any]] = []
        # Last successful enriched PipelineRun list (same traces as snapshot).
        # Desk endpoints (sessions / review / metrics) read this instead of
        # walking Langfuse again — a 2-minute sequential enrich blocked the
        # inspector overlay on the single uvicorn worker.
        self.runs: list[PipelineRun] = []
        self.pipeline_ops: dict[str, Any] = {"configured": False, "watcher": "unconfigured"}
        self._details: dict[str, tuple[float, dict[str, Any], tuple[Any, ...]]] = {}
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())
            log.info(
                "poller started (interval=%ss window=%ss inflight_ttl=%ss)",
                self.interval, self.window, self.inflight_ttl,
            )

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)
        await ws.send_json(self._snapshot_message(stale=False))

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    def _snapshot_message(self, *, stale: bool) -> dict[str, Any]:
        return {
            "type": "snapshot",
            "runs": self.snapshot,
            "stale": stale,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "poll_interval_s": self.interval,
            "pipeline": self.pipeline_ops,
        }

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                runs, ops = await asyncio.gather(
                    asyncio.to_thread(self._fetch),
                    asyncio.to_thread(fetch_pipeline_ops),
                )
                self.pipeline_ops = ops
                # V-4: a partial Langfuse failure must NOT wipe the floor —
                # keep the last good snapshot and mark it stale so the UI can
                # show a staleness badge instead of a blank screen with a
                # green lamp. `_fetch` returns None on failure (instead of
                # []), meaning "no fresh data".
                if runs is not None:
                    self.snapshot = runs
                payload = self._snapshot_message(stale=runs is None)
                dead: list[WebSocket] = []
                for ws in list(self.clients):
                    try:
                        await ws.send_json(payload)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    self.clients.discard(ws)
            except Exception as exc:  # pragma: no cover - defensive
                log.warning("poller iteration failed: %s", exc)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass

    def _needs_refresh(
        self,
        light: PipelineRun,
        cached: Optional[tuple[float, dict[str, Any], tuple[Any, ...]]],
        now: float,
        prev: Optional[PipelineRun],
    ) -> bool:
        if cached is None:
            return True
        ts, _payload, fp = cached
        if fp != run_fingerprint(light):
            return True
        if (
            prev is not None
            and light.session_id
            and prev.session_id
            and prev.session_id != light.session_id
        ):
            return True
        age = now - ts
        probe = prev or light
        if is_conveyor_hot(probe) or is_conveyor_hot(light):
            return age >= self.inflight_ttl
        st = (probe.stage.value if probe.stage else "") or (light.stage.value if light.stage else "")
        if st in _PARKED_STAGES or probe.needs_human:
            return age >= self.review_ttl
        return age >= self.detail_ttl

    def _fetch(self) -> Optional[list[dict[str, Any]]]:
        # Langfuse timestamps are UTC: the window must be UTC-aware or a
        # non-UTC server shifts it by the local offset (a UTC+9 box would
        # query a window starting in the future and show an empty floor).
        since = datetime.now(timezone.utc) - timedelta(seconds=self.window)
        try:
            runs = list_recent_runs(self.source, since=since, limit=self.limit)
        except Exception as exc:
            log.warning("langfuse fetch failed: %s", exc)
            # V-4: return None = "no fresh data" (keep last good snapshot).
            return None
        now = time.monotonic()
        out: list[dict[str, Any]] = []
        full_runs: list[PipelineRun] = []
        current_ids: set[str] = set()
        prev_by_id = {r.trace_id: r for r in self.runs if r.trace_id}
        for run in runs:
            if not run.trace_id:
                continue
            current_ids.add(run.trace_id)
            cached = self._details.get(run.trace_id)
            prev = prev_by_id.get(run.trace_id)
            chosen: PipelineRun = run
            mode = poll_enrich_mode()
            want_enrich = mode == "all" or (
                mode == "inflight" and is_conveyor_hot(prev or run)
            )
            if want_enrich and not self._needs_refresh(run, cached, now, prev):
                chosen = apply_light_identity(prev, run) if prev is not None else run
                payload = floor_payload(chosen)
                ts = cached[0] if cached else now
                self._details[run.trace_id] = (ts, payload, run_fingerprint(run))
            elif want_enrich:
                force = cached is not None
                try:
                    getter = getattr(self.source, "get_run", None)
                    if force and hasattr(self.source, "invalidate_run"):
                        try:
                            self.source.invalidate_run(run.trace_id)
                        except Exception as exc:
                            log.warning(
                                "invalidate_run(%s) failed — stale cached run kept "
                                "for the next refresh: %s",
                                run.trace_id,
                                exc,
                            )
                    full = getter(run.trace_id, force_refresh=force) if getter else None
                except TypeError:
                    try:
                        full = self.source.get_run(run.trace_id)
                    except Exception as exc:
                        log.warning(
                            "get_run(%s) failed — run displayed with LIGHT identity "
                            "only (no detail): %s",
                            run.trace_id,
                            exc,
                        )
                        full = None
                except Exception as exc:
                    log.warning(
                        "get_run(%s) failed — run displayed with LIGHT identity "
                        "only (no detail): %s",
                        run.trace_id,
                        exc,
                    )
                    full = None
                chosen = apply_light_identity(full, run) if full is not None else run
                payload = floor_payload(chosen)
                self._details[run.trace_id] = (now, payload, run_fingerprint(run))
                if full is not None:
                    try:
                        persist_run(run.trace_id, {
                            **payload,
                            "spans": [s.model_dump(mode="json") for s in full.spans],
                            "generations": [g.model_dump(mode="json") for g in full.generations],
                            "scores": full.scores,
                        })
                    except Exception as exc:
                        log.warning(
                            "persist_run(%s) failed — this run is NOT persisted "
                            "and will be re-fetched on restart: %s",
                            run.trace_id,
                            exc,
                        )
            else:
                chosen = apply_light_identity(prev, run) if prev is not None else run
                payload = floor_payload(chosen)
                ts = cached[0] if cached else now
                self._details[run.trace_id] = (ts, payload, run_fingerprint(run))
            full_runs.append(chosen)
            out.append(payload)
        for tid in list(self._details):
            if tid not in current_ids:
                del self._details[tid]
        self.runs = full_runs
        persist_floor(out, source="langfuse")
        return out
