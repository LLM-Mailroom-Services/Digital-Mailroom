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
    "n/a", "na", "unknown", "not found", "not applicable", "null", "none",
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


def _multi_class_questions() -> frozenset[str]:
    """Questions whose catalog holds multi-select answers.

    A question is multi-select when some catalog class is a comma-joined list
    that includes another catalog class (``"General R&Ws, …"``). Only these
    compare comma-joined answers as sets; elsewhere order is meaningful.
    """
    from llm_dojo_scoring.maud import MAUD_ANSWER_CLASSES

    out = set()
    for question, classes in MAUD_ANSWER_CLASSES.items():
        singles = {norm(c) for c in classes}
        for c in classes:
            parts = [norm(p) for p in str(c).split(",") if p.strip()]
            if len(parts) > 1 and any(p in singles for p in parts):
                out.add(question)
                break
    return frozenset(out)


MULTI_CLASS_QUESTIONS = _multi_class_questions()


def _catalog_norms() -> dict[str, frozenset[str]]:
    from llm_dojo_scoring.maud import MAUD_ANSWER_CLASSES

    return {q: frozenset(norm(c) for c in cs) for q, cs in MAUD_ANSWER_CLASSES.items()}


_CATALOG_NORMS = _catalog_norms()


def is_non_answer(answer: Any, question: str | None = None) -> bool:
    """Missing / placeholder answer. A placeholder that is itself a catalog
    class for *question* (``"None"`` on the matching-rights and fiduciary
    questions) is a real answer."""
    na = norm(answer)
    return na in _NON_ANSWERS and na not in _CATALOG_NORMS.get(question or "", ())


def same_answer(a: Any, b: Any, question: str | None = None) -> bool:
    """Exact match after ``norm``; comma-joined answers compare as sets only
    for a multi-select *question* (:data:`MULTI_CLASS_QUESTIONS`)."""
    na, nb = norm(a), norm(b)
    if na == nb:
        return True
    if question not in MULTI_CLASS_QUESTIONS or "," not in na:
        return False
    parts = lambda v: sorted(p.strip() for p in v.split(",") if p.strip())  # noqa: E731
    return parts(na) == parts(nb)


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


CONFLICT = "\x00conflict"


def _reduce(answers: list[str], question: str | None = None) -> str:
    """One answer per question from a chunk-merged list (SAND-042 RCA).

    Chunked runs answer every question on every chunk, so the preamble chunk
    contributes guesses / "not specified" before the chunk holding the
    clause. Position must not decide: drop non-answers, and when distinct
    real answers remain the question is a conflict (scored wrong, counted).
    """
    real: list[str] = []
    for a in answers:
        if not is_non_answer(a, question) and not any(same_answer(a, r, question) for r in real):
            real.append(a)
    if not real:
        return answers[0] if answers else ""
    return real[0] if len(real) == 1 else CONFLICT


def parse_maud_answers(pred: Mapping[str, Any], questions: list[str]) -> dict[str, str]:
    """Map the specialist's ``maud_clauses`` onto known question names.

    Entries are '<Question>: <Answer>'. Question names can themselves contain
    colons, so each entry is matched by normalized prefix against ``questions``
    (longest first) rather than split on the first colon. ``merger_consideration``
    backfills Type of Consideration when maud_clauses does not answer it.
    """
    ordered = sorted(questions, key=lambda q: -len(norm(q)))
    seen: dict[str, list[str]] = {}
    clauses = pred.get("maud_clauses") or []
    if isinstance(clauses, Mapping):
        # {question: null} is the object grammar's "not answered".
        clauses = [f"{k}: {v}" for k, v in clauses.items() if v is not None]
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
                    seen.setdefault(q, []).append(answer)
                    break
            else:
                continue
            break
    out = {q: _reduce(vals, q) for q, vals in seen.items()}
    if TYPE_OF_CONSIDERATION in questions and is_non_answer(out.get(TYPE_OF_CONSIDERATION), TYPE_OF_CONSIDERATION):
        enum = _CONSIDERATION_ENUM.get(str(pred.get("merger_consideration") or "").strip().lower())
        if enum:
            out[TYPE_OF_CONSIDERATION] = enum
    return out


def score_maud(pred: Mapping[str, Any], maud_clause_labels: Any) -> dict[str, Any]:
    gt = gt_labels(maud_clause_labels)
    answers = parse_maud_answers(pred or {}, list(gt))
    answered = {q: a for q, a in answers.items() if not is_non_answer(a, q)}
    conflicts = sum(1 for a in answered.values() if a == CONFLICT)
    correct = sum(1 for q, a in answered.items() if same_answer(a, gt[q], q))
    n = len(gt)
    clean = [q for q in gt if q in CLEAN_QUESTIONS]
    clean_correct = sum(1 for q in clean if q in answered and same_answer(answered[q], gt[q], q))
    return {
        "maud_clean_questions": len(clean),
        "maud_clean_correct": clean_correct,
        "maud_clean_accuracy": (clean_correct / len(clean)) if clean else None,
        "maud_questions": n,
        "maud_answered": len(answered),
        "maud_conflicts": conflicts,
        "maud_correct": correct,
        "maud_accuracy": (correct / n) if n else None,
        "maud_precision_answered": (correct / len(answered)) if answered else None,
    }
