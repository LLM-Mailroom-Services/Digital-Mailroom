"""Prompt-registry mirror tests: roster, names, override loading."""

from __future__ import annotations

import json

import pytest

from mailroom_ui.prompt_registry import (
    PROMPT_TEMPLATES,
    load_prompt_templates,
    prompt_name,
)

# Removed from the mix per the docclass-pilot doc-class universe.
REMOVED = {"due_diligence_specialist", "compliance_specialist",
           "court_opinions_specialist"}


def test_roster_matches_upstream_prompt_templates():
    """Mirror of llm-mailroom prompt_templates() @959bb0b — all 18 agents."""
    assert len(PROMPT_TEMPLATES) == 18
    assert not (set(PROMPT_TEMPLATES) & REMOVED)
    for expected in ("sorter", "sorter_reviewer", "contracts_specialist",
                     "merger_agreement_specialist",
                     "corporate_records_specialist", "correspondence_specialist",
                     "insurance_claims_specialist", "arbiter", "boss",
                     "reporter", "judge", "judge-classification",
                     "judge-correctness", "pdf_transcriber", "image_extractor",
                     "intake", "gmail_triage", "relations"):
        assert expected in PROMPT_TEMPLATES


def test_templates_are_substantive_text():
    for agent, template in PROMPT_TEMPLATES.items():
        # reporter is procedural upstream (assembly only) — a short prompt.
        floor = 100 if agent == "reporter" else 200
        assert isinstance(template, str) and len(template) > floor, agent


def test_prompt_name_contract():
    assert prompt_name("sorter") == "mailroom-sorter"
    assert prompt_name("judge-correctness") == "mailroom-judge-correctness"


def test_override_loader(tmp_path):
    override = tmp_path / "prompts.json"
    override.write_text(json.dumps({"sorter": "CUSTOM"}))
    loaded = load_prompt_templates(str(override))
    assert loaded == {"sorter": "CUSTOM"}


def test_override_loader_rejects_bad_shape(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"sorter": 42}))
    with pytest.raises(ValueError):
        load_prompt_templates(str(bad))


def test_schema_roster_consistency():
    """The schema's specialist mapping must only reference agents on the
    live roster, and every specialist has a vendored production prompt
    (compliance_specialist is removed upstream; the docclass arm was deleted
    from llm-mailroom, its mirror is kept for llm-entity-extraction)."""
    from mailroom_ui.docclass_prompts import DOCLASS_PROMPT_VERSIONS
    from mailroom_ui.pipeline_schema import AGENTS, SPECIALIST_BY_DOC_CLASS

    for doc_class, specialist in SPECIALIST_BY_DOC_CLASS.items():
        assert specialist in AGENTS, f"{doc_class} -> {specialist} missing from AGENTS"
        assert specialist in PROMPT_TEMPLATES, f"{doc_class} -> {specialist} has no prompt"
    assert DOCLASS_PROMPT_VERSIONS  # entity-extraction mirror still vendored


def test_docclass_registry_shape():
    """Vendored docclass mirror, resynced verbatim from
    llm-entity-extraction src/prompts_docclass.py (DMR-016): KANBAN-090
    family + pilot universe + HUB-041 mailroom v8 sorter + KANBAN-101/103
    specialists + DMR-015 reviewer v2 + DMR-015 mailroom_prompts lineage
    (74)."""
    from mailroom_ui.docclass_prompts import DOCLASS_PROMPT_VERSIONS, load_docclass_templates

    assert len(DOCLASS_PROMPT_VERSIONS) == 74
    assert "sorter_mailroom_pilot_v0" in DOCLASS_PROMPT_VERSIONS
    for key, template in DOCLASS_PROMPT_VERSIONS.items():
        assert isinstance(template, str) and len(template) > 200, key
    assert load_docclass_templates() == DOCLASS_PROMPT_VERSIONS


def test_docclass_override_loader(tmp_path):
    from mailroom_ui.docclass_prompts import load_docclass_templates

    override = tmp_path / "docclass.json"
    override.write_text(json.dumps({"sorter_docclass_v0": "CUSTOM"}))
    assert load_docclass_templates(str(override)) == {"sorter_docclass_v0": "CUSTOM"}
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"sorter_docclass_v0": 42}))
    with pytest.raises(ValueError):
        load_docclass_templates(str(bad))
