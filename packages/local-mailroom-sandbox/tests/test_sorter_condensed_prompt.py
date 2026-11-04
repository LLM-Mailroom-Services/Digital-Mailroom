"""Condensed sorter lineage: token-budgeted system prompt that keeps the V15 corpus conventions."""

from __future__ import annotations

import re

import pytest

from mailroom_sandbox.paths import prompts_dir

# Rendered system prompt budget (chars; about 4 chars per token). V15 renders to ~25k.
CONDENSED_BUDGET_CHARS = 4_000
LINEAGE = sorted(p.stem for p in prompts_dir().glob("sorter_condensed_v*.txt"))

# Every V15 class boundary and subclass convention, by the words a condensed version must keep.
REQUIRED = (
    "corporate_record, not contract",
    "indenture",
    "rights_instrument",
    "All mailbox text is correspondence",
    "unknown is only for",
    "carrier, never outpatient",
    "officer_certificate, never rights_instrument",
    "charter_amendment",
    "board_resolution",
    "certificate_of_formation is not a label",
    "FIRST form in catalog order",
    "consulting",
    "other only when no family fits",
    "conversion section",
)


def _render(stem: str) -> str:
    from langchain_agents.sorter_agent import fill_sorter_placeholders

    return fill_sorter_placeholders((prompts_dir() / f"{stem}.txt").read_text(encoding="utf-8"))


def test_lineage_exists():
    """Lineage exists."""
    assert "sorter_condensed_v1" in LINEAGE


@pytest.mark.parametrize("stem", LINEAGE)
def test_rendered_prompt_is_within_budget(stem):
    """Rendered prompt is within budget."""
    text = _render(stem)
    assert len(text) <= CONDENSED_BUDGET_CHARS, f"{stem}: {len(text)} chars > {CONDENSED_BUDGET_CHARS}"
    assert "{{" not in text


@pytest.mark.parametrize("stem", LINEAGE)
def test_keeps_the_v15_conventions(stem):
    """Keeps the v15 conventions."""
    text = _render(stem)
    missing = [clause for clause in REQUIRED if clause not in text]
    assert not missing, f"{stem} dropped {missing}"


@pytest.mark.parametrize("stem", LINEAGE)
def test_output_contract(stem):
    """Output contract."""
    text = _render(stem)
    for key in ("doc_type", "contract_subtype", "doc_subclass", "confidence", "reasoning"):
        assert re.search(rf'"{key}"', text), key


def test_condensed_is_a_fraction_of_v15():
    """Condensed is a fraction of v15."""
    from langchain_agents.prompts import PROMPT_VERSIONS

    v15 = len(_render_text(PROMPT_VERSIONS["sorter_v15"]))
    assert len(_render(LINEAGE[-1])) * 4 < v15


def _render_text(text: str) -> str:
    from langchain_agents.sorter_agent import fill_sorter_placeholders

    return fill_sorter_placeholders(text)


def test_lineage_file_names_every_version_and_a_frontrunner():
    """Lineage file names every version and a frontrunner."""
    import yaml

    data = yaml.safe_load((prompts_dir() / "sorter_condensed_lineage.yaml").read_text(encoding="utf-8"))
    assert data["lineage"] == "sorter-condensed" and data["budget_chars"] == CONDENSED_BUDGET_CHARS
    listed = {v["version"] for v in data["versions"]}
    assert listed == set(LINEAGE)
    assert data["frontrunner"] in listed
