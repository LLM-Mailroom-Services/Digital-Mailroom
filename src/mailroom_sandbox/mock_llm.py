"""Deterministic fake OpenAI client for --mock pipeline / eval runs."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock


def _user_text(messages: list) -> str:
    if not messages:
        return ""
    last = messages[-1]
    if isinstance(last, dict):
        content = last.get("content", "")
    else:
        content = getattr(last, "content", "") or ""
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def oracle_extraction(fields: dict[str, Any], doc_type: str, subclass: str | None = None) -> dict[str, Any]:
    """The ground truth rewritten as a specialist would answer it.

    The ground truth stores CUAD/MAUD labels as span objects and list fields as
    JSON strings, while the scorers read the model's ``cuad_clauses`` /
    ``maud_clauses`` entries and the live schemas want lists. Echoing the raw
    labels scored contracts and mergers 0 by construction. This answer scores
    1.0 on every scoreable corpus row, so a mock run drops below 1.0 only when
    the ground truth stops reaching the scorer.
    """
    from llm_dojo_scoring.sandbox_scoring import FIELD_CATEGORY, gt_categories, gt_labels

    from mailroom_sandbox.eval.schema_adherence import schema_keys_for

    pred = dict(fields)
    cuad = gt_categories(pred.pop("cuad_clause_labels", None))
    if cuad:
        pred["cuad_clauses"] = [f"{cat}: {spans[0]}" for cat, spans in cuad.items() if spans]
        for field, cat in FIELD_CATEGORY.items():
            if cuad.get(cat) and pred.get(field) in (None, "", []):
                pred[field] = cuad[cat] if field == "parties" else cuad[cat][0]
    maud = gt_labels(pred.pop("maud_clause_labels", None))
    if maud:
        pred["maud_clauses"] = [f"{question}: {answer}" for question, answer in maud.items()]
    keys = schema_keys_for(doc_type, subclass)
    if keys:
        pred = {k: v for k, v in pred.items() if k in keys}
    for key, value in pred.items():
        if isinstance(value, str) and value.strip().startswith("["):
            try:
                decoded = json.loads(value)
            except ValueError:
                continue
            if isinstance(decoded, list):
                pred[key] = decoded
    try:
        from schemas.documents import get_extraction_schema

        model = get_extraction_schema(doc_type)
    except Exception:  # noqa: BLE001 — no live schema: keep the decoded payload
        model = None
    for name, field in (getattr(model, "model_fields", None) or {}).items():
        if pred.get(name) == "" and "list" in str(field.annotation).lower():
            pred[name] = []
    return pred


def fake_structured_payload(user_content: str, expect: dict[str, Any]) -> dict[str, Any]:
    doc_type = expect.get("doc_type") or expect.get("expected_doc_class") or "contract"
    conf = expect.get("conf")
    if conf is None:
        # Above every class's "high" threshold (0.98 for contracts, mergers, claims),
        # so a mock document runs the whole graph instead of stopping for review.
        conf = 0.40 if expect.get("id") == "ambiguous_01" else 0.99
    fields = expect.get("expected_fields") or {}
    text = user_content or ""
    if ("Classify this legal document" in text or "RE-EVALUATION REQUESTED" in text
            or "CLASSIFY THIS DOCUMENT" in text):  # the last is the sorter reviewer's prompt
        return {
            "doc_type": doc_type,
            "contract_subtype": "other" if doc_type == "contract" else None,
            # Without a subclass the sorter guardrail sends every document to review.
            "doc_subclass": expect.get("expected_subclass"),
            "confidence": conf,
            "reasoning": "mock",
        }
    if "ADJUDICATION REQUEST" in text:
        return {
            "decision": expect.get("boss_decision") or expect.get("expected_decision") or "approved",
            "reasoning": "mock",
            "resolution_notes": "",
        }
    if "JUDGE VERDICT" in text or "Arbiter" in text:
        return {
            "decision": expect.get("arbiter_decision") or expect.get("expected_decision") or "accept_with_caveats",
            "fields_to_fix": [],
            "reasoning": "mock",
            "handoff_summary": "",
        }
    if "quality reviewer" in text.lower() or "completeness" in text.lower():
        return {
            "completeness": expect.get("expected_score") or 0.98,
            "completeness_label": expect.get("judge_verdict") or expect.get("expected_verdict") or "complete",
            "reasoning": "mock",
        }
    if "matter-record summary" in text or "compile this into" in text.lower():
        return {"summary": "mock report", "confidence": 0.9}
    if "Extract this document's fields" in text:  # the in-graph specialist
        return {"confidence": conf, **oracle_extraction(fields, doc_type, expect.get("expected_subclass"))}
    payload = {"confidence": conf, "mock_extraction": True}
    payload.update(fields)
    return payload


def fake_client(expect: dict[str, Any]) -> MagicMock:
    def create(**kwargs: Any) -> MagicMock:
        user = _user_text(kwargs.get("messages") or [])
        content = json.dumps(fake_structured_payload(user, expect))
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = content
        resp.usage = SimpleNamespace(prompt_tokens=12, completion_tokens=24)
        return resp

    client = MagicMock()
    client.chat.completions.create.side_effect = create
    return client
