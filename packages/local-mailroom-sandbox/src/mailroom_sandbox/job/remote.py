"""Remote Modal job execution for sandbox runs (DMR-027, DMR-047).

Push the run dir to the ``sandbox-runs`` Volume, spawn the ``sandbox-job``
``run_job`` function, persist the call id in the checkpoint, then poll /
resume / cancel. Live progress is mirrored to the ``sandbox-job-state``
Modal Dict so the CLI can poll without heavy Volume reads.

The ``modal`` module is imported lazily and ``modal volume`` is shelled out
to, so the package's default runtime stays lean; tests stub both.

DMR-047 hardening:

- the spawn payload carries the lock's ``mock`` flag (the worker defaulted to
  live, silently burning GPU on a mock-flagged replay),
- a re-fire skips the Volume upload when the remote lock's ``spec_hash``
  already matches the local one (``--force put`` used to clobber remote
  progress on resume),
- ``pull_run_dir`` downloads items/checkpoints/records for terminal runs so
  the CLI can finalize the local run dir and append the experiment records.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from mailroom_sandbox.job.checkpoint import RunStore

VOLUME_NAME = "sandbox-runs"
STATE_DICT = "sandbox-job-state"
APP_NAME = "sandbox-job"
FN_NAME = "run_job"

TERMINAL_STATES = ("SUCCESS", "FAILURE", "TERMINATED", "TIMEOUT", "INIT_FAILURE")


def _modal():
    import modal  # type: ignore

    return modal


def _call_status(fc: Any) -> str | None:
    try:
        graph = fc.get_call_graph()
    except Exception:
        return None
    if not graph:
        return None
    status = getattr(graph[0], "status", None)
    name = getattr(status, "name", None)
    return str(name) if name else (str(status) if status else None)


def _remote_lock_hash(run_id: str) -> str | None:
    """The remote ``spec.lock.json`` hash, or None when absent/unreadable."""
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run(
                ["modal", "volume", "get", VOLUME_NAME, f"/runs/{run_id}/spec.lock.json", tmp],
                capture_output=True,
                text=True,
            )
        except OSError:
            return None
        if proc.returncode != 0:
            return None
        matches = list(Path(tmp).rglob("spec.lock.json"))
        if not matches:
            return None
        try:
            payload = json.loads(matches[0].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return str(payload.get("spec_hash") or "") or None


def _lock_mock(store: RunStore) -> bool:
    lock = store.read_lock() or {}
    job = lock.get("job") or {}
    return bool(job.get("mock", False)) if isinstance(job, dict) else False


def upload_run_dir(run_dir: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [
            "modal",
            "volume",
            "put",
            "--force",
            VOLUME_NAME,
            str(run_dir),
            f"/runs/{run_dir.name}",
        ],
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stderr.strip() or proc.stdout.strip())


def fire(store: RunStore, *, payload: dict | None = None) -> dict[str, Any]:
    """Push the run dir (when needed) and spawn the remote job; persist the call id."""
    lock = store.read_lock() or {}
    local_hash = str(lock.get("spec_hash") or "") or None
    if local_hash is None or _remote_lock_hash(store.run_id) != local_hash:
        rc, err = upload_run_dir(store.dir)
        if rc != 0:
            raise RuntimeError(
                f"modal volume put failed: {err or 'rc=%d' % rc} — check `modal token new` "
                f"and `modal volume ls {VOLUME_NAME}`"
            )
    modal = _modal()
    fn = modal.Function.from_name(APP_NAME, FN_NAME)
    call = fn.spawn(payload or {"run_id": store.run_id, "mock": _lock_mock(store)})
    call_id = str(call.object_id)
    cp = store.read_checkpoint() or {}
    store.write_checkpoint(
        state="running",
        cursor=cp.get("cursor", 0),
        total=cp.get("total", len(store.dataset_rows())),
        remote={"call_id": call_id, "app": APP_NAME, "fn": FN_NAME},
    )
    store.append_event("fired", "info", call_id=call_id)
    return {"call_id": call_id}


def is_alive(store: RunStore) -> bool:
    remote = (store.read_checkpoint() or {}).get("remote")
    call_id = remote.get("call_id") if isinstance(remote, dict) else None
    if not call_id:
        return False
    try:
        modal = _modal()
        status = _call_status(modal.FunctionCall.from_id(call_id))
    except Exception:
        return False
    return status not in TERMINAL_STATES


def read_progress(store: RunStore) -> dict | None:
    """Live progress from the job-state Dict; fall back to the checkpoint."""
    try:
        modal = _modal()
        state_dict = modal.Dict.from_name(STATE_DICT, create_if_missing=True)
        value = state_dict.get(store.run_id, None)
        if isinstance(value, dict):
            return value
    except Exception:
        pass
    return store.read_checkpoint()


def pull_run_dir(store: RunStore) -> tuple[int, str]:
    """Download the remote run dir (items/checkpoints/records) into the local one."""
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            ["modal", "volume", "get", VOLUME_NAME, f"/runs/{store.run_id}", tmp],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return proc.returncode, (proc.stderr.strip() or proc.stdout.strip())
        source = Path(tmp) / store.run_id
        if not source.is_dir():
            # Some CLI versions nest the download under an extra component.
            matches = list(Path(tmp).rglob("spec.lock.json"))
            source = matches[0].parent if matches else source
        if not source.is_dir():
            return 1, f"remote run dir not found under {tmp}"
        for item in source.iterdir():
            if item.is_file():
                shutil.copy2(item, store.dir / item.name)
    return 0, ""


def cancel(store: RunStore, *, terminate: bool = False) -> None:
    remote = (store.read_checkpoint() or {}).get("remote")
    call_id = remote.get("call_id") if isinstance(remote, dict) else None
    if not call_id:
        raise RuntimeError(f"run {store.run_id} has no remote call to cancel")
    modal = _modal()
    modal.FunctionCall.from_id(call_id).cancel(terminate_containers=terminate)
    store.append_event("cancel_requested", "info", call_id=call_id)


def ensure_running(store: RunStore) -> dict:
    """Attach to a live call or (re)fire the job; returns the action taken."""
    cp = store.read_checkpoint() or {}
    remote = cp.get("remote")
    if isinstance(remote, dict) and remote.get("call_id") and is_alive(store):
        store.append_event("remote_reattached", "info", call_id=remote["call_id"])
        return {"action": "attached", "call_id": remote["call_id"]}
    result = fire(store)
    return {"action": "fired", "call_id": result["call_id"]}
