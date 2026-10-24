"""Pinned llm-mailroom (dist name ``mailroom``) import surface."""

from __future__ import annotations

from pathlib import Path

from mailroom_ui.producer import (
    DECISIONS,
    DISPOSITIONS,
    MAILROOM_DIST_NAME,
    MAILROOM_DIST_VERSION,
    MAILROOM_GIT_SHA,
    MAILROOM_PEP508,
    producer_status,
    serialize_catalog_row,
)

ROOT = Path(__file__).resolve().parent.parent


def test_pin_matches_pyproject_extra():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert MAILROOM_GIT_SHA in text
    assert MAILROOM_DIST_NAME in text
    assert "git+https://github.com/Exios66/llm-mailroom.git@" in text
    assert MAILROOM_PEP508.split(" @ ")[1] in text
    assert "[pipeline]" in text or "pipeline = [" in text


def test_bundled_validate_operator_extraction_rejects_foreign_keys():
    from mailroom_ui.pipeline_schema import (
        FAILURE_CLASSES,
        failure_class_from_text,
        validate_operator_extraction,
    )

    assert "llm_timeout" in FAILURE_CLASSES
    assert failure_class_from_text("run aborted [llm_timeout]: boom") == "llm_timeout"
    ok = validate_operator_extraction("contract", {"parties": ["A", "B"]})
    assert ok["parties"] == ["A", "B"]
    try:
        validate_operator_extraction("contract", {"sender": "A Corp", "parties": ["A"]})
        raise AssertionError("expected foreign-key rejection")
    except ValueError as exc:
        assert "another specialist" in str(exc)


def test_contract_dispositions_match_producer_main():
    assert DISPOSITIONS == frozenset({"resume", "record", "requeue", "complete"})
    assert DECISIONS == frozenset({"approved", "rejected"})


def test_serialize_catalog_row_matches_lookup_shape():
    row = serialize_catalog_row(
        {
            "doc_id": "doc-1",
            "matter_id": "matter-a",
            "original_filename": "claim.pdf",
            "stage": "review",
            "doc_type": "insurance_claim",
            "doc_subclass": "fnol",
            "contract_subtype": None,
            "classification_confidence": 0.91,
            "extraction_confidence": 0.55,
            "escalation_reason": "parked",
            "trace_id": "tray-complete",
            "review_decision": None,
            "extracted_data": {"claim_number": "CL-1"},
            "created_at": "2026-08-28T00:00:00+00:00",
            "updated_at": "2026-08-28T00:00:00+00:00",
        }
    )
    assert row["doc_id"] == "doc-1"
    assert row["original_filename"] == "claim.pdf"
    assert row["stage"] == "review"
    assert row["extracted_data"]["claim_number"] == "CL-1"
    assert "file" not in row


def test_producer_status_shape():
    info = producer_status()
    assert info["distribution"] == MAILROOM_DIST_NAME
    assert info["pin"] == MAILROOM_GIT_SHA
    assert info["version"] == MAILROOM_DIST_VERSION
    assert info["pep508"] == MAILROOM_PEP508
    assert info["origin"] in {"installed", "checkout", "pin", "fallback"}
    assert isinstance(info["imported"], bool)


def test_imported_contract_comes_from_pipeline_review_resolve():
    from mailroom_ui import producer as prod

    if not prod.producer_available():
        return
    assert prod.serialize_document.__module__ == "pipeline.review_resolve"
    assert prod.DISPOSITIONS == frozenset({"resume", "record", "requeue", "complete"})
    assert prod.DocumentManifest is not None


def test_meta_and_health_surface_mailroom_pin():
    from fastapi.testclient import TestClient

    from mailroom_ui.langfuse_source import LangfuseSource
    from server.main import create_app
    from tests.fake_langfuse import FakeClient, make_trace

    src = LangfuseSource(client=FakeClient([make_trace("t-pin")]))
    with TestClient(create_app(src)) as client:
        meta = client.get("/api/meta").json()
        assert meta["mailroom"]["pin"] == MAILROOM_GIT_SHA
        assert meta["mailroom"]["distribution"] == MAILROOM_DIST_NAME
        health = client.get("/api/health").json()
        assert health["mailroom"]["pin"] == MAILROOM_GIT_SHA
        debug = client.get("/api/debug/source").json()
        assert debug["mailroom"]["pin"] == MAILROOM_GIT_SHA
