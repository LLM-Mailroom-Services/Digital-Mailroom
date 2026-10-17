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


# ---- SAND-042 repaired specialists frozen as eval-environment v4 ----------

SAND42_SUCCESSORS = {
    "insurance_claims_specialist_simplified_v2": (
        "insurance_claims_specialist",
        "insurance_claims_specialist_v4",
        "insurance_claims_specialist_v3",
    ),
    "merger_agreement_specialist_maud_v2": (
        "merger_agreement_specialist",
        "merger_agreement_specialist_v4",
        "merger_agreement_specialist_v3",
    ),
}


def test_sand42_repaired_stems_are_frozen_successors():
    from mailroom_sandbox.eval_environment_lineage import successor_rows

    rows = {r["sandbox_stem"]: r for r in successor_rows()}
    assert set(rows) == set(SAND42_SUCCESSORS)
    for stem, (agent, key, parent) in SAND42_SUCCESSORS.items():
        row = rows[stem]
        assert (row["agent"], row["eval_environment_key"], row["parent_key"]) == (agent, key, parent)


@pytest.mark.parametrize("stem", sorted(SAND42_SUCCESSORS))
def test_successor_stem_resolves_to_its_frozen_key(stem):
    from mailroom_sandbox.eval_environment_lineage import (
        eval_environment_key_for,
        lookup,
    )

    agent, key, _ = SAND42_SUCCESSORS[stem]
    assert eval_environment_key_for(stem=stem) == key
    assert lookup(key=key)["sandbox_stem"] == stem
    assert agents_for_variant(stem) == [agent]
    # Freezing a successor does not move the default v1 pin.
    assert default_prompt_variant(agent) != stem
    assert eval_environment_key_for(agent=agent) == agent + "_v1"


@pytest.mark.parametrize("stem", sorted(SAND42_SUCCESSORS))
def test_successor_drift_is_refused(stem):
    from mailroom_sandbox.eval_environment_lineage import assert_catalog_sha
    from mailroom_sandbox.paths import prompts_dir

    agent = SAND42_SUCCESSORS[stem][0]
    text = (prompts_dir() / f"{stem}.txt").read_text(encoding="utf-8")
    assert_catalog_sha(agent, stem, text)
    with pytest.raises(ValueError, match="lineage drift"):
        assert_catalog_sha(agent, stem, text + " ")


def test_sibling_successor_check_reads_mutations_json(tmp_path):
    import json

    from mailroom_sandbox.eval_environment_lineage import (
        _verify_sibling_successors,
        successor_rows,
    )
    from mailroom_sandbox.paths import prompts_dir

    rows = successor_rows()
    (tmp_path / "prompts").mkdir()
    mutations = [
        {
            "key": r["eval_environment_key"],
            "parent": r["parent_key"],
            "sha256": r["sha256"],
            "text": (prompts_dir() / f"{r['sandbox_stem']}.txt").read_text(encoding="utf-8"),
        }
        for r in rows
    ]
    path = tmp_path / "prompts" / "mutations.json"
    path.write_text(json.dumps({"mutations": mutations}), encoding="utf-8")
    assert _verify_sibling_successors(tmp_path) == []

    mutations[0]["sha256"] = "0" * 64
    path.write_text(json.dumps({"mutations": mutations[:1]}), encoding="utf-8")
    errors = _verify_sibling_successors(tmp_path)
    assert any("sha256" in e for e in errors)
    assert any("missing" in e for e in errors)


def test_sibling_successor_check_hashes_the_mutation_text(tmp_path):
    """An edited mutation text whose recorded sha256 was left alone must fail."""
    import json

    from mailroom_sandbox.eval_environment_lineage import (
        _verify_sibling_successors,
        successor_rows,
    )

    (tmp_path / "prompts").mkdir()
    mutations = [
        {
            "key": r["eval_environment_key"],
            "parent": r["parent_key"],
            "sha256": r["sha256"],
            "text": "edited after the freeze",
        }
        for r in successor_rows()
    ]
    (tmp_path / "prompts" / "mutations.json").write_text(
        json.dumps({"mutations": mutations}), encoding="utf-8"
    )
    errors = _verify_sibling_successors(tmp_path)
    assert len(errors) == len(mutations)
    assert all("text sha256" in e for e in errors)


# ---- dojo #30: corrected v1 specialist stems (eval-environment *_v7 / *_v6) --

# trailing-newline-normalized sha256 of the dojo `production_prompts` text
CORRECTED = {
    "correspondence_specialist": (
        "correspondence_specialist_v7",
        "correspondence_specialist_v6",
        "correspondence_specialist_v1",
        "correspondence_specialist_simplified",
        "2b0b81ff98920b9207627707443e2b023db39212fda5bdcba7bfbded39fa38b6",
        "eab63b5afd29906b1ad3aca2d7698bf5c15d4b7f4ce9ade3b744be535d18d4f3",
        6061,
    ),
    "corporate_records_specialist": (
        "corporate_records_specialist_v6",
        "corporate_records_specialist_v5",
        "corporate_records_specialist_v1",
        "corporate_records_specialist_simplified",
        "fe13501f667fcd9f64f7dfbf8b0f124f81d9dd039f4109288b43f106f82b1399",
        "484e64dd847b7bb35afebca74edc1fb6c381f0f7d5e9367ad8673bec0b8af45c",
        5801,
    ),
}


@pytest.mark.parametrize("agent", sorted(CORRECTED))
def test_corrected_stem_is_the_dojo_production_prompts_text(agent):
    import hashlib

    from llm_dojo_scoring.prompts import get_prompt
    from mailroom_sandbox.paths import prompts_dir

    *_, stem, sha, _old_sha, _old_chars = CORRECTED[agent]
    text = get_prompt(agent, "production_prompts").text  # loader strips the provenance comment
    body = text if text.endswith("\n") else text + "\n"
    on_disk = (prompts_dir() / f"{stem}.txt").read_bytes()
    assert on_disk == body.encode("utf-8")  # same body, no provenance comment
    assert not on_disk.lstrip().startswith(b"<!--")
    assert hashlib.sha256(on_disk).hexdigest() == sha


@pytest.mark.parametrize("agent", sorted(CORRECTED))
def test_refrozen_row_names_the_mutation_and_keeps_v1_history(agent):
    from mailroom_sandbox.eval_environment_lineage import (
        eval_environment_key_for,
        specialist_rows,
        superseded_rows,
    )
    from mailroom_sandbox.paths import prompts_dir

    key, parent, old_key, stem, sha, old_sha, old_chars = CORRECTED[agent]
    row = specialist_rows()[agent]
    assert (row["eval_environment_key"], row["parent_key"], row["sha256"]) == (key, parent, sha)
    assert row["chars"] == len((prompts_dir() / f"{stem}.txt").read_text(encoding="utf-8"))
    assert row["refrozen_at"]
    assert eval_environment_key_for(agent=agent) == key
    assert not key.endswith("_v2")
    old = row["superseded"]
    assert (old["eval_environment_key"], old["sha256"], old["chars"]) == (old_key, old_sha, old_chars)
    # the original freeze stamp is kept, not overwritten by the re-freeze
    assert old["frozen_at"] == "2026-09-26T05:09:29+00:00"
    assert any(r["agent"] == agent and r["eval_environment_key"] == old_key for r in superseded_rows())


def test_untouched_v1_rows_keep_their_original_identity():
    from mailroom_sandbox.eval_environment_lineage import specialist_rows

    rows = specialist_rows()
    for agent in set(rows) - set(CORRECTED):
        assert rows[agent]["eval_environment_key"] == f"{agent}_v1"
        assert "superseded" not in rows[agent]


def test_sibling_check_verifies_refrozen_rows_and_superseded_v1(tmp_path):
    import json

    from mailroom_sandbox.eval_environment_lineage import specialist_rows, verify_sibling_catalog
    from mailroom_sandbox.paths import prompts_dir

    rows = specialist_rows()
    (tmp_path / "prompts").mkdir()
    versions = {}
    mutations = []
    for agent, row in rows.items():
        if row.get("parent_key"):
            old = row["superseded"]
            versions[old["eval_environment_key"]] = {"sha256": old["sha256"]}
            mutations.append(
                {
                    "key": row["eval_environment_key"],
                    "parent": row["parent_key"],
                    "sha256": row["sha256"],
                    "text": (prompts_dir() / f"{row['sandbox_stem']}.txt").read_text(encoding="utf-8"),
                }
            )
        else:
            key = row["eval_environment_key"]
            versions[key] = {"sha256": row["sha256"]}
            body = (prompts_dir() / f"{row['sandbox_stem']}.txt").read_text(encoding="utf-8")
            (tmp_path / "prompts" / f"{key}.md").write_text(body, encoding="utf-8")
    from mailroom_sandbox.eval_environment_lineage import successor_rows

    for r in successor_rows():
        mutations.append(
            {
                "key": r["eval_environment_key"],
                "parent": r["parent_key"],
                "sha256": r["sha256"],
                "text": (prompts_dir() / f"{r['sandbox_stem']}.txt").read_text(encoding="utf-8"),
            }
        )
    (tmp_path / "prompts" / "manifest.json").write_text(json.dumps({"versions": versions}), encoding="utf-8")
    (tmp_path / "prompts" / "mutations.json").write_text(json.dumps({"mutations": mutations}), encoding="utf-8")
    assert verify_sibling_catalog(tmp_path) == []

    versions["corporate_records_specialist_v1"]["sha256"] = "0" * 64
    (tmp_path / "prompts" / "manifest.json").write_text(json.dumps({"versions": versions}), encoding="utf-8")
    assert any("superseded corporate_records_specialist_v1" in e for e in verify_sibling_catalog(tmp_path))
