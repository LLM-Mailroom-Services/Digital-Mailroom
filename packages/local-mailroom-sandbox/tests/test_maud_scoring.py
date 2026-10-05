"""SAND-032: merger_agreement ground truth is MAUD question→answer labels only.

The suite field map scores document_name/parties/… which the Hub rows never
populate, so extraction_f1 was 0 by construction. The sandbox MAUD scorer
compares the specialist's ``maud_clauses`` ('<Question>: <Answer>') against
``expected_fields.maud_clause_labels``.
"""

import json

from mailroom_sandbox.eval.maud_scoring import parse_maud_answers, score_maud
from mailroom_sandbox.eval.scoring import score_extraction_row

GT = json.dumps({
    "Type of Consideration": {"answer": "All Cash", "valid_classes": ["All Cash", "All Stock"]},
    "No-Shop": {"answer": "Yes", "valid_classes": ["No", "Yes"]},
    "Fiduciary exception:  Board determination (no-shop)": {
        "answer": "Superior Offer, or Acquisition Proposal reasonably likely/expected to result in a Superior Offer",
        "valid_classes": [],
    },
    "MAE Definition": {"answer": "No", "valid_classes": ["No", "Yes"]},
})


def test_parses_question_names_containing_colons():
    got = parse_maud_answers(
        {"maud_clauses": ["Fiduciary exception: Board determination (no-shop): Superior Offer, or "
                          "Acquisition Proposal reasonably likely/expected to result in a Superior Offer"]},
        questions=list(json.loads(GT)),
    )
    assert got == {"Fiduciary exception:  Board determination (no-shop)":
                   "Superior Offer, or Acquisition Proposal reasonably likely/expected to result in a Superior Offer"}


def test_merger_consideration_enum_backfills_type_of_consideration():
    got = parse_maud_answers({"maud_clauses": [], "merger_consideration": "all_cash"},
                             questions=["Type of Consideration"])
    assert got == {"Type of Consideration": "All Cash"}


def test_score_is_accuracy_over_labeled_questions_with_normalization():
    pred = {"maud_clauses": ["Type of Consideration: all cash", "No-Shop: yes",
                             "MAE Definition: not specified"]}
    s = score_maud(pred, GT)
    assert s["maud_questions"] == 4
    assert s["maud_correct"] == 2
    assert s["maud_answered"] == 2          # 'not specified' is a non-answer
    assert s["maud_accuracy"] == 0.5
    assert s["maud_precision_answered"] == 1.0


def test_score_extraction_row_uses_maud_for_merger():
    row = score_extraction_row(
        "merger_agreement",
        {"document_name": "AGREEMENT AND PLAN OF MERGER", "maud_clauses": ["No-Shop: Yes"]},
        {"maud_clause_labels": GT, "label_evidence": "MAUD-annotated clauses: …"},
    )
    assert row["overall_extraction_score"] == 0.25
    assert row["maud_correct"] == 1
    assert row["scoring_method"] == "suite+maud"


def test_echoed_question_name_is_a_non_answer_and_enum_backfills():
    pred = {"maud_clauses": ["Type of Consideration: Type of Consideration", "No-Shop: No-Shop"],
            "merger_consideration": "all_cash"}
    s = score_maud(pred, GT)
    assert s["maud_answered"] == 1 and s["maud_correct"] == 1   # only the enum backfill counts


def test_corpus_typo_fundermental_matches_fundamental():
    gt = json.dumps({"Accuracy of Target R&W Closing Condition":
                     {"answer": "General R&Ws, Fundermental/Special R&Ws", "valid_classes": []}})
    s = score_maud({"maud_clauses": ["Accuracy of Target R&W Closing Condition: "
                                     "General R&Ws, fundamental/Special R&Ws"]}, gt)
    assert s["maud_correct"] == 1


def test_clean_subset_counts_only_single_subquestion_items():
    # No-Shop collapses several MAUD sub-questions in the corpus; Type of Consideration does not.
    s = score_maud({"maud_clauses": ["Type of Consideration: All Cash", "No-Shop: Yes"]}, GT)
    assert (s["maud_clean_questions"], s["maud_clean_correct"]) == (1, 1)
    assert s["maud_clean_accuracy"] == 1.0
