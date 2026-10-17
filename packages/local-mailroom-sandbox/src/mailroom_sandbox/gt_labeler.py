"""Chunked ground-truth labeling for mailroom-dataset Hub tag v9.1.

The labeler fills unfinished fields only. Golden CUAD clause maps and golden
MAUD clause maps are never requested. One invocation submits one chunk: at
most ``CHUNK_DOC_CAP`` documents, and only when the projected 2×L4 bill for
that chunk is at most ``CHUNK_USD_CAP``. The corpus is not labeled in one job.

Serving posture (happy medium, SAND-045):

* ``Qwen/Qwen3-14B-AWQ`` — larger than the 8B cost-eval default, and the
  largest Qwen3 checkpoint the model matrix boots on a 24 GB L4 at 32k.
* Two L4 replicas (data parallel, ``max_containers=2``). Not tensor parallel.
* ``max_num_seqs=8`` and ``max_inputs=8`` per replica so a chunk that keeps
  16 requests in flight saturates both GPUs.
* ``min_containers=0`` and a 120s scaledown so the GPUs do not stay warm
  between chunks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from langchain_agents.cuad_maud import CUAD_CLAUSE_CATEGORIES

from mailroom_sandbox.job.spec import (
    FAMILY_HF_DATA_REVISION,
    FAMILY_HF_REVISION,
    FAMILY_HF_TAG,
    HF_DEFAULT_REPO,
)

DATASET_TAG = FAMILY_HF_TAG
DATASET_REVISION = FAMILY_HF_REVISION
DATASET_DATA_REVISION = FAMILY_HF_DATA_REVISION
DATASET_REPO = HF_DEFAULT_REPO

APP_NAME = "sandbox-vllm-gt-labeler"

# Env the Modal app must actually boot with. Overrides that disagree are
# refused before deploy so a shell export cannot silently swap in 8B or an
# 80 GB GPU.
POSTURE: dict[str, str] = {
    "MODAL_VLLM_APP_NAME": APP_NAME,
    "MODAL_VLLM_MODEL": "Qwen/Qwen3-14B-AWQ",
    "MODAL_VLLM_GPU": "L4",
    "MODAL_VLLM_QUANTIZATION": "awq_marlin",
    "MODAL_VLLM_MAX_MODEL_LEN": "32768",
    "MODAL_VLLM_MAX_NUM_SEQS": "8",
    "MODAL_VLLM_GPU_MEMORY_UTILIZATION": "0.90",
    "MODAL_VLLM_ENABLE_PREFIX_CACHING": "1",
    "MODAL_VLLM_ENFORCE_EAGER": "0",
    "MODAL_VLLM_MAX_CONTAINERS": "2",
    "MODAL_VLLM_MIN_CONTAINERS": "0",
    "MODAL_VLLM_SCALEDOWN_SECONDS": "120",
    "MODAL_VLLM_ASYNC_SCHEDULING": "0",
    "MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS": '{"enable_thinking": false}',
    "MODAL_VLLM_KV_CACHE_DTYPE": "fp8",
    "MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES": "1,2,4,8",
    "MODAL_VLLM_MAX_INPUTS": "8",
}

L4_USD_PER_HOUR = 0.80
REPLICAS = 2
MAX_NUM_SEQS = 8
# Cold boot is billed once per chunk (both replicas start together).
COLD_BOOT_WALL_SECONDS = 300
SCALEDOWN_SECONDS = 120
SECONDS_PER_SLOT = 45.0
CHUNK_DOC_CAP = 40
CHUNK_USD_CAP = 2.00
CLIENT_IN_FLIGHT = REPLICAS * MAX_NUM_SEQS

CORRESPONDENCE_INTENTS = (
    "payment_demand",
    "notice",
    "analysis",
    "request",
    "update",
    "meeting_invite",
    "press_communication",
    "other",
)
CORPORATE_INTENTS = (
    "entity_formation",
    "governance_rules",
    "corporate_action_approval",
    "authority_delegation",
    "investor_rights",
    "other",
)
INSURANCE_INTENTS = (
    "claim_filing",
    "coverage_determination",
    "claim_data_record",
)
CONTRACT_INTENTS = ("material_agreement",)
COVERAGE_DETERMINATIONS = ("approved", "pending", "denied")
CLAIM_TYPES = ("health", "auto", "property")
SENTIMENT_LABELS = ("positive", "negative", "neutral")

GOLDEN_CUAD_FIELDS = frozenset({
    "cuad_clause_labels", "label_evidence", "clause_count",
})
GOLDEN_MAUD_FIELDS = frozenset({
    "maud_clause_labels", "label_evidence", "maud_label_count",
})

_WINDOW_CHARS = 12_000


class LabelSpendError(RuntimeError):
    """A labeling submission would exceed the per-chunk spend cap."""


class GoldenLabelError(ValueError):
    """The request asks the model to rewrite a golden CUAD or MAUD field."""


def apply_posture_env(environ: dict[str, str] | None = None) -> dict[str, str]:
    """Set missing ``MODAL_VLLM_*`` keys to the labeling posture.

    Existing exports are left in place so ``assert_posture`` can refuse a
    disagreement instead of quietly overwriting it.
    """
    env = environ if environ is not None else __import__("os").environ
    for key, value in POSTURE.items():
        env.setdefault(key, value)
    return env


def assert_posture(environ: Mapping[str, str] | None = None) -> None:
    """Raise unless the effective env is exactly the 2×L4 14B-AWQ posture."""
    import os

    env = environ if environ is not None else os.environ
    problems: list[str] = []
    for key, want in POSTURE.items():
        have = str(env.get(key, "")).strip()
        if have != want:
            problems.append(f"{key}={have!r} (want {want!r})")
    gpu = str(env.get("MODAL_VLLM_GPU", ""))
    if ":" in gpu:
        problems.append(
            f"MODAL_VLLM_GPU={gpu!r} is tensor-parallel; use two containers"
        )
    tp = str(env.get("MODAL_VLLM_TP_SIZE", "") or "1").strip()
    if tp not in ("", "1"):
        problems.append(f"MODAL_VLLM_TP_SIZE={tp!r} (want 1)")
    if problems:
        raise LabelSpendError(
            "refusing GT labeler deploy:\n- " + "\n- ".join(problems)
        )


def slots_for(target: Mapping[str, Any]) -> int:
    """Request slots one document consumes. Overflow docs take two windows."""
    if str(target.get("context_window_band") or "") == ">32k":
        return 2
    return 1


def project_usd(
    n_slots: int,
    *,
    seconds_per_slot: float = SECONDS_PER_SLOT,
) -> float:
    """Projected bill for one chunk on two L4s, including boot and scaledown.

    Both replicas are billed for the wall clock. Work wall is the slot time
    divided by the 16-way in-flight cap, because that is the concurrency the
    client must hold to keep both GPUs busy.
    """
    if n_slots < 0:
        raise LabelSpendError("n_slots must be >= 0")
    slots = max(n_slots, 0)
    work_wall = (slots * seconds_per_slot) / CLIENT_IN_FLIGHT if slots else 0.0
    wall = COLD_BOOT_WALL_SECONDS + work_wall + SCALEDOWN_SECONDS
    return wall / 3600.0 * L4_USD_PER_HOUR * REPLICAS


@dataclass(frozen=True)
class LabelChunk:
    index: int
    targets: tuple[Mapping[str, Any], ...]
    slots: int
    projected_usd: float

    @property
    def doc_count(self) -> int:
        return len(self.targets)

    def manifest(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "doc_count": self.doc_count,
            "slots": self.slots,
            "projected_usd": round(self.projected_usd, 4),
            "usd_cap": CHUNK_USD_CAP,
            "doc_cap": CHUNK_DOC_CAP,
            "dataset": DATASET_REPO,
            "dataset_tag": DATASET_TAG,
            "dataset_revision": DATASET_REVISION,
            "model": POSTURE["MODAL_VLLM_MODEL"],
            "gpu": POSTURE["MODAL_VLLM_GPU"],
            "replicas": REPLICAS,
            "in_flight": CLIENT_IN_FLIGHT,
            "filenames": [str(t.get("filename") or t.get("id") or "") for t in self.targets],
        }


def plan_chunks(
    targets: Sequence[Mapping[str, Any]],
    *,
    seconds_per_slot: float = SECONDS_PER_SLOT,
) -> list[LabelChunk]:
    """Split targets into chunks that each fit the doc cap and the USD cap."""
    chunks: list[LabelChunk] = []
    current: list[Mapping[str, Any]] = []
    current_slots = 0

    def _close() -> None:
        nonlocal current, current_slots
        if not current:
            return
        usd = project_usd(current_slots, seconds_per_slot=seconds_per_slot)
        chunks.append(
            LabelChunk(
                index=len(chunks),
                targets=tuple(current),
                slots=current_slots,
                projected_usd=usd,
            )
        )
        current = []
        current_slots = 0

    for target in targets:
        need = slots_for(target)
        if project_usd(need, seconds_per_slot=seconds_per_slot) > CHUNK_USD_CAP:
            raise LabelSpendError(
                "one document projects over the chunk cap; lower seconds_per_slot "
                "or raise the cap explicitly"
            )
        would_docs = len(current) + 1
        would_usd = project_usd(current_slots + need, seconds_per_slot=seconds_per_slot)
        if current and (would_docs > CHUNK_DOC_CAP or would_usd > CHUNK_USD_CAP):
            _close()
        current.append(target)
        current_slots += need
    _close()
    for chunk in chunks:
        assert_one_chunk(chunk)
    return chunks


def assert_one_chunk(chunk: LabelChunk) -> None:
    """Refuse a submission that is not a single under-cap chunk."""
    if chunk.doc_count > CHUNK_DOC_CAP or chunk.projected_usd > CHUNK_USD_CAP + 1e-9:
        raise LabelSpendError(
            f"refusing chunk index={chunk.index} docs={chunk.doc_count} "
            f"projected_usd={chunk.projected_usd:.4f} "
            f"(caps {CHUNK_DOC_CAP} docs / ${CHUNK_USD_CAP:.2f})"
        )


def next_chunk(
    targets: Sequence[Mapping[str, Any]],
    done_ids: set[str] | None = None,
    *,
    seconds_per_slot: float = SECONDS_PER_SLOT,
) -> LabelChunk | None:
    """The first unfinished chunk. Never returns the rest of the queue."""
    done = done_ids or set()
    remaining = [
        t for t in targets if str(t.get("id") or t.get("filename") or "") not in done
    ]
    planned = plan_chunks(remaining, seconds_per_slot=seconds_per_slot)
    if not planned:
        return None
    chunk = planned[0]
    assert_one_chunk(chunk)
    return chunk


def _golden_fields(target: Mapping[str, Any]) -> frozenset[str]:
    doc_class = str(target.get("doc_class") or target.get("expected") or "")
    source = str(target.get("source_corpus") or "")
    if doc_class == "merger_agreement":
        return GOLDEN_MAUD_FIELDS
    if doc_class == "contract" and source in ("", "theatticusproject/cuad"):
        # EX-10 rows set source_corpus to sec_edgar. Anything else on the
        # contract class is the golden CUAD draw.
        if str(target.get("source_dataset") or "") == "sec_edgar":
            return frozenset()
        return GOLDEN_CUAD_FIELDS
    return frozenset()


def assert_labelable(target: Mapping[str, Any]) -> list[str]:
    """Return the requested fields, or raise if any of them are golden."""
    fields = [str(f) for f in (target.get("fields") or [])]
    if not fields:
        raise ValueError("label target has no fields")
    blocked = _golden_fields(target)
    hit = [f for f in fields if f in blocked]
    if hit:
        raise GoldenLabelError(
            f"{target.get('filename')}: refusing golden fields {hit}"
        )
    return fields


def _intent_vocab(doc_class: str) -> tuple[str, ...]:
    return {
        "correspondence": CORRESPONDENCE_INTENTS,
        "corporate_record": CORPORATE_INTENTS,
        "insurance_claim": INSURANCE_INTENTS,
        "contract": CONTRACT_INTENTS,
    }.get(doc_class, ())


def _field_instruction(doc_class: str, field: str) -> str:
    if field == "intent":
        vocab = _intent_vocab(doc_class)
        labels = ", ".join(vocab) if vocab else "(no vocabulary for this class)"
        return (
            "intent: exactly one label from this closed list, the label the "
            f"text supports: {labels}. Do not invent a new label."
        )
    if field == "subject_matter":
        return (
            "subject_matter: one sentence grounded in the text. Name the "
            "parties or the event and what the document is doing. Do not "
            "answer with only 'Correspondence concerning <topic>.'"
        )
    if field == "keywords":
        return (
            "keywords: a JSON array of 3 to 8 short strings that appear in "
            "the document. No duplicates, no empty strings."
        )
    if field == "cuad_clause_labels":
        names = "; ".join(CUAD_CLAUSE_CATEGORIES)
        return (
            "cuad_clause_labels: Atticus CUAD spans. Copy the short operative "
            "excerpt a CUAD annotator would highlight — the date, the party "
            "names, or the one sentence that states the clause. Do not paste "
            "an entire article. \"text\" must be copied from the document, "
            "not paraphrased. Use [] when the category is absent. Include "
            f"every one of these 41 keys. Categories: {names}."
        )
    if field == "sentiment_label":
        return (
            "sentiment_label: one of "
            + ", ".join(SENTIMENT_LABELS)
            + "."
        )
    if field == "sentiment_score":
        return "sentiment_score: a number from -1 to 1."
    if field == "coverage_determination":
        return (
            "coverage_determination: one of "
            + ", ".join(COVERAGE_DETERMINATIONS)
            + ". Use pending when the text does not adjudicate the claim."
        )
    if field == "claim_type":
        return "claim_type: one of " + ", ".join(CLAIM_TYPES) + "."
    if field == "denial_reasons":
        return (
            "denial_reasons: a JSON array of short reasons copied from the "
            "text. [] when the claim is not denied."
        )
    if field == "supporting_documents":
        return (
            "supporting_documents: a JSON array of document names the text "
            "actually mentions. [] when none are mentioned."
        )
    if field in ("date_of_loss", "date_filed"):
        return f"{field}: YYYY-MM-DD as printed in the document, or N/A when the source prints N/A."
    if field == "claimed_amount":
        return "claimed_amount: the number printed in the document, without inventing cents."
    if field in ("intent_source", "intent_status", "intent_confidence"):
        return (
            f"{field}: leave this to the bookkeeping step. If you must emit "
            "it, use intent_source=llm_zero_shot, intent_status=auto_labeled, "
            "and intent_confidence between 0 and 1."
        )
    return (
        f"{field}: copy the value from the document. If the document does "
        "not state it, abstain instead of guessing."
    )


def _document_block(text: str, band: str) -> str:
    body = text or ""
    if band == ">32k" or len(body) > 100_000:
        head = body[:_WINDOW_CHARS]
        tail = body[-_WINDOW_CHARS:]
        return (
            "The document is longer than the 32k context window. Two excerpts "
            "follow. If the value would sit only in the omitted middle, abstain.\n\n"
            "--- BEGIN HEAD ---\n"
            f"{head}\n"
            "--- END HEAD ---\n\n"
            "--- BEGIN TAIL ---\n"
            f"{tail}\n"
            "--- END TAIL ---"
        )
    return "--- BEGIN DOCUMENT ---\n" + body + "\n--- END DOCUMENT ---"


def build_messages(target: Mapping[str, Any]) -> list[dict[str, str]]:
    """Chat messages for one document. Asks only for that document's fields."""
    fields = assert_labelable(target)
    doc_class = str(target.get("doc_class") or target.get("expected") or "")
    subclass = str(target.get("expected_subclass") or "")
    band = str(target.get("context_window_band") or "")
    instructions = "\n".join(
        f"{i}. {_field_instruction(doc_class, field)}"
        for i, field in enumerate(fields, start=1)
    )
    system = (
        "You write missing ground-truth labels for one legal document from "
        f"{DATASET_REPO} tag {DATASET_TAG}.\n"
        "Return one JSON object and nothing else, with this shape:\n"
        '{"fields": {<requested field>: <value>, ...}, '
        '"abstain": [{"field": "<name>", "reason": "<short reason>"}]}\n'
        "Rules:\n"
        "- Every requested field appears in fields or in abstain, not both.\n"
        "- Copy values from the document. Do not guess a party, date, amount, "
        "or clause span that is not printed.\n"
        "- Do not emit fields you were not asked for.\n"
        "- Do not relabel CUAD clause maps from the Atticus CUAD draw or MAUD "
        "clause maps. Those are golden and are never requested.\n"
        "- Closed lists are mandatory. A value outside the list is invalid.\n"
        "- JSON arrays and objects must be raw JSON, not a string wrapped in quotes."
    )
    user = (
        f"document class: {doc_class}\n"
        f"subclass: {subclass or '(none)'}\n"
        f"filename: {target.get('filename') or ''}\n"
        f"context band: {band or '(unknown)'}\n"
        f"requested fields: {', '.join(fields)}\n\n"
        "Field instructions:\n"
        f"{instructions}\n\n"
        + _document_block(str(target.get("doc_text") or ""), band)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def validate_label_response(
    requested: Sequence[str],
    payload: Mapping[str, Any],
) -> list[str]:
    """Structural checks on one model JSON object. Empty means accept."""
    errors: list[str] = []
    extra = set(payload) - {"fields", "abstain"}
    if extra:
        errors.append(f"unexpected keys {sorted(extra)}")
    fields = payload.get("fields")
    abstain = payload.get("abstain")
    if not isinstance(fields, dict):
        return errors + ["fields must be an object"]
    if not isinstance(abstain, list):
        return errors + ["abstain must be a list"]
    asked = [str(f) for f in requested]
    abstained: set[str] = set()
    for item in abstain:
        if not isinstance(item, dict) or not str(item.get("field") or "").strip():
            errors.append("abstain entries need a field")
            continue
        if not str(item.get("reason") or "").strip():
            errors.append(f"abstain {item.get('field')} needs a reason")
        abstained.add(str(item["field"]))
    for name in fields:
        if name not in asked:
            errors.append(f"unrequested field {name}")
    for name in asked:
        in_fields = name in fields
        in_abstain = name in abstained
        if in_fields == in_abstain:
            errors.append(f"{name} must be in fields or abstain, not both and not neither")
    cuad = fields.get("cuad_clause_labels")
    if isinstance(cuad, dict):
        missing = [k for k in CUAD_CLAUSE_CATEGORIES if k not in cuad]
        unknown = [k for k in cuad if k not in CUAD_CLAUSE_CATEGORIES]
        if missing:
            errors.append(f"cuad_clause_labels missing {len(missing)} categories")
        if unknown:
            errors.append(f"cuad_clause_labels unknown keys {unknown[:3]}")
        for key, value in cuad.items():
            if key not in CUAD_CLAUSE_CATEGORIES:
                continue
            if not isinstance(value, list):
                errors.append(f"{key} must be a list")
                continue
            for span in value:
                if not isinstance(span, dict) or not str(span.get("text") or "").strip():
                    errors.append(f"{key} spans need verbatim text")
                    break
    return errors


def response_json_schema(requested: Sequence[str]) -> dict[str, Any]:
    """Object schema passed to vLLM ``response_format`` for one document."""
    properties = {
        name: {"description": _field_instruction("", name)}
        for name in requested
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["fields", "abstain"],
        "properties": {
            "fields": {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
            },
            "abstain": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["field", "reason"],
                    "properties": {
                        "field": {"type": "string", "enum": list(requested)},
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    }


def loads_response(text: str) -> dict[str, Any]:
    """Parse a model message. Raises ``json.JSONDecodeError`` on failure."""
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise json.JSONDecodeError("response is not an object", text, 0)
    return payload


# CUAD answer spans are short. The golden draw's 90th percentile is 584
# characters and the longest published span is under 4,000.
MAX_CUAD_SPAN_CHARS = 4000
MIN_PRESENT_CUAD_CATEGORIES = 4


def cuad_span_schema() -> dict[str, Any]:
    """Guided-JSON schema: present clauses only, as verbatim excerpts.

    Absent categories are omitted here and filled with ``[]`` when the
    payload is normalized into the 41-key Hub object. Asking the model to
    emit forty-one empty lists wastes the decode budget and truncates the
    spans that matter.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["clauses"],
        "properties": {
            "clauses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["category", "text"],
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": list(CUAD_CLAUSE_CATEGORIES),
                        },
                        "text": {"type": "string"},
                    },
                },
            }
        },
    }


def build_cuad_messages(target: Mapping[str, Any]) -> list[dict[str, str]]:
    """CUAD-style messages for one EX-10 contract.

    Same document window as ``build_messages``. The JSON shape is the
    present-clause list from ``cuad_span_schema``, which ``normalize_cuad_labels``
    turns into the Hub 41-key object.
    """
    fields = assert_labelable(target)
    if fields != ["cuad_clause_labels"]:
        raise ValueError(
            "build_cuad_messages is the EX-10 clause pass; "
            f"got {fields}"
        )
    doc_class = str(target.get("doc_class") or target.get("expected") or "")
    subclass = str(target.get("expected_subclass") or "")
    band = str(target.get("context_window_band") or "")
    names = "; ".join(CUAD_CLAUSE_CATEGORIES)
    system = (
        "You annotate one SEC EDGAR exhibit in the Atticus CUAD style so it "
        f"can sit beside the golden CUAD draw in {DATASET_REPO} tag {DATASET_TAG}.\n"
        "Return one JSON object and nothing else:\n"
        '{"clauses": [{"category": "<exact CUAD name>", "text": "<verbatim span>"}]}\n'
        "Rules:\n"
        "- category is exactly one of the 41 Atticus names.\n"
        "- text is copied from the document, character for character. "
        "Do not paraphrase, summarize, or modernize the wording.\n"
        "- Highlight the short operative span: the date, the party names, or "
        "the sentence that states the clause. Do not paste an entire article "
        "or the whole document.\n"
        "- Markdown emphasis marks (* and _) may wrap words in the filing. "
        "Copy the words themselves.\n"
        "- Omit categories that are absent. Do not invent a clause the text "
        "does not contain.\n"
        "- Document Name is the title in the opening lines: the exhibit "
        "heading, letter agreement, or amendment title. Parties are the named "
        "person and company in the salutation and the first paragraph, "
        "including a letter that addresses someone as you. Copy those when "
        "they are printed.\n"
        "- If you were shown only the head and the tail, annotate only those "
        "excerpts."
    )
    user = (
        f"document class: {doc_class}\n"
        f"CUAD family: {subclass or '(none)'}\n"
        f"filename: {target.get('filename') or ''}\n"
        "Annotate every present category. Exact names:\n"
        f"{names}\n\n"
        + _document_block(str(target.get("doc_text") or ""), band)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _norm_index(text: str, skip: str = "") -> tuple[str, list[int]]:
    """Collapse whitespace and remember the original index of each kept char."""
    chars: list[str] = []
    indexes: list[int] = []
    pending_space: int | None = None
    for index, char in enumerate(text):
        if char in skip:
            continue
        if char.isspace():
            if pending_space is None and chars:
                pending_space = index
            continue
        if pending_space is not None:
            chars.append(" ")
            indexes.append(pending_space)
            pending_space = None
        chars.append(char)
        indexes.append(index)
    return "".join(chars), indexes


def _slice_folded(
    document: str,
    folded: str,
    indexes: list[int],
    wanted: str,
) -> tuple[int, str] | None:
    wanted = wanted.strip()
    if len(wanted) < 2 or not indexes:
        return None
    at = folded.find(wanted)
    if at < 0:
        return None
    start = indexes[at]
    end = indexes[at + len(wanted) - 1] + 1
    sliced = document[start:end]
    if len(sliced) > MAX_CUAD_SPAN_CHARS:
        return None
    if len(sliced) > max(len(wanted) * 3, len(wanted) + 80):
        return None
    return start, sliced


def locate_verbatim(document: str, text: str) -> tuple[int, str] | None:
    """Find ``text`` in ``document`` and return the exact document slice.

    Exact match wins. A whitespace-only difference still counts, and the
    returned text is the document's own characters so the stored span cannot
    drift from the filing.
    """
    snippet = " ".join(str(text or "").split())
    if len(snippet) < 2 or not document:
        return None
    exact = document.find(str(text).strip())
    if exact >= 0:
        taken = str(text).strip()
        return exact, document[exact:exact + len(taken)]
    folded, indexes = _norm_index(document)
    wanted, _ = _norm_index(snippet)
    hit = _slice_folded(document, folded, indexes, wanted)
    if hit is not None:
        return hit
    # Filings converted from EDGAR HTML wrap words in markdown emphasis.
    # A span that copies the words and drops * / _ still snaps onto the
    # document's own characters, emphasis marks included.
    folded, indexes = _norm_index(document, skip="*_")
    wanted, _ = _norm_index(snippet, skip="*_")
    return _slice_folded(document, folded, indexes, wanted)


def _clause_items(payload: Mapping[str, Any]) -> list[tuple[str, str]]:
    clauses = payload.get("clauses")
    if isinstance(clauses, list):
        items: list[tuple[str, str]] = []
        for item in clauses:
            if not isinstance(item, dict):
                continue
            items.append((str(item.get("category") or ""), str(item.get("text") or "")))
        return items
    fields = payload.get("fields")
    cuad = fields.get("cuad_clause_labels") if isinstance(fields, dict) else None
    if not isinstance(cuad, dict):
        return []
    items = []
    for category, spans in cuad.items():
        if isinstance(spans, list):
            for span in spans:
                if isinstance(span, dict):
                    items.append((str(category), str(span.get("text") or "")))
                elif isinstance(span, str):
                    items.append((str(category), span))
        elif isinstance(spans, str):
            items.append((str(category), spans))
    return items


def normalize_cuad_labels(
    document: str,
    payload: Mapping[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """Hub 41-key CUAD object plus reasons for spans that were dropped.

    Every kept span is a verbatim slice of ``document``. Missing categories
    are ``[]``. ``start`` is the character offset of that slice.
    """
    labels: dict[str, list[dict[str, Any]]] = {
        name: [] for name in CUAD_CLAUSE_CATEGORIES
    }
    dropped: list[str] = []
    seen: set[tuple[str, str]] = set()
    allowed = set(CUAD_CLAUSE_CATEGORIES)
    for category, text in _clause_items(payload):
        if category not in allowed:
            dropped.append(f"unknown category {category!r}")
            continue
        located = locate_verbatim(document, text)
        if located is None:
            dropped.append(f"{category}: not verbatim")
            continue
        start, exact = located
        key = (category, exact)
        if key in seen:
            continue
        seen.add(key)
        labels[category].append({"start": start, "text": exact})
    for spans in labels.values():
        spans.sort(key=lambda item: int(item["start"]))
    return labels, dropped


def cuad_label_problems(labels: Mapping[str, list]) -> list[str]:
    """Quality bar against the golden CUAD draw (median 13 present categories)."""
    problems: list[str] = []
    if set(labels) != set(CUAD_CLAUSE_CATEGORIES):
        problems.append("labels are not the 41 CUAD categories")
    present = [name for name, spans in labels.items() if spans]
    if len(present) < MIN_PRESENT_CUAD_CATEGORIES:
        problems.append(
            f"{len(present)} present categories; golden contracts are annotated "
            f"across the clause inventory (floor {MIN_PRESENT_CUAD_CATEGORIES})"
        )
    if not any(labels.get(name) for name in ("Document Name", "Parties")):
        problems.append("neither Document Name nor Parties was recovered")
    return problems


def fold_label_journal(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Collapse an append-only label journal to one record per document.

    An accepted record sticks. A later failed attempt does not erase it.
    Until a document is accepted, the record with more verbatim spans is kept
    so a weaker retry does not discard a better partial annotation.
    """
    folded: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        key = str(row.get("id") or row.get("filename") or "")
        if not key:
            continue
        current = folded.get(key)
        if current is None:
            folded[key] = row
            continue
        current_ok = bool(current.get("accepted"))
        row_ok = bool(row.get("accepted"))
        if row_ok and not current_ok:
            folded[key] = row
        elif current_ok and not row_ok:
            continue
        elif row_ok and current_ok:
            folded[key] = row
        elif int(row.get("span_count") or 0) > int(current.get("span_count") or 0):
            folded[key] = row
    return folded


def accepted_ids(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    """Filenames that already have an accepted label and must not be re-sent."""
    return {key for key, row in fold_label_journal(rows).items() if row.get("accepted")}


def label_evidence_for(labels: Mapping[str, list]) -> str:
    """Same evidence line the v9 builder writes for a populated CUAD map."""
    names = sorted(name for name, spans in labels.items() if spans)
    if not names:
        return ""
    return "CUAD-annotated clauses: " + ", ".join(names)
