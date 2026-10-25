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


def test_chunk_merged_answers_are_not_first_wins():
    """SAND-042 RCA: the preamble chunk's guess must not beat the clause chunk."""
    from mailroom_sandbox.eval.maud_scoring import score_maud

    gt = {"No-Shop": {"answer": "Yes"}, "Breach of No Shop": {"answer": "No"}}
    pred = {"maud_clauses": [
        "No-Shop: not specified", "Breach of No Shop: Yes",  # chunk 1
        "No-Shop: Yes", "Breach of No Shop: No",             # chunk 4
    ]}
    out = score_maud(pred, gt)
    assert out["maud_correct"] == 1          # No-Shop recovered
    assert out["maud_conflicts"] == 1        # Breach of No Shop: Yes vs No
    assert out["maud_accuracy"] == 0.5


def test_multi_class_answer_order_insensitive_and_null_mapping():
    from mailroom_sandbox.eval.maud_scoring import score_maud

    q = "Accuracy of Target R&W Closing Condition"
    gt = {q: {"answer": "General R&Ws, Capitalization R&Ws"}, "No-Shop": {"answer": "Yes"}}
    out = score_maud({"maud_clauses": {q: "Capitalization R&Ws, General R&Ws", "No-Shop": None}}, gt)
    assert out["maud_correct"] == 1
    assert out["maud_answered"] == 1


def test_unordered_match_only_for_multi_select_questions():
    from mailroom_sandbox.eval.maud_scoring import MULTI_CLASS_QUESTIONS, same_answer

    rw = "Accuracy of Target R&W Closing Condition"
    assert rw in MULTI_CLASS_QUESTIONS
    assert "No-Shop" not in MULTI_CLASS_QUESTIONS
    assert same_answer("Capitalization R&Ws, General R&Ws", "General R&Ws, Capitalization R&Ws", rw)
    # order is meaningful for a single-answer question
    assert not same_answer("A, then B", "then B, A", "No-Shop")
    assert not same_answer("A, then B", "then B, A")


def test_catalog_none_is_an_answer_not_a_placeholder():
    from mailroom_sandbox.eval.maud_scoring import is_non_answer, score_maud

    cor = "Agreement provides for matching rights in connection with COR"
    assert not is_non_answer("None", cor)
    assert is_non_answer("None", "No-Shop")
    assert is_non_answer("not specified", cor)
    # a chunk saying "None" vs one saying "3 business days" is a real conflict
    gt = {cor: {"answer": "None"}}
    out = score_maud({"maud_clauses": [f"{cor}: None", f"{cor}: 3 business days"]}, gt)
    assert out["maud_conflicts"] == 1 and out["maud_correct"] == 0
    out = score_maud({"maud_clauses": [f"{cor}: None"]}, gt)
    assert out["maud_correct"] == 1 and out["maud_answered"] == 1
