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


def test_roster_matches_pilot_universe():
    assert len(PROMPT_TEMPLATES) == 13
    assert not (set(PROMPT_TEMPLATES) & REMOVED)
    for expected in ("sorter", "sorter_reviewer", "contracts_specialist",
                     "corporate_records_specialist", "correspondence_specialist",
                     "insurance_claims_specialist", "arbiter", "boss",
                     "reporter", "judge", "judge-classification",
                     "judge-correctness", "pdf_transcriber"):
        assert expected in PROMPT_TEMPLATES


def test_templates_are_substantive_text():
    for agent, template in PROMPT_TEMPLATES.items():
        assert isinstance(template, str) and len(template) > 200, agent


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
    live roster. Extractors may have a vendored production prompt, a
    docclass-arm prompt, or both (compliance_specialist is live again in
    dojo 0.9.0 / mailroom #30; its production prompt_templates catch-up
    is still on the pipeline)."""
    from mailroom_ui.docclass_prompts import DOCLASS_PROMPT_VERSIONS
    from mailroom_ui.pipeline_schema import AGENTS, SPECIALIST_BY_DOC_CLASS

    for doc_class, specialist in SPECIALIST_BY_DOC_CLASS.items():
        assert specialist in AGENTS, f"{doc_class} -> {specialist} missing from AGENTS"
        has_live = specialist in PROMPT_TEMPLATES
        has_docclass = any(k.startswith(specialist) for k in DOCLASS_PROMPT_VERSIONS)
        assert has_live or has_docclass, f"{doc_class} -> {specialist} has no prompt"


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
