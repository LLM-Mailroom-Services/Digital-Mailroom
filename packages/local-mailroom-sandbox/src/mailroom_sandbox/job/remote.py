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
import logging
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mailroom_sandbox.job.checkpoint import RunStore

logger = logging.getLogger(__name__)

VOLUME_NAME = "sandbox-runs"
STATE_DICT = "sandbox-job-state"
APP_NAME = "sandbox-job"
FN_NAME = "run_job"

TERMINAL_STATES = ("SUCCESS", "FAILURE", "TERMINATED", "TIMEOUT", "INIT_FAILURE")

# hub#41: refuse to re-fire a call younger than this (the sandbox modal app's
# scaledown window) — a double-fired worker would append to the same run dir.
REMOTE_REFIRE_COOLDOWN_SECONDS = 15 * 60


def _modal():
    import modal  # type: ignore

    return modal


def _call_status(fc: Any) -> str | None:
    try:
        graph = fc.get_call_graph()
    except Exception:
        # NOTE (DMR-056): a status-lookup failure returns None, and None is
        # NOT in TERMINAL_STATES — so is_alive treats an undeterminable call
        # as alive and ensure_running attaches to it. Acceptable for a
        # polling CLI; the SDK's own docs note call-graph data is not
        # populated in real time and not recommended for critical use.
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
        except OSError as exc:
            logger.warning("modal volume get for %s could not start: %s", run_id, exc)
            return None
        if proc.returncode != 0:
            logger.warning(
                "remote lock hash for %s unreadable (rc=%d): %s",
                run_id,
                proc.returncode,
                (proc.stderr.strip() or proc.stdout.strip())[:400],
            )
            return None
        matches = list(Path(tmp).rglob("spec.lock.json"))
        if not matches:
            logger.warning("remote lock file for %s not found under the volume fetch", run_id)
            return None
        try:
            payload = json.loads(matches[0].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("remote lock for %s is corrupt/unreadable: %s", run_id, exc)
            return None
        return str(payload.get("spec_hash") or "") or None


def _lock_mock(store: RunStore) -> bool:
    lock = store.read_lock() or {}
    job = lock.get("job") or {}
    return bool(job.get("mock", False)) if isinstance(job, dict) else False


def upload_run_dir(run_dir: Path) -> tuple[int, str]:
    try:
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
    except FileNotFoundError:
        # Modal job mode needs the SDK — point at the extra (DMR-058) instead
        # of a bare "no such file: modal" from main()'s generic catch.
        raise FileNotFoundError(
            "modal CLI not installed — pip install -e \".[deploy]\" (then `modal token new`)"
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
        remote={
            "call_id": call_id,
            "app": APP_NAME,
            "fn": FN_NAME,
            "fired_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
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
    except Exception as exc:  # noqa: BLE001 — hub#41: false death double-fires workers
        # An undeterminable call (transient SDK/network error, missing SDK)
        # must be treated as ALIVE — is_alive=False on any exception made
        # ensure_running re-fire the job, spawning a second worker on the
        # same run dir. Match _call_status's None posture: alive unless
        # provably terminal.
        logger.warning("could not determine remote call status; treating as alive: %s", exc)
        return True
    return status not in TERMINAL_STATES


def read_progress(store: RunStore) -> dict | None:
    """Live progress from the job-state Dict; fall back to the checkpoint."""
    try:
        modal = _modal()
        state_dict = modal.Dict.from_name(STATE_DICT, create_if_missing=True)
        value = state_dict.get(store.run_id, None)
        if isinstance(value, dict):
            return value
        logger.warning(
            "job-state Dict has no live entry for run %s — falling back to the "
            "local checkpoint (progress shown may be stale)",
            store.run_id,
        )
    except Exception as exc:
        logger.warning(
            "job-state Dict could not be read for run %s — falling back to the "
            "local checkpoint (progress shown may be stale): %s",
            store.run_id,
            exc,
        )
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
    if isinstance(remote, dict) and remote.get("call_id"):
        if is_alive(store):
            store.append_event("remote_reattached", "info", call_id=remote["call_id"])
            return {"action": "attached", "call_id": remote["call_id"]}
        # hub#41: a call that looks dead but was fired within the cooldown
        # window is treated as possibly-live — re-firing would spawn a second
        # worker appending to the same run dir (corrupting items.jsonl). The
        # _remote_lock_hash guard only skips the Volume upload, not the
        # re-fire, so the guard lives here.
        fired_at = remote.get("fired_at")
        age: float | None = None
        if fired_at:
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(fired_at)).total_seconds()
            except ValueError as exc:
                raise RuntimeError(
                    f"remote call {remote['call_id']} carries a MALFORMED fired_at "
                    f"({fired_at!r}) — the hub#41 re-fire cooldown cannot be "
                    f"verified, and a possibly-live worker must not be doubled. "
                    f"Refusing to re-fire; inspect the checkpoint's remote section: "
                    f"{remote!r}"
                ) from exc
        if age is not None and age < REMOTE_REFIRE_COOLDOWN_SECONDS:
            raise RuntimeError(
                f"remote call {remote['call_id']} is not alive but was fired "
                f"{age / 60:.0f} minutes ago (< {REMOTE_REFIRE_COOLDOWN_SECONDS // 60}-minute "
                f"cooldown) — refusing to re-fire a possibly-live worker; inspect with "
                f"`sandbox run status {store.run_id} --watch`"
            )
    result = fire(store)
    return {"action": "fired", "call_id": result["call_id"]}
