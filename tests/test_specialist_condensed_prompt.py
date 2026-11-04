"""Specialist-condensed lineage: budgeted prompts that keep each class's vocabulary and rules."""
from __future__ import annotations

import sys

import pytest
import yaml

from mailroom_sandbox.paths import prompts_dir, repo_root

LINEAGE = yaml.safe_load((prompts_dir() / "specialist_condensed_lineage.yaml").read_text(encoding="utf-8"))
BUDGET = LINEAGE["budget_chars"]
BUDGET_BY_AGENT = LINEAGE.get("budget_chars_by_agent") or {}
FROZEN = {"insurance_claims_specialist": "insurance_claims_specialist_simplified",
          "correspondence_specialist": "correspondence_specialist_simplified",
          "corporate_records_specialist": "corporate_records_specialist_subclass_v2"}
# Tokens and rules every version must keep (the schema vocabulary the dojo scores against).
REQUIRED = {
    "insurance_claims_specialist": ("claim_data_record", "Notice ID", "Fill Reference", "Total drug cost",
                                    "bare JSON number", "Claim total paid by Medicare", "claim_filing"),
    "correspondence_specialist": ("payment_demand", "meeting_invite", "press_communication", "date SENT",
                                  "attorney_demand", "never null"),
    "corporate_records_specialist": ("governance_rules", "corporate_action_approval", "entity_formation",
                                     "authority_delegation", "investor_rights", "never an SEC form", "owning company"),
}
VERSIONS = [(agent, v["version"]) for agent, row in LINEAGE["agents"].items() for v in row["versions"]]


# Templates every insurance version from v3 on must brief (the six corpus layouts).
INSURANCE_TEMPLATES = ("MEDICARE SUMMARY NOTICE", "PRESCRIPTION DRUG BENEFIT", "AUTOMOBILE CLAIMS DECISION LETTER",
                       "CLAIM RECORD EXTRACT", "FIRST NOTICE OF LOSS")


def test_insurance_frontrunner_briefs_every_template():
    front = LINEAGE["agents"]["insurance_claims_specialist"]["frontrunner"]
    if int(front.rsplit("_v", 1)[1]) < 3:
        pytest.skip("frontrunner predates the per-template brief")
    text = (prompts_dir() / f"{front}.txt").read_text(encoding="utf-8")
    for heading in INSURANCE_TEMPLATES:
        assert heading in text, heading


@pytest.mark.parametrize("agent,version", VERSIONS)
def test_version_file_budget_and_vocabulary(agent, version):
    text = (prompts_dir() / f"{version}.txt").read_text(encoding="utf-8")
    assert version.startswith(f"{agent}_condensed_v")
    budget = BUDGET_BY_AGENT.get(agent, BUDGET)
    assert len(text) <= budget, f"{version}: {len(text)} chars > {budget}"
    frozen = len((prompts_dir() / f"{FROZEN[agent]}.txt").read_text(encoding="utf-8"))
    assert len(text) < (frozen / 2 if agent not in BUDGET_BY_AGENT else frozen)
    for clause in REQUIRED[agent]:
        assert clause in text, f"{version} dropped {clause!r}"
    assert "sorter handed you" not in text and "no subclass is given" in text
    assert "Output JSON only" in text


def test_every_condensed_file_is_in_the_lineage():
    listed = {v for _, v in VERSIONS}
    on_disk = {p.stem for p in prompts_dir().glob("*_specialist_condensed_v*.txt")}
    assert on_disk == listed
    for agent, row in LINEAGE["agents"].items():
        assert row["frontrunner"] in listed


def test_compare_verdict_rule():
    sys.path.insert(0, str(repo_root() / "scripts"))
    import compare_specialist_prompt as cmp

    item = lambda s, err=False: {"ok": True, "score": {"overall_extraction_score": s}, "pred": {"_parse_error": err}}  # noqa: E731
    ref = {"a": item(0.8), "b": item(0.6)}
    assert cmp.compare(ref, {"a": item(0.79), "b": item(0.6)}, max_mean_drop=0.02)["verdict"] == "adopt"
    assert cmp.compare(ref, {"a": item(0.5), "b": item(0.6)}, max_mean_drop=0.02)["verdict"] == "reject"
    assert cmp.compare(ref, {"a": item(0.9), "b": item(0.6, err=True)}, max_mean_drop=0.02)["verdict"] == "reject"
    # A partial candidate (one reference document missing) is rejected, however good the rest is.
    partial = cmp.compare(ref, {"a": item(0.95)}, max_mean_drop=0.02)
    assert partial["verdict"] == "reject" and partial["missing_from_candidate"] == 1
