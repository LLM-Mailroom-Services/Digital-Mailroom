"""SAND-032: funding projections are transparent formulas over measured unit costs."""

import pytest

from mailroom_sandbox.job.funding import (
    UnitCost,
    eval_iteration_usd,
    full_corpus_usd,
    tier_budget,
    with_contingency,
)

UNITS = {"correspondence": UnitCost("correspondence", 0.0025, 0.10),
         "contract": UnitCost("contract", 0.019, 0.20)}
ROWS = {"correspondence": 1000, "contract": 600}


def test_full_corpus_mid_is_formula():
    low, mid, high = full_corpus_usd(UNITS, ROWS, overhead_usd=0.5, seeds=1)
    assert mid == pytest.approx(1000 * 0.0025 + 600 * 0.019 + 0.5)
    assert low == pytest.approx(1000 * 0.0025 * 0.9 + 600 * 0.019 * 0.8 + 0.5)
    assert low < mid < high


def test_full_corpus_scales_with_seeds():
    _, mid1, _ = full_corpus_usd(UNITS, ROWS, overhead_usd=0.5, seeds=1)
    _, mid3, _ = full_corpus_usd(UNITS, ROWS, overhead_usd=0.5, seeds=3)
    assert mid3 == pytest.approx(3 * (mid1 - 0.5) + 0.5)


def test_missing_class_unit_cost_is_loud():
    with pytest.raises(KeyError, match="insurance_claim"):
        full_corpus_usd(UNITS, {**ROWS, "insurance_claim": 1100}, overhead_usd=0, seeds=1)


def test_eval_iteration_and_contingency():
    assert eval_iteration_usd(UNITS["contract"], 50, overhead_usd=0.1) == pytest.approx(1.05)
    assert with_contingency(100.0, 0.2) == pytest.approx(120.0)


def test_tier_budget_counts_whole_items():
    fit = tier_budget(200.0, contingency=0.2,
                      line_items={"full_corpus_pass": 25.0, "prompt_iter": 1.0})
    # 200 / 1.2 = 166.67 spendable; greedy in given order: 6 passes (150) then 16 iters
    assert fit == {"full_corpus_pass": 6, "prompt_iter": 16}


def test_tier_budget_zero_cost_item_is_rejected():
    with pytest.raises(ValueError, match="prompt_iter"):
        tier_budget(200.0, contingency=0.2, line_items={"prompt_iter": 0.0})
