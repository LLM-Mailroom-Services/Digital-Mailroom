"""MAUD answer scoring for ``merger_agreement`` (SAND-032).

The pinned Hub rows for merger agreements carry ground truth only as
``expected_fields.maud_clause_labels`` — a JSON map of LegalBench MAUD
question → {answer, valid_classes, …}. The vendored suite field map scores
document_name / parties / … instead, which those rows never populate, so
field-level F1 was 0 by construction. This module scores what the ground
truth actually labels: per-question answer accuracy.

Headline ``maud_accuracy`` = correct / labeled questions (an unanswered
question counts as wrong). ``maud_precision_answered`` = correct / answered.
Matching is exact after normalization (case, underscores, whitespace, quotes).
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

TYPE_OF_CONSIDERATION = "Type of Consideration"
_CONSIDERATION_ENUM = {
    "all_cash": "All Cash",
    "all_stock": "All Stock",
    "mixed_cash_stock": "Mixed Cash/Stock",
    "mixed_cash_stock_election": "Mixed Cash/Stock: Election",
}
_NON_ANSWERS = {
    "", "none stated", "not specified", "not answered", "not stated", "unanswered",
    "n/a", "na", "unknown", "not found", "not applicable", "null",
}


# Questions whose corpus answers all come from ONE MAUD sub-question. The Hub
# rows collapse several sub-questions under names like "No-Shop" / "MAE
# Definition" (answers "Yes", "Strict liability", … for different
# sub-questions), so only this subset has an unambiguous target per doc.
CLEAN_QUESTIONS = frozenset({
    "Type of Consideration", "General Antitrust Efforts Standard",
    "Compliance with Covenant Closing Condition", "Specific Performance",
    "Agreement provides for matching rights in connection with COR",
    "Agreement provides for matching rights in connection with FTR",
    "Limitations on FTR Exercise", "Absence of Litigation Closing Condition",
    "Accuracy of Target R&W Closing Condition", "Breach of Meeting Covenant",
    "Breach of No Shop", "FTR Triggers",
})


def norm(text: Any) -> str:
    s = str(text or "").lower().replace("_", " ").replace("fundermental", "fundamental")
    s = re.sub(r"[\"'“”‘’`]", "", s)
    s = re.sub(r"\s+", " ", s).strip(" .;:-")
    return s


def gt_labels(raw: Any) -> dict[str, str]:
    """``maud_clause_labels`` (JSON string or mapping) → {question: answer}."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, Mapping):
        return {}
    return {q: str(v.get("answer", "")) for q, v in raw.items() if isinstance(v, Mapping)}


def parse_maud_answers(pred: Mapping[str, Any], questions: list[str]) -> dict[str, str]:
    """Map the specialist's ``maud_clauses`` onto known question names.

    Entries are '<Question>: <Answer>'. Question names can themselves contain
    colons, so each entry is matched by normalized prefix against ``questions``
    (longest first) rather than split on the first colon. ``merger_consideration``
    backfills Type of Consideration when maud_clauses does not answer it.
    """
    ordered = sorted(questions, key=lambda q: -len(norm(q)))
    out: dict[str, str] = {}
    clauses = pred.get("maud_clauses") or []
    if isinstance(clauses, Mapping):
        clauses = [f"{k}: {v}" for k, v in clauses.items()]
    for entry in clauses if isinstance(clauses, list) else []:
        text = str(entry)
        for q in ordered:
            nq = norm(q)
            # walk the raw entry until its normalized prefix covers the question
            for cut in range(len(nq), len(text) + 1):
                if norm(text[:cut]) == nq and (cut == len(text) or text[cut] in ": -–—"):
                    answer = text[cut:].lstrip(" :-–—").strip()
                    if norm(answer) == nq:  # echoed the question name — no answer
                        answer = ""
                    out.setdefault(q, answer)
                    break
            else:
                continue
            break
    if TYPE_OF_CONSIDERATION in questions and norm(out.get(TYPE_OF_CONSIDERATION)) in _NON_ANSWERS:
        enum = _CONSIDERATION_ENUM.get(str(pred.get("merger_consideration") or "").strip().lower())
        if enum:
            out[TYPE_OF_CONSIDERATION] = enum
    return out


def score_maud(pred: Mapping[str, Any], maud_clause_labels: Any) -> dict[str, Any]:
    gt = gt_labels(maud_clause_labels)
    answers = parse_maud_answers(pred or {}, list(gt))
    answered = {q: a for q, a in answers.items() if norm(a) not in _NON_ANSWERS}
    correct = sum(1 for q, a in answered.items() if norm(a) == norm(gt[q]))
    n = len(gt)
    clean = [q for q in gt if q in CLEAN_QUESTIONS]
    clean_correct = sum(1 for q in clean if q in answered and norm(answered[q]) == norm(gt[q]))
    return {
        "maud_clean_questions": len(clean),
        "maud_clean_correct": clean_correct,
        "maud_clean_accuracy": (clean_correct / len(clean)) if clean else None,
        "maud_questions": n,
        "maud_answered": len(answered),
        "maud_correct": correct,
        "maud_accuracy": (correct / n) if n else None,
        "maud_precision_answered": (correct / len(answered)) if answered else None,
    }
