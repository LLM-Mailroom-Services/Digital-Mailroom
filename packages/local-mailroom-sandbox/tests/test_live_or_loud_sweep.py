"""DMR-061 — live-or-loud sweep pins.

Every behavior this file asserts is a regression guard for the sweep: silent
degradation that was converted to a raise/warn/count must STAY loud. If one
of these goes red, the error path went quiet again — fix it loudly, do not
soften the test.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

import mailroom_sandbox.eval.tracing as tracing
import mailroom_sandbox.job.remote as remote
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.spec import EngineSpec, ModalSpec, RunSpec, engine_base_url


# Tiny modal-surface stubs (mirror test_job_remote's; kept local to avoid
# cross-importing test modules).
class _Call:
    def __init__(self, status_name):
        self.object_id = "call-abc"
        self.status_name = status_name
        self.canceled = False

    def get_call_graph(self):
        return [SimpleNamespace(status=SimpleNamespace(name=self.status_name))]

    def cancel(self, terminate_containers=False):
        self.canceled = True


class _MockFunction:
    def __init__(self, calls):
        self.calls = calls

    def from_name(self, app, fn):
        return self

    def spawn(self, payload=None):
        return self.calls["live"]


class _MockFunctionCall:
    def __init__(self, calls):
        self.calls = calls

    def from_id(self, call_id):
        return self.calls["live"]


class _MockDict:
    def __init__(self):
        self.store = {}
        self.put_calls = []

    def from_name(self, name, create_if_missing=False):
        return self

    def get(self, key, default=None):
        return self.store.get(key, default)

    def put(self, key, value):
        self.put_calls.append((key, value))
        self.store[key] = value


def _stub_remote_modal(monkeypatch, *, live_status="PENDING"):
    calls = {"live": _Call(live_status)}
    modal_stub = SimpleNamespace(
        Function=_MockFunction(calls),
        FunctionCall=_MockFunctionCall(calls),
        Dict=_MockDict(),
    )
    monkeypatch.setattr(remote, "_modal", lambda: modal_stub)


# ── engine-base resolution (job/spec.py) ──────────────────────────────────

def test_engine_base_url_unknown_profile_raises(monkeypatch):
    """A typo'd profile must raise, never silently resolve to localhost."""
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    spec = RunSpec(profile="definitely-not-a-profile", task="sorter")
    with pytest.raises(FileNotFoundError, match="Unknown profile"):
        engine_base_url(spec)


def test_engine_base_url_modal_without_workspace_raises(monkeypatch):
    """modal-vllm without MODAL_WORKSPACE must raise, never emit a literal
    '<workspace>' placeholder URL."""
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("MODAL_WORKSPACE", raising=False)
    from mailroom_sandbox import overlay as ov

    monkeypatch.setattr(ov, "load_profile", lambda name: {})
    spec = RunSpec(
        task="sorter",
        engine=EngineSpec(
            kind="modal-vllm",
            model="Qwen/Qwen3-8B",
            modal=ModalSpec(app="entity-vllm"),
        ),
    )
    with pytest.raises(ValueError, match="MODAL_WORKSPACE"):
        engine_base_url(spec)


# ── remote re-fire cooldown (job/remote.py) fail-closed ───────────────────

def _store_with_remote(tmp_path, fired_at: str) -> RunStore:
    store = RunStore(tmp_path / "run-r")
    store.write_lock({"spec_hash": "s1"})
    store.write_checkpoint(
        state="running",
        cursor=1,
        total=2,
        remote={"call_id": "call-abc", "fired_at": fired_at},
    )
    return store


def test_corrupt_fired_at_refuses_refire(tmp_path, monkeypatch):
    """A malformed fired_at must FAIL CLOSED (hub#41 guard) — re-firing a
    possibly-live worker is the corruption the guard exists to prevent."""
    _stub_remote_modal(monkeypatch, live_status="SUCCESS")
    monkeypatch.setattr(remote, "upload_run_dir", lambda d: (0, ""))
    monkeypatch.setattr(remote, "_remote_lock_hash", lambda run_id: None)

    store = _store_with_remote(tmp_path, fired_at="not-a-timestamp")
    with pytest.raises(RuntimeError, match="MALFORMED fired_at"):
        remote.ensure_running(store)


def test_fire_upload_failure_raises(tmp_path, monkeypatch):
    """fire() must raise loudly when the volume upload fails — a silent skip
    would have the worker score nothing while the CLI claims it fired."""
    _stub_remote_modal(monkeypatch, live_status="PENDING")
    monkeypatch.setattr(remote, "upload_run_dir", lambda d: (1, "denied by modal"))
    monkeypatch.setattr(remote, "_remote_lock_hash", lambda run_id: "different")

    store = _store_with_remote(tmp_path, fired_at="2026-09-14T00:00:00+00:00")
    with pytest.raises(RuntimeError, match="modal volume put failed"):
        remote.fire(store)


def test_read_progress_warns_when_state_dict_fails(tmp_path, monkeypatch, caplog):
    """A broken job-state Dict must warn and fall back to the checkpoint —
    never present the stale checkpoint as live progress silently."""
    class _BrokenDict:
        def from_name(self, name, create_if_missing=False):
            return self

        def get(self, key, default=None):
            raise RuntimeError("modal unavailable")

    modal_stub = SimpleNamespace(
        Function=_MockFunction({}),
        FunctionCall=_MockFunctionCall({}),
        Dict=_BrokenDict(),
    )
    monkeypatch.setattr(remote, "_modal", lambda: modal_stub)
    store = _store_with_remote(tmp_path, fired_at="2026-09-14T00:00:00+00:00")
    with caplog.at_level("WARNING", logger="mailroom_sandbox.job.remote"):
        progress = remote.read_progress(store)
    assert progress is not None and progress.get("state") == "running"
    assert any("job-state Dict could not be read" in r.message for r in caplog.records)


# ── tracing loudness (eval/tracing.py) ────────────────────────────────────

class _FailingClient:
    def __init__(self, *, fail_score=True, fail_flush=True):
        self.fail_score = fail_score
        self.fail_flush = fail_flush

    def score_current_trace(self, **kwargs):
        raise RuntimeError("sink down")

    def create_score(self, **kwargs):
        raise RuntimeError("sink down too")

    def flush(self):
        raise RuntimeError("flush down")


def test_tracing_score_emit_failure_is_counted(monkeypatch, caplog):
    """A score that cannot be emitted through EITHER SDK path must be logged
    as an error and counted — a silent drop is a lost score."""
    monkeypatch.setattr(tracing, "_mailroom_setup", lambda: None)
    monkeypatch.setattr(tracing, "_sdk_client", lambda: _FailingClient())
    before = tracing.tracing_failure_counts()["score_emit_failures"]
    with caplog.at_level("ERROR", logger="mailroom_sandbox.tracing"):
        tracing.emit_langfuse_score("class_correct", 0.5)
    after = tracing.tracing_failure_counts()["score_emit_failures"]
    assert after == before + 1
    assert any("score is LOST" in r.message for r in caplog.records)
    tracing._TRACING_WARNED.clear()


def test_tracing_flush_failure_is_counted(monkeypatch, caplog):
    """A failed flush must log at ERROR and increment the counter — buffered
    traces lost without a trace is a silent observability gap."""
    monkeypatch.setattr(tracing, "_mailroom_setup", lambda: None)
    monkeypatch.setattr(tracing, "_sdk_client", lambda: _FailingClient())
    before = tracing.tracing_failure_counts()["flush_failures"]
    with caplog.at_level("ERROR", logger="mailroom_sandbox.tracing"):
        tracing.flush_traces()
    after = tracing.tracing_failure_counts()["flush_failures"]
    assert after == before + 1
    assert any("flush failed" in r.message for r in caplog.records)


def test_tracing_sdk_missing_warns_once(monkeypatch, caplog):
    """A configured sink whose SDK is missing must WARN (once) — tracing must
    never vanish silently."""
    monkeypatch.setattr(tracing, "tracing_backend", lambda: "langfuse")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    with mock.patch.dict("sys.modules", {"langfuse": None}), caplog.at_level(
        "WARNING", logger="mailroom_sandbox.tracing"
    ):
        client = tracing._sdk_client()
    assert client is None
    assert any("Langfuse SDK unavailable" in r.message for r in caplog.records)
    tracing._TRACING_WARNED.clear()


# ── vendor self-containment is a standing guard (not a conditional skip) ──

def test_vendor_trees_present_so_drift_guard_is_live():
    """The vendor drift guard must not silently SKIP when a snapshot is
    missing — in this monorepo the trees are always tracked, so absence is a
    failure, never a graceful skip."""
    vendor = Path(__file__).resolve().parents[1] / "vendor"
    assert (vendor / "llm-mailroom" / "VENDOR.md").is_file(), (
        f"vendored llm-mailroom snapshot missing — `sandbox fetch-deps` restores it"
    )
    assert (vendor / "llm-dojo-scoring" / "VENDOR.md").is_file(), (
        f"vendored llm-dojo-scoring snapshot missing — `sandbox fetch-deps` restores it"
    )


# ── preflight engine probe diagnosis (job/preflight.py) ───────────────────

def test_probe_engine_unparseable_json_reports_diagnosis(monkeypatch):
    """An unparseable /v1/models response must be diagnosed as a wrong-API
    condition, never misreported as 'served []'."""
    from mailroom_sandbox.job.preflight import _probe_engine

    class _Resp:
        status_code = 200

        def json(self):
            raise ValueError("no json here")

        @property
        def text(self):
            return "<html>not an API</html>"

    import httpx

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp())
    # probe now retries an unparseable 2xx within the boot budget; zero it so
    # the diagnosis is returned on the first attempt (SAND-018).
    monkeypatch.setenv("SANDBOX_ENGINE_PROBE_TIMEOUT_SECONDS", "0")
    spec = RunSpec(task="sorter", profile="vllm-local")
    result = _probe_engine(spec)
    assert result["ok"] is False
    assert "unparseable" in result["reason"]
    assert "served []" not in result["reason"]


# ── CLI health rc (cli.py:_cmd_health) ────────────────────────────────────

def test_health_failure_returns_rc1(monkeypatch, capsys):
    """`sandbox health` must exit 1 when any probe fails — a green-looking
    health table that returns 0 is the silent-failure lie."""
    import argparse

    from mailroom_sandbox import cli

    monkeypatch.setattr(
        "mailroom_sandbox.health.health_check",
        lambda profile_name: {
            "profile": profile_name,
            "ok": False,
            "models": {"ok": False, "name": "x"},
            "chat": {"ok": False, "name": "x"},
        },
    )
    monkeypatch.setattr("mailroom_sandbox.health.probe_models", lambda profile, **kw: SimpleNamespace(
        ok=False, as_dict=lambda: {"ok": False, "name": "x"}
    ))
    monkeypatch.setattr("mailroom_sandbox.runtime.load_env_file", lambda: None)
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3000")

    args = argparse.Namespace(profile="ollama")
    assert cli._cmd_health(args) == 1


# ── chained eval composite integrity (eval/runners.py) ────────────────────

def test_chained_composite_refuses_missing_half(monkeypatch):
    """run_chained_eval must raise when either half produced no scores — a
    0-sentinel composite would silently hide the failed half."""
    from mailroom_sandbox.eval import runners

    monkeypatch.setattr(
        runners,
        "run_sorter_eval",
        lambda **kw: {"scores": {"exact_match": None}, "sorter": {}},
    )
    monkeypatch.setattr(
        runners,
        "run_extract_eval",
        lambda **kw: {"scores": {"overall_extraction_score": None}, "extract": {}},
    )
    with pytest.raises(RuntimeError, match="chained eval"):
        runners.run_chained_eval(mock=True, profile="ollama")


# ── intake fallback provenance (eval/agents.py:_live_intake) ──────────────

def test_live_intake_fallback_marks_offline_provenance(monkeypatch, caplog):
    """A live intake failure must fall back AND label the row
    offline_fallback=True — a silently-replaced prediction is a provenance lie."""
    from mailroom_sandbox.eval import agents

    def _fake_normalize(text):
        return text.strip(), {"method": "deterministic"}

    # A None entry in sys.modules makes `from agents.intake import ...` raise
    # ImportError WITHOUT breaking any other import in the fallback path.
    sys_modules = mock.patch.dict("sys.modules", {"agents.intake": None})
    import llm_dojo_scoring.intake as dojo_intake

    with sys_modules, mock.patch.object(
        dojo_intake, "deterministic_normalize", side_effect=_fake_normalize
    ), caplog.at_level("WARNING", logger="mailroom_sandbox.eval.agents"):
        result = agents._live_intake({"id": "row-1", "text": "  hello  "})
    assert result["offline_fallback"] is True
    assert any("apply_intake failed" in r.message for r in caplog.records)