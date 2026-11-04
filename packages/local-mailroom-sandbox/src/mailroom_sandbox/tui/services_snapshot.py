"""mailroom.services/v1 — the last `sandbox doctor` result, published for the job board.

Stdlib only (like ``beacon.py``). ``sandbox doctor --publish`` writes ``services.json`` next to
the beacon heartbeats; the board only *reads* it, so it never probes anything itself. A snapshot
older than ``STALE_S`` is flagged ``stale`` instead of being shown as current.
"""

from __future__ import annotations

import json
import math
import os
import socket
import time
from pathlib import Path
from typing import Any

from mailroom_sandbox.tui.beacon import beacon_root

SERVICES_VERSION = "mailroom.services/v1"
SERVICES_FILE = "services.json"
STALE_S = 900.0


def publish_services(
    services: list[dict[str, Any]],
    *,
    profile: str,
    live: bool,
    root: Path | str | None = None,
) -> Path:
    """Atomically write the snapshot and return its path."""
    base = Path(root) if root is not None else beacon_root()
    base.mkdir(parents=True, exist_ok=True)
    path = base / SERVICES_FILE
    tmp = base / f".services.{os.getpid()}.tmp"
    payload = {
        "schema": SERVICES_VERSION,
        "generated_at": time.time(),
        "host": socket.gethostname(),
        "profile": profile,
        "live": bool(live),
        "services": services,
    }
    tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_services(root: Path | str | None = None, *, stale_s: float = STALE_S) -> dict[str, Any] | None:
    """The published snapshot with ``age_s`` / ``stale`` added, or None if absent or unreadable."""
    base = Path(root) if root is not None else beacon_root()
    try:
        data = json.loads((base / SERVICES_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != SERVICES_VERSION or not isinstance(data.get("services"), list):
        return None
    if any(not isinstance(row, dict) or any(not isinstance(row.get(key, ""), str)
           for key in ("name", "state", "detail", "hint")) for row in data["services"]):
        return None
    try:
        generated_at = float(data.get("generated_at", 0))
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(generated_at):
        return None
    age = max(0.0, time.time() - generated_at)
    data["age_s"] = round(age, 1)
    data["stale"] = age > stale_s
    return data
