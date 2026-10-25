"""SAND-032: the isolated sorter stored SorterAgent.classify's tuple as a string doc_type."""

from mailroom_sandbox.eval.agents import _score_class


def test_score_class_reads_stringified_classify_tuple():
    pred = {"doc_type": "('corporate_record', None, 0.95, \"lists subsidiaries\")"}
    s = _score_class({"expected_doc_class": "corporate_record"}, pred)
    assert s["match"] == 1.0 and s["predicted"] == "corporate_record"


def test_score_class_plain_dict_unchanged():
    assert _score_class({"expected_doc_class": "contract"}, {"doc_type": "contract"})["match"] == 1.0
