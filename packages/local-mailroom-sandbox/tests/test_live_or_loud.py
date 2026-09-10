"""DMR-044 live-or-loud regression tests for the eval harness.

These pin the silent-mock root causes found by the 2026-09-10 specialist
sweep: an undefined ``_doc_text`` (NameError swallowed into a mock), prepared
corpus rows hitting the fixture-only ``subdir`` path, live errors degrading to
mock predictions, and the legalbench model defaulting to an Ollama tag on a
vLLM serve.
"""

from __future__ import annotations

import json

import pytest

from mailroom_sandbox.eval import runners
from mailroom_sandbox.eval.agents import AgentSpec, _doc_text


def test_doc_text_prefers_doc_text_then_text():
    assert _doc_text({"doc_text": "corpus"}) == "corpus"
    assert _doc_text({"text": "inline"}) == "inline"
    assert _doc_text({"doc_text": "a", "text": "b"}) == "a"


def test_doc_text_raises_when_missing():
    with pytest.raises(ValueError, match="no document text"):
        _doc_text({"id": "row-1"})


def test_doc_text_falls_back_to_fixture_file(tmp_path, monkeypatch):
    fixture = tmp_path / "doc.txt"
    fixture.write_text("from-disk", encoding="utf-8")
    monkeypatch.setattr("mailroom_sandbox.eval.agents.fixture_file", lambda row: fixture)
    assert _doc_text({"id": "row-2", "subdir": "x", "filename": "doc.txt"}) == "from-disk"


def test_predict_spec_reraises_live_errors():
    def boom(row):
        raise RuntimeError("engine down")

    spec = AgentSpec(name="t", observation="o", live_predict=boom)
    with pytest.raises(RuntimeError, match="engine down"):
        runners._predict_spec(spec, {"id": "r"}, mock=False)


def test_predict_spec_falls_back_only_without_live_fn():
    spec = AgentSpec(name="t", observation="o", mock_predict=lambda row: {"value": "m"})
    pred, fell_back = runners._predict_spec(spec, {"id": "r"}, mock=False)
    assert pred == {"value": "m"}
    assert fell_back is True


def test_materialize_row_writes_doc_text_as_text(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    queued = runners._materialize_row(
        {"id": "doc-1", "filename": "case.pdf", "doc_text": "corpus text"}, inbox
    )
    assert queued.name == "case.txt"
    assert queued.read_text(encoding="utf-8") == "corpus text"


def test_materialize_row_copies_fixture(tmp_path, monkeypatch):
    source = tmp_path / "src.pdf"
    source.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr("mailroom_sandbox.eval.runners.fixture_file", lambda row: source)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    queued = runners._materialize_row({"id": "f", "subdir": "s", "filename": "src.pdf"}, inbox)
    assert queued.name == "src.pdf"
    assert queued.read_bytes() == b"%PDF-1.4"


def test_live_serve_target_follows_provider(monkeypatch):
    monkeypatch.setenv("DEFAULT_PROVIDER", "vllm")
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm:8000/v1")
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    base, model = runners._live_serve_target()
    assert base == "http://vllm:8000/v1"
    assert model == "Qwen/Qwen3-8B"

    monkeypatch.setenv("DEFAULT_PROVIDER", "ollama")
    _, model = runners._live_serve_target()
    assert model == "qwen3:8b"


def test_normalize_rows_carries_question_answer_stage_and_json_fields():
    from mailroom_sandbox.corpus import normalize_rows

    rows = normalize_rows(
        [
            {
                "id": "q1",
                "filename": "q1.txt",
                "doc_text": "text",
                "expected": "contract",
                "expected_stage": "archived",
                "expected_fields": json.dumps({"a": 1}),
                "question": "Is it valid?",
                "answer": "Yes",
            }
        ]
    )
    row = rows[0]
    assert row["expected_stage"] == "archived"
    assert row["expected_fields"] == {"a": 1}
    assert row["question"] == "Is it valid?"
    assert row["answer"] == "Yes"
