"""Primary/secondary outcomes and archive filenames."""

from __future__ import annotations

from datetime import datetime, timezone

from mailroom_ui.classification import (
    HIT,
    MISS,
    N_A,
    PENDING,
    archive_document_name,
    archive_name_from_run,
    classification_card,
    classification_from_run,
)
from server.poller import floor_payload
from tests.fake_langfuse import make_trace, make_trace_v4
from tests.test_interpreter import _run


def test_primary_hit_vs_ground_truth():
    card = classification_card(
        doc_type="contract",
        expected_hf_class="contract",
        doc_subclass="nda",
        expected_subclass="nda",
    )
    assert card["primary_outcome"] == HIT
    assert card["secondary_outcome"] == HIT
    assert "Contract" in card["primary_label"]


def test_primary_miss_and_pending_without_gt():
    miss = classification_card(doc_type="contract", expected_hf_class="insurance_claim")
    assert miss["primary_outcome"] == MISS
    pending = classification_card(doc_type="unknown")
    assert pending["primary_outcome"] == PENDING
    untyped = classification_card()
    assert untyped["primary_outcome"] == PENDING
    assert untyped["secondary_outcome"] == N_A


def test_merger_exact_match_counts_as_hit():
    card = classification_card(
        doc_type="merger_agreement",
        expected_hf_class="merger_agreement",
        doc_subclass="all_cash",
        expected_subclass="all_cash",
    )
    assert card["primary_outcome"] == HIT


def test_merger_vs_contract_counts_as_miss():
    """v0.6.0: MAUD and CUAD are distinct live classes."""
    card = classification_card(
        doc_type="merger_agreement",
        expected_hf_class="contract",
        doc_subclass="all_cash",
        expected_subclass="all_cash",
    )
    assert card["primary_outcome"] == MISS


def test_assigned_class_without_gt_is_hit():
    card = classification_card(doc_type="correspondence", doc_subclass="email")
    assert card["primary_outcome"] == HIT
    assert card["secondary_outcome"] == HIT


def test_archive_document_name_shape():
    name = archive_document_name(
        doc_type="contract",
        doc_subclass="nda",
        filename="Acme MSA (final).PDF",
        doc_id="a1b2c3d4eeee",
        created_at=datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc),
    )
    assert name == "contract/2026-08-29/contract__nda__acme-msa-final__a1b2c3d4.pdf"


def test_floor_payload_v2_and_v4_carry_outcomes():
    now = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
    snake = _run(make_trace(
        "t-class-v2",
        filename="acme-msa.pdf",
        doc_type="compliance_filing",
        doc_subclass="10-K",
        extra_metadata={"expected_hf_class": "compliance_filing", "expected_subclass": "10-K"},
        output_extra={"doc_id": "doc-10k99"},
        base_time=now,
    ))
    camel = _run(make_trace_v4(
        "t-class-v4",
        filename="acme-msa.pdf",
        doc_type="compliance_filing",
        doc_subclass="10-K",
        extra_metadata={"expected_hf_class": "compliance_filing", "expected_subclass": "10-K"},
        output_extra={"doc_id": "doc-10k99"},
    ))
    for run in (snake, camel):
        card = classification_from_run(run)
        assert card["primary_outcome"] == HIT
        assert card["secondary_outcome"] == HIT
        payload = floor_payload(run)
        assert payload["primary_outcome"] == HIT
        assert payload["secondary_label"]
        assert payload["archive_name"].startswith("compliance_filing/")
        assert archive_name_from_run(run) == payload["archive_name"]
        assert "classification_confidence" in payload
