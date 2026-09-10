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


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
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


class RunStore:
    def __init__(self, run_dir: Path):
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.dir / "spec.lock.json"
        self.prompt_lock_path = self.dir / "prompt.lock.json"
        self.dataset_path = self.dir / "dataset.jsonl"
        self.items_path = self.dir / "items.jsonl"
        self.checkpoint_path = self.dir / "checkpoint.json"
        self.events_path = self.dir / "events.jsonl"
        self.flock_path = self.dir / "run.lock"
        self.run_id = self.dir.name

    # ── single-writer guard ─────────────────────────────────────────────────
    @contextmanager
    def acquire(self) -> Iterator["RunStore"]:
        with open(self.flock_path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield self
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    # ── lock (immutable preflight manifest) ─────────────────────────────────
    def write_lock(self, payload: dict[str, Any]) -> Path:
        if self.lock_path.is_file():
            return self.lock_path
        _atomic_write(self.lock_path, json.dumps(payload, indent=2, sort_keys=True, default=str))
        return self.lock_path

    def read_lock(self) -> dict[str, Any] | None:
        return _read_json(self.lock_path)

    def spec_hash(self) -> str | None:
        lock = self.read_lock()
        return lock.get("spec_hash") if lock else None

    def write_prompt_lock(self, payload: dict[str, Any]) -> Path:
        _atomic_write(self.prompt_lock_path, json.dumps(payload, indent=2, sort_keys=True, default=str))
        return self.prompt_lock_path

    def read_prompt_lock(self) -> dict[str, Any] | None:
        return _read_json(self.prompt_lock_path)

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
        for line in self.dataset_path.read_text(encoding="utf-8").splitlines():
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
        with open(self.items_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
            fh.flush()

    def load_item_rows(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (completed rows, expected/predicted reconstruction)."""
        return self.load_items()

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
