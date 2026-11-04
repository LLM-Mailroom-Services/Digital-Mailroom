"""SAND-042 RCA guard: vendored extraction schemas honor the dojo empty-field contract.

Insurance schema-valid read 26–34 % on Qwen3-8B because five fields were
``str = ""`` while the prompt, the JSON-schema grammar and the dojo all say
an unstated scalar is ``null`` (corporate_record ``entity_name`` /
``record_type`` carried the same bug at 96 %). Any future schema edit that
rejects a contract-empty value — or a currency phrase on a money field —
fails here before it can skew a run.
"""

from __future__ import annotations

import pytest

import mailroom_sandbox  # noqa: F401  (prepends vendor/ trees to sys.path)
from llm_dojo_scoring.corpus import CORPUS_DOC_TYPES
from llm_dojo_scoring.schema_contract import contract_violations
from schemas.documents import EXTRACTION_SCHEMAS

MONEY_PROBES = {
    "insurance_claim": {"claimed_amount": "$18,530.00"},
    "correspondence": {"demand_amount": "$5,000.00"},
}


@pytest.mark.parametrize("doc_type", CORPUS_DOC_TYPES)
def test_vendored_schema_accepts_contract_empty_values(doc_type):
    assert contract_violations(doc_type, EXTRACTION_SCHEMAS[doc_type]) == []


@pytest.mark.parametrize("doc_type", sorted(MONEY_PROBES))
def test_money_fields_accept_currency_phrases(doc_type):
    assert contract_violations(
        doc_type, EXTRACTION_SCHEMAS[doc_type], fields=MONEY_PROBES[doc_type]
    ) == []


def test_money_parse_values():
    model = EXTRACTION_SCHEMAS["insurance_claim"]
    assert model.model_validate({"claimed_amount": "$18,530.00"}).claimed_amount == 18530.0
    assert model.model_validate({"claimed_amount": 0}).claimed_amount == 0.0
    with pytest.raises(Exception):
        model.model_validate({"claimed_amount": "about ten grand"})


def test_maud_v2_prompt_is_fresh_against_dojo_catalog():
    """The maud_v2 answer catalog is generated from the scorer's own classes."""
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(repo / "scripts" / "gen_maud_v2_prompt.py"), "--check"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
