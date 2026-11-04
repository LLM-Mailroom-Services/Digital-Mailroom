"""Opt-in periodic doctor snapshots for the board; offline unless explicitly requested."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

from mailroom_sandbox.services._cli import warn
from mailroom_sandbox.services.doctor import run_doctor
from mailroom_sandbox.tui.services_snapshot import publish_services


@contextmanager
def periodic_services(profile: str, *, interval: float = 0, live: bool = False,
                      root: Path | None = None) -> Iterator[None]:
    """Refresh once before rendering, then periodically until the board closes."""
    if not interval:
        yield
        return
    from mailroom_sandbox.runtime import load_env_file

    load_env_file()
    stop = threading.Event()

    def refresh() -> None:
        rows = run_doctor(profile, live=live)
        if not stop.is_set():
            publish_services([row.as_dict() for row in rows], profile=profile, live=live, root=root)

    if live and profile == "modal-vllm":
        warn("periodic --live probes can cold-start a billed Modal GPU container")
    try:
        refresh()
    except OSError as exc:
        # Publishing is optional for the board: a read-only/missing --root must
        # not prevent it from starting.
        warn(f"could not publish service snapshot: {exc}")

    def loop() -> None:
        while not stop.wait(interval):
            try:
                refresh()
            except OSError as exc:
                warn(f"could not publish service snapshot: {exc}")

    thread = threading.Thread(target=loop, name="services-doctor", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1)
