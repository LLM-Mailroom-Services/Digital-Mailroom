"""Modal remote job tests (DMR-027) — modal SDK stubbed."""

from __future__ import annotations

import types
from unittest import mock

import mailroom_sandbox.job.remote as remote
from mailroom_sandbox.job.checkpoint import RunStore


class _Call:
    def __init__(self, status_name):
        self.object_id = "call-abc"
        self.status_name = status_name
        self.canceled = False

    def get_call_graph(self):
        return [types.SimpleNamespace(status=types.SimpleNamespace(name=self.status_name))]

    def cancel(self, terminate_containers=False):
        self.canceled = True


def _stub_modal(monkeypatch, *, live_status="PENDING"):
    calls = {"live": _Call(live_status), "dead": _Call("SUCCESS")}

    modal_stub = types.SimpleNamespace(
        Function=MockFunction(calls),
        FunctionCall=MockFunctionCall(calls),
        Dict=MockDict(),
    )
    monkeypatch.setattr(remote, "_modal", lambda: modal_stub)
    monkeypatch.setattr(remote, "upload_run_dir", lambda d: (0, ""))


class MockFunction:
    def __init__(self, calls):
        self.calls = calls

    def from_name(self, app, fn):
        return self

    def spawn(self, payload=None):
        return self.calls["live"]


class MockFunctionCall:
    def __init__(self, calls):
        self.calls = calls

    def from_id(self, call_id):
        return self.calls["live"]


class MockDict:
    def __init__(self):
        self.store = {}

    def from_name(self, name, create_if_missing=False):
        return self

    def get(self, key, default=None):
        return self.store.get(key, default)


def _store(tmp_path) -> RunStore:
    store = RunStore(tmp_path / "run-r")
    store.write_lock({"spec_hash": "s1"})
    store.write_dataset([])
    store.write_checkpoint(state="prepared", cursor=0, total=0, remote=None)
    return store


def test_fire_persists_call_id(tmp_path, monkeypatch):
    _stub_modal(monkeypatch)
    store = _store(tmp_path)
    res = remote.fire(store)
    assert res["call_id"] == "call-abc"
    cp = store.read_checkpoint()
    assert cp["remote"]["call_id"] == "call-abc"
    assert any(e["event"] == "fired" for e in store.events())


def test_is_alive_reflects_input_state(tmp_path, monkeypatch):
    _stub_modal(monkeypatch, live_status="PENDING")
    store = _store(tmp_path)
    remote.fire(store)
    assert remote.is_alive(store)
    _stub_modal(monkeypatch, live_status="SUCCESS")
    assert not remote.is_alive(store)


def test_ensure_running_reattaches_live(tmp_path, monkeypatch):
    _stub_modal(monkeypatch, live_status="PENDING")
    store = _store(tmp_path)
    remote.fire(store)
    action = remote.ensure_running(store)
    assert action["action"] == "attached"


def test_cancel_calls_function_call(tmp_path, monkeypatch):
    _stub_modal(monkeypatch)
    store = _store(tmp_path)
    remote.fire(store)
    remote.cancel(store)
    assert any(e["event"] == "cancel_requested" for e in store.events())