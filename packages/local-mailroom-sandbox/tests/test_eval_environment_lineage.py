"""eval-environment frozen v1 catalog lock (SAND-027-3)."""

from __future__ import annotations

import pytest

from mailroom_sandbox.eval_environment_lineage import (
    agents_for_variant,
    catalog_agents,
    default_prompt_variant,
    sibling_eval_environment_root,
    verify_local_catalog,
    verify_sibling_catalog,
)
from mailroom_sandbox.job.specialist_posture import SPECIALIST_POSTURE


def test_local_stems_match_eval_environment_catalog():
    errors = verify_local_catalog()
    assert errors == [], errors


def test_catalog_covers_five_live_specialists():
    assert set(catalog_agents()) == {
        "contracts_specialist",
        "corporate_records_specialist",
        "correspondence_specialist",
        "insurance_claims_specialist",
        "merger_agreement_specialist",
    }


def test_specialist_posture_pins_catalog_stems():
    """Modal run-30 / run-20 specialist YAMLs must pin the frozen v1 sandbox stems.

    Isolation twins that intentionally use vendor production (the FP16
    correspondence diagnosis YAML) are the only exception.
    """
    production_ok = {"run-20-correspondence-fp16-c8"}
    for run_id, row in SPECIALIST_POSTURE.items():
        agent = row["agent"]
        stem = row["prompt_file"]
        catalog_stem = default_prompt_variant(agent)
        if run_id in production_ok:
            assert stem != catalog_stem
            continue
        assert stem == catalog_stem, f"{run_id} pins {stem!r}, catalog wants {catalog_stem!r}"


def test_agents_for_variant_maps_catalog_and_local_v0():
    assert agents_for_variant("correspondence_specialist_simplified") == [
        "correspondence_specialist"
    ]
    assert agents_for_variant("contracts_specialist_v33_simplified") == [
        "contracts_specialist"
    ]
    assert agents_for_variant("sorter_local_v0") == ["sorter", "sorter_reviewer"]
    assert agents_for_variant("judge_local_v0") == ["judge"]


def test_sibling_eval_environment_matches_when_present():
    root = sibling_eval_environment_root()
    if root is None:
        pytest.skip("eval-environment checkout not adjacent")
    errors = verify_sibling_catalog(root)
    assert errors == [], errors
