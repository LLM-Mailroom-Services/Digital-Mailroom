"""Checkpoint-aware item loop + scoring + experiment-log append (DMR-027).

``run_job`` executes the locked dataset row-by-row for the per-item tasks
(``sorter``) so a pause/error resumes from the last
appended item. Progress source of truth is ``items.jsonl``;
``checkpoint.json`` is the atomic mirror. Other tasks delegate to the
existing public eval runner at whole-run granularity.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from mailroom_sandbox.eval import experiment_log
from mailroom_sandbox.eval import runners as eval_runners  # noqa: F401
from mailroom_sandbox.job.checkpoint import RunStore, utc_now
from mailroom_sandbox.job.metrics import lock_dataset_provenance, record_from_run, routed_gpu_fleet
from mailroom_sandbox.eval.prompt_provenance import (
    resolve_logged_prompt_version,
    stamp_prompt_provenance,
)
from mailroom_sandbox.job.otel import current_context, job_span
from mailroom_sandbox.job.usage_capture import (
    merge_item_metrics,
    usage_from_pipeline,
)
from mailroom_sandbox.providers import default_profile

_log = logging.getLogger("mailroom_sandbox.job.runner")

PER_ITEM_TASKS = ("sorter",)
_WHOLE_RUN_TASKS = ("specialist", "pipeline", "extract", "chained", "local_vs_api", "sorter_vs_modernbert", "isolated")

# DMR-056: every registered isolated agent (SPECS in eval/agents.py) is also a
# runnable whole-run job task — registering a new AgentSpec is the ONE-file
# extension point for a new eval task, and it automatically becomes runnable
# via `sandbox run start --config <run.yaml>` with `task: <agent>`.
# The dispatch + validation lookups are LIVE (see _agent_task_names /
# job.spec.known_tasks) so a spec registered at runtime is picked up without
# re-import; this tuple is the import-time snapshot used for messages/tests.
try:
    from mailroom_sandbox.eval.agents import SPECS as _AGENT_SPECS

    ISOLATED_AGENT_TASKS = tuple(name for name in _AGENT_SPECS if name not in PER_ITEM_TASKS)
except Exception as exc:  # pragma: no cover — import fallback for isolated tooling
    _log.warning(
        "eval.agents.SPECS unavailable — agent-registered whole-run tasks are "
        "NOT runnable this session; 'unknown task' errors below would "
        "misattribute the root cause",
        exc_info=exc,
    )
    ISOLATED_AGENT_TASKS = ()

# Whole-run evaluators that take no ``api_budget``: a capped API run on them would spend unbounded.
_API_CAP_UNENFORCED_TASKS = ("extract", "chained", "local_vs_api", "sorter_vs_modernbert")

RUNNABLE_TASKS = PER_ITEM_TASKS + _WHOLE_RUN_TASKS + ISOLATED_AGENT_TASKS


def _agent_task_names() -> tuple[str, ...]:
    """LIVE agent-task names (DMR-056): a spec registered after import counts."""
    from mailroom_sandbox.eval.agents import SPECS

    return tuple(name for name in SPECS if name not in PER_ITEM_TASKS)


def _expected_for(task: str, row: dict[str, Any]) -> str:
    """Ground-truth label for a row, by task."""
    return str(row.get("expected_doc_class") or "")


def _predict_row(
    task: str,
    row: dict[str, Any],
    *,
    mock: bool,
    model: str | None,
    run_id: str | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Run one row; return ``(prediction, item_metrics)``.

    ``item_metrics`` carries ``prompt_tokens`` / ``completion_tokens`` /
    ``llm_calls`` when the live path recorded OpenAI-compatible usage.
    TTFT is never inferred here (streaming-only); leave it absent.
    """
    if task == "sorter":
        if mock:
            return eval_runners._classify_mock(row), {}
        # DMR-072 live-or-loud: the unactivated graph falls through to
        # doc_type="unknown" WITHOUT touching the LLM (the vendored default
        # config resolves providers that don't exist here) — that is not a
        # prediction, and recording it ok=True once lied through a whole run.
        from mailroom_sandbox.runtime import active as _runtime_active

        if _runtime_active() is None:
            raise RuntimeError(
                "runtime profile not activated — refusing a live sorter run on "
                "a dead pipeline; activate(profile) before running (the "
                "unactivated graph returns doc_type='unknown' without any LLM "
                "call and would record ok=True lies)"
            )
        result = eval_runners._run_pipeline_doc(row, mock=False, run_id=run_id)
        doc_type = result.get("doc_type")
        if not doc_type or str(doc_type).strip().lower() == "unknown":
            raise RuntimeError(
                f"live pipeline returned no real doc_type for row "
                f"{row.get('id') or row.get('filename') or '?'} "
                f"(got {doc_type!r}) — refusing to score a dead live path as "
                f"'unknown' (recorded ok=True would lie)"
            )
        return doc_type, usage_from_pipeline()
    raise ValueError(f"task {task!r} is not a per-item task in v1")


def _score(task: str, expected: list[str], predicted: list[str]) -> dict[str, Any]:
    from mailroom_sandbox.eval import scoring as sc

    return sc.score_classification(expected, predicted)


def _task_defaults(store: RunStore) -> dict[str, Any]:
    lock = store.read_lock() or {}
    return lock.get("job", {})


def _lock_prompt_source(store: RunStore) -> str:
    """The lock's default prompt source ('' when the lock has no prompt block)."""
    lock = store.read_lock() or {}
    prompt_block = lock.get("prompt") or {}
    return str((prompt_block.get("default") or {}).get("source") or "code-default")


def _lock_prompt_variant(store: RunStore, task: str | None = None) -> str | None:
    """The lock's LOCAL prompt variant stem for this task, when pinned.

    Specialist run YAMLs pin ``prompt.agents.<task>`` with ``default:
    code-default``. Looking only at the default dropped the eval-environment
    stem, so ``activate(prompt_variant=)`` never ran and records could not
    name the frozen v1 key.

    The runners' ``prompt_version`` param is a local variant stem (e.g.
    ``correspondence_specialist_simplified``), never the source string —
    passing 'code-default' would trigger the prompt-patch machinery.
    """
    lock = store.read_lock() or {}
    prompt_block = lock.get("prompt") or {}
    task_name = task or str(lock.get("task") or "")
    agents = prompt_block.get("agents") or {}
    if task_name and isinstance(agents, dict):
        ref = agents.get(task_name)
        if isinstance(ref, dict) and ref.get("source") == "local":
            stem = str(ref.get("file") or "").strip()
            if stem:
                return stem
    default = prompt_block.get("default") or {}
    if isinstance(default, dict) and default.get("source") == "local":
        return str(default.get("file") or "") or None
    return None


def _run_whole_run(
    store: RunStore,
    task: str,
    *,
    mock: bool,
    model: str | None,
    profile: str | None,
    on_event: Any = None,
) -> dict[str, Any]:
    """Delegate a whole-run task to the existing public eval runner.

    The per-item task (``sorter``) runs row-by-row so a
    pause/error resumes from the last appended item. Everything else in
    ``RUNNABLE_TASKS`` delegates to the matching ``eval.runners`` function at
    whole-run granularity: the locked prompt overrides are applied, the runner
    is invoked with lock-derived kwargs, and a terminal checkpoint + event
    record the completion. The experiment log record is appended by the
    delegated runner itself.
    """
    from mailroom_sandbox.eval import runners as eval_runners

    lock = store.read_lock() or {}
    default_ref = _lock_prompt_source(store)
    prompt_variant = _lock_prompt_variant(store, task=task)
    kwargs: dict[str, Any] = {
        "mock": mock,
        "dry_run": False,
        "experiment_name": f"sandbox_{task}_{store.run_id}",
        "profile": profile,
        "model": model,
        # DMR-053 (plan gap): the delegated runner used to label every whole-run
        # record 'mailroom-default' even when the lock pinned a local variant —
        # pass the LOCK's default variant stem so log records carry it.
        "prompt_version": prompt_variant,
        "agent_models": dict(lock.get("agent_models") or {}),
    }
    # DMR-056: whole-run tasks score the LOCKED live dataset when the run spec
    # prepared one (Hub/local); an empty lock falls back to the runners'
    # fixture defaults (serving-only specs like local_vs_api stay fixture-based).
    # A lock whose dataset.jsonl EXISTS but holds 0 rows is a prep defect —
    # refuse instead of silently scoring fixtures under the locked-dataset claim.
    locked_rows = store.dataset_rows()
    if not locked_rows and store.dataset_path.is_file():
        raise RuntimeError(
            f"locked dataset {store.dataset_path} exists but holds 0 rows — "
            f"refusing to score fixture rows while claiming the locked dataset; "
            f"re-run `sandbox datasets pull/prepare` with a nonzero limit"
        )
    locked_rows = locked_rows or None
    from mailroom_sandbox.eval import primary

    target = lock.get("target")
    if target and task == "pipeline":
        # Level 2: one document class through the full graph.
        locked_rows = primary.rows_for_class(locked_rows or eval_runners.load_manifest(), target)
    # SAND-018: the measured cold boot (written by `preflight --live`) travels
    # into the whole-run record too — isolated agent tasks append their own
    # experiment-log copy, so it must be passed through explicitly.
    cold_boot = store.read_cold_boot()
    cold_boot_seconds = (
        float(cold_boot["cold_boot_seconds"])
        if cold_boot and cold_boot.get("cold_boot_seconds") is not None
        else None
    )
    # SAND-018: the isolated-agent path used to be serial and ignore
    # job.concurrency / cost_cap / max_wall. Pass them through so a specialist
    # run is concurrent, measurable, and bounded.
    concurrency = _concurrency(store)
    max_wall = _max_wall_seconds(store)
    cost_cap = _cost_cap_usd(store)
    api_budget = _api_budget(store)
    gpu = _lock_gpu(store)
    replicas = _lock_replicas(store)
    gpu_fleet = _lock_fleet(store)
    from mailroom_sandbox.report_paths import experiment_prefix

    report_group = experiment_prefix(store.run_id, lock)
    score_metadata = {"report_group": report_group} if report_group else None
    # SAND-018: the isolated-agent path used to show nothing until it finished.
    # Write a running checkpoint per completed item and forward events so
    # `sandbox run status` (and --watch) track a live specialist run.
    startup_total = len(locked_rows or [])
    if target and task == "specialist" and locked_rows:
        startup_total = len(primary.rows_for_class(locked_rows, target))
    store.write_checkpoint(state="running", cursor=0, total=startup_total, remote=None)
    # The watchers time the SORTING stage from the latest start/resume.
    store.append_event("resume" if store.load_items() else "start", task=task)

    def _progress(done: int, total: int, ok: int, errors: int) -> None:
        store.write_checkpoint(state="running", cursor=done, total=total, remote=None)
        if on_event is not None:
            try:
                on_event(
                    {"cursor": done, "total": total, "ok": ok, "errors": errors, "state": "running"}
                )
            except Exception as exc:  # noqa: BLE001
                _log.warning("on_event callback raised — --watch may stop updating: %s", exc)

    def _isolated(agent: str, rows: list[dict[str, Any]] | None, progress: Any = None, **extra: Any) -> dict[str, Any]:
        return eval_runners.run_isolated_eval(
            agent,
            rows=rows,
            cold_boot_seconds=cold_boot_seconds,
            concurrency=concurrency,
            max_wall_seconds=max_wall,
            cost_cap_usd=cost_cap,
            api_budget=api_budget,
            gpu=gpu,
            replicas=replicas,
            gpu_fleet=gpu_fleet,
            progress_cb=progress or _progress,
            row_cb=lambda entry: _persist_isolated_items(store, [entry]),
            score_metadata=score_metadata,
            **{**kwargs, **extra},
        )

    try:
        if api_budget is not None and task in _API_CAP_UNENFORCED_TASKS:
            raise ValueError(
                f"task {task!r} cannot enforce job.api_cost_cap_usd (its evaluator makes API calls without a "
                "token budget); run it on a local or Modal route, or use a task that enforces the cap"
            )
        if task == "specialist":
            # Level 1 sweeps all five specialists, level 2 (`target`) runs one.
            # Each specialist scores only its own class's locked rows; with no
            # locked dataset it falls back to its committed fixture rows.
            agents = primary.specialists_for(target)
            per_agent: dict[str, Any] = {}
            offset, grand_total = 0, len(locked_rows or [])
            for agent in agents:
                cls = next(c for c, a in primary.SPECIALISTS.items() if a == agent)
                rows = [r for r in locked_rows if primary.row_class(r) == cls] if locked_rows else None
                if locked_rows and not rows:
                    continue  # the locked subset has no documents of this class
                def swept(done: int, total: int, ok: int, errors: int, _base: int = offset) -> None:
                    # One cursor across the sweep, not one per specialist.
                    _progress(_base + done, grand_total or total, ok, errors)

                per_agent[agent] = _isolated(agent, rows, progress=swept if len(agents) > 1 else None,
                                             experiment_name=f"sandbox_{agent}_{store.run_id}",
                                             prompt_version=_lock_prompt_variant(store, task=agent))
                offset += len(rows or [])
            if not per_agent:
                raise ValueError("the locked dataset has no documents for any live-class specialist")
            if len(per_agent) == 1:
                result = next(iter(per_agent.values()))
            else:
                result = {
                    "task": "specialist",
                    "targets": list(per_agent),
                    "summary": {agent: primary._headline(r) for agent, r in per_agent.items()},
                    "n": sum(int((r.get("scores") or {}).get("n") or r.get("n") or 0) for r in per_agent.values()),
                    "rows": [row for r in per_agent.values() for row in (r.get("rows") or [])],
                    "scores": {},
                }
        elif task == "pipeline":
            result = eval_runners.run_pipeline_eval(
                connected=True, rows=locked_rows,
                row_cb=lambda entry: _persist_isolated_items(store, [entry]),
                progress_cb=_progress, node_cb=store.append_node, max_wall_seconds=max_wall,
                cost_cap_usd=cost_cap, api_budget=api_budget, gpu=gpu, replicas=replicas,
                gpu_fleet=gpu_fleet, concurrency=concurrency, **kwargs)
        elif task == "extract":
            result = eval_runners.run_extract_eval(rows=locked_rows, **kwargs)
        elif task == "chained":
            result = eval_runners.run_chained_eval(rows=locked_rows, **kwargs)
        elif task == "local_vs_api":
            result = eval_runners.run_local_vs_api_eval(
                score_metadata=score_metadata,
                **kwargs,
            )
        elif task == "sorter_vs_modernbert":
            result = eval_runners.run_sorter_vs_modernbert_eval(**kwargs)
        elif task == "isolated":
            # Historical alias: `isolated` runs the sorter spec (docs/jobs.md).
            result = eval_runners.run_isolated_eval(
                "sorter",
                rows=locked_rows,
                cold_boot_seconds=cold_boot_seconds,
                concurrency=concurrency,
                max_wall_seconds=max_wall,
                cost_cap_usd=cost_cap,
                api_budget=api_budget,
                gpu=gpu,
                replicas=replicas,
                gpu_fleet=gpu_fleet,
                progress_cb=_progress,
                row_cb=lambda entry: _persist_isolated_items(store, [entry]),
                score_metadata=score_metadata,
                **kwargs,
            )
        elif task in _agent_task_names():
            # DMR-056: any registered AgentSpec name is a whole-run job task —
            # `task: judge` / `task: gmail_triage` (once registered) etc.
            result = eval_runners.run_isolated_eval(
                task,
                rows=locked_rows,
                cold_boot_seconds=cold_boot_seconds,
                concurrency=concurrency,
                max_wall_seconds=max_wall,
                cost_cap_usd=cost_cap,
                api_budget=api_budget,
                gpu=gpu,
                replicas=replicas,
                gpu_fleet=gpu_fleet,
                progress_cb=_progress,
                row_cb=lambda entry: _persist_isolated_items(store, [entry]),
                score_metadata=score_metadata,
                **kwargs,
            )
        else:
            raise ValueError(f"task {task!r} is not runnable")
    except Exception as exc:  # noqa: BLE001
        store.write_checkpoint(
            state="failed",
            cursor=0,
            total=0,
            last_error={"type": "whole-run", "message": f"{type(exc).__name__}: {str(exc)[:512]}", "at": utc_now(), "retryable": False},
        )
        store.append_event("failed", "error", cursor=0, last_error=str(exc)[:512])
        # SAND-089: a document that raised has no item row (a resume re-runs it), but its
        # billed tokens must still count against the API ceiling of a resumed run.
        if failed_usage := getattr(exc, "sandbox_failed_usage", None):
            from mailroom_sandbox.job.api_budget import FAILED_USAGE_EVENT

            store.append_event(FAILED_USAGE_EVENT, "warning", **failed_usage)
        return {"state": "failed", "task": task, "error": str(exc)[:512], "ok": 0, "errors": 1}

    _persist_isolated_items(store, result.get("rows") if isinstance(result, dict) else None)
    scores = result.get("scores") or {}
    # The delegated runner reports how many rows it actually processed; fall
    # back to the locked dataset length when the runner has no n.
    processed = result.get("n") if isinstance(result.get("n"), int) else None
    if processed is None:
        processed = scores.get("n") if isinstance(scores.get("n"), int) else len(store.dataset_rows())
    # DMR-053: stamp the returned record with the lock's provenance so the
    # caller (and the Modal state dict) can pair it with the locked spec even
    # though the runner appended its own log copy.
    record = result.get("record") if isinstance(result, dict) else None
    if isinstance(record, dict):
        lock_prompt = store.read_prompt_lock()
        logged, sha = resolve_logged_prompt_version(
            prompt_variant,
            task=task,
            prompt_lock=lock_prompt,
        )
        record.setdefault("spec_hash", store.spec_hash() or "")
        record.setdefault("dataset_fingerprint", _fingerprint(store))
        # The dojo refuses a serving scorecard without dataset_revision; the
        # lock is the only truthful source (never derived from the fingerprint).
        for key, value in lock_dataset_provenance(store.read_lock()).items():
            record.setdefault(key, value)
        record.setdefault("prompt_version", logged or default_ref)
        if sha:
            record.setdefault("prompt_sha256", sha)
        # a locked eval-environment selection IS the record's prompt identity
        from mailroom_sandbox.prompt_versions import selection_from_lock

        locked = selection_from_lock(lock_prompt)
        if locked and locked.label_for(task) is not None:
            record["prompt_version"], record["prompt_sha256"] = locked.label_for(task)
        stamp_prompt_provenance(
            record, record["prompt_version"], record.get("prompt_sha256"), prompt_lock=lock_prompt
        )
        record.setdefault("run_id", store.run_id)
    items = store.load_items()
    ok_items = [item for item in items if item.get("ok")]
    if items and all((item.get("score") or {}).get("parse_error") for item in ok_items):
        # Live-or-loud: nothing usable came back, whether the rows errored or
        # every answer was unparseable. The same doctrine as the per-item path.
        failed = next((item for item in items if not item.get("ok")), items[0])
        message = str(failed.get("error") or "every document's answer failed to parse")
        last_error = {"type": "item", "message": message[:512], "at": utc_now(),
                      "item_id": failed.get("item_id"), "retryable": False}
        store.write_checkpoint(state="failed", cursor=processed, total=processed, remote=None, last_error=last_error)
        store.append_event("failed", "error", cursor=processed, last_error=message[:512])
        return {"state": "failed", "task": task, "cursor": processed, "total": processed, "ok": 0,
                "errors": len(items), "last_error": last_error}
    store.write_checkpoint(state="done", cursor=processed, total=processed, remote=None)
    store.append_event("done", "info", cursor=processed, ok_count=len(ok_items) if items else processed)
    from mailroom_sandbox.job.dated_reports import maybe_write_run_reports

    maybe_write_run_reports(store, scores=scores if isinstance(scores, dict) else None)
    from mailroom_sandbox.job.grid_cards import maybe_write_card

    maybe_write_card(store, scores=scores if isinstance(scores, dict) else None)
    return {
        "state": "done",
        "task": task,
        "cursor": processed,
        "total": processed,
        "ok": len(ok_items) if items else processed,
        "errors": len(items) - len(ok_items),
        "scores": scores,
        "default_prompt_source": default_ref,
        "spec_hash": store.spec_hash() or "",
        "dataset_fingerprint": _fingerprint(store),
        "result": result,
    }


def _max_retries(store: RunStore) -> int:
    return int(_task_defaults(store).get("max_retries", 2))


# Bounded fan-out guard for the concurrent per-item loop (see JobSpec
# concurrency): a runaway spec value is a cost accident, not a feature.
_MAX_CONCURRENCY = 64


def _concurrency(store: RunStore) -> int:
    value = int(_task_defaults(store).get("concurrency", 4) or 4)
    return max(1, min(value, _MAX_CONCURRENCY))


def _cost_cap_usd(store: RunStore) -> float | None:
    raw = _task_defaults(store).get("cost_cap_usd")
    if raw is None or raw == "":
        return None
    return float(raw)


def _api_budget(store: RunStore):
    """SAND-089: the run's API token budget, seeded with tokens already spent.

    That is every persisted item plus every document that raised after a paid call
    (recorded as a ``FAILED_USAGE_EVENT``; it has no item row).
    """
    from mailroom_sandbox.job.api_budget import budget_for, usage_records

    return budget_for(store.read_lock() or {}, usage_records(store))


def _max_wall_seconds(store: RunStore) -> int | None:
    raw = _task_defaults(store).get("max_wall_seconds")
    if raw is None or raw == "":
        return None
    return int(raw)


def _estimate_run_gpu_usd(store: RunStore, wall_seconds: float) -> float:
    """Wall-clock GPU $ estimate for abort caps (Modal endpoint = warm GPU)."""
    from mailroom_sandbox.job.metrics import fleet_gpu_cost_usd

    return fleet_gpu_cost_usd(wall_seconds, _lock_fleet(store))


def _lock_fleet(store: RunStore) -> list[tuple[str, int]]:
    """Base engine plus per-agent Modal route apps (SAND-078 judge, SAND-079 tiers)."""
    from mailroom_sandbox.job.metrics import lock_gpu_fleet

    return lock_gpu_fleet(store.read_lock() or {})


def verify_dataset_lock(store: RunStore) -> None:
    """Refuse to score when dataset.jsonl drifted from the lock's sha256."""
    lock = store.read_lock() or {}
    dataset_block = lock.get("dataset") if isinstance(lock.get("dataset"), dict) else {}
    expected = str((dataset_block or {}).get("sha256") or "")
    actual = store.dataset_sha256() or ""
    if expected and actual and expected != actual:
        raise RuntimeError(
            f"dataset.jsonl changed since the lock (lock={expected[:12]} file={actual[:12]}) — "
            "refusing to score drifted rows; re-run preflight with --force to archive this "
            "generation and re-lock"
        )


def _fail_fast(store: RunStore) -> bool:
    return bool(_task_defaults(store).get("fail_fast", False))


def _lock_task(store: RunStore) -> str:
    lock = store.read_lock() or {}
    return str(lock.get("task") or "sorter")


def _lock_model(store: RunStore) -> str | None:
    engine = (store.read_lock() or {}).get("engine") or {}
    if isinstance(engine, dict):
        return engine.get("model")
    return None


def _lock_profile(store: RunStore) -> str:
    """Profile recorded in the run lock.

    A lock without one means the default profile, the same fallback ``runtime.activate`` applies.
    """
    return str((store.read_lock() or {}).get("profile") or default_profile())


def _lock_mock(store: RunStore, default: bool) -> bool:
    return bool(_task_defaults(store).get("mock", default))


def _fingerprint(store: RunStore) -> str:
    rows = store.dataset_rows()
    if not rows:
        return ""
    # One canonical fingerprint shared with the eval-run records so
    # pair_comparable_runs can pair job and eval runs (DMR-049).
    from mailroom_sandbox.datasets import dataset_fingerprint

    return dataset_fingerprint(rows)


def _apply_prompt_overrides(store: RunStore) -> None:
    """Apply the store's frozen prompt selection and texts to the runtime.

    Propagate prompt-selection errors and RuntimeError for required texts
    that cannot be applied.
    """
    from mailroom_sandbox.prompt_registry import apply_locked_prompts

    apply_locked_prompts(store.read_prompt_lock() or {})


def _lock_gpu(store: RunStore) -> str | None:
    """Modal GPU class from the lock's engine.modal block (e.g. ``L4``)."""
    engine = (store.read_lock() or {}).get("engine") or {}
    if not isinstance(engine, dict):
        return None
    modal = engine.get("modal") or {}
    if isinstance(modal, dict) and modal.get("gpu"):
        return str(modal["gpu"]).split(":")[0]
    return None


def _persist_isolated_items(store: RunStore, rows: list[dict[str, Any]] | None) -> int:
    """SAND-032: isolated specialist runs wrote no items.jsonl — per-doc rows
    are the evidence the reports and offline BT rows are built from."""
    if not rows:
        return 0
    seen = {i.get("item_id") for i in store.load_items()}
    written = 0
    for row in rows:
        item_id = row.get("id")
        if item_id in seen:
            continue
        store.append_item(
            {
                "item_id": item_id,
                "ok": not row.get("error") and not (row.get("score") or {}).get("parse_error"),
                "error": row.get("error"),
                "pred": row.get("pred"),
                "score": row.get("score"),
                "latency_ms": row.get("latency_ms"),
                "prompt_tokens": row.get("prompt_tokens"),
                "completion_tokens": row.get("completion_tokens"),
                "ts": utc_now(),
            }
        )
        seen.add(item_id)
        written += 1
    return written


def _lock_replicas(store: RunStore) -> int:
    """Concurrently-billed replicas (SAND-032: MIN=MAX pinned 2×L4 bills 2 GPUs).

    ``max_containers`` over-estimates a scale-to-zero config — the safe
    direction for a spend cap.
    """
    engine = (store.read_lock() or {}).get("engine") or {}
    modal = engine.get("modal") if isinstance(engine, dict) else None
    if isinstance(modal, dict):
        return max(1, int(modal.get("max_containers") or 1))
    return 1


def _build_record(
    store: RunStore, task: str, model: str | None, scores: dict[str, Any], *, mock: bool,
    wall_seconds: float | None = None,
) -> dict[str, Any]:
    """Build the experiment-log record for a finished run from its lock, items and scores.

    The profile is the lock's, falling back to the default profile exactly as activation does, so a record never names a profile that did not run. Cost bills the measured wall time plus the cold boot, unless ``MODAL_BILLED_GPU_SECONDS`` overrides it.
    """
    lock = store.read_lock() or {}
    profile = str(lock.get("profile") or default_profile())
    engine = lock.get("engine") or {}
    model = model or (engine.get("model") if isinstance(engine, dict) else None) or "unknown"
    prompt_variant = _lock_prompt_variant(store, task=task)
    logged_prompt, prompt_sha = resolve_logged_prompt_version(
        prompt_variant,
        task=task,
        prompt_lock=store.read_prompt_lock(),
    )
    prompt_version = logged_prompt
    items = store.load_items()
    # SAND-018: carry the live engine-probe cold-boot measurement (written by
    # `preflight --live`, the step right after deploy) into the experiment-log
    # record — a measured boot, never the assumed 120 s estimate constant.
    cold_boot = store.read_cold_boot()
    cold_boot_seconds = (
        float(cold_boot["cold_boot_seconds"])
        if cold_boot and cold_boot.get("cold_boot_seconds") is not None
        else None
    )
    busy_sum_seconds = sum(float(i.get("latency_ms") or 0) for i in items) / 1000.0
    if wall_seconds is None:
        from mailroom_sandbox.job.metrics import infer_wall_seconds_from_items

        wall_seconds = infer_wall_seconds_from_items(items)
    # Cost accuracy: bill the warm interval (measured wall + cold boot). Summed
    # item latency overstates Modal spend under concurrency>1; keep the sum only
    # as a fallback when wall clock is unknown. MODAL_BILLED_GPU_SECONDS wins.
    import os

    env_billed = (os.environ.get("MODAL_BILLED_GPU_SECONDS") or "").strip()
    billed_window: float | None = None
    if env_billed:
        try:
            billed_window = float(env_billed)
        except ValueError:
            billed_window = None
    if billed_window is None:
        if wall_seconds is not None and wall_seconds > 0:
            billed_window = float(wall_seconds) + (cold_boot_seconds or 0.0)
        elif busy_sum_seconds > 0:
            billed_window = busy_sum_seconds + (cold_boot_seconds or 0.0)
    record = record_from_run(
        run_id=store.run_id,
        spec_hash=store.spec_hash() or "",
        task=task,
        profile=profile,
        model=model,
        prompt_version=prompt_version,
        dataset_fingerprint=_fingerprint(store),
        dataset_provenance=lock_dataset_provenance(lock),
        items=items,
        scores=scores or None,
        gpu=_lock_gpu(store),
        billed_window_seconds=billed_window if billed_window and billed_window > 0 else None,
        mock=bool(mock),
        # Price route apps like the cost cap does (SAND-083).
        gpu_fleet=routed_gpu_fleet(lock),
    )
    record["experiment_name"] = f"sandbox_{task}_{store.run_id}"
    record["mock"] = bool(mock)
    if cold_boot_seconds is not None:
        record["cold_boot_seconds"] = cold_boot_seconds
    if prompt_sha:
        record["prompt_sha256"] = prompt_sha
    from mailroom_sandbox.prompt_versions import selection_from_lock

    selection = selection_from_lock(store.read_prompt_lock())
    if selection:
        selection.stamp(record)  # selected eval-environment key + sha256 + per-role map
    return record


def _beacon_hook(run_id: str, *, task: str, on_event: Any = None) -> tuple[Any, Any]:
    """mailroom.beacon/v1 for `sandbox run start`: wrap ``on_event`` so every progress
    event also updates the job's heartbeat (shown by `sandbox board`). Never raises."""
    from mailroom_sandbox.tui.beacon import Beacon

    beacon = Beacon(run_id, package="local-mailroom-sandbox", title=f"{run_id} · {task}")

    def wrapped(ev: dict[str, Any]) -> None:
        beacon.update(
            phase=str(ev.get("state") or "running").upper(),
            done=ev.get("cursor"),
            total=ev.get("total"),
            ok=ev.get("ok"),
            errors=ev.get("errors"),
        )
        if on_event is not None:
            on_event(ev)

    def finish(summary: dict[str, Any] | None) -> None:
        summary = summary or {}
        state = str(summary.get("state") or "")
        if state in ("paused", "running"):
            # Cancelled mid-run or limited by --max-items: not finished. Leave the beacon
            # non-terminal so the board shows PAUSED (then stalled once this process exits)
            # instead of claiming the run is done.
            beacon.update(phase=state.upper(), done=summary.get("cursor"), total=summary.get("total"))
            return
        beacon.finish(
            "failed" if state in ("failed", "cancelled") else "done",
            done=summary.get("cursor"),
            total=summary.get("total"),
            phase=state.upper() or "DONE",
        )

    return wrapped, finish


def run_job(
    store: RunStore,
    *,
    task: str | None = None,
    model: str | None = None,
    profile: str | None = None,
    mock: bool | None = None,
    dry_run: bool = False,
    max_items: int | None = None,
    tracer: Any = None,
    on_event=None,
) -> dict[str, Any]:
    """Run or resume a locked job and return its current summary.

    The caller owns the store's writer lock. Non-dry runs validate the frozen
    generation and activate its runtime settings before execution. Per-item
    jobs may return ``paused`` after cancellation or ``running`` when
    ``max_items`` limits this invocation. ``dry_run`` verifies dataset integrity
    and returns row counts without activation or execution.

    Generation, activation, and uncaught execution errors propagate; handled
    item/delegate failures are reported in the returned summary.
    """
    if not dry_run:
        store.verify_generation()
    if dry_run:
        return _run_job(store, task=task, model=model, profile=profile, mock=mock, dry_run=True,
                        max_items=max_items, tracer=tracer, on_event=on_event)
    wrapped, finish = _beacon_hook(store.run_id, task=task or _lock_task(store), on_event=on_event)
    try:
        from mailroom_sandbox.job.otel import locked_pipeline_provider
        from mailroom_sandbox.runtime import activate, locked_runtime

        lock = store.read_lock() or {}
        with locked_runtime(lock, store.read_prompt_lock() or {}), locked_pipeline_provider(lock):
            activate()
            summary = _run_job(store, task=task, model=model, profile=profile, mock=mock, dry_run=False,
                               max_items=max_items, tracer=tracer, on_event=wrapped)
    except BaseException:
        finish({"state": "failed"})
        raise
    finish(summary if isinstance(summary, dict) else None)
    return summary


def _run_job(
    store: RunStore,
    *,
    task: str | None = None,
    model: str | None = None,
    profile: str | None = None,
    mock: bool | None = None,
    dry_run: bool = False,
    max_items: int | None = None,
    tracer: Any = None,
    on_event=None,
) -> dict[str, Any]:
    """Execute pending rows or delegate a whole-run task and return its summary.

    Per-item resumes skip recorded indices and retain prior error counts.
    Cancellation stops new submissions, drains in-flight work, and records a
    paused checkpoint. ``max_items`` limits pending rows for this invocation.
    Item prediction failures are persisted; fail-fast/cost/wall guards and an
    all-item failure produce failed summaries. Successful rows are scored and
    logged. Dataset mismatch raises RuntimeError; unknown tasks raise
    ValueError. Uncaught prompt,
    scoring, and persistence errors propagate.
    """
    task = task or _lock_task(store)
    model = model or _lock_model(store)
    profile = profile or _lock_profile(store)
    mock = _lock_mock(store, True) if mock is None else mock

    rows = store.dataset_rows()
    verify_dataset_lock(store)
    if dry_run:
        return {"state": "dry_run", "task": task, "n": len(rows), "cursor": 0, "total": len(rows)}
    if store.terminal():
        return store.summary()

    # Whole-run tasks delegate to the existing public eval runner; the locked
    # dataset may legitimately be empty for serving-only tasks (local_vs_api),
    # so dispatch before the per-item row guard.
    _apply_prompt_overrides(store)
    if task not in PER_ITEM_TASKS:
        from mailroom_sandbox.job.spec import known_tasks

        if task not in known_tasks():
            raise ValueError(f"task {task!r} is not runnable; have {sorted(known_tasks())}")
        return _run_whole_run(store, task, mock=mock, model=model, profile=profile, on_event=on_event)

    if not rows:
        store.write_checkpoint(state="done", cursor=0, total=0, remote=None)
        store.append_event("done", "info", cursor=0)
        return {"state": "done", "cursor": 0, "total": 0, "ok": 0, "errors": 0}

    # Reconstruct already-completed predictions so final scoring covers all rows.
    completed: dict[int, dict[str, Any]] = {}
    for done in store.load_items():
        if "index" in done:
            completed[int(done["index"])] = done
    expected: list[str] = []
    predicted: list[str] = []
    for index, row in enumerate(rows):
        expected.append(_expected_for(task, row))
        done = completed.get(index)
        if done is not None:
            predicted.append(str(done.get("predicted") or ""))
        else:
            predicted.append("")  # placeholder; refilled during the loop below

    # Resume skips by completed INDEX, not a contiguous cursor: concurrent
    # completions land out of order, so cursor == len(items) no longer implies
    # rows [0, cursor) are done. resume_cursor() is still called to reconcile
    # the checkpoint mirror (its drift guard is keyed on item count).
    total = len(rows)
    store.resume_cursor()
    pending = [i for i in range(len(rows)) if i not in completed]
    if max_items is not None:
        pending = pending[:max_items]

    ok_count = sum(bool(item.get("ok")) for item in completed.values())
    failures = [item for item in completed.values() if not item.get("ok")]
    error_count = len(failures)
    done_count = len(completed)
    last_error: str | None = failures[-1].get("error") if failures else None
    last_error_item: str | None = failures[-1].get("item_id") if failures else None
    fail_fast = _fail_fast(store)
    retries = _max_retries(store)
    run_started = time.perf_counter()
    cost_cap = _cost_cap_usd(store)
    max_wall = _max_wall_seconds(store)
    api_budget = None if mock else _api_budget(store)
    cap_abort_reason: str | None = None
    cap_abort_type: str | None = None

    # Worker threads do not inherit the caller's otel context; hand it over
    # explicitly so item spans nest under the run span.
    parent_ctx = current_context(tracer)

    def _attempt(index: int) -> tuple[Any, str | None, float, dict[str, Any]]:
        """Run one row (with retries); return (value, error, latency_ms, usage)."""
        row = rows[index]
        started = time.perf_counter()
        value: Any = None
        error: str | None = None
        usage: dict[str, Any] = {}
        failed_usage: dict[str, int] = {}  # billed by attempts that raised, then retried
        with job_span(
            tracer,
            "job.item",
            parent=parent_ctx,
            item_index=str(index),
            item_id=str(row.get("id") or row.get("filename") or index),
            task=task,
        ) as span:
            attempt = 0
            while attempt < retries + 1:
                attempt += 1
                try:
                    value, usage = _predict_row(
                        task, row, mock=mock, model=model, run_id=store.run_id
                    )
                    if not isinstance(usage, dict):
                        # Back-compat for test monkeypatches that still return
                        # the old ``(value, ok: bool)`` shape.
                        usage = {}
                    error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    error = f"{type(exc).__name__}: {str(exc)[:512]}"
                    usage = {}
                    if not mock:
                        # The failed call was billed; the next attempt's graph run resets the accumulator.
                        for key, value in usage_from_pipeline().items():
                            failed_usage[key] = failed_usage.get(key, 0) + value
                    if attempt <= retries:
                        time.sleep(0.2)
            if failed_usage:
                usage = {key: int(usage.get(key) or 0) + failed_usage.get(key, 0)
                         for key in {*usage, *failed_usage}}
            span.set_attribute("job.ok", error is None)
            span.set_attribute("job.attempts", attempt)
            if error is not None:
                span.set_attribute("job.error", error)
            for key, attr in (
                ("prompt_tokens", "gen_ai.usage.input_tokens"),
                ("completion_tokens", "gen_ai.usage.output_tokens"),
                ("llm_calls", "job.llm_calls"),
            ):
                if isinstance(usage.get(key), (int, float)):
                    span.set_attribute(attr, usage[key])
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        return value, error, latency_ms, usage

    def _record(
        index: int,
        value: Any,
        error: str | None,
        latency_ms: float,
        usage: dict[str, Any] | None = None,
    ) -> bool:
        """Persist one result (always from the calling thread) and return ok.

        The main thread owns every RunStore write in BOTH the serial and the
        concurrent paths — worker threads only compute, so append_item /
        append_event / write_checkpoint / on_event never race.
        """
        nonlocal ok_count, error_count, done_count, last_error, last_error_item, cap_abort_reason, cap_abort_type
        row = rows[index]
        item_id = str(row.get("id") or row.get("filename") or index)
        ok = error is None
        if ok:
            ok_count += 1
        else:
            error_count += 1
            last_error = error
            last_error_item = item_id
        done_count += 1
        predicted[index] = str(value) if value is not None else ""
        item: dict[str, Any] = {
            "item_id": item_id,
            "index": index,
            "expected": _expected_for(task, row),
            "predicted": predicted[index],
            "ok": ok,
            "error": error,
            "trace_id": "",
            "ts": utc_now(),
        }
        item.update(
            merge_item_metrics(latency_ms=latency_ms, usage=usage or {})
        )
        if not mock and ok and item.get("prompt_tokens") is None and item.get("completion_tokens") is None:
            _log.warning(
                "item %s ok but recorded no token usage — the run's "
                "estimated_cost_usd will be absent, as one unobserved request "
                "makes the run cost unknown (live OpenAI-compatible responses "
                "must expose usage.prompt_tokens)",
                item_id,
            )
        store.append_item(item)
        store.append_event(
            "item_" + ("done" if ok else "failed"), "info" if ok else "warn", index=index, item_id=item_id
        )
        store.write_checkpoint(state="running", cursor=done_count, total=total, remote=None)
        if on_event is not None:
            try:
                on_event({"cursor": done_count, "total": total, "ok": ok_count, "errors": error_count, "state": "running"})
            except Exception as exc:
                _log.warning(
                    "on_event callback raised — a `--watch` consumer may silently "
                    "stop updating while the run continues: %s",
                    exc,
                )
        if api_budget is not None:
            api_budget.add_usage(item)
        # DMR-078: cost / wall abort guards (Modal warm-GPU wall × $/hr).
        if not mock and cap_abort_reason is None:
            wall_s = time.perf_counter() - run_started
            if max_wall is not None and wall_s >= float(max_wall):
                cap_abort_type = "max_wall"
                cap_abort_reason = (
                    f"max_wall_seconds={max_wall} exceeded "
                    f"(wall={wall_s:.1f}s) — aborting to protect spend"
                )
            elif cost_cap is not None and (est := _estimate_run_gpu_usd(store, wall_s)) >= float(cost_cap):
                cap_abort_type = "cost_cap"
                cap_abort_reason = (
                    f"cost_cap_usd={cost_cap} exceeded "
                    f"(est_gpu_usd={est:.4f} at wall={wall_s:.1f}s) — aborting"
                )
            elif api_budget is not None and (reason := api_budget.exceeded()):
                # SAND-089: token spend on API-billed agents.
                cap_abort_type = "api_cost_cap"
                cap_abort_reason = reason
        return ok

    def _cap_abort_failed():
        """Write the cost/wall abort checkpoint and return the summary."""
        store.write_checkpoint(
            state="failed",
            cursor=done_count,
            total=total,
            last_error={
                "type": cap_abort_type or ("cost_cap" if cost_cap is not None else "max_wall"),
                "message": cap_abort_reason,
                "at": utc_now(),
                "item_id": last_error_item,
                "retryable": False,
            },
        )
        store.append_event("cost_cap_abort", "error", message=cap_abort_reason)
        return store.summary()

    def _fail_fast_failed():
        """Write the fail_fast failed checkpoint and return the summary."""
        store.write_checkpoint(
            state="failed",
            cursor=done_count,
            total=total,
            last_error={
                "type": "item",
                "message": last_error,
                "at": utc_now(),
                "item_id": last_error_item,
                "retryable": False,
            },
        )
        store.append_event("failed", "error", cursor=done_count, last_error=last_error)
        return store.summary()

    # Mark the first in-flight provider call as running too. Idle cancellation
    # distinguishes an active runner from prepared/paused stores using this
    # checkpoint; waiting until the first result loses first-row cancels.
    store.write_checkpoint(state="running", cursor=done_count, total=total,
                           remote=(store.read_checkpoint() or {}).get("remote"))
    store.append_event("resume" if done_count else "start", task=task)
    cancel_request = None

    def _cancelled() -> bool:
        """Remember an observed cancellation request and report whether to stop."""
        nonlocal cancel_request
        cancel_request = store.pending_cancel() or cancel_request
        return cancel_request is not None

    concurrency = _concurrency(store)
    if concurrency <= 1:
        for index in pending:
            if _cancelled():
                break
            value, error, latency_ms, usage = _attempt(index)
            _record(index, value, error, latency_ms, usage)
            if cap_abort_reason:
                return _cap_abort_failed()
            if fail_fast and error is not None:
                return _fail_fast_failed()
    else:
        # Throughput mode: bounded threads expose N concurrent docs to the
        # engine so vLLM's continuous batching fills up (Modal vllm_throughput
        # exemplar — offline evals are a throughput workload, not a latency
        # one). Each task runs in a copied context so the pipeline's
        # contextvar run limits (pipeline/limits.py) and trace state stay
        # per-doc isolated.
        import contextvars
        from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

        stopped = False
        it = iter(pending)
        futures: dict[Any, int] = {}

        def _submit_next() -> bool:
            """Submit the next pending row with a copy of the current context.

            Return False when cancellation is observed or no pending row remains.
            """
            if _cancelled():
                return False
            index = next(it, None)
            if index is None:
                return False
            ctx = contextvars.copy_context()
            futures[pool.submit(ctx.run, _attempt, index)] = index
            return True

        with ThreadPoolExecutor(max_workers=min(concurrency, len(pending) or 1)) as pool:
            while not stopped and len(futures) < concurrency:
                if not _submit_next():
                    break
            while futures:
                done, _ = wait(list(futures), return_when=FIRST_COMPLETED)
                for fut in done:
                    index = futures.pop(fut)
                    try:
                        value, error, latency_ms, usage = fut.result()
                    except Exception as exc:  # noqa: BLE001 — never drop a row
                        value, error, latency_ms, usage = (
                            None,
                            f"{type(exc).__name__}: {str(exc)[:512]}",
                            0.0,
                            {},
                        )
                    ok = _record(index, value, error, latency_ms, usage)
                    if cap_abort_reason:
                        stopped = True
                    elif fail_fast and not ok:
                        # Stop SCHEDULING new rows; in-flight requests still
                        # finish and persist (their GPU work is already spent).
                        stopped = True
                if not stopped:
                    while len(futures) < concurrency:
                        if not _submit_next():
                            break
        if stopped:
            if cap_abort_reason:
                return _cap_abort_failed()
            return _fail_fast_failed()

    final_cursor = len(store.load_items())
    if _cancelled():
        store.write_checkpoint(state="paused", cursor=final_cursor, total=total,
                               last_error={"type": "item", "message": last_error,
                                           "item_id": last_error_item} if last_error else None)
        store.acknowledge_cancel(cancel_request)
        store.append_event("paused", "info", cursor=final_cursor)
        return store.summary()
    if final_cursor < total:
        # max_items capped invocation: leave a resumable running state.
        store.write_checkpoint(state="running", cursor=final_cursor, total=total, remote=None)
        store.append_event("yielded", "info", cursor=final_cursor)
        return {
            "state": "running",
            "task": task,
            "cursor": final_cursor,
            "total": total,
            "ok": ok_count,
            "errors": error_count,
            "last_error": last_error,
        }
    ok_by_index = {int(d["index"]): bool(d.get("ok", False)) for d in store.load_items()}
    if rows and not any(ok_by_index.get(i, False) for i in range(len(rows))):
        # Live-or-loud (DMR-044/049 doctrine, hub#39): a run where EVERY item
        # errored (this invocation AND resumed rows) is a failed job — a
        # "done" checkpoint + log record would silently claim success over a
        # dead engine. Mirrors the run_isolated_eval all-rows guard
        # (eval/runners.py).
        first_error = {
            "type": "item",
            "message": last_error,
            "at": utc_now(),
            "item_id": last_error_item,
            "retryable": False,
        }
        store.write_checkpoint(
            state="failed", cursor=final_cursor, total=total, remote=None, last_error=first_error
        )
        store.append_event("failed", "error", cursor=final_cursor, last_error=last_error)
        return {
            "state": "failed",
            "task": task,
            "cursor": final_cursor,
            "total": total,
            "ok": 0,
            "errors": error_count,
            "last_error": first_error,
        }
    # Score only completed, ok rows — a failed row must never count as a wrong
    # prediction, and the error count is reported explicitly (DMR-049 F4).
    scored_pairs = [
        (expected[i], predicted[i])
        for i in range(len(rows))
        if ok_by_index.get(i, False) and predicted[i] != ""
    ]
    scores = (
        _score(task, [e for e, _ in scored_pairs], [p for _, p in scored_pairs])
        if scored_pairs
        else {}
    )
    if error_count:
        scores["error_count"] = error_count
    wall_seconds = round(time.perf_counter() - run_started, 3)
    record = _build_record(store, task, model, scores, mock=mock, wall_seconds=wall_seconds)
    experiment_log.append(record)
    store.append_event("done", "info", cursor=final_cursor, ok_count=ok_count)
    store.write_checkpoint(state="done", cursor=final_cursor, total=total, remote=None,
                           last_error={"type": "item", "message": last_error,
                                       "item_id": last_error_item} if last_error else None)
    from mailroom_sandbox.job.dated_reports import maybe_write_run_reports

    maybe_write_run_reports(store, scores=scores, wall_seconds=wall_seconds)
    from mailroom_sandbox.job.grid_cards import maybe_write_card

    maybe_write_card(store, scores=scores, wall_seconds=wall_seconds)
    return {
        "state": "done",
        "task": task,
        "cursor": final_cursor,
        "total": total,
        "ok": ok_count,
        "errors": error_count,
        "last_error": last_error,
        "scores": scores,
        "record": record,
    }


def cancel_or_pause(store: RunStore) -> dict[str, Any]:
    """Handle an interrupt: write paused checkpoint and return its summary."""
    cursor = store.resume_cursor()
    store.write_checkpoint(state="paused", cursor=cursor, total=len(store.dataset_rows()), remote=None)
    store.append_event("paused", "warn", cursor=cursor)
    return {"state": "paused", "cursor": cursor, "total": len(store.dataset_rows())}
