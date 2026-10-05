"""CUAD clause scoring for ``contract`` (SAND-032).

The pinned Hub rows for contracts carry ground truth only as
``expected_fields.cuad_clause_labels`` — a JSON map of CUAD category → list of
annotated spans (empty list = category absent). The vendored suite field map
scores document_name / parties / … instead, which those rows never populate,
so field-level F1 was 0 and the overall score null by construction.

Headline ``cuad_presence_f1``: per-document micro F1 of "which CUAD categories
does this contract contain", restricted to the categories the row labels (its
universe). A category is predicted present when ``cuad_clauses`` names it
('<Category>: <text>') or when the mapped schema field is non-empty.
Value checks compare the metadata fields against the annotated span text.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

# schema field → CUAD metadata category it evidences
FIELD_CATEGORY = {
    "document_name": "Document Name",
    "parties": "Parties",
    "effective_date": "Effective Date",
    "governing_law": "Governing Law",
    "term_length": "Expiration Date",
    "renewal_terms": "Renewal Term",
}
VALUE_FIELDS = ("document_name", "parties", "governing_law")


def _norm(text: Any) -> str:
    s = re.sub(r"[^a-z0-9 ]+", " ", str(text or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def _empty(v: Any) -> bool:
    return v is None or (isinstance(v, (str, list, dict)) and not v)


def gt_categories(raw: Any) -> dict[str, list[str]]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, Mapping):
        return {}
    return {k: [str(s.get("text", "")) for s in (v or []) if isinstance(s, Mapping)]
            for k, v in raw.items()}


def predicted_categories(pred: Mapping[str, Any], universe: list[str]) -> tuple[set[str], int]:
    by_norm = {_norm(c): c for c in universe}
    found: set[str] = set()
    outside = 0
    for entry in pred.get("cuad_clauses") or []:
        head = _norm(str(entry).split(":", 1)[0])
        if head in by_norm:
            found.add(by_norm[head])
        else:
            outside += 1
    for field, cat in FIELD_CATEGORY.items():
        if cat in universe and not _empty(pred.get(field)):
            found.add(cat)
    return found, outside


def _value_ok(field: str, value: Any, spans: list[str]) -> bool:
    blob = " ".join(_norm(s) for s in spans)
    if field == "parties":
        names = [_norm(v) for v in (value or [])] if isinstance(value, list) else [_norm(value)]
        return bool(names) and all(n and n in blob for n in names)
    v = _norm(value)
    return bool(v) and (v in blob or any(_norm(s) in v for s in spans if _norm(s)))


def score_cuad(pred: Mapping[str, Any], cuad_clause_labels: Any) -> dict[str, Any]:
    gt = gt_categories(cuad_clause_labels)
    universe = list(gt)
    present = {c for c, spans in gt.items() if spans}
    found, outside = predicted_categories(pred or {}, universe)
    tp, fp, fn = len(found & present), len(found - present), len(present - found)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = round(2 * p * r / (p + r), 4) if p + r else 0.0
    checked = correct = 0
    for field in VALUE_FIELDS:
        cat = FIELD_CATEGORY[field]
        if gt.get(cat) and not _empty((pred or {}).get(field)):
            checked += 1
            correct += _value_ok(field, pred[field], gt[cat])
    return {
        "cuad_universe": len(universe), "cuad_present": len(present),
        "cuad_tp": tp, "cuad_fp": fp, "cuad_fn": fn,
        "cuad_presence_precision": round(p, 4), "cuad_presence_recall": round(r, 4),
        "cuad_presence_f1": f1 if universe else None,
        "cuad_out_of_universe": outside,
        "cuad_value_checked": checked, "cuad_value_correct": correct,
    }
