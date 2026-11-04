"""Documents routed to human review: the same keys from pipeline, sorter and reviewer runs."""

from __future__ import annotations

from mailroom_sandbox.eval import human_review as hr


def test_pipeline_counts_review_stage():
    out = hr.for_pipeline([{"stage": "review", "doc_type": "contract"}, {"stage": "archived", "doc_type": "contract"},
                           {"stage": "review", "doc_type": None}])
    assert out["routed_to_human_review"] == 2 and out["routed_to_human_review_rate"] == round(2 / 3, 6)
    assert out["routed_to_human_review_by_class"]["contract"] == {"routed": 1, "n": 2, "rate": 0.5}
    assert out["routed_to_human_review_basis"] == "pipeline"


def test_sorter_routes_unknown_missing_and_below_high_band():
    assert hr.sorter_routes_to_human({"doc_type": "unknown", "confidence": 1.0})
    assert hr.sorter_routes_to_human({"doc_type": "contract"})
    assert hr.sorter_routes_to_human({"doc_type": "contract", "confidence": 0.5})
    assert not hr.sorter_routes_to_human({"doc_type": "contract", "confidence": 1.0})
    assert hr.for_isolated("sorter", [{"doc_type": "contract", "confidence": 1.0}])["routed_to_human_review"] == 0


def test_reviewer_verdict_and_cutoffs():
    human = {"doc_type": "contract", "confidence": 0.0, "route_to_human": True}
    sure = {"doc_type": "contract", "confidence": 0.9, "route_to_human": False}
    assert hr.reviewer_routes_to_human(human)
    assert not hr.reviewer_routes_to_human(sure)
    assert not hr.reviewer_routes_to_human(sure, {"contract": 0.78})
    assert hr.reviewer_routes_to_human(sure, {"contract": 0.95})
    assert hr.reviewer_routes_to_human(sure, {"merger_agreement": 0.99})  # no cutoff for its class
    out = hr.for_isolated("sorter_reviewer", [human, sure])
    assert out["routed_to_human_review"] == 1 and out["routed_to_human_review_basis"] == "reviewer"
    assert hr.for_isolated("contract_extractor", [sure]) is None
