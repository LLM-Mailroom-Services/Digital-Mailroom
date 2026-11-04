"""Interim ground-truth labels: the unpublished enhancements to the mailroom-dataset GT.

The Hub ``ground_truth`` rows leave key fields unlabelled (corporate entity/jurisdiction/dates/
signatories, correspondence sender/recipient/date/type, every merger field but consideration) and
carry a few labels the document contradicts or the scorer reads too strictly (CUAD party spans,
CUAD effective date; CMS claim_type collapsed onto ``health``). Until the next dataset revision
publishes them, this overlay supplies those labels from REAL specialist extractions that the
extraction gate accepted field by field, plus deterministic labels derived from the row itself.

Every label carries its status and basis:

``gap_fill``    the Hub has no label for the field; the gate supports the extracted value
                (field support >= ``SUPPORT_MIN``, verdict not human_review) and every token of
                it is in the document (``grounded``).
``derived``     computed from the row, no model involved (``cms_source_table``: dojo #93;
                ``record_type`` / ``communication_type``: the row's own expected_subclass).
``correction``  the Hub label exists but a documented GT/scorer defect makes it unattainable;
                the extracted value is gate-accepted AND checked against the Hub's own evidence
                (``cuad_party_spans``: every extracted party is a CUAD Parties span;
                ``cuad_agreement_date``: CUAD Effective Date is empty and the value equals the
                CUAD Agreement Date).
``disputed``    the Hub label exists, the scorer says the extraction is wrong, the gate says it
                is right, and no rule decides: NOT ground truth (``use_as_truth`` false), kept
                for the human review that the dataset revision needs.

Files live in ``data/labels/interim/`` (one JSONL per class plus ``MANIFEST.json`` with hashes,
sources and counts), built only by ``scripts/interim_labels.py build`` and verified by
``scripts/interim_labels.py check`` and ``tests/test_interim_labels.py``. Nothing reads them
unless a run asks: ``dataset.interim_labels: true`` merges the truth labels into the locked
rows' ``expected_fields`` and records the overlay hash in the lock, so a score that used them is
never mistaken for a Hub-GT score (dojo #97). A label the Hub publishes supersedes the overlay
(``check --rows`` reports it; ``build`` drops it on the next rebuild).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from mailroom_sandbox.paths import repo_root

SCHEMA = "mailroom-interim-labels/v1"
STATUSES = ("gap_fill", "derived", "correction", "disputed")
TRUTH_STATUSES = ("gap_fill", "derived", "correction")
SUPPORT_MIN = 0.9  # field support a gap fill / correction needs (calibrated in the manifest)
NULL_SUPPORT_MIN = 0.95  # "the document does not state it" needs more
CMS_TABLES = ("carrier", "inpatient", "outpatient", "pde")
# Extraction fields the Hub already labels under another name: the row's expected_subclass IS the
# record kind / communication form, so the label is derived from it, never from an extraction
# (a gap fill read "bylaws" off a board consent's exhibit title the Hub files as board_resolution).
SUBCLASS_FIELDS = {"corporate_record": "record_type", "correspondence": "communication_type"}
# Fields per class the overlay may gap-fill: the gate's key fields the Hub leaves unlabelled.
GAP_FIELDS: dict[str, tuple[str, ...]] = {
    "corporate_record": ("entity_name", "jurisdiction", "effective_date", "filing_number", "signatories"),
    "correspondence": ("sender", "recipient", "communication_date"),
    "merger_agreement": ("document_name", "parties", "effective_date", "effective_time", "governing_law"),
    "contract": (),
    "insurance_claim": (),
}
# The dojo issue whose dataset/scorer change supersedes each class's interim labels.
SUPERSEDED_BY = {
    "corporate_record": "llm-dojo-scoring#52 (corporate-record annotation)",
    "correspondence": "llm-dojo-scoring#94 (correspondence GT)",
    "merger_agreement": "llm-dojo-scoring#95 (merger fields without GT)",
    "insurance_claim": "llm-dojo-scoring#93 (CMS mapping)",
    "contract": "CUAD Parties / Effective Date scoring (dojo scorer)",
}


def overlay_dir() -> Path:
    return repo_root() / "data" / "labels" / "interim"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def doc_sha(doc_text: str | None) -> str:
    """Short hash binding a label to the exact document text it was read from."""
    return _sha(doc_text or "")[:16]


def _expected(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("expected_fields") or {}
    return json.loads(raw) if isinstance(raw, str) else dict(raw)


def _presence(exp: Mapping[str, Any]) -> dict[str, str]:
    raw = exp.get("gt_presence") or {}
    try:
        return json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (TypeError, ValueError):
        return {}


def hub_has(exp: Mapping[str, Any], field: str) -> bool:
    """Whether the Hub row labels ``field`` (populated, not a template/absence marker)."""
    pres = _presence(exp).get(field)
    if pres is not None:
        return pres == "populated"
    value = exp.get(field)
    return value not in (None, "", "nan", [], {}, "[]", "{}")


def _empty(value: Any) -> bool:
    return value in (None, "", [], {}) or (isinstance(value, str) and value.strip().lower() in {"none", "null", "n/a"})


_TOKEN = re.compile(r"[a-z0-9]+")
_ANNOTATION = re.compile(r"\((?:[^()]*)\)|\"[^\"]*\"|“[^”]*”")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.casefold()))


def _date_forms(value: str) -> set[str]:
    from datetime import date

    try:
        d = date.fromisoformat(value[:10])
    except ValueError:
        return set()
    month, short = d.strftime("%B"), d.strftime("%b")
    return {f"{d:%Y-%m-%d}", f"{d.month}/{d.day}/{d.year}", f"{d:%m/%d/%Y}", f"{month} {d.day}, {d.year}",
            f"{month} {d.day} {d.year}", f"{d.day} {month} {d.year}", f"{short} {d.day}, {d.year}",
            f"{short}. {d.day}, {d.year}", f"{month} {d.day}st, {d.year}", f"{month} {d.day}nd, {d.year}",
            f"{month} {d.day}rd, {d.year}", f"{month} {d.day}th, {d.year}", f"{d.day}th day of {month}, {d.year}",
            f"{d.day}th day of {month} {d.year}", f"{d.day}st day of {month}, {d.year}",
            f"{d.day}nd day of {month}, {d.year}", f"{d.day}rd day of {month}, {d.year}"}


def grounded(value: Any, doc_text: str) -> bool:
    """Every token of the value (each list element; annotations stripped) occurs in the document.

    Dates (``YYYY-MM-DD``) must appear in one of the usual written forms. Token-level, so name
    order ("Denne, Karen" / "Karen Denne") and punctuation do not matter.
    """
    if _empty(value):
        return True
    folded = re.sub(r"\s+", " ", doc_text.casefold())
    items = value if isinstance(value, list) else [value]
    doc_tokens = _tokens(doc_text)
    for item in items:
        text = str(item)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(T.*)?", text.strip()):
            forms = _date_forms(text.strip())
            if not any(f.casefold() in folded for f in forms):
                return False
            continue
        core = _ANNOTATION.sub(" ", text)
        toks = _tokens(core)
        if not toks or not toks <= doc_tokens:
            return False
    return True


def _party_core(text: str) -> str:
    return re.sub(r"\s+", " ", _ANNOTATION.sub(" ", str(text))).strip(" ,.;").casefold()


def _same_date(a: Any, b: str) -> bool:
    from dateutil import parser

    try:
        return parser.parse(str(a), fuzzy=True).date() == parser.parse(str(b), fuzzy=True).date()
    except (ValueError, OverflowError, TypeError):
        return False


#: Tokens that mark a span as a legal entity's name.
_ENTITY_SUFFIXES = frozenset({
    "inc", "incorporated", "llc", "l", "corp", "corporation", "co", "company", "ltd", "limited", "lp",
    "llp", "plc", "gmbh", "ag", "sa", "nv", "bv", "pty", "trust", "bank", "holdings", "partnership",
})


def _parties_cover_spans(value: list[Any], spans: list[str]) -> bool:
    """Whether the extracted parties are CUAD ``Parties`` spans and miss no named entity.

    Each extracted party (annotation stripped) must be a span. CUAD's ``Parties`` spans also
    hold defined terms, pronouns, abbreviations and whole "referred to as the Parties"
    sentences; those name no further party. A span that carries an entity suffix
    (``Inc.``, ``LLC``, ``Corporation`` ...) and is neither an extracted party, a defined term
    the extraction attaches, nor contained in an extracted party's name is a **missed legal
    entity**: the extraction is incomplete, and is not a correction of the Hub label.
    """
    gt = {_party_core(s) for s in spans} - {""}
    cores = [_party_core(v) for v in value]
    if not gt or not all(c in gt for c in cores):
        return False
    defined = {_party_core(m.group(0).strip("()\"“”")) for v in value for m in _ANNOTATION.finditer(str(v))}
    party_tokens = [_tokens(c) for c in cores]
    for span in gt:
        toks = _tokens(span)
        if span in cores or span in defined or any(toks <= p for p in party_tokens):
            continue
        if toks & _ENTITY_SUFFIXES and len(toks) <= 12:
            return False
    return True


def contract_correction(field: str, value: Any, exp: Mapping[str, Any]) -> str | None:
    """The basis that makes a contract value a correction of its CUAD label, or None."""
    from llm_dojo_scoring.sandbox_scoring import gt_categories

    spans = gt_categories(exp.get("cuad_clause_labels"))
    if field == "parties" and isinstance(value, list) and value and _parties_cover_spans(value, spans.get("Parties") or []):
        return "cuad_party_spans"
    if field == "effective_date" and not _empty(value):
        agreement = spans.get("Agreement Date") or []
        if not (spans.get("Effective Date") or []) and agreement and any(_same_date(value, a) for a in agreement):
            return "cuad_agreement_date"
    return None


def labels_for(row: Mapping[str, Any], fields: Mapping[str, Any], gate: Mapping[str, Any],
               truth: Mapping[str, bool]) -> dict[str, dict[str, Any]]:
    """The overlay labels of one document.

    ``fields``: the specialist's extraction; ``gate``: the gate answer (``verdict``,
    ``field_support``); ``truth``: the dojo per-field truth of the extraction (labelled fields).
    """
    cls = str(row.get("expected_doc_class") or "")
    sub = str(row.get("expected_subclass") or "")
    exp = _expected(row)
    text = str(row.get("doc_text") or "")
    support = gate.get("field_support") or {}
    # The verdict is answered apart from the field rules and separates poorly (gate vetting);
    # the field's own support decides. Only a human_review verdict (unreadable / wrong class)
    # blocks every label of the document.
    accepted = gate.get("verdict") != "human_review"
    out: dict[str, dict[str, Any]] = {}
    if cls == "insurance_claim" and sub in CMS_TABLES:
        out["cms_source_table"] = {"value": sub, "status": "derived", "basis": "cms_subclass", "hub_value": None}
    if cls in SUBCLASS_FIELDS and sub and not hub_has(exp, SUBCLASS_FIELDS[cls]):
        out[SUBCLASS_FIELDS[cls]] = {"value": sub, "status": "derived", "basis": "hub_subclass", "hub_value": None}
    for field, s in sorted(support.items()):
        if field in out:  # derived from the row: the extraction never overrides it
            continue
        value = fields.get(field)
        s = float(s)
        if field in GAP_FIELDS.get(cls, ()) and not hub_has(exp, field):
            need = NULL_SUPPORT_MIN if _empty(value) else SUPPORT_MIN
            if accepted and s >= need and grounded(value, text):
                out[field] = {"value": None if _empty(value) else value, "status": "gap_fill",
                              "basis": "gate_accepted_grounded", "support": round(s, 4)}
            continue
        if field not in truth or truth[field] or s < SUPPORT_MIN or not accepted or _empty(value):
            continue
        basis = contract_correction(field, value, exp) if cls == "contract" else None
        hub_value = exp.get(field) if field in exp else None
        if basis:
            out[field] = {"value": value, "status": "correction", "basis": basis, "support": round(s, 4),
                          "hub_value": hub_value}
        else:
            out[field] = {"value": value, "status": "disputed", "basis": "gate_vs_hub", "support": round(s, 4),
                          "hub_value": hub_value,
                          **({"hub_source": exp.get("intent_source")} if field == "intent" and exp.get("intent_source") else {})}
    for lab in out.values():
        lab["use_as_truth"] = lab["status"] in TRUTH_STATUSES
    return out


# ── reading and applying ───────────────────────────────────────────────────


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    path = (root or overlay_dir()) / "MANIFEST.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_overlay(root: Path | None = None) -> dict[str, dict[str, Any]]:
    """``{doc_id: record}`` over every class file the manifest lists."""
    root = root or overlay_dir()
    out: dict[str, dict[str, Any]] = {}
    for name in sorted((load_manifest(root).get("files") or {})):
        for rec in _jsonl(root / name):
            out[rec["doc_id"]] = rec
    return out


def verify(root: Path | None = None) -> list[str]:
    """Integrity problems of the committed overlay (empty list: consistent)."""
    root = root or overlay_dir()
    man = load_manifest(root)
    problems: list[str] = []
    if man.get("schema") != SCHEMA:
        return [f"MANIFEST.json schema {man.get('schema')!r} is not {SCHEMA!r}"]
    for name, sha in (man.get("files") or {}).items():
        path = root / name
        if not path.exists():
            problems.append(f"{name}: listed in the manifest but missing")
            continue
        if _sha(path.read_text(encoding="utf-8")) != sha:
            problems.append(f"{name}: sha256 differs from the manifest (edited by hand? rebuild with scripts/interim_labels.py build)")
        for rec in _jsonl(path):
            for field, lab in (rec.get("labels") or {}).items():
                if lab.get("status") not in STATUSES:
                    problems.append(f"{rec.get('doc_id')}.{field}: unknown status {lab.get('status')!r}")
                if lab.get("use_as_truth") != (lab.get("status") in TRUTH_STATUSES):
                    problems.append(f"{rec.get('doc_id')}.{field}: use_as_truth does not follow its status")
    extra = sorted(p.name for p in root.glob("*.jsonl") if p.name not in (man.get("files") or {}))
    problems += [f"{name}: not in the manifest" for name in extra]
    return problems


def superseded(rows: Iterable[Mapping[str, Any]], overlay: Mapping[str, Mapping[str, Any]] | None = None) -> list[tuple[str, str]]:
    """(doc_id, field) gap fills the given Hub rows now label themselves, or whose text changed."""
    overlay = load_overlay() if overlay is None else overlay
    out: list[tuple[str, str]] = []
    for row in rows:
        rec = overlay.get(str(row.get("id")))
        if not rec:
            continue
        if rec.get("doc_sha256") != doc_sha(row.get("doc_text")):
            out.append((rec["doc_id"], "*"))
            continue
        exp = _expected(row)
        out += [(rec["doc_id"], f) for f, lab in rec["labels"].items() if lab["status"] == "gap_fill" and hub_has(exp, f)]
    return out


def apply_overlay(row: Mapping[str, Any], overlay: Mapping[str, Mapping[str, Any]], *, overlay_sha: str) -> dict[str, Any]:
    """The row with its truth labels merged into ``expected_fields`` (Hub labels win).

    A gap fill never overrides a Hub label; a correction replaces the Hub value it names. A
    document whose text no longer matches the label's ``doc_sha256`` is left untouched.
    """
    out = dict(row)
    rec = overlay.get(str(row.get("id")))
    if not rec or rec.get("doc_sha256") != doc_sha(row.get("doc_text")):
        return out
    exp = _expected(row)
    pres = _presence(exp)
    applied = []
    for field, lab in sorted(rec["labels"].items()):
        if not lab.get("use_as_truth"):
            continue
        if lab["status"] in ("gap_fill", "derived") and hub_has(exp, field):
            continue
        exp[field] = lab["value"]
        # The Dojo's documented-absence status: a null truth label is "expected empty", not unlabeled
        # (``corporate_record_schema.unlabeled_fields`` drops any other status). ``interim_labels``
        # below records which fields came from the overlay.
        pres[field] = "populated" if lab["value"] is not None else "schema_documented_absence"
        applied.append(field)
    if not applied:
        return out
    if "gt_presence" in exp or pres:
        exp["gt_presence"] = json.dumps(pres, sort_keys=True)
    out["expected_fields"] = json.dumps(exp, ensure_ascii=False, sort_keys=True) if isinstance(row.get("expected_fields"), str) else exp
    out["interim_labels"] = {"fields": applied, "overlay_sha256": overlay_sha}
    return out


def overlay_fingerprint(root: Path | None = None) -> str:
    """sha256 of MANIFEST.json (which pins every file's sha): what a run lock records."""
    path = (root or overlay_dir()) / "MANIFEST.json"
    return _sha(path.read_text(encoding="utf-8")) if path.exists() else ""
