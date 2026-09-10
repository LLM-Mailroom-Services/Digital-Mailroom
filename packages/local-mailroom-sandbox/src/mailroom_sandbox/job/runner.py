"""Checkpoint-aware item loop + scoring + experiment-log append (DMR-027).

``run_job`` executes the locked dataset row-by-row for the per-item tasks
(``sorter``, ``legalbench`` in v1) so a pause/error resumes from the last
appended item. Progress source of truth is ``items.jsonl``;
``checkpoint.json`` is the atomic mirror. Other tasks delegate to the
existing public eval runner at whole-run granularity.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Callable

from mailroom_sandbox.eval import experiment_log
from mailroom_sandbox.eval import runners as eval_runners  # noqa: F401
from mailroom_sandbox.job.checkpoint import RunStore, utc_now
from mailroom_sandbox.job.metrics import record_from_run
from mailroom_sandbox.job.otel import job_span

PER_ITEM_TASKS = ("sorter", "legalbench")
RUNNABLE_TASKS = PER_ITEM_TASKS + ("pipeline", "extract", "chained", "local_vs_api", "isolated")


def _predict_row(task: str, row: dict[str, Any], *, mock: bool, model: str | None) -> tuple[Any, bool]:
    if task == "sorter":
        if mock:
            return eval_runners._classify_mock(row), True
        result = eval_runners._run_pipeline_doc(row, mock=False)
        return (result.get("doc_type") or "unknown"), True
    if task == "legalbench":
        if mock:
            blob = row.get("doc_text") or row.get("text") or ""
            answer = "Yes" if int(hashlib.md5(blob.encode()).hexdigest()[:2], 16) % 2 else "No"
            return answer, True
        return eval_runners._live_legalbench_answer(row, model=model), True
    raise ValueError(f"task {task!r} is not a per-item task in v1")


def _score(task: str, expected: list[str], predicted: list[str]) -> dict[str, Any]:
    from mailroom_sandbox.eval import scoring as sc

    if task == "legalbench":
        return sc.score_legalbench(expected, predicted)
    return sc.score_classification(expected, predicted)


def _task_defaults(store: RunStore) -> dict[str, Any]:
    lock = store.read_lock() or {}
    return lock.get("job", {})


def _max_retries(store: RunStore) -> int:
    return int(_task_defaults(store).get("max_retries", 2))


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
    return str((store.read_lock() or {}).get("profile") or "ollama")


def _lock_mock(store: RunStore, default: bool) -> bool:
    return bool(_task_defaults(store).get("mock", default))


def _fingerprint(store: RunStore) -> str:
    rows = store.dataset_rows()
    if not rows:
        return ""
    parts = [f"{r.get('id')}|{r.get('expected_doc_class')}" for r in rows]
    return hashlib.md5(";".join(sorted(parts)).encode()).hexdigest()[:12]


def _apply_prompt_overrides(store: RunStore) -> None:
    from mailroom_sandbox.prompt_registry import apply_runtime_overrides

    prompt_lock = store.read_prompt_lock() or {}
    texts = {}
    for agent, ref in (prompt_lock.get("agents") or {}).items():
        if isinstance(ref, dict) and ref.get("text"):
            texts[agent] = ref["text"]
    apply_runtime_overrides(texts)


def _build_record(
    store: RunStore, task: str, model: str | None, scores: dict[str, Any], *, mock: bool
) -> dict[str, Any]:
    lock = store.read_lock() or {}
    prompt_block = lock.get("prompt") or {}
    profile = str(lock.get("profile") or "ollama")
    engine = lock.get("engine") or {}
    model = model or (engine.get("model") if isinstance(engine, dict) else None) or "unknown"
    prompt_version = str((prompt_block.get("default") or {}).get("source") or "code-default")
    record = record_from_run(
        run_id=store.run_id,
        spec_hash=store.spec_hash() or "",
        task=task,
        profile=profile,
        model=model,
        prompt_version=prompt_version,
        dataset_fingerprint=_fingerprint(store),
        items=store.load_items(),
        scores=scores or None,
    )
    record["experiment_name"] = f"sandbox_{task}_{store.run_id}"
    record["mock"] = bool(mock)
    return record


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
    """Run (or resume) the locked job to completion and return a summary."""
    task = task or _lock_task(store)
    model = model or _lock_model(store)
    profile = profile or _lock_profile(store)
    mock = _lock_mock(store, True) if mock is None else mock

    rows = store.dataset_rows()
    if dry_run:
        return {"state": "dry_run", "task": task, "n": len(rows), "cursor": 0, "total": len(rows)}
    if store.terminal():
        return store.summary()
    if not rows:
        store.write_checkpoint(state="done", cursor=0, total=0, remote=None)
        store.append_event("done", "info", cursor=0)
        return {"state": "done", "cursor": 0, "total": 0, "ok": 0, "errors": 0}

    cursor = store.resume_cursor()
    total = len(rows)
    _apply_prompt_overrides(store)

    # Reconstruct already-completed predictions so final scoring covers all rows.
    completed: dict[int, dict[str, Any]] = {}
    for done in store.load_items():
        if "index" in done:
            completed[int(done["index"])] = done
    expected: list[str] = []
    predicted: list[str] = []
    for index, row in enumerate(rows):
        expected.append(str(row.get("expected_doc_class") or ""))
        done = completed.get(index)
        if done is not None:
            predicted.append(str(done.get("predicted") or ""))
        else:
            predicted.append("")  # placeholder; refilled during the loop below

    ok_count = 0
    error_count = 0
    last_error: str | None = None
    for index, row in enumerate(rows):
        if index < cursor:
            continue
        if max_items is not None and index >= cursor + max_items:
            break
        item_id = str(row.get("id") or row.get("filename") or index)
        started = time.perf_counter()
        value: Any = None
        error: str | None = None
        with job_span(tracer, "job.item", item_index=str(index), task=task):
            attempt = 0
            while attempt < _max_retries(store) + 1:
                attempt += 1
                try:
                    value, _ = _predict_row(task, row, mock=mock, model=model)
                    error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    error = f"{type(exc).__name__}: {str(exc)[:512]}"
                    if attempt <= _max_retries(store):
                        time.sleep(0.2)
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        ok = error is None
        if ok:
            ok_count += 1
        else:
            error_count += 1
            last_error = error
        predicted[index] = str(value) if value is not None else ""
        store.append_item(
            {
                "item_id": item_id,
                "index": index,
                "expected": row.get("expected_doc_class"),
                "predicted": predicted[index],
                "ok": ok,
                "error": error,
                "latency_ms": latency_ms,
                "trace_id": "",
                "ts": utc_now(),
            }
        )
        store.append_event("item_" + ("done" if ok else "failed"), "info" if ok else "warn", index=index, item_id=item_id)
        store.write_checkpoint(state="running", cursor=index + 1, total=total, remote=None)
        if on_event is not None:
            try:
                on_event({"cursor": index + 1, "total": total, "ok": ok_count, "errors": error_count, "state": "running"})
            except Exception:
                pass
        if _fail_fast(store) and not ok:
            store.write_checkpoint(
                state="failed",
                cursor=index + 1,
                total=total,
                last_error={"type": "item", "message": error, "at": utc_now(), "item_id": item_id, "retryable": False},
            )
            store.append_event("failed", "error", cursor=index + 1, last_error=error)
            return store.summary()

    final_cursor = len(store.load_items())
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
    scores = _score(task, expected, predicted) if expected and predicted else {}
    record = _build_record(store, task, model, scores, mock=mock)
    experiment_log.append(record)
    store.append_event("done", "info", cursor=final_cursor, ok_count=ok_count)
    store.write_checkpoint(state="done", cursor=final_cursor, total=total, remote=None)
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