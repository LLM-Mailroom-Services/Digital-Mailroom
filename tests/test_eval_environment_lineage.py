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
from mailroom_sandbox.job.specialist_posture import (
    SAND032_RUNS,
    SAND032_SORTER_RUNS,
    SPECIALIST_POSTURE,
)


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

    Intentional non-catalog pins are the only exceptions: the FP16
    correspondence diagnosis YAML, the 2xL4 AWQ correspondence follow-ups
    (production prompt is the experiment variable there), their Granite FP8
    twins (same prompt pin as each Qwen AWQ comparator), and the SAND-032
    Stage 5 MAUD merger prompt revision. The SAND-032 Stage 6 sorter row is
    not a specialist and pins no prompt stem.
    """
    production_ok = {
        "run-20-correspondence-fp16-c8",
        "run-20-correspondence-specialist-awq",
        "run-50-correspondence-specialist-awq",
        # SAND-027: Granite twins mirror the Qwen AWQ comparator's DMR-074
        # production pin for correspondence (apples-to-apples).
        "run-20-correspondence-granite",
        "run-50-correspondence-granite",
        # SAND-032: correspondence rows keep the production prompt constant
        # with the 2×L4 AWQ runs (0.23–0.25 vs simplified ~0.09).
        *(r for r in SAND032_RUNS if SPECIALIST_POSTURE[r]["agent"] == "correspondence_specialist"),
        # SAND-032 Stage 5: re-runs merger with the revised MAUD v1 prompt.
        "sand032-s5-merger50-maud",
        # SAND-040 † merger cells use the MAUD v1 prompt (the prompt is one of the variables).
        "sand40-50-merger-specialist-awq-2l4",
        "sand40-check-5-merger-specialist-awq-2l4",
        "sand40-probe-20-merger-specialist-awq-2l4-64k",
        # SAND-032 Stage 10: eval-environment v2 prompt A/B (the prompt IS the variable).
        *(r for r in SAND032_RUNS if r.startswith("sand032-s10-")),
    }
    for run_id, row in SPECIALIST_POSTURE.items():
        if "prompt_file" not in row:
            # SAND-032 Stage 6 sorter keeps the code-default sorter prompt.
            assert run_id in SAND032_SORTER_RUNS, run_id
            continue
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
    assert agents_for_variant("sorter_v1") == ["sorter"]
    assert agents_for_variant("judge_local_v0") == ["judge"]


def test_sibling_eval_environment_matches_when_present():
    root = sibling_eval_environment_root()
    if root is None:
        pytest.skip("eval-environment checkout not adjacent")
    errors = verify_sibling_catalog(root)
    assert errors == [], errors
