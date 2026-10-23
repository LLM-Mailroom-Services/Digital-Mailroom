"""Crash-safe, resumable run store for sandbox jobs (DMR-027).

Layout under ``data/runtime/runs/<run_id>/``:

- ``spec.lock.json``  — immutable locked preflight manifest (the commit point)
- ``dataset.jsonl``   — prepared, normalized corpus subset (byte-identical per spec)
- ``prompt.lock.json``— per-agent resolved prompt snapshot + sha256
- ``items.jsonl``     — append-only per-item results (source of truth for progress)
- ``checkpoint.json`` — atomic state mirror (cache; never authoritative)
- ``events.jsonl``    — append-only lifecycle journal (diagnostic)
- ``<run_id>.lock``   — advisory flock (single-writer guard)
"""

from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

TERMINAL_STATES = ("done", "failed")
STATES = ("prepared", "running", "paused", "failed", "done")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _atomic_write(path: Path, payload: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    try:
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def _read_json(path: Path, *, strict: bool = False) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        if strict:
            # hub#41: a corrupt lock must be LOUD — a silent None made
            # preflight skip the drift check, write_lock no-op, and every
            # experiment record carry spec_hash: null.
            raise RuntimeError(f"corrupt JSON in {path}: {exc}") from exc
        return None


def truncate_torn_tail(items_path: Path, events_path: Path) -> int:
    """Drop an unparseable newline-less tail; keep a parseable final record."""
    if not items_path.is_file():
        return 0
    data = items_path.read_bytes()
    if not data:
        return 0
    newline = data.rfind(b"\n")
    if newline == len(data) - 1:
        return len(data)
    tail = data[newline + 1 :]
    try:
        json.loads(tail.decode("utf-8"))
        return len(data)  # parseable fragment = complete-ish, keep it
    except Exception:
        with open(items_path, "r+b") as fh:
            fh.truncate(newline + 1)
        try:
            with open(events_path, "a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "ts": utc_now(),
                            "event": "items_truncated",
                            "level": "warn",
                            "detail": {"dropped_chars": len(tail)},
                        }
                    )
                    + "\n"
                )
        except OSError:
            pass
        return newline + 1


def generation_identity(lock: dict[str, Any]) -> dict[str, str]:
    """Return a canonical lock hash and its declared dataset/prompt digests.

    Missing dataset or prompt digests become empty strings. This does not
    read or validate the corresponding artifact files.
    """
    import hashlib

    blob = json.dumps(lock, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {"lock_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
            "dataset_sha256": (lock.get("dataset") or {}).get("sha256") or "",
            "prompt_text_sha": lock.get("prompt_text_sha") or ""}


class RunStore:
    def __init__(self, run_dir: Path):
        """Create the run directory if needed and use its basename as the run ID."""
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.dir / "spec.lock.json"
        self.prompt_lock_path = self.dir / "prompt.lock.json"
        self.dataset_path = self.dir / "dataset.jsonl"
        self.items_path = self.dir / "items.jsonl"
        self.checkpoint_path = self.dir / "checkpoint.json"
        self.events_path = self.dir / "events.jsonl"
        self.cold_boot_path = self.dir / "cold_boot.json"
        self.flock_path = self.dir / "run.lock"
        self.cancel_path = self.dir / "cancel.request.json"
        self.cancel_ack_path = self.dir / "cancel.ack.json"
        self.run_id = self.dir.name

    # ── single-writer guard ─────────────────────────────────────────────────
    @contextmanager
    def acquire(self, *, blocking: bool = True) -> Iterator["RunStore"]:
        """Yield this store while holding its advisory exclusive writer lock.

        With ``blocking=False``, raise BlockingIOError if another writer holds
        the lock. Release it on context exit, including when the body raises.
        """
        with open(self.flock_path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            try:
                yield self
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def control(self) -> Iterator["RunStore"]:
        """Short control/reset guard, independent of a running provider call."""
        with open(self.dir / "cancel.lock", "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield self
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    # ── lock (immutable preflight manifest) ─────────────────────────────────
    def write_lock(self, payload: dict[str, Any]) -> Path:
        if self.lock_path.is_file():
            # hub#41: an existing lock must be readable — a corrupt lock is a
            # loud failure, never a silent no-op that keeps stale state.
            _read_json(self.lock_path, strict=True)
            return self.lock_path
        _atomic_write(self.lock_path, json.dumps(payload, indent=2, sort_keys=True, default=str))
        return self.lock_path

    def read_lock(self) -> dict[str, Any] | None:
        return _read_json(self.lock_path, strict=True)

    def verify_generation(self) -> dict[str, Any]:
        """Return the lock after validating its frozen artifacts and checkpoint.

        Raise RuntimeError for missing, corrupt, or mismatched run/spec locks,
        datasets, prompt snapshots, or checkpoint identities/states. File-access
        errors propagate. Frozen prompt text is checked without resolving current
        local stems. Legacy locks need no checkpoint generation ID.
        """
        lock = self.read_lock()
        if not isinstance(lock, dict) or not lock.get("spec_hash") or lock.get("run_id") != self.run_id:
            raise RuntimeError("locked generation has no valid run/spec lock")
        cp = _read_json(self.checkpoint_path, strict=True)
        if not self.dataset_path.is_file() or not self.prompt_lock_path.is_file() or not isinstance(cp, dict) or not cp:
            raise RuntimeError("locked generation is missing dataset, prompt lock, or checkpoint")
        expected_sha = (lock.get("dataset") or {}).get("sha256")
        if not expected_sha or self.dataset_sha256() != expected_sha:
            raise RuntimeError("dataset.jsonl changed since the lock (locked dataset sha256 mismatch)")
        prompt = self.read_prompt_lock()
        if not isinstance(prompt, dict) or prompt != lock.get("prompt"):
            raise RuntimeError("locked prompt artifacts differ")
        if lock.get("prompt_text_sha"):
            from mailroom_sandbox.job.preflight import _prompt_text_sha

            if _prompt_text_sha(prompt) != lock["prompt_text_sha"]:
                raise RuntimeError("locked resolved prompt sha256 mismatch")
        if (cp.get("spec_hash") != lock["spec_hash"] or cp.get("run_id") != self.run_id
                or cp.get("state") not in STATES
                or (lock.get("generation_id") and cp.get("generation_id") != lock["generation_id"])):
            raise RuntimeError("checkpoint belongs to another run/spec/generation or has invalid state")
        return lock

    def spec_hash(self) -> str | None:
        lock = self.read_lock()
        return lock.get("spec_hash") if lock else None

    def archive_generation(self) -> Path | None:
        """Archive the current lock/items/checkpoint/events (preflight --force).

        ``write_lock`` refuses to overwrite in place, so a forced re-lock must
        move the old generation aside first — otherwise new dataset bytes live
        under an old lock/checkpoint and resume silently replays wrong rows
        (DMR-049). Returns the archive dir, or None when there was nothing to
        archive.
        """
        if not any(
            path.is_file()
            for path in (self.lock_path, self.items_path, self.checkpoint_path)
        ):
            return None
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        # Two resets in one second must never overwrite an older archive.
        import uuid

        dest = self.dir / f"archive-{stamp}-{uuid.uuid4().hex[:8]}"
        dest.mkdir(parents=True, exist_ok=False)
        for path in (
            self.lock_path,
            self.prompt_lock_path,
            self.items_path,
            self.checkpoint_path,
            self.events_path,
            self.dataset_path,
            self.cold_boot_path,
            self.cancel_path,
            self.cancel_ack_path,
            self.dir / "experiment_log.jsonl",
        ):
            if path.is_file():
                path.rename(dest / path.name)
        return dest

    def write_prompt_lock(self, payload: dict[str, Any]) -> Path:
        _atomic_write(self.prompt_lock_path, json.dumps(payload, indent=2, sort_keys=True, default=str))
        return self.prompt_lock_path

    def read_prompt_lock(self) -> dict[str, Any] | None:
        return _read_json(self.prompt_lock_path, strict=True)

    # ── cold boot (engine probe measurement, SAND-018) ──────────────────────
    def write_cold_boot(self, payload: dict[str, Any]) -> Path:
        """Persist the live engine-probe cold-boot measurement.

        Written by ``preflight --live`` (the step immediately after a deploy),
        read back into the run's experiment-log record so a cold-boot number
        travels with the run instead of being an assumed 120 s constant.
        """
        _atomic_write(
            self.cold_boot_path,
            json.dumps(payload, indent=2, sort_keys=True, default=str),
        )
        return self.cold_boot_path

    def read_cold_boot(self) -> dict[str, Any] | None:
        return _read_json(self.cold_boot_path)

    def summary(self) -> dict[str, Any]:
        cp = self.read_checkpoint() or {}
        items = self.load_items()
        ok_count = sum(1 for i in items if i.get("ok"))
        return {
            "run_id": self.run_id,
            "state": cp.get("state"),
            "cursor": cp.get("cursor"),
            "total": cp.get("total"),
            "ok": ok_count,
            "errors": len(items) - ok_count,
            "updated_at": cp.get("updated_at"),
            "spec_hash": cp.get("spec_hash"),
            "last_error": cp.get("last_error"),
        }

    # ── dataset (prepared subset) ───────────────────────────────────────────
    def write_dataset(self, lines: list[dict[str, Any]]) -> Path:
        _atomic_write(self.dataset_path, "".join(json.dumps(r, default=str) + "\n" for r in lines))
        return self.dataset_path

    def dataset_rows(self) -> list[dict[str, Any]]:
        if not self.dataset_path.is_file():
            return []
        rows = []
        with self.dataset_path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def dataset_sha256(self) -> str | None:
        import hashlib

        if not self.dataset_path.is_file():
            return None
        return hashlib.sha256(self.dataset_path.read_bytes()).hexdigest()

    # ── items (progress source of truth) ────────────────────────────────────
    def load_items(self) -> list[dict[str, Any]]:
        truncate_torn_tail(self.items_path, self.events_path)
        if not self.items_path.is_file():
            return []
        rows = []
        for line in self.items_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def resume_cursor(self) -> int:
        """Recompute cursor from items; reconcile checkpoint if it drifted."""
        items = self.load_items()
        cursor = len(items)
        cp = self.read_checkpoint()
        stored = (cp or {}).get("cursor")
        if stored != cursor:
            self.write_checkpoint(
                state=(cp or {}).get("state", "running"),
                cursor=cursor,
                total=(cp or {}).get("total", 0),
                remote=(cp or {}).get("remote"),
                last_error=(cp or {}).get("last_error"),
                reconcile=(stored, cursor),
            )
        return cursor

    def append_item(self, record: dict[str, Any]) -> None:
        # Callers own acquire(); normalize the accepted crash tail before the
        # next append. Do not turn two valid JSON objects into one invalid line.
        """Append a JSONL result after repairing an unterminated tail.

        Preserve a parseable final record and separate it with a newline; discard
        an unparseable final fragment. The caller must hold ``acquire()``.
        Serialization and file-access errors propagate.
        """
        if self.items_path.is_file() and self.items_path.stat().st_size:
            with self.items_path.open("rb") as tail:
                tail.seek(-1, 2)
                terminated = tail.read(1) == b"\n"
            if not terminated:
                truncate_torn_tail(self.items_path, self.events_path)
                if self.items_path.stat().st_size:
                    with self.items_path.open("ab") as tail:
                        tail.write(b"\n")
        with open(self.items_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
            fh.flush()

    def load_item_rows(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (completed rows, expected/predicted reconstruction)."""
        return self.load_items()

    def request_cancel(self) -> dict[str, Any]:
        """Persist and return a cancellation token for the current generation.

        Use the short control lock so a running provider call need not finish
        before the request is written; the runner acknowledges it after draining.
        """
        import uuid

        with self.control():
            lock = self.read_lock() or {}
            request = {"token": uuid.uuid4().hex, "spec_hash": lock.get("spec_hash"),
                       "generation": lock.get("generation_id") or lock.get("created_at"), "requested_at": utc_now()}
            _atomic_write(self.cancel_path, json.dumps(request, sort_keys=True))
            self.append_event("cancel_requested", "info", token=request["token"])
            return request

    def pending_cancel(self) -> dict[str, Any] | None:
        """Return an unacknowledged request matching the current generation.

        Return None for absent, stale, or acknowledged requests. Corrupt control
        or lock JSON raises RuntimeError; file-access errors propagate.
        """
        request = _read_json(self.cancel_path, strict=True)
        if not request:
            return None
        lock = self.read_lock() or {}
        if (request.get("spec_hash"), request.get("generation")) != (
            lock.get("spec_hash"), lock.get("generation_id") or lock.get("created_at")
        ):
            return None
        ack = _read_json(self.cancel_ack_path, strict=True) or {}
        return request if request.get("token") != ack.get("token") else None

    def acknowledge_cancel(self, request: dict[str, Any]) -> None:
        # A newer request arriving during drain stays pending: acknowledge only
        # the token this runner observed, never unlink the control file.
        """Persist the observed request token without removing the request file.

        A newer request remains pending when an older token is acknowledged.
        """
        _atomic_write(self.cancel_ack_path, json.dumps(request, sort_keys=True))

    # ── checkpoint (atomic mirror) ──────────────────────────────────────────
    def write_checkpoint(
        self,
        *,
        state: str,
        cursor: int,
        total: int,
        remote: dict[str, Any] | None = None,
        last_error: dict[str, Any] | None = None,
        reconcile: tuple[int, int] | None = None,
    ) -> Path:
        """Atomically replace the progress mirror and return its path.

        Stamp the current run/spec/generation identity. ``cursor`` and ``total``
        are item counts; optional ``reconcile`` holds old and new cursor counts
        and adds a reconciliation event. Raise ValueError for an unknown state;
        lock-reading, count-conversion, and file-access errors propagate.
        """
        if state not in STATES:
            raise ValueError(f"state {state!r} not in {STATES}")
        cp = {
            "schema_version": 1,
            "run_id": self.run_id,
            "spec_hash": self.spec_hash(),
            "state": state,
            "cursor": int(cursor),
            "total": int(total),
            "updated_at": utc_now(),
            "remote": remote,
            "last_error": last_error,
        }
        generation = (self.read_lock() or {}).get("generation_id")
        if generation:
            cp["generation_id"] = generation
        _atomic_write(self.checkpoint_path, json.dumps(cp, indent=2, sort_keys=True, default=str))
        if reconcile:
            self.append_event("checkpoint_reconciled", "warn", stored=reconcile[0], recomputed=reconcile[1])
        return self.checkpoint_path

    def read_checkpoint(self) -> dict[str, Any] | None:
        return _read_json(self.checkpoint_path)

    # ── events ──────────────────────────────────────────────────────────────
    def append_event(self, event: str, level: str = "info", **detail: Any) -> None:
        with open(self.events_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": utc_now(), "event": event, "level": level, "detail": detail or None}) + "\n")
            fh.flush()

    def events(self) -> list[dict[str, Any]]:
        if not self.events_path.is_file():
            return []
        rows = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    # ── resume / drift ──────────────────────────────────────────────────────
    def verify_spec(self, expected_hash: str, *, store_dir: Path | None = None) -> tuple[bool, str | None]:
        cp = self.read_checkpoint()
        got = cp.get("spec_hash") if cp else None
        if got is not None and got != expected_hash:
            return False, f"spec drift: checkpoint {got} != expected {expected_hash}"
        return True, None

    def terminal(self) -> bool:
        cp = self.read_checkpoint()
        return bool(cp and cp.get("state") in TERMINAL_STATES)

    def state(self) -> str | None:
        cp = self.read_checkpoint()
        return cp.get("state") if cp else None


def list_runs(root: Path) -> list[dict[str, Any]]:
    out = []
    if not root.is_dir():
        return out
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        store = RunStore(child)
        cp = store.read_checkpoint()
        lock = store.read_lock()
        out.append(
            {
                "run_id": child.name,
                "state": (cp or {}).get("state"),
                "cursor": (cp or {}).get("cursor"),
                "total": (cp or {}).get("total"),
                "updated_at": (cp or {}).get("updated_at"),
                "task": (lock or {}).get("task"),
                "spec_hash": (lock or {}).get("spec_hash"),
            }
        )
    return out


def store_for(run_id: str, *, root: Path | None = None) -> RunStore:
    from mailroom_sandbox.job.spec import run_dir

    base = root or run_dir(run_id)
    return RunStore(base if isinstance(base, Path) else Path(base))
