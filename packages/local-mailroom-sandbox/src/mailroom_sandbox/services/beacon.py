"""Publish a service command as a ``mailroom.beacon/v1`` job so the board shows it.

``with service_job("modal-deploy") as job:`` writes ``svc-modal-deploy.json`` (running, then done
or failed — an exception inside marks it failed and still propagates). ``job.log(line)`` mirrors
tool output into the board's log tail. Beacons never raise into the command (see ``tui/beacon.py``).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from mailroom_sandbox.tui.beacon import Beacon

PACKAGE = "local-mailroom-sandbox"


@contextmanager
def service_job(name: str, *, title: str = "", root: Path | str | None = None) -> Iterator[Beacon]:
    beacon = Beacon(f"svc-{name}", package=PACKAGE, title=title or name, root=root)
    beacon.update(phase="RUNNING")
    with beacon:
        yield beacon
