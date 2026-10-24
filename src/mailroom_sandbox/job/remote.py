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
- transfers, dispatch, progress and finalization bind the complete locked
  generation; new uploads use content-addressed directories without force,
- an intact matching legacy directory can be resumed without rewriting it,
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

from mailroom_sandbox.job.checkpoint import RunStore, generation_identity

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


def generation_fields(lock: dict) -> dict:
    """Return run/spec IDs, the optional generation ID, and content identity."""
    return {"run_id": lock["run_id"], "spec_hash": lock["spec_hash"],
            "generation_id": lock.get("generation_id"), "run_generation": generation_identity(lock)}


def generation_path(lock: dict) -> str:
    """Return the content-addressed run path relative to RUNS_MOUNT.

    Keep the run ID as the basename. Raise RuntimeError for an empty,
    traversal, or path-containing run ID.
    """
    run_id = lock["run_id"]
    if not isinstance(run_id, str) or run_id in {"", ".", ".."} or "/" in run_id or "\\" in run_id:
        raise RuntimeError("invalid remote run ID")
    return f".generations/{generation_identity(lock)['lock_sha256']}/{run_id}"


def _run_path(store: RunStore) -> str:
    """Return the checkpoint's remote path, defaulting to the legacy run ID.

    Raise RuntimeError if the path or stamped remote identity belongs to
    another generation, or the lock's run ID is invalid.
    """
    lock = store.read_lock() or {}
    remote = (store.read_checkpoint() or {}).get("remote") or {}
    path = remote.get("run_path", store.run_id)
    if path not in {store.run_id, generation_path(lock)}:
        raise RuntimeError("remote path belongs to another generation")
    if remote.get("run_generation") is not None and remote["run_generation"] != generation_identity(lock):
        raise RuntimeError("remote call belongs to another generation")
    return path


def _remote_lock(run_path: str) -> dict | None:
    """Fetch the full remote lock, returning None for a nonzero CLI exit.

    Raise RuntimeError for missing, ambiguous, unreadable, or non-object lock
    JSON after a successful download. Process-launch and staging errors
    propagate. Uploads never force an overwrite when identity is unknown.
    """
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            ["modal", "volume", "get", VOLUME_NAME, f"/runs/{run_path}/spec.lock.json", tmp],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            logger.info("remote lock unavailable for %s: %s", run_path, proc.stderr.strip()[:400])
            return None
        matches = list(Path(tmp).rglob("spec.lock.json"))
        if len(matches) != 1:
            raise RuntimeError("remote generation lock missing or ambiguous")
        try:
            lock = json.loads(matches[0].read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError("remote generation lock unreadable") from exc
        if not isinstance(lock, dict):
            raise RuntimeError("remote generation lock is not an object")
        return lock


def _same_lock(left: dict | None, right: dict) -> bool:
    """Return whether a remote lock exists and has the same content identity."""
    return isinstance(left, dict) and generation_identity(left) == generation_identity(right)


def _lock_mock(store: RunStore) -> bool:
    lock = store.read_lock() or {}
    job = lock.get("job") or {}
    return bool(job.get("mock", False)) if isinstance(job, dict) else False


def upload_run_dir(run_dir: Path, *, run_path: str | None = None) -> tuple[int, str]:
    """Upload a directory to a Volume path without requesting an overwrite.

    ``run_path`` is relative to the Volume's ``/runs`` directory and defaults
    to the local directory basename. Return the CLI exit code and stderr
    (or stdout when stderr is empty). Raise FileNotFoundError with setup
    guidance when the Modal CLI is missing; other process errors propagate.
    """
    try:
        proc = subprocess.run(
            [
                "modal",
                "volume",
                "put",
                VOLUME_NAME,
                str(run_dir),
                f"/runs/{run_path or run_dir.name}",
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
    """Dispatch the verified generation and return its persisted call ID.

    Reuse a matching remote directory or upload to a content-addressed path
    without overwriting existing data. ``payload`` adds worker options but
    cannot replace the locked identity, path, or mock setting. Update the
    checkpoint and lifecycle journal after spawning.

    Raise RuntimeError for invalid/mismatched generations or failed uploads.
    CLI, SDK, and local store errors propagate.
    """
    lock = store.verify_generation()
    # Prefer a prior matching location, including original /runs/<run_id>
    # stores. Mismatched legacy work is left untouched, even when apparently
    # terminal. A new generation gets a distinct immutable-content namespace.
    run_path = _run_path(store)
    remote_lock = _remote_lock(run_path)
    if not _same_lock(remote_lock, lock):
        run_path = generation_path(lock)
        remote_lock = _remote_lock(run_path)
        if remote_lock is not None and not _same_lock(remote_lock, lock):
            raise RuntimeError("remote generation destination contains a mismatched lock; refusing overwrite")
        if remote_lock is None:
            # Do not upload local archives, lock inodes, or cancellation tokens.
            with tempfile.TemporaryDirectory() as tmp:
                upload = Path(tmp) / store.run_id
                upload.mkdir()
                for name in ("spec.lock.json", "prompt.lock.json", "dataset.jsonl", "checkpoint.json",
                             "items.jsonl", "events.jsonl", "cold_boot.json", "experiment_log.jsonl"):
                    source = store.dir / name
                    if source.is_file():
                        shutil.copy2(source, upload / name)
                rc, err = upload_run_dir(upload, run_path=run_path)
            if rc != 0:
                raise RuntimeError(f"modal volume put failed (no overwrite): {err or rc}")
    modal = _modal()
    fn = modal.Function.from_name(APP_NAME, FN_NAME)
    expected = generation_fields(lock)
    call = fn.spawn({**(payload or {}), **expected, "mock": _lock_mock(store), "run_path": run_path})
    call_id = str(call.object_id)
    cp = store.read_checkpoint() or {}
    store.write_checkpoint(
        state="running",
        cursor=cp.get("cursor", 0),
        total=cp.get("total", len(store.dataset_rows())),
        remote={
            "call_id": call_id,
            **expected,
            "run_path": run_path,
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


def terminal_confirmed(store: RunStore) -> bool:
    """Prove a known single-input call has finished before resetting its files.

    Call graphs are best-effort diagnostics, not a destructive-reset guard.
    In modal==1.6.2, get(timeout=0) returns a result or raises one of the
    result-path exceptions below only after the input finishes. A polling
    timeout, lookup/transport failure, or ambiguous exception proves nothing.
    """
    remote = (store.read_checkpoint() or {}).get("remote")
    call_id = remote.get("call_id") if isinstance(remote, dict) else None
    if not call_id:
        return False
    try:
        modal = _modal()
        call = modal.FunctionCall.from_id(call_id)
        terminal_errors = (modal.exception.FunctionTimeoutError,
                           modal.exception.OutputExpiredError, modal.exception.RemoteError)
    except Exception as exc:
        logger.warning("could not look up remote call for reset; refusing reset: %s", exc)
        return False
    try:
        call.get(timeout=0)
    except terminal_errors:
        # 1.6.2: FunctionTimeoutError/RemoteError are emitted by result
        # processing; OutputExpiredError means zero unfinished inputs.
        # Lookup errors are handled separately above, never as results.
        return True
    except Exception as exc:
        logger.warning("remote completion is undetermined; refusing reset: %s", exc)
        return False
    return True


def read_progress(store: RunStore) -> dict | None:
    """Return progress proven to match this generation, else the local checkpoint.

    Legacy cache entries require matching run/spec identity, a fresh heartbeat,
    and a matching remote lock. Remote lookup and validation errors are caught;
    the fallback checkpoint may be stale or absent.
    """
    try:
        modal = _modal()
        state_dict = modal.Dict.from_name(STATE_DICT, create_if_missing=True)
        lock = store.verify_generation()
        key = f"generation:{generation_identity(lock)['lock_sha256']}:{store.run_id}"
        value = state_dict.get(key, None)
        if isinstance(value, dict) and all(value.get(k) == v for k, v in generation_fields(lock).items()):
            return value
        # Real old workers used run_id keys and emitted run/spec/heartbeat only.
        # Require a legacy local lock, identical remote lock and a heartbeat no
        # earlier than lock creation; stamped generations never trust this cache.
        value = state_dict.get(store.run_id, None)
        if isinstance(value, dict):
            if value.get("run_generation") is not None:
                if all(value.get(k) == v for k, v in generation_fields(lock).items()):
                    return value
            elif not lock.get("generation_id") and value.get("generation_id") is None:
                try:
                    fresh = datetime.fromisoformat(value["heartbeat_at"].replace("Z", "+00:00")) >= datetime.fromisoformat(lock["created_at"].replace("Z", "+00:00"))
                except (KeyError, TypeError, ValueError):
                    fresh = False
                if (fresh and value.get("run_id") == store.run_id and value.get("spec_hash") == lock["spec_hash"]
                        and _same_lock(_remote_lock(_run_path(store)), lock)):
                    return value
            logger.warning("ignoring stale or unproven remote generation progress for %s", store.run_id)
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
    """Validate fetched terminal artifacts in staging before replacing local results.

    Immutable local artifacts and lock/control inodes are never replaced;
    the local remote-call metadata is retained. Return ``(0, "")`` on success,
    a CLI error pair on download failure, or ``(1, detail)`` for rejected
    staged artifacts, a changed local generation, or a busy local store. Initial
    local generation validation, process-launch, and other store/copy errors propagate.
    """
    lock = store.verify_generation()
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            ["modal", "volume", "get", VOLUME_NAME, f"/runs/{_run_path(store)}", tmp],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            return proc.returncode, (proc.stderr.strip() or proc.stdout.strip())
        matches = list(Path(tmp).rglob("spec.lock.json"))
        if len(matches) != 1:
            return 1, "remote generation missing or ambiguous"
        source = matches[0].parent
        if source.name != store.run_id:
            # CLI versions may download contents directly into the destination.
            staged_dir = Path(tmp) / "validated" / store.run_id
            shutil.copytree(source, staged_dir, ignore=shutil.ignore_patterns("validated"))
            source = staged_dir
        try:
            staged = RunStore(source)
            remote_lock = staged.verify_generation()
            if not _same_lock(remote_lock, lock):
                raise RuntimeError("fetched remote generation differs from the local generation")
            if staged.state() not in {"done", "failed"}:
                raise RuntimeError("fetched remote generation is not terminal")
            # Parse every transferable JSON/JSONL before touching local files.
            for name in ("items.jsonl", "events.jsonl", "experiment_log.jsonl"):
                path = source / name
                if path.is_file():
                    for line in path.read_text(encoding="utf-8").splitlines():
                        if line.strip() and not isinstance(json.loads(line), dict):
                            raise RuntimeError(f"invalid remote {name} record")
            cold_boot = source / "cold_boot.json"
            if cold_boot.is_file():
                json.loads(cold_boot.read_text(encoding="utf-8"))
        except (RuntimeError, OSError, ValueError) as exc:
            return 1, f"remote generation validation failed: {exc}"
        try:
            with store.acquire(blocking=False), store.control():
                if not _same_lock(store.verify_generation(), lock):
                    return 1, "local generation changed during remote fetch"
                checkpoint = json.loads((source / "checkpoint.json").read_text(encoding="utf-8"))
                checkpoint["remote"] = (store.read_checkpoint() or {}).get("remote")
                (source / "checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
                for name in ("items.jsonl", "events.jsonl", "cold_boot.json", "experiment_log.jsonl", "checkpoint.json"):
                    item = source / name
                    if item.is_file():
                        # Replace each file from a local staging file; checkpoint last.
                        dest = store.dir / name
                        staged_file = dest.with_name(dest.name + ".pull.tmp")
                        shutil.copy2(item, staged_file)
                        staged_file.replace(dest)
        except BlockingIOError:
            return 1, "local store is busy; refusing remote pull"
    return 0, ""


def cancel(store: RunStore, *, terminate: bool = False) -> None:
    """Request cancellation of the generation's remote call and journal the request.

    ``terminate`` also requests container termination. Raise RuntimeError for
    a missing call ID or mismatched generation/path; SDK and store errors
    propagate. This does not mark the local checkpoint terminal.
    """
    remote = (store.read_checkpoint() or {}).get("remote")
    call_id = remote.get("call_id") if isinstance(remote, dict) else None
    if not call_id:
        raise RuntimeError(f"run {store.run_id} has no remote call to cancel")
    _run_path(store)
    modal = _modal()
    modal.FunctionCall.from_id(call_id).cancel(terminate_containers=terminate)
    store.append_event("cancel_requested", "info", call_id=call_id)


def ensure_running(store: RunStore) -> dict:
    """Return ``action`` and ``call_id`` after attaching or dispatching a job.

    An undetermined call status is treated as alive. Re-dispatch requires
    confirmed completion and expiry of the 15-minute cooldown when a dispatch
    time is recorded. Raise RuntimeError for unproven generation identity,
    a malformed dispatch timestamp, an active cooldown, or unconfirmed
    completion; remote dispatch and store errors propagate.
    """
    cp = store.read_checkpoint() or {}
    remote = cp.get("remote")
    if isinstance(remote, dict) and remote.get("call_id"):
        lock = store.verify_generation()
        # Never attach a call whose expected identity differs from this lock.
        _run_path(store)
        if remote.get("run_generation") is None and not _same_lock(_remote_lock(_run_path(store)), lock):
            raise RuntimeError("legacy remote call has no matching generation proof; refusing attach/refire")
        if is_alive(store):
            store.append_event("remote_reattached", "info", call_id=remote["call_id"])
            return {"action": "attached", "call_id": remote["call_id"]}
        # hub#41: a call that looks dead but was fired within the cooldown
        # window is treated as possibly-live — re-firing would spawn a second
        # worker appending to the same run dir (corrupting items.jsonl). The
        # generation comparison skips uploads but cannot serialize dispatch,
        # so the cooldown and result-path guard live here.
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
        if not terminal_confirmed(store):
            raise RuntimeError("remote completion is unconfirmed; refusing to re-fire a possibly-live worker")
    result = fire(store)
    return {"action": "fired", "call_id": result["call_id"]}
