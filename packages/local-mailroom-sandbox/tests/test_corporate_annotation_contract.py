"""SAND-059: sandbox preserves dojo's annotated corporate scoring contract."""
import json
import pytest
from mailroom_sandbox.eval.scoring import score_extraction_row

@pytest.mark.parametrize("field,value,status,precision", [
    ("certifying_officer", "Bob", "populated", 1.0),
    ("certifying_officer", "", "schema_documented_absence", 0.6667),
    ("entity_name", None, "schema_documented_absence", 0.6667),
])
def test_annotated_error_survives_adapter(field, value, status, precision):
    """Two correct semantic fields cannot conceal a third annotated error."""
    expected = {"intent": "governance_rules", "subject_matter": "Bylaws", field: value,
                "gt_presence": json.dumps({field: status})}
    prediction = {"intent": "governance_rules", "subject_matter": "Bylaws", field: "Alice"}
    result = score_extraction_row("corporate_record", prediction, expected, expected_subclass="bylaws")
    assert result["extraction_f1"] == pytest.approx(0.8)
    assert result["extraction_precision"] == pytest.approx(precision)
    assert field not in result["unlabeled_fields"]
    assert expected[field] == value


def test_extension_schema_uses_own_subclass():
    """A bylaws officer is valid; a power-of-attorney principal is extra."""
    result = score_extraction_row("corporate_record", {
        "entity_name": "Example LLC", "record_type": "bylaws", "intent": "governance_rules",
        "subject_matter": "Bylaws", "keywords": ["bylaws"],
        "certifying_officer": "Alice", "principal": "Wrong subclass",
    }, {"intent": "governance_rules", "certifying_officer": "Alice"}, expected_subclass="bylaws")
    assert "certifying_officer" not in result["extra_schema_keys"]
    assert "principal" in result["extra_schema_keys"]


def test_prediction_cannot_replace_ground_truth_presence():
    """Prediction metadata is untrusted and cannot erase an annotated miss."""
    expected = {"intent": "governance_rules", "subject_matter": "Bylaws",
                "certifying_officer": "Bob",
                "gt_presence": json.dumps({"certifying_officer": "populated"})}
    prediction = {"intent": "governance_rules", "subject_matter": "Bylaws",
                  "certifying_officer": "Alice"}
    baseline = score_extraction_row("corporate_record", prediction, expected, expected_subclass="bylaws")
    prediction["gt_presence"] = json.dumps({"certifying_officer": "not_applicable"})
    spoofed = score_extraction_row("corporate_record", prediction, expected, expected_subclass="bylaws")
    assert spoofed["extraction_f1"] == baseline["extraction_f1"] == pytest.approx(0.8)
    assert json.loads(expected["gt_presence"])["certifying_officer"] == "populated"


@pytest.mark.parametrize("subclass_kwargs", [{}, {"expected_subclass": "bylaws"}, {"doc_subclass": "bylaws"}])
@pytest.mark.parametrize("pending_annotation", [False, True])
def test_optional_subclass_uses_canonical_aligned_corporate_metrics(subclass_kwargs, pending_annotation):
    from llm_dojo_scoring import suite_for_doc_type

    expected = {"intent": "governance_rules", "subject_matter": "Bylaws"}
    if pending_annotation:
        expected.update(certifying_officer="Bob",
                        gt_presence=json.dumps({"certifying_officer": "pending_annotation"}))
    prediction = {"intent": "governance_rules", "subject_matter": "Bylaws",
                  "entity_name": "Acme", "certifying_officer": "Alice"}
    sub = subclass_kwargs.get("doc_subclass") or subclass_kwargs.get("expected_subclass")
    canonical = suite_for_doc_type("corporate_record").score(
        expected, prediction, detailed=True, **({"doc_subclass": sub} if sub else {}))
    result = score_extraction_row("corporate_record", prediction, expected, **subclass_kwargs)
    # Neither missing nor pending entity labels can turn into false positives.
    assert result["extraction_f1"] == canonical["extraction_f1"] == 1.0
    assert result["extraction_precision"] == canonical["extraction_precision"] == 1.0
    assert set(result["unlabeled_fields"]) == set(canonical["unlabeled_fields"])
