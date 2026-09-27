"""Braintrust backend contract for sandbox eval tracing.

The regression these tests exist to stop: ``tracing_backend()`` could already
return ``"braintrust"`` while ``_sdk_client()`` returned ``None`` for it, so a
run reported ``tracing_backend: braintrust`` and emitted **nothing** — a
silent no-op wearing a working-sink label. These tests pin the opposite: a
selected Braintrust sink produces real spans, scores and flushes, and every
failure path is counted (live-or-loud).
"""

from __future__ import annotations

import pytest

from mailroom_sandbox.eval import tracing


class _FakeSpan:
    def __init__(self, name, **event):
        self.name = name
        self.id = f"span-{name}"
        self.event = {k: v for k, v in event.items() if v is not None}
        self.ended = 0
        self.parent = None
        self.children: list[_FakeSpan] = []
        self.logs: list[dict] = []

    def log(self, **event):
        self.logs.append({k: v for k, v in event.items() if v is not None})
        self.event.update(self.logs[-1])

    def start_span(self, name=None, **event):
        child = _FakeSpan(name, **event)
        child.parent = self
        self.children.append(child)
        return child

    def end(self):
        self.ended += 1


class _FakeLogger:
    def __init__(self, *, fail_start: bool = False, fail_flush: bool = False):
        self.spans: list[_FakeSpan] = []
        self.flushed = 0
        self._fail_start = fail_start
        self._fail_flush = fail_flush
        self.project = type("P", (), {"name": "Mailroom-Evals"})()

    def start_span(self, name=None, **event):
        if self._fail_start:
            raise RuntimeError("sink down")
        span = _FakeSpan(name, **event)
        self.spans.append(span)
        return span

    def flush(self):
        if self._fail_flush:
            raise RuntimeError("flush down")
        self.flushed += 1


@pytest.fixture
def bt(monkeypatch):
    """Braintrust selected + credentialed + a fake logger, fully isolated."""
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "braintrust")
    monkeypatch.setenv("BRAINTRUST_API_KEY", "sk-test-not-a-real-key")
    monkeypatch.setenv("BRAINTRUST_PROJECT_ID", "d665b053-c25a-4fe9-a8f4-71a45fb54f94")
    logger = _FakeLogger()
    monkeypatch.setattr(tracing, "_braintrust_logger", lambda: logger)
    monkeypatch.setattr(tracing, "_mailroom_setup", lambda: None)
    # never touch the hosted sink from the suite
    monkeypatch.setattr(tracing, "_sdk_client", lambda: None)
    tracing._TRACING_WARNED.clear()
    yield logger
    tracing._TRACING_WARNED.clear()
    tracing._BT_SPAN_STACK.set(())


def test_backend_selection_is_honest(bt):
    """Selecting braintrust must report braintrust AND be considered configured."""
    assert tracing.tracing_backend() == "braintrust"
    assert tracing.braintrust_configured() is True


def test_root_trace_opens_a_real_braintrust_span(bt):
    with tracing.document_pipeline_trace(input={"doc": "x"}, metadata={"run": "r1"}) as root:
        assert isinstance(root, tracing._BraintrustSpan)
        assert root is not None
    assert len(bt.spans) == 1
    span = bt.spans[0]
    assert span.name == "document-pipeline"
    assert span.event["type"] == "task"  # chain -> braintrust task
    assert span.event["metadata"]["pipeline"] == "mailroom"
    assert "mailroom" in span.event["tags"]
    assert span.ended == 1


def test_child_llm_span_nests_under_root(bt):
    with tracing.document_pipeline_trace(input={"doc": "x"}):
        with tracing.child_observation("extract-fields", as_type="generation", input={"f": 1}) as child:
            assert child is not None
            assert tracing._braintrust_current_span() is child
            child.log(output={"value": "v"}, metrics={"latency_s": 1.5})
    # one root span from the logger; the LLM call nests under it
    assert len(bt.spans) == 1
    root = bt.spans[0]
    assert len(root.children) == 1
    child_span = root.children[0]
    assert child_span.parent is root
    assert child_span.name == "extract-fields"
    assert child_span.event["type"] == "llm"  # generation -> braintrust llm
    assert child_span.logs and "output" in child_span.logs[0]
    assert root.ended == 1 and child_span.ended == 1


def test_score_attaches_to_the_active_span_via_scores_mapping(bt):
    """0.42 has no Span.score/Logger.score — scores must ride log(scores=...)."""
    with tracing.document_pipeline_trace(input={"doc": "x"}):
        tracing.emit_langfuse_score("class_correct", 1.0, comment="exact")
    root = bt.spans[0]
    scored = [ev for ev in root.logs if "scores" in ev]
    assert scored, "score never reached the span"
    assert scored[-1]["scores"] == {"class_correct": 1.0}
    assert scored[-1]["metadata"]["comment"] == "exact"


def test_flush_reaches_braintrust(bt):
    with tracing.document_pipeline_trace(input={"doc": "x"}):
        pass
    tracing.flush_traces()
    assert bt.flushed == 1


def test_flush_failure_is_counted_not_swallowed(monkeypatch, caplog):
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "braintrust")
    monkeypatch.setenv("BRAINTRUST_API_KEY", "sk-test")
    monkeypatch.setattr(tracing, "_braintrust_logger", lambda: _FakeLogger(fail_flush=True))
    before = tracing.tracing_failure_counts()["flush_failures"]
    with caplog.at_level("ERROR", logger="mailroom_sandbox.tracing"):
        tracing.flush_traces()
    assert tracing.tracing_failure_counts()["flush_failures"] == before + 1
    assert any("Braintrust flush failed" in r.message for r in caplog.records)
    tracing._TRACING_WARNED.clear()


def test_start_span_failure_is_counted_and_run_continues(monkeypatch, caplog):
    """A dead sink must not abort the eval run, but must be loud."""
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "braintrust")
    monkeypatch.setenv("BRAINTRUST_API_KEY", "sk-test")
    monkeypatch.setattr(tracing, "_braintrust_logger", lambda: _FakeLogger(fail_start=True))
    monkeypatch.setattr(tracing, "_mailroom_setup", lambda: None)
    monkeypatch.setattr(tracing, "_sdk_client", lambda: None)
    before = tracing.tracing_failure_counts()["braintrust_span_failures"]
    with caplog.at_level("ERROR", logger="mailroom_sandbox.tracing"):
        with tracing.document_pipeline_trace(input={"doc": "x"}) as root:
            # the run keeps going; the body still executes
            assert root is not None
    assert tracing.tracing_failure_counts()["braintrust_span_failures"] == before + 1
    assert any("FAILED" in r.message for r in caplog.records)
    tracing._TRACING_WARNED.clear()


def test_score_outside_any_span_is_lost_loudly(monkeypatch, caplog):
    """A score with no active trace has nowhere to land — that is a real loss."""
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "braintrust")
    monkeypatch.setenv("BRAINTRUST_API_KEY", "sk-test")
    monkeypatch.setattr(tracing, "_braintrust_logger", lambda: _FakeLogger())
    tracing._BT_SPAN_STACK.set(())
    before = tracing.tracing_failure_counts()["score_emit_failures"]
    with caplog.at_level("WARNING", logger="mailroom_sandbox.tracing"):
        tracing.emit_langfuse_score("stage_correct", 0.0)
    assert tracing.tracing_failure_counts()["score_emit_failures"] == before + 1
    assert any("LOST" in r.message for r in caplog.records)
    tracing._TRACING_WARNED.clear()


def test_uncredentialed_braintrust_is_not_configured(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "braintrust")
    monkeypatch.delenv("BRAINTRUST_API_KEY", raising=False)
    assert tracing.tracing_backend() == "braintrust"
    assert tracing.braintrust_configured() is False


def test_type_map_covers_every_node_type_in_the_family_contract():
    """Every node in NODE_OBSERVATION_TYPES must map to a real braintrust type."""
    from llm_dojo_scoring.mailroom import NODE_OBSERVATION_TYPES

    for node, obs_type in NODE_OBSERVATION_TYPES.items():
        mapped = tracing._braintrust_type(obs_type)
        assert mapped in {
            "automation", "classifier", "eval", "facet", "function", "llm",
            "log", "preprocessor", "question", "review", "score", "task", "tool",
        }, f"{node} ({obs_type}) -> {mapped}"


def test_export_bookmark_names_the_real_sink(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "braintrust")
    monkeypatch.setenv("BRAINTRUST_API_KEY", "sk-test")
    monkeypatch.setattr(tracing, "_braintrust_logger", lambda: _FakeLogger())
    out = tracing.export_traces(tmp_path / "export.json")
    import json

    payload = json.loads(out.read_text())
    assert payload["tracing_backend"] == "braintrust"
    assert payload["braintrust"]["project"] == "Mailroom-Evals"
    assert "NOT" in payload["braintrust"]["note"]  # not the The-Mailroom sink
    tracing._TRACING_WARNED.clear()
