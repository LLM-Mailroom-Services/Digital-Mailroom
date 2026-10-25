"""mailroom.beacon/v1 — live progress heartbeats for long mailroom jobs.

Single file, stdlib only, safe to vendor into any mailroom-family package (copy it
verbatim; keep the ``BEACON_VERSION`` line). A job writes::

    from beacon import Beacon            # or mailroom_sandbox.tui.beacon
    with Beacon("sand032-s6", package="local-mailroom-sandbox", title="sorter n=1000") as b:
        for i, doc in enumerate(docs):
            ...
            b.update(phase="SORTING", done=i + 1, total=len(docs), ok=ok, errors=err)
            b.log(f"{doc.id} ok")

and ``sandbox board`` (browser + terminal TUI) shows every job under the beacon root:
``$MAILROOM_BEACON_DIR`` or ``~/.mailroom/jobs``. Files: ``<job_id>.json`` (atomic
heartbeat) and ``<job_id>.log`` (appended lines). A beacon never raises into the job.
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
import traceback
from pathlib import Path
from typing import Any

BEACON_VERSION = "mailroom.beacon/v1"
TERMINAL_STATES = ("done", "failed")
_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")


def beacon_root() -> Path:
    env = os.environ.get("MAILROOM_BEACON_DIR", "").strip()
    return Path(env).expanduser() if env else Path.home() / ".mailroom" / "jobs"


def safe_job_id(job_id: str) -> str:
    cleaned = _SAFE_ID.sub("-", str(job_id)).strip(".-")
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    return cleaned or "job"


class Beacon:
    """Heartbeat writer for one job. Every method is best-effort and never raises."""

    def __init__(
        self,
        job_id: str,
        *,
        package: str,
        title: str = "",
        root: Path | str | None = None,
        total: int | None = None,
        resume: bool = False,
        pid: int | None | bool = True,
    ) -> None:
        """``resume`` continues an existing heartbeat (short-lived CLI writers);
        ``pid=None`` opts out of dead-process stall detection for such writers."""
        self.job_id = safe_job_id(job_id)
        self.root = Path(root) if root is not None else beacon_root()
        now = time.time()
        self._state: dict[str, Any] = {
            "schema": BEACON_VERSION,
            "job_id": self.job_id,
            "package": package,
            "title": title or self.job_id,
            "phase": "STARTING",
            "state": "running",
            "done": 0,
            "total": total,
            "ok": 0,
            "errors": 0,
            "metrics": {},
            "started_at": now,
            "updated_at": now,
            "finished_at": None,
            "pid": os.getpid() if pid is True else pid,
            "host": socket.gethostname(),
        }
        if resume:
            try:
                prior = json.loads((self.root / f"{self.job_id}.json").read_text(encoding="utf-8"))
                if isinstance(prior, dict) and prior.get("schema") == BEACON_VERSION:
                    prior.update({"pid": self._state["pid"], "host": self._state["host"]})
                    if title:
                        prior["title"] = title
                    self._state = prior
            except Exception:  # noqa: BLE001
                pass
        self._write()

    # ── writer API ────────────────────────────────────────────────────────────
    def update(self, *, metrics: dict[str, Any] | None = None, **fields: Any) -> None:
        for key, value in fields.items():
            if value is not None and key in self._state and key not in ("schema", "job_id", "pid", "host"):
                self._state[key] = value
        if metrics:
            self._state["metrics"].update(metrics)
        self._state["updated_at"] = time.time()
        self._write()

    def log(self, line: str) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with (self.root / f"{self.job_id}.log").open("a", encoding="utf-8") as fh:
                fh.write(str(line).rstrip("\n") + "\n")
        except Exception:  # noqa: BLE001 — a beacon never breaks the job
            pass

    def finish(self, state: str = "done", **fields: Any) -> None:
        state = state if state in TERMINAL_STATES else "done"
        self._state["finished_at"] = time.time()
        fields.setdefault("phase", state.upper())
        self.update(state=state, **fields)

    # ── context manager: exception → failed (re-raised), else done ───────────
    def __enter__(self) -> "Beacon":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            if self._state["state"] not in TERMINAL_STATES:
                self.finish("done")
        else:
            msg = "".join(traceback.format_exception_only(exc_type, exc)).strip()
            self.finish("failed", metrics={"error": msg[:500]})
        return False

    # ── internals ─────────────────────────────────────────────────────────────
    def _write(self) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            path = self.root / f"{self.job_id}.json"
            tmp = self.root / f".{self.job_id}.{os.getpid()}.tmp"
            tmp.write_text(json.dumps(self._state, default=str), encoding="utf-8")
            os.replace(tmp, path)
        except Exception:  # noqa: BLE001 — a beacon never breaks the job
            pass
