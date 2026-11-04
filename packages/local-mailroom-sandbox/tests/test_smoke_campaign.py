"""Smoke campaign score gates."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("smoke_campaign", Path(__file__).resolve().parents[1] / "scripts/smoke_campaign.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
_check = module._check


@pytest.mark.parametrize("score", [None, 0.999, 0.9999, 1.001, float("nan")])
def test_smoke_requires_exact_perfect_scores(score):
    report = {"complete": True, "paired_dataset_bytes": True, "runs": [{
        "run_id": "run", "stored_score_means": {"overall_extraction_score": score, "class_correct": score},
    }]}
    errors = _check("pipeline", report)
    assert len(errors) == 2
    assert "oracle extraction headline" in errors[0]
    assert "class_correct" in errors[1]
    report["runs"][0]["stored_score_means"] = {"overall_extraction_score": 1.0, "class_correct": 1.0}
    assert _check("pipeline", report) == []
