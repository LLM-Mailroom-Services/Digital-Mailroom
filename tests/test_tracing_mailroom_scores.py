"""Mailroom score path for sandbox eval tracing (SAND-042).

The regression: ``emit_langfuse_score`` called ``observability.scores.score``,
which the vendored mailroom never exposed (its API is ``score_trace``). Every
run end logged ``AttributeError`` plus a warning with a literal ``%r`` and fell
back to the SDK. These tests pin the call to the vendored public API, the SDK
fallback when the mailroom path cannot take a score, and a readable warning.
All network-free: fake modules and fake clients only.
"""

from __future__ import annotations

import ast
import logging
import sys
import types
from pathlib import Path

import pytest

from mailroom_sandbox.eval import tracing

_VENDORED_SCORES = (
    Path(__file__).resolve().parents[1] / "vendor" / "llm-mailroom" / "src" / "observability" / "scores.py"
)


class _FakeSdk:
    def __init__(self):
        self.calls: list[dict] = []

    def score_current_trace(self, **kwargs):
        self.calls.append(kwargs)


def _install_scores(monkeypatch, module: types.ModuleType) -> None:
    pkg = types.ModuleType("observability")
    pkg.scores = module
    monkeypatch.setitem(sys.modules, "observability", pkg)
    monkeypatch.setitem(sys.modules, "observability.scores", module)


@pytest.fixture
def lf(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "langfuse")
    monkeypatch.setattr(tracing, "_mailroom_setup", lambda: object())
    sdk = _FakeSdk()
    monkeypatch.setattr(tracing, "_sdk_client", lambda: sdk)
    tracing._TRACING_WARNED.clear()
    yield sdk
    tracing._TRACING_WARNED.clear()


def test_vendored_scores_exposes_score_trace():
    """Drift guard: the pinned vendor surface the sandbox calls still exists."""
    tree = ast.parse(_VENDORED_SCORES.read_text())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert "score" not in funcs
    fn = funcs["score_trace"]
    positional = [a.arg for a in fn.args.args]
    keyword = {a.arg for a in fn.args.kwonlyargs}
    assert positional[:2] == ["name", "value"]
    assert {"comment", "data_type"} <= keyword


def test_score_routes_through_score_trace(lf, monkeypatch, caplog):
    calls: list[tuple] = []
    mod = types.ModuleType("observability.scores")
    mod.is_enabled = lambda: True
    mod.score_trace = lambda name, value, *, data_type=None, comment=None: calls.append(
        (name, value, data_type, comment)
    )
    _install_scores(monkeypatch, mod)
    before = tracing.tracing_failure_counts()["score_emit_failures"]

    with caplog.at_level(logging.WARNING, logger="mailroom_sandbox.tracing"):
        tracing.emit_langfuse_score("extraction_overall_verified_precision", 0.9, comment="c", data_type="NUMERIC")

    assert calls == [("extraction_verified_precision", 0.9, "NUMERIC", "c")]
    assert lf.calls == []  # no SDK fallback
    assert not [r for r in caplog.records if "score path failed" in r.getMessage()]
    assert tracing.tracing_failure_counts()["score_emit_failures"] == before


def test_mailroom_not_on_langfuse_falls_back_to_sdk(lf, monkeypatch):
    calls: list[tuple] = []
    mod = types.ModuleType("observability.scores")
    mod.is_enabled = lambda: False
    mod.score_trace = lambda *a, **k: calls.append((a, k))
    _install_scores(monkeypatch, mod)

    tracing.emit_langfuse_score("judge_verdict", 1)

    assert calls == []
    assert lf.calls == [{"name": "judge_verdict", "value": 1}]


def test_missing_entry_point_warns_readably_and_falls_back(lf, monkeypatch, caplog):
    _install_scores(monkeypatch, types.ModuleType("observability.scores"))

    with caplog.at_level(logging.WARNING, logger="mailroom_sandbox.tracing"):
        tracing.emit_langfuse_score("judge_verdict", 1)

    assert lf.calls == [{"name": "judge_verdict", "value": 1}]
    msgs = [r.getMessage() for r in caplog.records if "score path failed" in r.getMessage()]
    assert msgs == ["mailroom score path failed for 'judge_verdict' — falling back to Langfuse SDK"]
    assert "%r" not in msgs[0]


def test_braintrust_outside_span_warning_names_the_score(monkeypatch, caplog):
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "braintrust")
    monkeypatch.setattr(tracing, "_braintrust_current_span", lambda: None)
    tracing._TRACING_WARNED.clear()
    with caplog.at_level(logging.WARNING, logger="mailroom_sandbox.tracing"):
        tracing.emit_langfuse_score("judge_verdict", 1)
    tracing._TRACING_WARNED.clear()
    rec = [r for r in caplog.records if "no active span" in r.getMessage()]
    assert len(rec) == 1
    assert "'judge_verdict'" in rec[0].getMessage()
    assert "%r" not in rec[0].getMessage()
    assert rec[0].exc_info is None
