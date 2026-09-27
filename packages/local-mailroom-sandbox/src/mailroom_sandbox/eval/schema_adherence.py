"""Parse-failure / schema-adherence checks, separate from extraction scores.

Mailroom already emits ``parse_error`` / ``schema_valid`` on the connected
graph (``observability.scores.validate_extraction``). Isolated specialist
evals never attached those flags, so a format failure and a genuine miss
both looked like ``extraction_f1 = 0``. This module is additive: it classifies
the *payload shape* without changing ``overall_extraction_score``.

Dojo ``extraction_f1`` counts (field, value) events at score ``>= 1.0``. A
row can be schema-valid JSON and still score F1 0.0 — that is a quality miss,
not a parse failure.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Mapping, Sequence

# Keys the specialist / scorer may attach that are not extraction fields.
_META_KEYS = frozenset(
    {
        "_parse_error",
        "_raw",
        "confidence",
        "reasoning",
        "offline_fallback",
        "error",
    }
)

# Retired correspondence schema (production-doctrine still names these).
_LEGACY_CORRESPONDENCE_KEYS = frozenset({"key_points", "referenced_communications"})

# Hub GT provenance / content differentiators — not CorrespondenceExtraction.
_NON_EXTRACTION_GT_KEYS = frozenset(
    {
        "content_topic",
        "topic_evidence",
        "sentiment_label",
        "sentiment_score",
        "sentiment_evidence",
        "label_evidence",
        "intent_source",
        "intent_confidence",
        "intent_status",
        "claimed_amount",  # insurance schema; correspondence uses demand_amount
    }
)

_FALLBACK_SCHEMA_KEYS: dict[str, frozenset[str]] = {
    "correspondence": frozenset(
        {
            "sender",
            "recipient",
            "additional_recipients",
            "communication_type",
            "communication_date",
            "demand_amount",
            "action_items",
            "urgency",
            "intent",
            "subject_matter",
            "keywords",
        }
    ),
    "contract": frozenset(
        {
            "document_name",
            "parties",
            "effective_date",
            "term_length",
            "governing_law",
            "contract_value",
            "renewal_terms",
            "cuad_family",
            "merger_consideration",
            "cuad_clauses",
            "maud_clauses",
        }
    ),
    "insurance_claim": frozenset(
        {
            "claim_number",
            "policy_number",
            "insurer",
            "insured_party",
            "claim_type",
            "date_of_loss",
            "date_filed",
            "claimed_amount",
            "adjuster",
            "damages_description",
            "coverage_determination",
            "denial_reasons",
            "supporting_documents",
            "intent",
            "subject_matter",
            "keywords",
            "claim_checklist",
        }
    ),
    "corporate_record": frozenset(
        {
            "entity_name",
            "record_type",
            "effective_date",
            "signatories",
            "jurisdiction",
            "filing_number",
            "intent",
            "subject_matter",
            "keywords",
        }
    ),
    "merger_agreement": frozenset(
        {
            "document_name",
            "parties",
            "effective_date",
            "effective_time",
            "governing_law",
            "merger_consideration",
            "maud_clauses",
            "intent",
            "subject_matter",
            "keywords",
        }
    ),
}

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

# Additive payload keys (never replace extraction scores).
SCHEMA_ADHERENCE_ROW_KEYS = (
    "parse_error",
    "schema_valid",
    "schema_adherence",
    "parse_failure_reason",
    "extra_schema_keys",
    "extra_schema_key_count",
    "legacy_schema_keys",
    "prose_wrapper",
)


def schema_keys_for(doc_type: str) -> frozenset[str]:
    """Live extraction-schema field names for ``doc_type``."""
    resolved = str(doc_type or "").strip()
    try:
        from schemas.documents import get_extraction_schema

        model = get_extraction_schema(resolved)
        if model is not None:
            return frozenset(model.model_fields) - {"confidence", "reasoning"}
    except Exception:
        pass
    if resolved in _FALLBACK_SCHEMA_KEYS:
        return _FALLBACK_SCHEMA_KEYS[resolved]
    # Agent names (correspondence_specialist) map onto the class key.
    for suffix, keys in _FALLBACK_SCHEMA_KEYS.items():
        if resolved.endswith(suffix) or suffix in resolved:
            return keys
    return frozenset()


def coerce_predicted_payload(predicted: Any) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Turn a specialist prediction into a dict, or explain why it is not one.

    Isolated evals keep a dict. Job ``items.jsonl`` stores ``str(value)``
    (Python repr, not JSON). Raw LLM text may wrap a JSON object in prose.
    """
    meta: dict[str, Any] = {
        "parse_error": False,
        "parse_failure_reason": None,
        "prose_wrapper": False,
    }
    if predicted is None:
        meta["parse_error"] = True
        meta["parse_failure_reason"] = "null_payload"
        return None, meta
    if isinstance(predicted, dict):
        if predicted.get("_parse_error"):
            meta["parse_error"] = True
            meta["parse_failure_reason"] = "flagged_parse_error"
            raw = predicted.get("_raw")
            if isinstance(raw, str) and raw.strip():
                recovered, raw_meta = coerce_predicted_payload(raw)
                if recovered is not None and not raw_meta.get("parse_error"):
                    # Specialist flagged parse failure but the raw text is
                    # recoverable — still a parse_error (the live path dropped
                    # the fields); keep the recovered dict for schema checks.
                    meta["recovered_from_raw"] = True
                    return recovered, meta
            return predicted, meta
        return predicted, meta
    if isinstance(predicted, (bytes, bytearray)):
        try:
            predicted = predicted.decode("utf-8")
        except Exception:
            meta["parse_error"] = True
            meta["parse_failure_reason"] = "undecodable_bytes"
            return None, meta
    if not isinstance(predicted, str):
        meta["parse_error"] = True
        meta["parse_failure_reason"] = f"unsupported_type:{type(predicted).__name__}"
        return None, meta
    text = predicted.strip()
    if not text:
        meta["parse_error"] = True
        meta["parse_failure_reason"] = "empty_string"
        return None, meta

    parsed, how = _parse_object_text(text)
    if parsed is not None:
        if how == "wrapped_json":
            meta["prose_wrapper"] = True
        return parsed, meta

    meta["parse_error"] = True
    meta["parse_failure_reason"] = "unparseable"
    return None, meta


def _parse_object_text(text: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj, "json"
    except json.JSONDecodeError:
        pass
    try:
        obj = ast.literal_eval(text)
        if isinstance(obj, dict):
            return obj, "python_repr"
    except (SyntaxError, ValueError):
        pass
    match = _JSON_OBJECT_RE.search(text)
    if match and (text[: match.start()].strip() or text[match.end() :].strip()):
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj, "wrapped_json"
        except json.JSONDecodeError:
            pass
        try:
            obj = ast.literal_eval(match.group(0))
            if isinstance(obj, dict):
                return obj, "wrapped_python_repr"
        except (SyntaxError, ValueError):
            pass
    return None, None


def _pydantic_valid(doc_type: str, payload: Mapping[str, Any]) -> bool | None:
    """True/False when a pydantic schema is importable; None if unavailable."""
    try:
        from schemas.documents import get_extraction_schema
    except Exception:
        return None
    model = get_extraction_schema(str(doc_type or "").strip())
    if model is None:
        # Agent name like correspondence_specialist.
        for cls in ("correspondence", "contract", "insurance_claim", "corporate_record", "merger_agreement"):
            if cls in str(doc_type):
                model = get_extraction_schema(cls)
                break
    if model is None:
        return None
    try:
        model.model_validate(dict(payload))
        return True
    except Exception:
        return False


def assess_extraction_payload(
    predicted: Any,
    doc_type: str,
) -> dict[str, Any]:
    """Classify format/parse vs schema for one specialist prediction.

    Returns additive keys only. ``schema_adherence`` is 1.0 when the payload
    parsed *and* validated; 0.0 otherwise. Extra/legacy keys are reported
    even when pydantic would ignore them (default ``extra='ignore'``).
    """
    payload, meta = coerce_predicted_payload(predicted)
    parse_error = bool(meta.get("parse_error"))
    extra: list[str] = []
    legacy: list[str] = []
    schema_valid = False
    if payload is not None and not parse_error:
        keys = schema_keys_for(doc_type)
        public = [k for k in payload if k not in _META_KEYS]
        extra = sorted(k for k in public if keys and k not in keys)
        legacy = sorted(k for k in public if k in _LEGACY_CORRESPONDENCE_KEYS)
        typed = _pydantic_valid(doc_type, payload)
        if typed is None:
            # Structural fallback: a dict whose public keys are a subset of the
            # known schema (or unknown doc type → any dict that parsed).
            schema_valid = bool(payload) and (not keys or not extra or set(public) & keys)
        else:
            schema_valid = bool(typed)
    elif payload is not None and parse_error:
        # Flagged parse_error: never schema_valid, even if a dict remains.
        schema_valid = False

    adherence = (not parse_error) and schema_valid
    out: dict[str, Any] = {
        "parse_error": parse_error,
        "schema_valid": schema_valid,
        "schema_adherence": 1.0 if adherence else 0.0,
        "parse_failure_reason": meta.get("parse_failure_reason"),
        "extra_schema_keys": extra,
        "extra_schema_key_count": len(extra),
        "legacy_schema_keys": legacy,
        "prose_wrapper": bool(meta.get("prose_wrapper")),
    }
    if meta.get("recovered_from_raw"):
        out["recovered_from_raw"] = True
    return out


def merge_schema_adherence(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Run-level rates from per-row ``assess_extraction_payload`` dicts.

    Additive names only (``*_rate`` / ``*_count``). Does not emit ``n``.
    """
    n = len(rows)
    if n == 0:
        return {}
    parse_n = sum(1 for r in rows if r.get("parse_error"))
    valid_n = sum(1 for r in rows if r.get("schema_valid"))
    adhere_n = sum(
        1
        for r in rows
        if (not r.get("parse_error")) and r.get("schema_valid")
    )
    wrapper_n = sum(1 for r in rows if r.get("prose_wrapper"))
    extra_n = sum(1 for r in rows if int(r.get("extra_schema_key_count") or 0) > 0)
    legacy_n = sum(1 for r in rows if r.get("legacy_schema_keys"))
    return {
        "parse_error_count": parse_n,
        "parse_error_rate": round(parse_n / n, 4),
        "schema_valid_count": valid_n,
        "schema_valid_rate": round(valid_n / n, 4),
        "schema_adherence_rate": round(adhere_n / n, 4),
        "prose_wrapper_count": wrapper_n,
        "extra_schema_key_docs": extra_n,
        "legacy_schema_key_docs": legacy_n,
    }


def classify_floor_mode(row: Mapping[str, Any]) -> str:
    """Bucket a low-scoring row into issue #21's (a)/(b)/(c) modes.

    * ``format`` — parse failure or prose wrapper (a)
    * ``schema`` — parsed but extra/legacy keys the scorer does not credit (a/b)
    * ``scorer`` — schema-clean payload; quality zero is a value miss (c)
    """
    if row.get("parse_error") or row.get("prose_wrapper"):
        return "format"
    extra = set(row.get("extra_schema_keys") or [])
    legacy = set(row.get("legacy_schema_keys") or [])
    if extra or legacy:
        if extra & _NON_EXTRACTION_GT_KEYS or extra & _LEGACY_CORRESPONDENCE_KEYS:
            return "schema"
        return "schema"
    return "scorer"
