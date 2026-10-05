"""Filesystem observer — bin moves become structured operator events.

Prefer the in-process watcher started from the visualizer lifespan
(``MAILROOM_OBSERVER=1``). A standalone ``mailroom-observer`` process POSTs
events to ``{MAILROOM_API_URL}/v1/ops/events`` so the API owns the WS bus.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .db import (
    archive_dir,
    base_dir,
    connect,
    ensure_bins,
    migrate,
    pipeline_dir,
    upsert_archive_entry,
)

log = logging.getLogger("mailroom.operator.observer")

try:
    from watchdog.events import FileSystemEventHandler
except ImportError:  # pragma: no cover - optional extra
    class FileSystemEventHandler:  # type: ignore[no-redef]
        pass


_TEMP_SUFFIXES = (".tmp", ".part", ".partial", ".crdownload", ".swp")


def _is_temp_name(path: Path) -> bool:
    name = path.name
    return name.startswith((".", "~")) or name.endswith(_TEMP_SUFFIXES)


def _wait_settled(path: Path, *, checks: int = 10, interval: float = 0.2) -> bool:
    """True once the file size is stable across two reads."""
    last = -1
    for _ in range(checks):
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if size == last:
            return True
        last = size
        time.sleep(interval)
    return False


class PipelineEventHandler(FileSystemEventHandler):
    """Translate inbox/archive filesystem events into operator payloads."""

    def __init__(self, event_callback: Callable[[dict], None]):
        self.callback = event_callback
        self.pipeline_root = pipeline_dir()
        self.archive_root = archive_dir()

    def _get_bin_name(self, path: Path) -> Optional[str]:
        try:
            rel = path.resolve().relative_to(self.pipeline_root.resolve())
            return rel.parts[0] if rel.parts else None
        except ValueError:
            try:
                path.resolve().relative_to(self.archive_root.resolve())
                return "archive"
            except ValueError:
                return None

    def _get_doc_info(self, path: Path) -> Optional[dict]:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='documents'"
            ).fetchone()
            if not row:
                return None
            doc_id = path.stem
            found = conn.execute(
                "SELECT doc_id, matter_id, doc_type, confidence, status "
                "FROM documents WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
            return dict(found) if found else None
        except Exception:
            return None
        finally:
            conn.close()

    def _index_if_archive(self, path: Path, bin_name: Optional[str]) -> None:
        if bin_name != "archive" or not path.is_file() or _is_temp_name(path):
            return
        # on_created fires when the file is opened for writing: wait for the
        # size to settle so the stored checksum matches the finished file
        # (a half-written checksum later made /verify report tampering).
        if not _wait_settled(path):
            log.warning("archive file %s still changing — indexing skipped", path)
            return
        data = path.read_bytes()
        upsert_archive_entry(
            doc_id=path.stem,
            matter_id="unknown",
            doc_type="unknown",
            archive_path=str(path.resolve()),
            file_size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
        )

    def on_moved(self, event: Any) -> None:
        src = getattr(event, "src_path", None)
        dest = getattr(event, "dest_path", None)
        if not src or not dest:
            return
        if getattr(event, "is_directory", False):
            return
        src_bin = self._get_bin_name(Path(src))
        dest_bin = self._get_bin_name(Path(dest))
        dest_path = Path(dest)
        if src_bin and dest_bin and src_bin == dest_bin:
            # Same-bin rename = atomic write (tmp -> final) landing in the
            # archive: index the final name, but it is not a stage change.
            self._index_if_archive(dest_path, dest_bin)
            return
        if not (src_bin and dest_bin):
            return
        self._index_if_archive(dest_path, dest_bin)
        self.callback(
            {
                "type": "stage_change",
                "doc_id": dest_path.stem,
                "from_stage": src_bin,
                "to_stage": dest_bin,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "document": self._get_doc_info(dest_path),
            }
        )

    def on_created(self, event: Any) -> None:
        src = getattr(event, "src_path", None)
        if not src or getattr(event, "is_directory", False):
            return
        path = Path(src)
        if _is_temp_name(path):
            return  # partial/atomic-write temp file; the rename announces it
        bin_name = self._get_bin_name(path)
        if bin_name == "inbox":
            self.callback(
                {
                    "type": "new_document",
                    "doc_id": path.stem,
                    "stage": "inbox",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "document": self._get_doc_info(path),
                }
            )
        elif bin_name == "archive":
            self._index_if_archive(path, bin_name)
            self.callback(
                {
                    "type": "archived",
                    "doc_id": path.stem,
                    "stage": "archive",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "document": self._get_doc_info(path),
                }
            )


class Watcher:
    def __init__(self, observer: Any):
        self._observer = observer

    def stop(self) -> None:
        try:
            self._observer.stop()
            self._observer.join(timeout=5)
        except Exception as exc:
            log.warning("observer stop failed: %s", exc)


class AsyncEventBridge:
    """Watchdog callbacks are sync; publish on the API event loop."""

    def __init__(self, loop: asyncio.AbstractEventLoop, emit: Optional[Callable] = None):
        self.loop = loop
        self._emit = emit

    def emit(self, event: dict) -> None:
        future = asyncio.run_coroutine_threadsafe(self._publish(event), self.loop)
        # Errors inside _publish vanished in the unobserved future.
        future.add_done_callback(_log_future_error)

    async def _publish(self, event: dict) -> None:
        if self._emit is not None:
            await self._emit(event)
            return
        from .websocket import publish_event, publish_matter_event

        await publish_event(str(event.get("type") or "event"), event)
        document = event.get("document") if isinstance(event.get("document"), dict) else {}
        matter_id = document.get("matter_id")
        if matter_id:
            await publish_matter_event(str(matter_id), str(event.get("type") or "event"), event)


def _log_future_error(future: Any) -> None:
    try:
        exc = future.exception()
    except Exception as cancel:  # cancelled on shutdown
        log.debug("observer publish cancelled: %s", cancel)
        return
    if exc is not None:
        log.warning("observer publish failed: %s", exc)


def observer_enabled() -> bool:
    raw = os.environ.get("MAILROOM_OBSERVER", "0").strip().lower()
    return raw in ("1", "true", "on", "yes")


def start_observer(
    loop: Optional[asyncio.AbstractEventLoop] = None,
    emit: Optional[Callable] = None,
) -> Optional[Watcher]:
    try:
        from watchdog.observers import Observer
    except ImportError:
        log.warning("watchdog not installed — mailroom-observer disabled (pip install -e '.[operator]')")
        return None
    ensure_bins()
    migrate()
    loop = loop or asyncio.get_event_loop()
    bridge = AsyncEventBridge(loop, emit=emit)
    handler = PipelineEventHandler(bridge.emit)
    observer = Observer()
    observer.schedule(handler, str(pipeline_dir()), recursive=True)
    observer.schedule(handler, str(archive_dir()), recursive=True)
    observer.start()
    log.info("watching %s and %s", pipeline_dir(), archive_dir())
    return Watcher(observer)


def _post_event(event: dict) -> None:
    base = (
        os.environ.get("MAILROOM_API_URL")
        or os.environ.get("MAILROOM_OPERATOR_INGEST_URL")
        or "http://127.0.0.1:8001"
    ).rstrip("/")
    token = (
        os.environ.get("MAILROOM_OPERATOR_INGEST_TOKEN")
        or os.environ.get("MAILROOM_OPERATOR_JWT")
        or ""
    ).strip()
    url = f"{base}/v1/ops/events"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url, data=json.dumps(event).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        hint = " (set MAILROOM_OPERATOR_INGEST_TOKEN on both sides)" if exc.code in (401, 403) else ""
        log.warning("observer ingest rejected: HTTP %s%s", exc.code, hint)
    except (urllib.error.URLError, OSError) as exc:
        log.warning("observer ingest failed: %s", exc)


async def _standalone() -> None:
    loop = asyncio.get_running_loop()

    async def emit(event: dict) -> None:
        await loop.run_in_executor(None, _post_event, event)

    watcher = start_observer(loop=loop, emit=emit)
    if watcher is None:
        return
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        watcher.stop()


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    ensure_bins()
    migrate()
    log.info("operator observer starting under %s", base_dir())
    try:
        asyncio.run(_standalone())
    except KeyboardInterrupt:
        log.info("observer stopped")


if __name__ == "__main__":
    run()
