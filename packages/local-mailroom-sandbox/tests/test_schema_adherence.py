"""Parse/schema-adherence metrics + empty-field / partial-credit scoring (issue #21)."""

from __future__ import annotations

import json

from llm_dojo_scoring.extraction_metrics import extraction_binary_metrics
from llm_dojo_scoring.field_scoring import score_extraction

from mailroom_sandbox.eval import scoring
from mailroom_sandbox.eval.schema_adherence import (
    assess_extraction_payload,
    classify_floor_mode,
    coerce_predicted_payload,
    merge_schema_adherence,
)
from mailroom_sandbox.job import metrics


CORRESPONDENCE_TYPES = {
    "sender": "name",
    "recipient": "name",
    "additional_recipients": "entity_list",
    "communication_type": "name",
    "communication_date": "date",
    "demand_amount": "money",
    "action_items": "entity_list",
    "urgency": "name",
    "intent": "name",
    "subject_matter": "free_text",
    "keywords": "entity_list:name",
}


def test_parse_error_flag_is_not_schema_valid():
    pred = {"_parse_error": True, "confidence": 0.3}
    out = assess_extraction_payload(pred, "correspondence")
    assert out["parse_error"] is True
    assert out["schema_valid"] is False
    assert out["schema_adherence"] == 0.0
    assert classify_floor_mode(out) == "format"


def test_unparseable_prose_is_parse_error():
    out = assess_extraction_payload("the sender is Dana Alvarez, demand $218440", "correspondence")
    assert out["parse_error"] is True
    assert out["schema_valid"] is False
    assert out["parse_failure_reason"] == "unparseable"


def test_json_inside_prose_wrapper_is_flagged_not_parse_error():
    blob = (
        "Sure, here is the extraction:\n"
        '{"sender": "Dana Alvarez", "recipient": "Northwind Logistics", '
        '"intent": "demand_payment", "keywords": ["invoice"]}\n'
        "Hope that helps!"
    )
    out = assess_extraction_payload(blob, "correspondence")
    assert out["parse_error"] is False
    assert out["prose_wrapper"] is True
    assert out["schema_valid"] is True
    assert out["schema_adherence"] == 1.0
    assert classify_floor_mode(out) == "format"


def test_python_repr_from_items_jsonl_coerces():
    """Job items.jsonl stores ``str(dict)``, which is not JSON."""
    payload, meta = coerce_predicted_payload("{'sender': 'Dana Alvarez', 'intent': 'notice'}")
    assert meta["parse_error"] is False
    assert payload["sender"] == "Dana Alvarez"


def test_legacy_correspondence_keys_are_extra_not_parse_error():
    pred = {
        "sender": "Dana Alvarez",
        "recipient": None,
        "key_points": ["pay the invoice"],
        "referenced_communications": ["prior letter"],
        "intent": "demand_payment",
    }
    out = assess_extraction_payload(pred, "correspondence")
    assert out["parse_error"] is False
    assert "key_points" in out["legacy_schema_keys"]
    assert "referenced_communications" in out["extra_schema_keys"]
    assert classify_floor_mode(out) == "schema"


def test_schema_clean_payload_adheres():
    pred = {
        "sender": "Dana Alvarez",
        "recipient": "Northwind Logistics",
        "additional_recipients": [],
        "communication_type": "demand",
        "communication_date": "2024-01-15",
        "demand_amount": None,
        "action_items": [],
        "urgency": "routine",
        "intent": "demand_payment",
        "subject_matter": "unpaid invoices",
        "keywords": ["invoice", "breach"],
    }
    out = assess_extraction_payload(pred, "correspondence")
    assert out["parse_error"] is False
    assert out["schema_valid"] is True
    assert out["schema_adherence"] == 1.0
    assert out["extra_schema_key_count"] == 0
    assert classify_floor_mode(out) == "scorer"


def test_merge_schema_adherence_rates_are_additive():
    rows = [
        assess_extraction_payload({"_parse_error": True}, "correspondence"),
        assess_extraction_payload(
            {"sender": "A", "key_points": ["x"]}, "correspondence"
        ),
        assess_extraction_payload(
            {"sender": "A", "intent": "notice"}, "correspondence"
        ),
    ]
    agg = merge_schema_adherence(rows)
    assert agg["parse_error_count"] == 1
    assert agg["parse_error_rate"] == 0.3333
    assert "n" not in agg
    assert 0.0 < agg["schema_adherence_rate"] < 1.0


def test_score_extraction_row_attaches_schema_keys_without_clobbering_overall():
    pred = {
        "sender": "Dana Alvarez",
        "intent": "demand_payment",
        "subject_matter": "unpaid invoices",
        "keywords": ["invoice"],
    }
    expected = {
        "sender": "Dana Alvarez",
        "intent": "demand_payment",
        "subject_matter": "unpaid invoices",
        "keywords": ["invoice"],
    }
    out = scoring.score_extraction_row("correspondence", pred, expected)
    assert "overall_extraction_score" in out
    assert "parse_error" in out
    assert "schema_valid" in out
    assert out["parse_error"] is False
    assert out["schema_adherence"] == 1.0
    assert isinstance(out["overall_extraction_score"], (int, float))


def test_empty_gt_scalar_is_not_a_requirement():
    """None/\"\" expected fields are skipped — correctly-empty pred does not score."""
    expected = {
        "sender": "Dana Alvarez",
        "recipient": "",
        "demand_amount": None,
        "intent": "notice",
    }
    predicted = {"sender": "Dana Alvarez", "intent": "notice"}
    result = score_extraction("correspondence", CORRESPONDENCE_TYPES, predicted, expected)
    assert set(result.field_scores) == {"sender", "intent"}
    assert result.field_scores["sender"] == 1.0
    assert result.field_scores["intent"] == 1.0
    assert result.overall_score == 1.0


def test_spurious_value_on_empty_scalar_does_not_enter_overall():
    """Prompt-discipline failure on a null/\"\" GT scalar is invisible to overall."""
    expected = {"sender": "Dana Alvarez", "recipient": "", "intent": "notice"}
    clean = {"sender": "Dana Alvarez", "intent": "notice"}
    spurious = {
        "sender": "Dana Alvarez",
        "recipient": "Invented Recipient LLC",
        "intent": "notice",
    }
    clean_s = score_extraction("correspondence", CORRESPONDENCE_TYPES, clean, expected)
    noisy_s = score_extraction("correspondence", CORRESPONDENCE_TYPES, spurious, expected)
    assert clean_s.overall_score == noisy_s.overall_score == 1.0
    assert "recipient" not in clean_s.field_scores
    assert "recipient" not in noisy_s.field_scores


def test_miss_on_populated_field_zeros_that_field():
    expected = {"sender": "Dana Alvarez", "intent": "notice"}
    predicted = {"sender": "Dana Alvarez"}  # intent missing
    result = score_extraction("correspondence", CORRESPONDENCE_TYPES, predicted, expected)
    assert result.field_scores["sender"] == 1.0
    assert result.field_scores["intent"] == 0.0
    assert result.overall_score == 0.5


def test_empty_list_both_empty_scores_one():
    expected = {"sender": "Dana Alvarez", "additional_recipients": []}
    predicted = {"sender": "Dana Alvarez", "additional_recipients": []}
    result = score_extraction("correspondence", CORRESPONDENCE_TYPES, predicted, expected)
    assert result.field_scores["additional_recipients"] == 1.0
    assert result.overall_score == 1.0


def test_spurious_items_on_empty_list_zero_that_field_like_a_miss():
    """Empty-list GT + invented items → list F1 0.0, same as missing a populated field.

    ``overall_extraction_score`` therefore punishes prompt-discipline on empty
    *lists* as hard as an extraction miss. Empty *scalars* (None/\"\") do not.
    """
    expected = {"sender": "Dana Alvarez", "additional_recipients": []}
    predicted = {
        "sender": "Dana Alvarez",
        "additional_recipients": ["cc@example.com"],
    }
    result = score_extraction("correspondence", CORRESPONDENCE_TYPES, predicted, expected)
    assert result.field_scores["additional_recipients"] == 0.0
    assert result.overall_score == 0.5


def test_extraction_f1_skips_empty_lists_so_spurious_cc_is_not_fn():
    """PRF events skip empty lists; overall still includes them (see previous test)."""
    expected = {"sender": "Dana Alvarez", "additional_recipients": []}
    predicted = {
        "sender": "Dana Alvarez",
        "additional_recipients": ["cc@example.com"],
    }
    result = score_extraction("correspondence", CORRESPONDENCE_TYPES, predicted, expected)
    prf = extraction_binary_metrics(
        expected,
        predicted,
        field_map=CORRESPONDENCE_TYPES,
        doc_class="correspondence",
        result=result,
    )
    assert prf["expected_events"] == 1  # sender only
    assert prf["tp"] == 1
    assert prf["fn"] == 0


def test_name_field_partial_credit_lifts_overall_but_not_f1_tp():
    """Typed name scoring is graded; extraction_f1 TP requires score >= 1.0."""
    expected = {"sender": "Dana Alvarez"}
    predicted = {"sender": "Dana A."}
    result = score_extraction("correspondence", CORRESPONDENCE_TYPES, predicted, expected)
    score = result.field_scores["sender"]
    assert 0.0 < score < 1.0
    prf = extraction_binary_metrics(
        expected,
        predicted,
        field_map=CORRESPONDENCE_TYPES,
        doc_class="correspondence",
        result=result,
    )
    assert prf["tp"] == 0
    assert prf["fn"] == 1
    assert prf["extraction_f1"] == 0.0
    assert result.overall_score == score


def test_single_item_entity_list_skips_hungarian():
    """SAND-019 scipy assignment is for multi-item lists; singles use a threshold compare."""
    expected = {"keywords": ["invoice"]}
    predicted = {"keywords": ["invoice"]}
    result = score_extraction("correspondence", CORRESPONDENCE_TYPES, predicted, expected)
    assert result.field_scores["keywords"] == 1.0
    assert "keywords" in result.entity_list_scores
    assert result.entity_list_scores["keywords"].matched == 1


def test_exact_match_alias_is_runner_not_scorer():
    """Isolated eval copies overall_extraction_score into scores.exact_match.

    Equality on the c8 serving JSON is therefore not evidence that partial
    credit is inactive — it is the runner alias in ``run_isolated_eval``.
    """
    pred = {"sender": "Dana Alvarez"}
    expected = {"sender": "Dana Alvarez"}
    row = scoring.score_extraction_row("correspondence", pred, expected)
    assert "exact_match" not in row
    assert row["overall_extraction_score"] == 1.0


def test_metrics_quality_picks_up_schema_rates():
    rec = {
        "profile": "modal-vllm",
        "scores": {
            "overall_extraction_score": 0.08714,
            "extraction_f1": 0.0,
            "parse_error_rate": 0.05,
            "schema_valid_rate": 0.9,
            "schema_adherence_rate": 0.9,
        },
    }
    q = metrics._score_quality(rec)
    assert q["overall_extraction_score"] == 0.08714
    assert q["parse_error_rate"] == 0.05
    assert q["schema_adherence_rate"] == 0.9
    # Pre-existing keys still present when supplied.
    rec2 = {"scores": {"exact_match": 1.0, "f1_macro": 1.0}}
    q2 = metrics._score_quality(rec2)
    assert q2["exact_match"] == 1.0
    assert "parse_error_rate" not in q2


def test_aggregate_schema_adherence_empty():
    assert scoring.aggregate_schema_adherence([]) == {}


def test_items_jsonl_roundtrip_json_string():
    dumped = json.dumps({"sender": "Dana Alvarez", "intent": "notice"})
    out = assess_extraction_payload(dumped, "correspondence")
    assert out["parse_error"] is False
    assert out["schema_valid"] is True
