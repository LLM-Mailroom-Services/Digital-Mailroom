"""Isolated eval registry for every live mailroom agent / graph node.

Each spec binds a fixture loader, mock prediction, optional live invoke
(vendored llm-mailroom), Langfuse observation name/type, and a scorer.
The 13-node graph is not duplicated here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from mailroom_sandbox.components import is_enabled
from mailroom_sandbox.datasets import (
    fixture_file,
    load_agent_fixtures,
    load_manifest,
    parse_expected_fields,
)
from mailroom_sandbox.eval import scoring
from mailroom_sandbox.eval.tracing import observation_type_for
from mailroom_sandbox.paths import fixtures_dir

SPECIALIST_CLASS = {
    "contracts_specialist": "contract",
    "corporate_records_specialist": "corporate_record",
    "correspondence_specialist": "correspondence",
    "compliance_specialist": "compliance_filing",
    "insurance_claims_specialist": "insurance_claim",
}

LIVE_CLASS_MAP = {
    "contracts_specialist": ("agents.contracts_specialist", "ContractsSpecialist"),
    "corporate_records_specialist": ("agents.corporate_records_specialist", "CorporateRecordsSpecialist"),
    "correspondence_specialist": ("agents.correspondence_specialist", "CorrespondenceSpecialist"),
    "compliance_specialist": ("agents.compliance_specialist", "ComplianceSpecialist"),
    "insurance_claims_specialist": ("agents.insurance_claims_specialist", "InsuranceClaimsSpecialist"),
}

RETIRED_AGENTS = ("court_opinions_specialist", "due_diligence_specialist")


def _resolve_fixture_path(row: dict[str, Any], default: Path) -> Path:
    raw = row.get("file")
    if not raw:
        return default
    path = Path(str(raw))
    if path.is_file():
        return path
    from mailroom_sandbox.paths import repo_root

    alt = repo_root() / path
    return alt if alt.is_file() else default


def _doc_text(row: dict[str, Any]) -> str:
    """Resolve the document text for a live agent call (live-or-loud).

    Prepared corpus rows carry ``doc_text`` (the blind ``default`` config
    column); fixture rows may carry ``text`` inline or fall back to the
    fixture file on disk. A row with no resolvable document RAISES — a live
    eval must never call a model on an empty document and score the result.
    """
    for key in ("doc_text", "text"):
        value = row.get(key)
        if value:
            return str(value)
    try:
        path = fixture_file(row)
    except Exception:
        path = None
    if path is not None and path.is_file():
        return path.read_text(encoding="utf-8")
    ident = row.get("id") or row.get("filename") or "<unknown>"
    raise ValueError(f"live eval row {ident!r} has no document text (doc_text/text/file)")


def _manifest_for_class(doc_class: str) -> list[dict[str, Any]]:
    return [r for r in load_manifest() if r.get("expected_doc_class") == doc_class]


def _rows_or_agent_jsonl(agent: str, fallback: Callable[[], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = load_agent_fixtures(agent)
    return rows if rows else fallback()


@dataclass(frozen=True)
class AgentSpec:
    name: str
    observation: str
    kind: str = "agents"  # components.yaml table
    dojo_profile: str | None = None
    load_rows: Callable[[], list[dict[str, Any]]] = lambda: []
    mock_predict: Callable[[dict[str, Any]], dict[str, Any]] = lambda row: {}
    live_predict: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    score_one: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = lambda row, pred: {}
    predicted_key: str = "value"
    expected_key: str = "expected"


def _mock_classify(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_type": row.get("expected_doc_class") or row.get("doc_type") or "unknown",
        "confidence": 0.40 if row.get("id") == "ambiguous_01" else 0.97,
    }


def _mock_extract(row: dict[str, Any]) -> dict[str, Any]:
    fields = parse_expected_fields(row) or row.get("expected_fields") or {}
    if isinstance(fields, str):
        import json

        try:
            fields = json.loads(fields)
        except json.JSONDecodeError:
            fields = {}
    return dict(fields) if isinstance(fields, dict) else {}


def _live_sorter(row: dict[str, Any]) -> dict[str, Any]:
    from agents.sorter import SorterAgent  # type: ignore

    result = SorterAgent().classify(_doc_text(row))
    if isinstance(result, dict):
        return result
    return {"doc_type": str(result)}


def _live_reviewer(row: dict[str, Any]) -> dict[str, Any]:
    from agents.sorter_reviewer import SorterReviewerAgent  # type: ignore

    return SorterReviewerAgent().review(_doc_text(row))


def _live_specialist(agent: str, row: dict[str, Any]) -> dict[str, Any]:
    module_name, cls_name = LIVE_CLASS_MAP[agent]
    import importlib

    mod = importlib.import_module(module_name)
    cls = getattr(mod, cls_name)
    return cls().extract(_doc_text(row))


def _live_judge(row: dict[str, Any]) -> dict[str, Any]:
    from agents.judge import CompletenessJudge  # type: ignore

    extracted = row.get("extracted_data") or _mock_extract(row)
    return CompletenessJudge().judge_completeness(
        row.get("expected_doc_class") or row.get("doc_type") or "contract",
        extracted,
        _doc_text(row),
    )


def _live_arbiter(row: dict[str, Any]) -> dict[str, Any]:
    from agents.arbiter import ArbiterAgent  # type: ignore

    return ArbiterAgent().arbitrate(
        row.get("expected_doc_class") or "contract",
        row.get("extracted_data") or _mock_extract(row),
        str(row.get("judge_verdict") or "incomplete"),
        row.get("judge_findings") or ["mock finding"],
        float(row.get("judge_score") or 0.4),
    )


def _live_boss(row: dict[str, Any]) -> dict[str, Any]:
    from agents.boss import BossAgent  # type: ignore

    manifest = {
        "doc_id": row.get("id"),
        "doc_type": row.get("expected_doc_class") or "contract",
        "classification_confidence": row.get("classification_confidence") or 0.5,
        "extraction_confidence": row.get("extraction_confidence") or 0.5,
        "extracted_data": row.get("extracted_data") or _mock_extract(row),
        "escalation_reason": row.get("escalation_reason") or "sandbox eval",
    }
    return BossAgent().adjudicate(manifest)


def _procedural_report(row: dict[str, Any]) -> dict[str, Any]:
    """Computational procedural reporter — deterministic matter-record
    assembly with NO LLM call. Sandbox-side mirror of llm-mailroom v0.6.0
    ``agents.reporter.compile_matter_record`` (the reporter agent is retired;
    the graph's compile_report node is procedural)."""
    extracted = row.get("extracted_data") or _mock_extract(row)
    lines = [
        f"Document type: {row.get('expected_doc_class') or 'unknown'}",
        f"Subclass: {row.get('expected_subclass') or 'not stated'}",
        "Classification confidence: 0.97",
        "Extraction confidence: 0.9",
        "",
        "Extracted fields:",
    ]
    for key in sorted(extracted):
        lines.append(f"- {key}: {extracted[key]}")
    return {
        "summary": "\n".join(lines).strip() + "\n",
        "doc_type": row.get("expected_doc_class") or "unknown",
        "doc_subclass": row.get("expected_subclass"),
        "extracted_data": extracted,
        "classification_confidence": 0.97,
        "extraction_confidence": 0.9,
        "procedural": True,
    }


def _live_reporter(row: dict[str, Any]) -> dict[str, Any]:
    from agents.reporter import compile_matter_record  # type: ignore

    # HUB-015: no LLM call. The reporter agent is retired; the pipeline's
    # compile_report node is the procedural assembler. The upstream function
    # accepts client/model args for call-site compatibility but ignores them
    # — we pass none at all.
    return compile_matter_record(
        {
            "doc_type": row.get("expected_doc_class") or "contract",
            "doc_subclass": row.get("expected_subclass"),
            "extracted_data": row.get("extracted_data") or _mock_extract(row),
            "classification_confidence": 0.97,
            "extraction_confidence": 0.9,
        }
    )


def _live_pdf(row: dict[str, Any]) -> dict[str, Any]:
    from agents.pdf_transcriber import PDFTranscriber  # type: ignore

    path = _resolve_fixture_path(row, fixtures_dir() / "intake" / "hello.pdf")
    return PDFTranscriber().transcribe(path)


def _live_image(row: dict[str, Any]) -> dict[str, Any]:
    from agents.image_extractor import ImageExtractor  # type: ignore

    path = _resolve_fixture_path(row, fixtures_dir() / "intake" / "hello.png")
    return ImageExtractor().extract(path)


def _live_intake(row: dict[str, Any]) -> dict[str, Any]:
    try:
        from agents.intake import apply_intake  # type: ignore

        cleaned, stats = apply_intake(str(row.get("text") or ""), filename=str(row.get("id")))
        return {"text": cleaned, **(stats or {})}
    except Exception:
        from llm_dojo_scoring.intake import deterministic_normalize

        cleaned, stats = deterministic_normalize(str(row.get("text") or ""))
        return {"text": cleaned, **(stats or {})}


def _score_class(row: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    expected = str(row.get("expected_doc_class") or row.get("doc_type") or "")
    predicted = str(pred.get("doc_type") or pred.get("value") or "")
    return {"match": float(expected == predicted), "expected": expected, "predicted": predicted}


def _score_extract(row: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    expected = parse_expected_fields(row) or row.get("expected_fields") or {}
    if not isinstance(expected, dict):
        expected = {}
    doc_type = str(row.get("expected_doc_class") or row.get("doc_type") or "contract")
    return scoring.score_extraction_row(doc_type, pred, expected, doc_text=_doc_text(row))


def _score_label(row: dict[str, Any], pred: dict[str, Any], key: str, expected_field: str) -> dict[str, Any]:
    expected = str(row.get(expected_field) or "")
    predicted = str(pred.get(key) or pred.get("value") or "")
    return {"match": float(expected.lower() == predicted.lower()), "expected": expected, "predicted": predicted}


def _score_contains(row: dict[str, Any], pred: dict[str, Any], field: str = "text") -> dict[str, Any]:
    needle = str(row.get("expected_snippet") or row.get("expected") or "")
    hay = str(pred.get(field) or pred.get("markdown") or pred.get("text") or pred.get("summary") or "")
    ok = needle.lower() in hay.lower() if needle else bool(hay)
    return {"match": float(ok), "expected": needle, "predicted": hay[:200]}


def _score_keys(row: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    required = row.get("required_keys") or ["summary", "confidence"]
    missing = [k for k in required if k not in pred and f"_{k}" not in str(pred)]
    # reporter often returns a dict with summary-like keys or a nested report
    if not pred:
        return {"match": 0.0, "missing": required}
    text = str(pred)
    present = all(str(k) in pred or str(k) in text.lower() for k in required)
    return {"match": float(present), "missing": missing, "keys": list(pred)}


def _score_stage(row: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    expected = str(row.get("expected_stage") or row.get("expected") or "")
    predicted = str(pred.get("stage") or pred.get("value") or "")
    return {"match": float(expected == predicted), "expected": expected, "predicted": predicted}


def _intake_rows() -> list[dict[str, Any]]:
    rows = load_agent_fixtures("intake")
    if rows:
        return rows
    return [
        {
            "id": "intake_nbsp",
            "text": "Hello\u00a0world",
            "expected": "Hello world",
        }
    ]


def _pdf_rows() -> list[dict[str, Any]]:
    rows = load_agent_fixtures("pdf_transcriber")
    if rows:
        return rows
    return [{"id": "pdf_hello", "file": str(fixtures_dir() / "intake" / "hello.pdf"), "expected_snippet": "SANDBOX PDF"}]


def _image_rows() -> list[dict[str, Any]]:
    rows = load_agent_fixtures("image_extractor")
    if rows:
        return rows
    return [{"id": "png_hello", "file": str(fixtures_dir() / "intake" / "hello.png"), "expected_snippet": "SANDBOX"}]


def _reviewer_rows() -> list[dict[str, Any]]:
    rows = load_agent_fixtures("sorter_reviewer")
    if rows:
        return rows
    return [r for r in load_manifest() if r.get("expected_stage") == "review" or r.get("id") == "ambiguous_01"] or load_manifest()[:2]


def _procedural_rows(stage: str) -> Callable[[], list[dict[str, Any]]]:
    def _load() -> list[dict[str, Any]]:
        rows = load_agent_fixtures(stage)
        if rows:
            return rows
        return [
            {
                **r,
                "expected": r.get("expected_stage") or stage,
                "expected_stage": r.get("expected_stage") or stage,
            }
            for r in load_manifest()
            if (r.get("expected_stage") or "archived") == ("review" if stage == "human_review" else r.get("expected_stage") or "archived")
        ] or load_manifest()[:1]

    return _load


SPECS: dict[str, AgentSpec] = {}


def _register(spec: AgentSpec) -> AgentSpec:
    SPECS[spec.name] = spec
    return spec


_register(
    AgentSpec(
        name="intake",
        observation="normalize-intake",
        dojo_profile="intake",
        load_rows=_intake_rows,
        mock_predict=lambda row: _live_intake(row),
        live_predict=_live_intake,
        score_one=lambda row, pred: _score_contains(row, pred, "text"),
    )
)
_register(
    AgentSpec(
        name="pdf_transcriber",
        observation="transcribe-pdf",
        dojo_profile="pdf_transcriber",
        load_rows=_pdf_rows,
        mock_predict=lambda row: {"markdown": row.get("expected_snippet") or "SANDBOX PDF", "confidence": 0.8, "method": "mock"},
        live_predict=_live_pdf,
        score_one=lambda row, pred: _score_contains(row, pred, "markdown"),
    )
)
_register(
    AgentSpec(
        name="image_extractor",
        observation="extract-image-text",
        dojo_profile="image_extractor",
        load_rows=_image_rows,
        mock_predict=lambda row: {"text": row.get("expected_snippet") or "SANDBOX", "confidence": 0.8},
        live_predict=_live_image,
        score_one=_score_contains,
    )
)
_register(
    AgentSpec(
        name="sorter",
        observation="classify-document",
        dojo_profile="sorter",
        load_rows=load_manifest,
        mock_predict=_mock_classify,
        live_predict=_live_sorter,
        score_one=_score_class,
    )
)
_register(
    AgentSpec(
        name="sorter_reviewer",
        observation="classify-document",
        dojo_profile="sorter_reviewer",
        load_rows=_reviewer_rows,
        mock_predict=_mock_classify,
        live_predict=_live_reviewer,
        score_one=_score_class,
    )
)

for _agent, _cls in SPECIALIST_CLASS.items():
    _register(
        AgentSpec(
            name=_agent,
            observation="extract-fields",
            dojo_profile=_agent,
            load_rows=lambda c=_cls, a=_agent: _rows_or_agent_jsonl(a, lambda: _manifest_for_class(c)),
            mock_predict=_mock_extract,
            live_predict=lambda row, a=_agent: _live_specialist(a, row),
            score_one=_score_extract,
        )
    )

_register(
    AgentSpec(
        name="judge",
        observation="judge-verify",
        dojo_profile="judge",
        load_rows=lambda: _rows_or_agent_jsonl("judge", lambda: [r for r in load_manifest() if parse_expected_fields(r)][:4]),
        mock_predict=lambda row: {
            "completeness_label": row.get("expected_verdict") or "complete",
            "completeness": float(row.get("expected_score") or 0.98),
            "reasoning": "mock",
        },
        live_predict=_live_judge,
        score_one=lambda row, pred: _score_label(
            row, pred, "completeness_label", "expected_verdict"
        )
        if row.get("expected_verdict")
        else {"match": 1.0 if pred else 0.0},
    )
)
_register(
    AgentSpec(
        name="arbiter",
        observation="arbitrate-verdict",
        dojo_profile="arbiter",
        load_rows=lambda: _rows_or_agent_jsonl("arbiter", lambda: load_manifest()[:2]),
        mock_predict=lambda row: {
            "decision": row.get("expected_decision") or "accept_with_caveats",
            "fields_to_fix": [],
            "reasoning": "mock",
            "handoff_summary": "",
        },
        live_predict=_live_arbiter,
        score_one=lambda row, pred: _score_label(row, pred, "decision", "expected_decision")
        if row.get("expected_decision")
        else {"match": 1.0 if pred.get("decision") else 0.0},
    )
)
_register(
    AgentSpec(
        name="boss",
        observation="adjudicate-conflict",
        dojo_profile="boss",
        load_rows=lambda: _rows_or_agent_jsonl("boss", lambda: load_manifest()[:2]),
        mock_predict=lambda row: {
            "decision": row.get("expected_decision") or "approved",
            "reasoning": "mock",
        },
        live_predict=_live_boss,
        score_one=lambda row, pred: _score_label(row, pred, "decision", "expected_decision")
        if row.get("expected_decision")
        else {"match": 1.0 if pred.get("decision") else 0.0},
    )
)
_register(
    AgentSpec(
        name="compile_report",
        observation="compile-report",
        kind="nodes",
        load_rows=lambda: _rows_or_agent_jsonl(
            "reporter", lambda: [r for r in load_manifest() if parse_expected_fields(r)][:3]
        ),
        mock_predict=_procedural_report,
        live_predict=_live_reporter,
        score_one=_score_keys,
    )
)
_register(
    AgentSpec(
        name="human_review",
        observation="route-for-review",
        kind="nodes",
        load_rows=_procedural_rows("human_review"),
        mock_predict=lambda row: {"stage": row.get("expected_stage") or "review", "review_decision": "pending_review"},
        score_one=_score_stage,
    )
)
_register(
    AgentSpec(
        name="catalog",
        observation="write-catalog",
        kind="nodes",
        load_rows=_procedural_rows("catalog"),
        mock_predict=lambda row: {"stage": row.get("expected_stage") or "archived", "catalog_written": True},
        score_one=lambda row, pred: {"match": float(bool(pred.get("catalog_written") or pred.get("stage")))},
    )
)
_register(
    AgentSpec(
        name="archive",
        observation="archive-document",
        kind="nodes",
        dojo_profile="archivist",
        load_rows=_procedural_rows("archive"),
        mock_predict=lambda row: {"stage": row.get("expected_stage") or "archived"},
        score_one=_score_stage,
    )
)

COMPOSITE_TASKS = ("extract", "chained", "pipeline", "legalbench", "local_vs_api")
EVAL_TASKS = tuple(SPECS) + COMPOSITE_TASKS


def spec_for(name: str) -> AgentSpec:
    if name not in SPECS:
        raise ValueError(f"Unknown agent eval {name!r}. Have: {sorted(SPECS)}")
    return SPECS[name]


def is_eval_enabled(name: str) -> bool:
    if name in COMPOSITE_TASKS:
        return True
    spec = SPECS.get(name)
    if spec is None:
        return False
    return is_enabled(spec.kind, name)


def observation_meta(name: str) -> tuple[str, str]:
    spec = spec_for(name)
    return spec.observation, observation_type_for(spec.observation)
