"""Crash-safe run-store tests (DMR-027)."""

from __future__ import annotations

import json

import pytest

from mailroom_sandbox.job.checkpoint import RunStore, truncate_torn_tail


@pytest.fixture
def store(tmp_path) -> RunStore:
    return RunStore(tmp_path / "run-1")


def test_lock_immutable(store):
    store.write_lock({"spec_hash": "abc", "task": "sorter"})
    store.write_lock({"spec_hash": "zzz", "task": "other"})  # no-op
    assert store.read_lock()["spec_hash"] == "abc"


def test_items_append_and_cursor(store):
    store.append_item({"index": 0, "item_id": "a", "predicted": "x", "ok": True})
    store.append_item({"index": 1, "item_id": "b", "predicted": "y", "ok": False})
    assert len(store.load_items()) == 2
    assert store.resume_cursor() == 2


def test_checkpoint_state_and_atomic(store):
    store.write_lock({"spec_hash": "abc", "task": "sorter"})
    store.write_checkpoint(state="running", cursor=1, total=5)
    cp = store.read_checkpoint()
    assert cp["state"] == "running" and cp["cursor"] == 1 and cp["spec_hash"] == "abc"
    with pytest.raises(ValueError):
        store.write_checkpoint(state="bogus", cursor=0, total=0)


def test_parseable_fragment_kept(store):
    store.append_item({"index": 0, "item_id": "a", "ok": True})
    with open(store.items_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"index": 1, "item_id": "b", "ok": True}))  # no trailing newline
    assert len(store.load_items()) == 2


def test_unparseable_fragment_truncated(store, tmp_path):
    store.append_item({"index": 0, "item_id": "a", "ok": True})
    with open(store.items_path, "a", encoding="utf-8") as fh:
        fh.write('{"index": 1, "item_id"')  # torn
    rows = store.load_items()
    assert len(rows) == 1
    assert rows[0]["index"] == 0
    events = store.events()
    assert any(e["event"] == "items_truncated" for e in events)


def test_resume_reconciles_cursor(store):
    store.write_lock({"spec_hash": "s1"})
    store.append_item({"index": 0, "item_id": "a", "ok": True})
    store.write_checkpoint(state="running", cursor=0, total=2)  # stale (0 != 1)
    assert store.resume_cursor() == 1
    events = store.events()
    assert any(e["event"] == "checkpoint_reconciled" for e in events)


def test_terminal_and_summary(store):
    store.append_item({"index": 0, "item_id": "a", "ok": True})
    store.write_checkpoint(state="done", cursor=1, total=1)
    assert store.terminal()
    assert store.summary()["state"] == "done"