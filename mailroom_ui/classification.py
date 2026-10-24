"""Primary / secondary classification outcomes and archive filenames.

Display helpers only — they never invent a class. Outcomes are derived from
the interpreted run (predicted tokens + optional ground truth).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Optional

from .pipeline_schema import (
    DOC_CLASSES,
    DOC_SUBCLASS_BY_CLASS,
    EXTRACT_CLASS_ALIASES,
    LIVE_DOC_TYPES,
    UNKNOWN_DOC_TYPE,
)

HIT = "hit"
MISS = "miss"
PENDING = "pending"
N_A = "n_a"

_UNTYPED = "untyped"
_SLUG_MAX = 40
_DOC_ID8 = 8


def align_class(token: Optional[str]) -> Optional[str]:
    if token is None:
        return None
    key = str(token).strip().lower().replace(" ", "_")
    if not key:
        return None
    return EXTRACT_CLASS_ALIASES.get(key, key)


def align_subclass(token: Optional[str]) -> Optional[str]:
    if token is None:
        return None
    text = str(token).strip()
    if not text:
        return None
    return text


def _compact(token: str) -> str:
    return "".join(ch for ch in token.lower() if ch.isalnum())


def _subclass_in_catalog(predicted: str, catalog: tuple[str, ...]) -> bool:
    compact = _compact(predicted)
    for token in catalog:
        if token == predicted or _compact(token) == compact:
            return True
    return False


def _human_class(token: Optional[str]) -> str:
    if not token:
        return "untyped"
    return DOC_CLASSES.get(token) or DOC_CLASSES.get(align_class(token) or "") or token.replace("_", " ")


def _human_subclass(token: Optional[str]) -> str:
    if not token:
        return "no subclass"
    return str(token).replace("_", " ")


def _level_outcome(
    *,
    predicted: Optional[str],
    expected: Optional[str],
    assigned: bool,
) -> str:
    if expected:
        if not predicted:
            return PENDING
        if predicted == expected:
            return HIT
        return MISS
    if not assigned:
        return PENDING
    return HIT


def classification_card(
    *,
    doc_type: Optional[str] = None,
    doc_subclass: Optional[str] = None,
    contract_subtype: Optional[str] = None,
    expected_hf_class: Optional[str] = None,
    expected_subclass: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """Return labels + hit/miss/pending/n_a for the Observatory card."""
    primary = align_class(doc_type)
    expected_p = align_class(expected_hf_class)
    secondary = align_subclass(doc_subclass) or align_subclass(contract_subtype)
    expected_s = align_subclass(expected_subclass)
    if expected_s:
        expected_s = expected_s.strip()

    live = frozenset(LIVE_DOC_TYPES) | frozenset(EXTRACT_CLASS_ALIASES)
    primary_assigned = bool(primary and primary != UNKNOWN_DOC_TYPE and (
        primary in live or primary in DOC_CLASSES
    ))
    catalog = ()
    if primary:
        catalog = DOC_SUBCLASS_BY_CLASS.get(primary) or DOC_SUBCLASS_BY_CLASS.get(
            EXTRACT_CLASS_ALIASES.get(primary, primary), ()
        )
    if not catalog and secondary:
        # Predicted subclass without a roster for this class — still show it.
        catalog = (secondary,)

    if catalog:
        secondary_assigned = bool(secondary and _subclass_in_catalog(secondary, catalog))
        if secondary and expected_s:
            secondary_match = _compact(secondary) == _compact(expected_s)
            if secondary_match:
                expected_s = secondary  # treat as exact for outcome
        secondary_outcome = _level_outcome(
            predicted=_compact(secondary) if secondary else None,
            expected=_compact(expected_s) if expected_s else None,
            assigned=secondary_assigned,
        )
    else:
        if expected_s:
            secondary_outcome = MISS if secondary and _compact(secondary) != _compact(expected_s) else (
                HIT if secondary and _compact(secondary) == _compact(expected_s) else PENDING
            )
        elif secondary:
            secondary_outcome = HIT
        else:
            secondary_outcome = N_A

    return {
        "primary_outcome": _level_outcome(
            predicted=primary,
            expected=expected_p,
            assigned=primary_assigned,
        ),
        "secondary_outcome": secondary_outcome,
        "primary_label": _human_class(doc_type or primary),
        "secondary_label": _human_subclass(secondary),
    }


def classification_from_run(run: Any) -> dict[str, Optional[str]]:
    return classification_card(
        doc_type=getattr(run, "doc_type", None),
        doc_subclass=getattr(run, "doc_subclass", None),
        contract_subtype=getattr(run, "contract_subtype", None),
        expected_hf_class=getattr(run, "expected_hf_class", None),
        expected_subclass=getattr(run, "expected_subclass", None),
    )


def _slug(filename: Optional[str]) -> str:
    raw = (filename or "").strip()
    stem = raw.rsplit("/", 1)[-1]
    if "." in stem and not stem.startswith("."):
        stem = stem.rsplit(".", 1)[0]
    folded = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    folded = folded.lower()
    folded = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    if not folded:
        folded = "untitled"
    return folded[:_SLUG_MAX].strip("-") or "untitled"


def _ext(filename: Optional[str]) -> str:
    raw = (filename or "").rsplit("/", 1)[-1]
    if "." in raw and not raw.startswith("."):
        return "." + raw.rsplit(".", 1)[-1].lower()
    return ""


def _date_token(created_at: Any) -> str:
    if isinstance(created_at, datetime):
        stamp = created_at
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc).date().isoformat()
    if created_at:
        text = str(created_at).replace("Z", "+00:00")
        try:
            stamp = datetime.fromisoformat(text)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return stamp.astimezone(timezone.utc).date().isoformat()
        except ValueError:
            pass
    return datetime.now(timezone.utc).date().isoformat()


def _id8(doc_id: Optional[str], trace_id: Optional[str]) -> str:
    raw = (doc_id or trace_id or "unknown").strip()
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", raw) or "unknown"
    return cleaned[:_DOC_ID8]


def archive_document_name(
    *,
    doc_type: Optional[str] = None,
    doc_subclass: Optional[str] = None,
    contract_subtype: Optional[str] = None,
    filename: Optional[str] = None,
    doc_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    created_at: Any = None,
) -> str:
    """Stable display / export name. Does not rename producer files."""
    kind = align_class(doc_type) or UNKNOWN_DOC_TYPE
    if kind == UNKNOWN_DOC_TYPE and not doc_type:
        kind = _UNTYPED
    subclass = align_subclass(doc_subclass) or align_subclass(contract_subtype) or _UNTYPED
    subclass_token = re.sub(r"[^A-Za-z0-9_-]+", "-", str(subclass)).strip("-") or _UNTYPED
    return (
        f"{kind}/{_date_token(created_at)}/"
        f"{kind}__{subclass_token}__{_slug(filename)}__{_id8(doc_id, trace_id)}"
        f"{_ext(filename)}"
    )


def archive_name_from_run(run: Any) -> str:
    return archive_document_name(
        doc_type=getattr(run, "doc_type", None),
        doc_subclass=getattr(run, "doc_subclass", None),
        contract_subtype=getattr(run, "contract_subtype", None),
        filename=getattr(run, "filename", None),
        doc_id=getattr(run, "doc_id", None),
        trace_id=getattr(run, "trace_id", None),
        created_at=getattr(run, "created_at", None),
    )
