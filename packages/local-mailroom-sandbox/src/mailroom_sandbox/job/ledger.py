"""Run ledger: who signed which paid run, when, and how it ended.

One Markdown table, tracked in git at ``reports/run-ledger.md`` (override with
``SANDBOX_RUN_LEDGER``). A row is appended each time ``sandbox run start`` or
``sandbox run resume`` passes the spend gate with a signed initials receipt, so
every paid run has a preflight confirmation on record. The last cell is the
result: blank while the run is open, then ``✓`` when it finishes (state
``done``) or ``✗`` when it fails. Only that cell is ever rewritten.

The table is the machine format too: fixed columns, one row per line, no
cell holds a ``|``. :func:`rows` parses it back.

    | signed_utc | initials | action | run_id | config | spec | rows | api_cap_usd | result |
"""

from __future__ import annotations

import contextlib
import fcntl
import logging
import os
import time
from pathlib import Path
from typing import Any, Iterator

from mailroom_sandbox.paths import repo_root

_log = logging.getLogger(__name__)

COLUMNS = ("signed_utc", "initials", "action", "run_id", "config", "spec", "rows", "api_cap_usd", "result")
OK, FAILED = "✓", "✗"
_HEADER = (
    "# Run ledger\n\n"
    "Every paid run that passed the spend gate: who signed it (initials), when (UTC), the run and its\n"
    "locked spec, and how it ended. Appended by `sandbox run start` / `sandbox run resume`; the result\n"
    f"cell is filled when the run reaches a terminal state ({OK} done, {FAILED} failed; blank = still open).\n"
    "Do not edit rows by hand. Parse with `mailroom_sandbox.job.ledger.rows()`.\n\n"
    "| " + " | ".join(COLUMNS) + " |\n"
    "|" + "|".join("---" for _ in COLUMNS) + "|\n"
)


def ledger_path() -> Path:
    override = os.environ.get("SANDBOX_RUN_LEDGER", "").strip()
    return Path(override) if override else repo_root() / "reports" / "run-ledger.md"


@contextlib.contextmanager
def _locked(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_name(path.name + ".lock"), "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return " ".join(text.replace("|", "/").split()) or "-"


def _line(values: dict[str, Any]) -> str:
    return "| " + " | ".join(_cell(values.get(c)) if c != "result" else (values.get(c) or " ") for c in COLUMNS) + " |"


def _split(line: str) -> list[str] | None:
    if not line.startswith("| ") or line.startswith("| signed_utc "):
        return None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells if len(cells) == len(COLUMNS) else None


def rows(path: Path | None = None) -> list[dict[str, str]]:
    """Every ledger row as a dict of the column names (``result`` is ``""`` while open)."""
    path = path or ledger_path()
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = _split(line)
        if cells is not None:
            out.append({c: ("" if v == "-" and c == "result" else v) for c, v in zip(COLUMNS, cells)})
    return out


def record_signed(lock: dict[str, Any], *, initials: str, action: str, config: str | None = None,
                  rows_total: int | None = None, path: Path | None = None) -> dict[str, str]:
    """Append the open row for a run that just passed the spend gate."""
    path = path or ledger_path()
    job = lock.get("job") or {}
    values = {
        "signed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "initials": initials,
        "action": action,
        "run_id": lock.get("run_id"),
        "config": _relative(config),
        "spec": str(lock.get("spec_hash") or "")[:12],
        "rows": rows_total,
        "api_cap_usd": job.get("api_cost_cap_usd"),
        "result": "",
    }
    with _locked(path):
        text = path.read_text(encoding="utf-8") if path.exists() else _HEADER
        if not text.endswith("\n"):
            text += "\n"
        _write(path, text + _line(values) + "\n")
    return {k: _cell(v) if k != "result" else "" for k, v in values.items()}


def mark_result(run_id: str, spec_hash: str | None, *, ok: bool, path: Path | None = None) -> int:
    """Close every open row of this run and spec with ✓ or ✗; return how many were closed."""
    path = path or ledger_path()
    if not path.exists():
        return 0
    spec = str(spec_hash or "")[:12]
    closed = 0
    with _locked(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            cells = _split(line)
            if cells is None:
                continue
            row = dict(zip(COLUMNS, cells))
            if row["run_id"] == run_id and (not spec or row["spec"] == spec) and row["result"] in ("", "-"):
                row["result"] = OK if ok else FAILED
                lines[i] = _line(row)
                closed += 1
        if closed:
            _write(path, "\n".join(lines) + "\n")
    return closed


def close_run(store: Any) -> int:
    """Close a terminal run's open ledger rows; a ledger write error is logged, never raised.

    The ledger is bookkeeping: an unwritable ledger (read-only checkout, a bad
    ``SANDBOX_RUN_LEDGER`` directory) must not fail the checkpoint write or the remote sync
    that calls this. Returns the number of rows closed (0 on error or when not terminal).
    """
    if not store.terminal():
        return 0
    try:
        return mark_result(store.run_id, store.spec_hash(), ok=store.state() == "done")
    except OSError as exc:
        _log.warning("run ledger not updated for %s: %s", store.run_id, exc)
        return 0


def _relative(config: str | None) -> str | None:
    if not config:
        return None
    try:
        return str(Path(config).resolve().relative_to(repo_root().resolve()))
    except ValueError:
        return Path(config).name


def _write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
