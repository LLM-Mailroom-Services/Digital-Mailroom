"""DMR-086 regression: storage.db must be safe under concurrent first use.

* ``ensure_schema()`` claims to be thread-safe; concurrent first calls used to
  race check-then-create_all, one hit ``table ... already exists``, the error
  was swallowed and the call returned False.
* ``get_engine()`` used to keep ONE async engine shared across event loops, so
  threads running their own loops hit ``bound to a different event loop``.
"""

import asyncio
import threading

from sqlalchemy import text

from storage import db

THREADS = 16


class _SpyLogger:
    def __init__(self):
        self.exceptions = []

    def exception(self, event, *a, **kw):
        self.exceptions.append(event)

    def __getattr__(self, name):  # info / warning / debug ...
        return lambda *a, **kw: None


def _point_at_fresh_db(monkeypatch, tmp_path, name="race"):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / name).mkdir()
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path / name))
    monkeypatch.setattr(db, "_schema_checked_url", None)


def test_ensure_schema_concurrent_first_calls_all_succeed(monkeypatch, tmp_path):
    _point_at_fresh_db(monkeypatch, tmp_path)
    spy = _SpyLogger()
    monkeypatch.setattr(db, "logger", spy)
    barrier = threading.Barrier(THREADS)
    results: list = [None] * THREADS
    errors: list = []

    def worker(i):
        try:
            barrier.wait(timeout=30)
            results[i] = db.ensure_schema()
        except BaseException as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not errors
    assert results == [True] * THREADS
    assert spy.exceptions == []


def test_get_engine_usable_from_two_event_loops(monkeypatch, tmp_path):
    _point_at_fresh_db(monkeypatch, tmp_path, "loops")
    assert db.ensure_schema() is True
    barrier = threading.Barrier(2)
    errors: list = []
    engines: list = []

    async def use_engine():
        engines.append(db.get_engine())
        for _ in range(20):
            async with db.async_session() as session:
                await session.execute(text("SELECT 1"))
            await asyncio.sleep(0)

    def worker():
        try:
            barrier.wait(timeout=30)
            asyncio.run(use_engine())
        except BaseException as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not errors
    assert len(engines) == 2
    assert engines[0] is not engines[1]  # one engine per event loop
