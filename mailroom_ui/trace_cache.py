"""Disk snapshot of Langfuse-derived runs (never fabricated).

Layout matches ``scripts/export_snapshot.py``:

    <dir>/traces.json
    <dir>/runs/<id>.json
    <dir>/metrics.json

Served when Langfuse is slow or down *and* a snapshot already exists.
Empty cache + Langfuse down stays MAILROOM CLOSED.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("mailroom.trace_cache")

DEFAULT_CACHE_DIR = "/tmp/mailroom-trace-cache"
CACHE_SOURCE = "langfuse-cache"


def _project_key() -> str:
    """Stable, non-secret tag for the configured source project.

    The default cache dir is shared by every process on the box; without a
    per-project subdirectory, switching Langfuse keys/hosts served the
    previous project's runs from disk. Only a hash of the PUBLIC key + host
    (never the secret) is used.
    """
    import hashlib

    host = (os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL") or "").strip()
    public = (os.environ.get("LANGFUSE_PUBLIC_KEY") or "").strip()
    phoenix = "|".join((os.environ.get(k) or "").strip() for k in ("PHOENIX_ENDPOINT", "MAILROOM_PHOENIX_PROJECT"))
    source = (os.environ.get("MAILROOM_SOURCE") or "langfuse").strip().lower()
    digest = hashlib.sha256(f"{source}|{host}|{public}|{phoenix}".encode("utf-8")).hexdigest()
    return digest[:12]


def cache_dir() -> Path:
    raw = (os.environ.get("MAILROOM_TRACE_CACHE_DIR") or "").strip()
    if raw:
        return Path(raw)  # explicit dir: the operator owns its scoping
    return Path(DEFAULT_CACHE_DIR) / _project_key()


def safe_id(trace_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(trace_id))


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".mailroom-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, default=_json_default)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("trace cache unreadable %s: %s", path, exc)
        return None
    return data if isinstance(data, dict) else None


def persist_floor(runs: list[dict[str, Any]], *, source: str = "langfuse") -> None:
    """Write light floor rows. Does nothing with an empty list (keep last good)."""
    if not runs:
        return
    payload = {
        "count": len(runs),
        "source": source,
        "cache_source": CACHE_SOURCE,
        "cached_at": _utcnow(),
        "runs": runs,
    }
    try:
        _write_json(cache_dir() / "traces.json", payload)
    except OSError as exc:
        log.warning("trace cache write failed: %s", exc)


def persist_run(trace_id: str, detail: dict[str, Any]) -> None:
    if not trace_id or not detail:
        return
    body = dict(detail)
    body.setdefault("cached_at", _utcnow())
    try:
        _write_json(cache_dir() / "runs" / f"{safe_id(trace_id)}.json", body)
    except OSError as exc:
        log.warning("run cache write failed: %s", exc)


def persist_metrics(metrics: dict[str, Any]) -> None:
    if not metrics:
        return
    body = dict(metrics)
    body.setdefault("cached_at", _utcnow())
    try:
        _write_json(cache_dir() / "metrics.json", body)
    except OSError as exc:
        log.warning("metrics cache write failed: %s", exc)


def load_traces() -> Optional[dict[str, Any]]:
    data = _read_json(cache_dir() / "traces.json")
    if not data or not isinstance(data.get("runs"), list):
        return None
    return data


def load_run(trace_id: str) -> Optional[dict[str, Any]]:
    if not trace_id:
        return None
    return _read_json(cache_dir() / "runs" / f"{safe_id(trace_id)}.json")


def load_metrics() -> Optional[dict[str, Any]]:
    return _read_json(cache_dir() / "metrics.json")


def snapshot_bundle() -> dict[str, Any]:
    traces = load_traces() or {"count": 0, "runs": [], "cached_at": None}
    details: dict[str, Any] = {}
    runs_dir = cache_dir() / "runs"
    if runs_dir.is_dir():
        for path in runs_dir.glob("*.json"):
            row = _read_json(path)
            if row and row.get("trace_id"):
                details[str(row["trace_id"])] = row
    return {
        "source": CACHE_SOURCE,
        "cached_at": traces.get("cached_at"),
        "traces": traces,
        "runs": details,
        "metrics": load_metrics(),
    }


def cache_status() -> dict[str, Any]:
    traces = load_traces()
    count = len((traces or {}).get("runs") or []) if traces else 0
    return {
        "dir": str(cache_dir()),
        "cached_at": (traces or {}).get("cached_at"),
        "cached_trace_count": count if traces else 0,
        "has_snapshot": bool(traces),
    }
