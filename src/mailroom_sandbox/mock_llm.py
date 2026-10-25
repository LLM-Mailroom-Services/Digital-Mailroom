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


def fake_structured_payload(user_content: str, expect: dict[str, Any]) -> dict[str, Any]:
    doc_type = expect.get("doc_type") or expect.get("expected_doc_class") or "contract"
    conf = expect.get("conf")
    if conf is None:
        conf = 0.40 if expect.get("id") == "ambiguous_01" else 0.97
    fields = expect.get("expected_fields") or {}
    text = user_content or ""
    if "Classify this legal document" in text or "RE-EVALUATION REQUESTED" in text:
        return {
            "doc_type": doc_type,
            "contract_subtype": "other" if doc_type == "contract" else None,
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
    if "Yes" in text and "No" in text and expect.get("legalbench_answer"):
        return {"answer": expect["legalbench_answer"]}
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
