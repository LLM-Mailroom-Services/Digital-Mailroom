"""Prompt variant loading."""

from pathlib import Path

from mailroom_sandbox.prompts import list_variants, load_variant


def test_sorter_local_variant_mentions_json():
    assert "sorter_local_v0" in list_variants()
    text = load_variant("sorter_local_v0")
    assert "json" in text.lower()
    assert "sorter_reviewer_local_v0" in list_variants()
    assert "json" in load_variant("sorter_reviewer_local_v0").lower()
    assert "json" in load_variant("judge_local_v0").lower()


def test_merger_specialist_production_prompt_is_maud_not_cuad():
    path = Path(__file__).resolve().parents[1] / "config" / "prompts" / "merger_agreement_specialist_production.txt"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "merger-agreement specialist" in text.lower() or "merger agreement" in text.lower()
    assert "maud" in text.lower()
    assert "contracts_specialist_v33" not in text
    assert "You are a legal extraction specialist focused on commercial contracts" not in text

