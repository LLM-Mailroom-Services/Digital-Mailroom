"""Tolerant numeric env knobs.

``float(os.environ.get(...))`` at import time turned a blank ``.env`` line
(``MAILROOM_TRACE_LIMIT=``) or ``200.0`` into a ValueError that stopped the
server from starting. These helpers log the bad value and keep the default.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Optional

log = logging.getLogger("mailroom.env")


def env_float(name: str, default: float, *, minimum: Optional[float] = None) -> float:
    raw = (os.environ.get(name) or "").strip()
    value = default
    if raw:
        try:
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError(raw)
        except ValueError:
            log.warning("%s=%r is not a number — using %s", name, raw, default)
            value = default
    if minimum is not None and value < minimum:
        log.warning("%s=%s is below the minimum %s — clamping", name, value, minimum)
        value = minimum
    return value


def env_int(name: str, default: int, *, minimum: Optional[int] = None) -> int:
    value = env_float(name, float(default))
    out = int(value)
    if minimum is not None and out < minimum:
        log.warning("%s=%s is below the minimum %s — clamping", name, out, minimum)
        out = minimum
    return out
