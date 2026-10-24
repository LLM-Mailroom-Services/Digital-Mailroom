"""SAND-045: chunked v9.1 GT labeler posture, spend cap, and prompts."""

from __future__ import annotations

import json

import pytest

from mailroom_sandbox.gt_labeler import (
    APP_NAME,
    CHUNK_DOC_CAP,
    CHUNK_USD_CAP,
    CLIENT_IN_FLIGHT,
    DATASET_REVISION,
    DATASET_TAG,
    POSTURE,
    GoldenLabelError,
    LabelChunk,
    LabelSpendError,
    apply_posture_env,
    assert_one_chunk,
    assert_posture,
    build_messages,
    next_chunk,
    plan_chunks,
    project_usd,
    validate_label_response,
)
from mailroom_sandbox.job.spec import FAMILY_HF_DATA_REVISION, FAMILY_HF_REVISION


def _target(i: int, **over) -> dict:
    row = {
        "id": f"doc-{i:04d}",
        "filename": f"doc-{i:04d}.txt",
        "doc_class": "contract",
        "source_corpus": "sec_edgar",
        "source_dataset": "sec_edgar",
        "fields": ["cuad_clause_labels"],
        "context_window_band": "<=16k",
        "expected_subclass": "Service",
        "doc_text": "This Service Agreement is governed by the laws of Delaware.",
    }
    row.update(over)
    return row


def test_benchmark_gate_accepts_the_data_parent_and_the_tag():
    """Measured SAND-032 YAMLs stay on the parquet SHA. New pulls use the tag."""
    from mailroom_sandbox.job.benchmark_check import BENCHMARK_EXPECTED

    accepted = BENCHMARK_EXPECTED["accepted_revisions"]
    assert FAMILY_HF_REVISION in accepted
    assert FAMILY_HF_DATA_REVISION in accepted
    assert "not-a-revision" not in accepted


def test_dataset_pin_is_hub_tag_v9_1():
    assert DATASET_TAG == "v9.1"
    assert DATASET_REVISION == "bc9eab280044befb51e19dda3071d290a8677f42"
    assert DATASET_REVISION == FAMILY_HF_REVISION
    assert FAMILY_HF_DATA_REVISION == "ed7576b676343e0b402ec5412cded301e629bdee"


def test_posture_is_two_l4s_of_qwen3_14b_awq():
    assert POSTURE["MODAL_VLLM_APP_NAME"] == APP_NAME == "sandbox-vllm-gt-labeler"
    assert APP_NAME.startswith("sandbox-vllm")
    assert POSTURE["MODAL_VLLM_MODEL"] == "Qwen/Qwen3-14B-AWQ"
    assert POSTURE["MODAL_VLLM_GPU"] == "L4"
    assert POSTURE["MODAL_VLLM_MAX_CONTAINERS"] == "2"
    assert POSTURE["MODAL_VLLM_MIN_CONTAINERS"] == "0"
    assert POSTURE["MODAL_VLLM_MAX_NUM_SEQS"] == "8"
    assert POSTURE["MODAL_VLLM_MAX_INPUTS"] == "8"
    assert CLIENT_IN_FLIGHT == 16
    assert "enable_thinking" in POSTURE["MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS"]
    assert '"enable_thinking": false' in POSTURE["MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS"]
    assert POSTURE["MODAL_VLLM_ASYNC_SCHEDULING"] == "0"


def test_assert_posture_accepts_the_pin_and_refuses_drift():
    env = apply_posture_env({})
    assert_posture(env)
    drifted = dict(env)
    drifted["MODAL_VLLM_MODEL"] = "Qwen/Qwen3-8B"
    with pytest.raises(LabelSpendError):
        assert_posture(drifted)
    wide = dict(env)
    wide["MODAL_VLLM_GPU"] = "A100-80GB"
    with pytest.raises(LabelSpendError):
        assert_posture(wide)
    one = dict(env)
    one["MODAL_VLLM_MAX_CONTAINERS"] = "1"
    with pytest.raises(LabelSpendError):
        assert_posture(one)


def test_full_corpus_is_not_one_chunk():
    targets = [_target(i) for i in range(3302)]
    chunks = plan_chunks(targets)
    assert len(chunks) > 1
    assert all(c.doc_count <= CHUNK_DOC_CAP for c in chunks)
    assert all(c.projected_usd <= CHUNK_USD_CAP for c in chunks)
    assert sum(c.doc_count for c in chunks) == 3302
    combined = LabelChunk(
        index=0,
        targets=tuple(targets),
        slots=3302,
        projected_usd=project_usd(3302),
    )
    assert combined.projected_usd > CHUNK_USD_CAP
    with pytest.raises(LabelSpendError):
        assert_one_chunk(combined)


def test_next_chunk_returns_only_the_first_unfinished_slice():
    targets = [_target(i) for i in range(100)]
    first = next_chunk(targets)
    assert first is not None
    assert first.doc_count == CHUNK_DOC_CAP
    assert first.index == 0
    done = {t["id"] for t in first.targets}
    second = next_chunk(targets, done)
    assert second is not None
    assert second.doc_count == CHUNK_DOC_CAP
    assert set(second.manifest()["filenames"]).isdisjoint(done)
    rest_done = done | {t["id"] for t in second.targets}
    last = next_chunk(targets, rest_done)
    assert last is not None
    assert last.doc_count == 20
    assert next_chunk(targets, rest_done | {t["id"] for t in last.targets}) is None


def test_overflow_documents_consume_two_slots():
    short = project_usd(1)
    long = project_usd(2)
    assert long > short
    chunks = plan_chunks([_target(1, context_window_band=">32k")])
    assert chunks[0].slots == 2


def test_ex10_prompt_lists_cuad_categories_and_refuses_golden_rows():
    messages = build_messages(_target(1))
    user = messages[1]["content"]
    system = messages[0]["content"]
    assert "Governing Law" in user
    assert "Document Name" in user
    assert "v9.1" in system
    assert "golden" in system.lower() or "golden" in system
    with pytest.raises(GoldenLabelError):
        build_messages(_target(2, source_dataset="", source_corpus="theatticusproject/cuad"))
    with pytest.raises(GoldenLabelError):
        build_messages(
            _target(
                3,
                doc_class="merger_agreement",
                fields=["maud_clause_labels"],
                source_corpus="maud",
            )
        )


def test_correspondence_prompt_uses_the_closed_intent_list():
    messages = build_messages(
        _target(
            4,
            doc_class="correspondence",
            source_corpus="Lucius-Morningstar/enron-correspondence-dedup",
            source_dataset="",
            fields=["intent", "subject_matter"],
            doc_text="Please send the invoice by Friday.",
        )
    )
    user = messages[1]["content"]
    assert "payment_demand" in user
    assert "meeting_invite" in user
    assert "Governing Law" not in user
    assert "requested fields: intent, subject_matter" in user


def test_validate_label_response_requires_every_requested_field():
    requested = ["intent"]
    ok = {"fields": {"intent": "notice"}, "abstain": []}
    assert validate_label_response(requested, ok) == []
    both = {"fields": {"intent": "notice"}, "abstain": [{"field": "intent", "reason": "unsure"}]}
    assert validate_label_response(requested, both)
    missing = {"fields": {}, "abstain": []}
    assert validate_label_response(requested, missing)
    abstained = {
        "fields": {},
        "abstain": [{"field": "intent", "reason": "the text does not say"}],
    }
    assert validate_label_response(requested, abstained) == []


def test_cuad_response_must_cover_every_category():
    from langchain_agents.cuad_maud import CUAD_CLAUSE_CATEGORIES

    payload = {
        "fields": {
            "cuad_clause_labels": {
                name: [] for name in CUAD_CLAUSE_CATEGORIES
            }
        },
        "abstain": [],
    }
    payload["fields"]["cuad_clause_labels"]["Governing Law"] = [
        {"start": 10, "text": "laws of the State of Delaware"}
    ]
    assert validate_label_response(["cuad_clause_labels"], payload) == []
    del payload["fields"]["cuad_clause_labels"]["Parties"]
    assert validate_label_response(["cuad_clause_labels"], payload)


def test_verbatim_spans_snap_to_the_document_and_drop_paraphrases():
    from mailroom_sandbox.gt_labeler import (
        cuad_label_problems,
        label_evidence_for,
        locate_verbatim,
        normalize_cuad_labels,
    )

    document = (
        "This Consulting Agreement is entered into as of June 21, 1999 "
        "by and between North Coast Minerals and Ada Consulting LLC. "
        "This Agreement shall be governed by the laws of the State of Delaware."
    )
    start, exact = locate_verbatim(document, "June   21, 1999")
    assert exact == "June 21, 1999"
    assert document[start:start + len(exact)] == exact
    assert locate_verbatim(document, "the parties mutually agree to arbitrate") is None
    letter = 'entered into between Roxanne Oulman ("**you**") and Medallia, Inc.'
    snapped = locate_verbatim(letter, 'Roxanne Oulman ("you") and Medallia, Inc.')
    assert snapped is not None
    assert snapped[1] == 'Roxanne Oulman ("**you**") and Medallia, Inc.'
    assert letter[snapped[0]:snapped[0] + len(snapped[1])] == snapped[1]

    labels, dropped = normalize_cuad_labels(
        document,
        {
            "clauses": [
                {"category": "Document Name", "text": "Consulting Agreement"},
                {"category": "Agreement Date", "text": "June 21, 1999"},
                {"category": "Parties", "text": "North Coast Minerals and Ada Consulting LLC"},
                {
                    "category": "Governing Law",
                    "text": "governed by the laws of the State of Delaware",
                },
                {"category": "Exclusivity", "text": "exclusive worldwide rights"},
                {"category": "Not A Clause", "text": "Consulting Agreement"},
            ]
        },
    )
    assert len(labels) == 41
    assert labels["Agreement Date"] == [{"start": start, "text": exact}]
    assert labels["Exclusivity"] == []
    assert any("not verbatim" in item for item in dropped)
    assert any("unknown category" in item for item in dropped)
    assert cuad_label_problems(labels) == []
    assert label_evidence_for(labels).startswith("CUAD-annotated clauses: ")
    assert "Governing Law" in label_evidence_for(labels)


def test_label_journal_keeps_accepted_and_the_better_partial():
    from mailroom_sandbox.gt_labeler import accepted_ids, fold_label_journal

    rows = [
        {"id": "a.txt", "filename": "a.txt", "accepted": False, "span_count": 6},
        {"id": "a.txt", "filename": "a.txt", "accepted": False, "span_count": 2},
        {"id": "b.txt", "filename": "b.txt", "accepted": True, "span_count": 10},
        {"id": "b.txt", "filename": "b.txt", "accepted": False, "span_count": 12},
    ]
    folded = fold_label_journal(rows)
    assert folded["a.txt"]["span_count"] == 6
    assert folded["b.txt"]["accepted"] is True
    assert accepted_ids(rows) == {"b.txt"}


def test_response_round_trip():
    from mailroom_sandbox.gt_labeler import loads_response

    raw = json.dumps({"fields": {"intent": "request"}, "abstain": []})
    assert loads_response(raw)["fields"]["intent"] == "request"
