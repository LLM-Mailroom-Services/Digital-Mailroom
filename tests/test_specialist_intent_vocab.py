"""SAND-042 RCA guard: the structured-output hint must not teach off-vocab intents.

The JSON schema appended to every specialist call listed example ``intent``
labels (``demand_payment``, ``acknowledge``, ``coverage_denial`` …) that the
dojo scorer's controlled vocabulary does not contain, so a model that copied
the hint scored 0 on a field carrying a third of correspondence quality.
Every label named in an ``intent`` description must be a registered label.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "vendor" / "llm-dojo-scoring" / "src"))
sys.path.insert(0, str(REPO / "vendor" / "llm-mailroom" / "src"))

INTENT_LABELS = {
    "corporate_record": (
        "governance_rules", "corporate_action_approval", "entity_formation",
        "authority_delegation", "investor_rights", "other",
    ),
    "correspondence": (
        "payment_demand", "notice", "analysis", "request", "update",
        "meeting_invite", "press_communication", "other",
    ),
    "insurance_claim": (
        "claim_filing", "coverage_determination", "loss_report",
        "claim_data_record", "other",
    ),
}

_SCHEMAS = {
    "corporate_record": "CORPORATE_RECORDS_SCHEMA",
    "correspondence": "CORRESPONDENCE_SCHEMA",
    "insurance_claim": "INSURANCE_CLAIMS_SCHEMA",
}


def _intent_description(schema: dict) -> str:
    props = schema.get("properties") or schema.get("schema", {}).get("properties") or {}
    if not props:
        for value in schema.values():
            if isinstance(value, dict) and "properties" in value:
                props = value["properties"]
    return str(props["intent"].get("description", ""))


@pytest.mark.parametrize("doc_type", sorted(_SCHEMAS))
def test_intent_hint_names_only_registered_labels(doc_type):
    agents = pytest.importorskip("langchain_agents.specialist_agents")
    desc = _intent_description(getattr(agents, _SCHEMAS[doc_type]))
    # Workspace llm-mailroom renders ``label = meaning; label = meaning. other = residual.``
    # (INTENT_DESCRIPTIONS); the older hint was ``Exactly one label: a, b, c``.
    if " = " in desc:
        named = set(re.findall(r"\b([a-z]+(?:_[a-z]+)*) = ", desc))
    else:
        named = set(re.findall(r"\b[a-z]+(?:_[a-z]+)*\b", desc.split(":", 1)[-1]))
    assert named == set(INTENT_LABELS[doc_type]), desc


def test_local_vocab_mirrors_dojo():
    intents = pytest.importorskip("llm_dojo_scoring.intents")
    for doc_type, labels in INTENT_LABELS.items():
        assert tuple(intents.INTENT_LABELS[doc_type]) == labels
