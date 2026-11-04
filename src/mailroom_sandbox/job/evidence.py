"""Run identity checks for append-only experiment evidence (no scoring logic)."""
from __future__ import annotations

from typing import Any

from mailroom_sandbox.job.checkpoint import generation_identity


def record_matches(record: dict[str, Any], store, lock: dict[str, Any], *, state: str = "done") -> bool:
    """Return whether evidence matches the locked run, spec, task, and state.

    Stamped records must match the full generation identity; task aliases
    also require the matching scorer task. Unstamped evidence is accepted
    only for successful, unarchived legacy runs with one matching prompt,
    dataset fingerprint, and timestamp within the lock/checkpoint interval.
    Missing or invalid legacy timestamps return False; store errors propagate.
    """
    task = lock.get("task")
    if record.get("spec_hash") != lock.get("spec_hash"):
        return False
    if record.get("run_id") is not None:
        if record["run_id"] != lock.get("run_id"):
            return False
    elif record.get("experiment_name") != f"sandbox_{task}_{lock.get('run_id')}":
        return False
    if "run_generation" in record:
        # New alias records carry both immutable run task and original scorer
        # task. Older stamps must still prove the task exactly; no wildcard.
        if "run_task" in record:
            scorer_task = {"isolated": "sorter", "chained": "extract"}.get(task, task)
            task_matches = record["run_task"] == task and record.get("task") == scorer_task
        else:
            task_matches = record.get("task") == task
        return (record["run_generation"] == generation_identity(lock)
                and record.get("run_state") == state and task_matches)
    # Historical proof is deliberately narrow: exact task, unreset legacy
    # lock, bounded timestamp, one explicit full prompt SHA and dataset hash.
    if (state != "done" or record.get("task") != task
            or ("run_task" in record and record["run_task"] != task)
            or lock.get("generation_id") or any(store.dir.glob("archive-*"))
            or record.get("run_state") not in (None, "done")):
        return False
    from datetime import datetime
    from mailroom_sandbox.job.runner import _fingerprint

    try:
        start = datetime.fromisoformat(lock["created_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(store.read_checkpoint()["updated_at"].replace("Z", "+00:00"))
        stamp = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        if not start <= stamp <= end:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    agents = (lock.get("prompt") or {}).get("agents") or {}
    prompt = agents.get(task) or {}
    return (len(agents) == 1 and bool(prompt.get("sha256"))
            and record.get("prompt_sha256") == prompt["sha256"]
            and record.get("dataset_fingerprint") == _fingerprint(store))
