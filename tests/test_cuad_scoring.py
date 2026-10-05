"""SAND-032: contract ground truth is CUAD clause spans only (``cuad_clause_labels``).

The suite field map scores document_name/parties/… which those rows never
populate, so extraction_f1 was 0 and the overall score null. The sandbox CUAD
scorer measures clause-category detection within the labeled category universe
plus value checks for the metadata categories.
"""

import json

from mailroom_sandbox.eval.cuad_scoring import score_cuad
from mailroom_sandbox.eval.scoring import score_extraction_row

GT = json.dumps({
    "Document Name": [{"start": 0, "text": "MASTER SERVICES AGREEMENT"}],
    "Parties": [{"start": 40, "text": "Acme Corp"}, {"start": 60, "text": "Beta LLC"}],
    "Governing Law": [{"start": 900, "text": "governed by the laws of the State of New York"}],
    "Anti-Assignment": [{"start": 700, "text": "may not assign"}],
    "Audit Rights": [],
    "Exclusivity": [],
})


def test_presence_f1_within_labeled_universe_and_field_mapping():
    pred = {
        "document_name": "Master Services Agreement",
        "parties": ["Acme Corp", "Beta LLC"],
        "governing_law": "New York",
        "cuad_clauses": ["Anti-Assignment: may not assign", "Exclusivity: exclusive supplier",
                         "Co-Branding: joint logos"],          # out of universe → ignored
    }
    s = score_cuad(pred, GT)
    assert (s["cuad_tp"], s["cuad_fp"], s["cuad_fn"]) == (4, 1, 0)
    assert s["cuad_presence_f1"] == 0.8889
    assert s["cuad_out_of_universe"] == 1


def test_value_checks_on_metadata_categories():
    pred = {"document_name": "Master Services Agreement", "parties": ["Acme Corp", "Gamma Inc"],
            "governing_law": "New York"}
    s = score_cuad(pred, GT)
    # document name ✓, governing law ✓ (containment), parties 1 of 2 → not exact
    assert (s["cuad_value_checked"], s["cuad_value_correct"]) == (3, 2)


def test_score_extraction_row_uses_cuad_for_contract():
    row = score_extraction_row("contract", {"cuad_clauses": ["Anti-Assignment: x"]},
                               {"cuad_clause_labels": GT})
    assert row["scoring_method"].endswith("+cuad")
    assert row["overall_extraction_score"] == row["cuad_presence_f1"]
