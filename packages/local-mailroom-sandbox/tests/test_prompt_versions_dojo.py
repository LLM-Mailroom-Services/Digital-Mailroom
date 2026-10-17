"""``prompt_versions`` against the REAL vendored dojo lineage (no stub).

The seam's one dojo-facing function resolves every eval-environment version; these
tests pin that all 40 resolve to the lineage bytes, that the sorter and every
specialist mutation are the eval-environment texts (cross-checked against a sibling
eval-environment checkout when present), and that every lineage role either maps to
a sandbox pipeline role or is refused loudly.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from llm_dojo_scoring.prompts import (
    LINEAGE_SOURCE,
    default_prompt_version,
    latest_prompt_version,
    list_prompt_versions,
    prompt_roles,
)

from mailroom_sandbox import eval_environment_lineage as lineage
from mailroom_sandbox import prompt_versions as pv
from mailroom_sandbox.prompts import load_variant

ALL = list_prompt_versions()
#: Lineage roles that are eval-environment prompts but not sandbox pipeline agents.
NOT_PIPELINE_ROLES = {"pipeline_quality", "pipeline_verdict"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sibling() -> Path | None:
    env = os.environ.get("EVAL_ENVIRONMENT_ROOT")
    candidates = [Path(env)] if env else []
    root = lineage.sibling_eval_environment_root()
    if root is not None:
        candidates.append(root)
    for cand in candidates:
        if (cand / "prompts" / "mutations.json").is_file():
            return cand
    return None


def test_lineage_is_the_expected_catalog():
    assert len(ALL) == 40 and len(prompt_roles()) == 15
    assert {v.lineage for v in ALL} == {"archived", "frozen", "mutation"}
    assert LINEAGE_SOURCE["source_repo"] == "LLM-Mailroom-Services/eval-environment"


def test_every_accepted_lineage_role_is_a_pipeline_role_and_the_rest_are_refused():
    roles = pv.pipeline_roles()
    accepted = set(prompt_roles()) - NOT_PIPELINE_ROLES
    assert accepted <= roles, f"lineage roles without a sandbox pipeline agent: {sorted(accepted - roles)}"
    assert NOT_PIPELINE_ROLES.isdisjoint(roles)
    for role in sorted(NOT_PIPELINE_ROLES):
        key = f"{role}_v1"
        with pytest.raises(pv.PromptSelectionError, match="not a pipeline agent"):
            pv.resolve_selection([key])


@pytest.mark.parametrize("v", [v for v in ALL if v.role not in NOT_PIPELINE_ROLES], ids=lambda v: v.key)
def test_every_version_resolves_to_the_lineage_bytes(v):
    key, text, sha = pv.resolve_prompt(v.role, v.key)
    assert (key, text, sha) == (v.key, v.text, v.sha256)
    assert pv.parse_selection([v.key]) == {v.role: v.key}  # the bare key infers its own role
    sel = pv.resolve_selection([v.key])
    assert sel.prompts[v.role].lineage == v.lineage and sel.keys == {v.role: v.key}


def test_a_bare_key_infers_every_lineage_role_including_hyphenated_ones():
    for v in ALL:
        assert pv.role_from_key(v.key) == v.role


@pytest.mark.parametrize("key", ["sorter_v1", "sorter_v2", "sorter_v3", "sorter_v4"])
def test_sorter_versions_are_the_eval_environment_texts(key):
    v = [x for x in ALL if x.key == key][0]
    assert pv.resolve_prompt("sorter", key)[1] == v.text
    assert "{{doc_type_descriptions}}" in v.text  # the placeholder the sorter agent fills
    # not the mailroom stem of the same name
    if key == "sorter_v1":
        assert load_variant("sorter_v1") != v.text


def test_sorter_v4_is_the_latest_and_sorter_v3_keeps_its_duplicate_block():
    assert latest_prompt_version("sorter").key == "sorter_v4"
    heading = 'CORPORATE RECORD SUBCLASS (only when doc_type is "corporate_record"):'
    assert pv.resolve_prompt("sorter", "sorter_v3")[1].count(heading) == 2
    assert pv.resolve_prompt("sorter", "sorter_v4")[1].count(heading) == 1


def test_contracts_v33_is_an_archived_rekey_of_v0_and_never_the_latest():
    v33 = pv.resolve_selection(["contracts_specialist_v33"]).prompts["contracts_specialist"]
    assert v33.lineage == "archived"
    assert latest_prompt_version("contracts_specialist").key == "contracts_specialist_v3"


SPECIALIST_MUTATIONS = [
    v.key for v in ALL if v.lineage == "mutation" and v.role.endswith("_specialist")
]


def test_all_specialist_mutations_are_covered():
    assert len(SPECIALIST_MUTATIONS) == 17
    assert {"correspondence_specialist_v3", "contracts_specialist_v2", "correspondence_specialist_v7"} <= set(
        SPECIALIST_MUTATIONS
    )


def test_default_stems_are_bytes_equal_to_their_lineage_versions():
    """No flag = today: the default stem for each catalog role IS a lineage version."""
    in_lineage = {v.key: v for v in ALL}
    for role, row in lineage.specialist_rows().items():
        key = str(row["eval_environment_key"])
        assert key in in_lineage, f"{role}: default {key} missing from the dojo lineage"
        dkey, dtext, dsha = pv.resolve_prompt(role)  # the sandbox default, never the dojo
        assert dkey == key and dtext == load_variant(str(row["sandbox_stem"]))
        assert dsha == in_lineage[key].sha256, f"{role}: stem {row['sandbox_stem']} differs from lineage {key}"
    assert pv.resolve_prompt("correspondence_specialist")[0] == "correspondence_specialist_v7"
    assert pv.resolve_prompt("corporate_records_specialist")[0] == "corporate_records_specialist_v6"


def test_sandbox_successor_keys_not_in_the_lineage_are_not_selectable():
    """insurance/merger ``*_v4`` stems claim an eval-environment key the lineage does not catalog.

    Pinned so the gap is explicit: when the dojo catalogs them this test fails and the
    stems get byte-verified instead (``--prompt <stem>`` keeps running them meanwhile).
    """
    missing = {str(r["eval_environment_key"]) for r in lineage.successor_rows()} - {v.key for v in ALL}
    assert missing == {"insurance_claims_specialist_v4", "merger_agreement_specialist_v4"}
    for key in sorted(missing):
        with pytest.raises(pv.PromptSelectionError, match="unknown eval-environment prompt version"):
            pv.resolve_selection([key])


def test_unknown_key_error_carries_the_dojo_suggestions():
    with pytest.raises(pv.PromptSelectionError, match="did you mean: sorter_v4"):
        pv.resolve_selection(["sorter_v44"])


def test_key_under_the_wrong_role_and_default_roles():
    with pytest.raises(pv.PromptSelectionError, match="belongs to role 'sorter', not 'sorter_reviewer'"):
        pv.resolve_selection(["sorter_reviewer=sorter_v4"])
    for v in ALL:
        if v.lineage == "frozen":
            assert default_prompt_version(v.role).key == v.key  # eval-env default is the frozen _v1


def test_seam_end_to_end_activates_the_real_sorter_text(monkeypatch):
    from mailroom_sandbox.prompt_registry import deactivate_runtime_overrides
    from mailroom_sandbox.runtime import resolve_mailroom_src

    monkeypatch.syspath_prepend(str(resolve_mailroom_src()))
    import langchain_agents.prompts as lc

    try:
        sel = pv.resolve_selection(["sorter_v4"])
        pv.apply_selection(sel)
        assert lc.get_prompt("sorter_v14") == sel.prompts["sorter"].text
        assert _sha(lc.get_prompt("sorter_v14")) == "89ce6efaf241199f1a35e7a38270c5ded1a5baf44b66fee5c6a0d19a0c778938"
    finally:
        deactivate_runtime_overrides()


# ── cross-check against a sibling eval-environment checkout ──────────────────
def test_lineage_matches_the_sibling_eval_environment_checkout():
    root = _sibling()
    if root is None:
        pytest.skip("no sibling eval-environment checkout (set EVAL_ENVIRONMENT_ROOT)")
    by_key = {v.key: v for v in ALL}
    mutations = json.loads((root / "prompts" / "mutations.json").read_text(encoding="utf-8"))["mutations"]
    assert mutations, "sibling mutations.json is empty"
    for m in mutations:
        v = by_key[m["key"]]
        key, text, sha = pv.resolve_prompt(v.role, v.key)
        assert text == m["text"], f"{m['key']}: lineage text differs from sibling mutations.json"
        assert sha == m["sha256"] == _sha(m["text"])
        assert v.parent == m["parent"] and v.lineage == "mutation" and v.created_at == m["created_at"]
    manifest = json.loads((root / "prompts" / "manifest.json").read_text(encoding="utf-8"))["versions"]
    for key, meta in manifest.items():
        v = by_key[key]
        assert v.sha256 == meta["sha256"] and v.chars == meta["chars"], key
    in_siblings = {m["key"] for m in mutations} | set(manifest)
    archived = {v.key for v in ALL if v.lineage == "archived"}
    assert set(by_key) - in_siblings == archived  # the only extras are the archived _v0 / _v33 files
    for key in archived:
        md = root / "prompts" / "archive" / f"{key}.md"
        assert md.is_file(), md
