"""Mirror of the llm-mailroom pipeline topology.

This mirrors graph/build_graph.py + graph/routing.py + config/taxonomy.yaml of
the llm-mailroom repo so traces can be interpreted without importing that repo.
If MAILROOM_TAXONOMY points at the live taxonomy.yaml, thresholds/doc classes
are read from there instead (the topology above is data-driven there too).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from .models import Phase, Stage

# Verb-first observation names (traced_node) plus LangGraph node names, so
# a floor envelope never falls through to INBOX/unknown when the producer
# records the underscored graph id instead of the display span.
SPAN_STAGE_MAP: dict[str, Stage] = {
    "intake-document": Stage.INTAKE,
    "normalize-intake": Stage.INTAKE,
    "transcribe-pdf": Stage.INTAKE,
    "extract-image-text": Stage.INTAKE,
    "classify-document": Stage.CLASSIFY,
    "judge-verify": Stage.JUDGE_VERIFY,
    "arbitrate-verdict": Stage.ARBITER,
    "extract-fields": Stage.EXTRACT,
    "route-for-review": Stage.HUMAN_REVIEW,
    "adjudicate-conflict": Stage.BOSS,
    "compile-report": Stage.COMPILE_REPORT,
    "write-catalog": Stage.CATALOG,
    "archive-document": Stage.ARCHIVE,
    # LangGraph add_node ids (build_graph.py)
    "intake": Stage.INTAKE,
    "classify": Stage.CLASSIFY,
    "retry_classify": Stage.RETRY_CLASSIFY,
    "review_classify": Stage.RETRY_CLASSIFY,
    "extract": Stage.EXTRACT,
    "retry_extract": Stage.RETRY_EXTRACT,
    "judge_verify": Stage.JUDGE_VERIFY,
    "arbiter": Stage.ARBITER,
    "human_review": Stage.HUMAN_REVIEW,
    "boss_escalation": Stage.BOSS,
    "compile_report": Stage.COMPILE_REPORT,
    "catalog_write": Stage.CATALOG,
    "archive": Stage.ARCHIVE,
}

# Langfuse observation types (llm-mailroom observability/tracing.py
# NODE_OBSERVATION_TYPES). The data-model docs require the most specific
# type: chain = one document run; agent = specialist orchestration;
# evaluator = judge gate; retriever = document reads; generation = LLM
# result / LegalBench answer; span = remaining units of work.
NODE_OBSERVATION_TYPES: dict[str, str] = {
    "document-pipeline": "chain",
    "intake-document": "span",
    "normalize-intake": "span",
    "extract-image-text": "retriever",
    "transcribe-pdf": "retriever",
    "classify-document": "agent",
    "extract-fields": "agent",
    "judge-verify": "evaluator",
    "arbitrate-verdict": "agent",
    "route-for-review": "span",
    "adjudicate-conflict": "agent",
    "compile-report": "agent",
    "write-catalog": "span",
    "archive-document": "span",
    "pipeline-result": "generation",
    "answer-question": "generation",
}

# Graph node names (underscored) that can appear as observation names
# when a trace is recorded from LangGraph rather than traced_node().
_NODE_TYPE_ALIASES: dict[str, str] = {
    "classify": "agent",
    "retry_classify": "agent",
    "review_classify": "agent",
    "extract": "agent",
    "retry_extract": "agent",
    "judge_verify": "evaluator",
}


def observation_type_for(name: str, default: str = "span") -> str:
    """Most-specific Langfuse observation type for a verb-first span name."""
    key = (name or "").strip()
    if key in NODE_OBSERVATION_TYPES:
        return NODE_OBSERVATION_TYPES[key]
    lower = key.lower()
    if lower in NODE_OBSERVATION_TYPES:
        return NODE_OBSERVATION_TYPES[lower]
    if lower in _NODE_TYPE_ALIASES:
        return _NODE_TYPE_ALIASES[lower]
    if lower.startswith("answer-question"):
        return "generation"
    return default

STAGE_PHASE: dict[Stage, Phase] = {
    Stage.INBOX: Phase.INTAKE_SORT,
    Stage.INTAKE: Phase.INTAKE_SORT,
    Stage.CLASSIFY: Phase.INTAKE_SORT,
    Stage.RETRY_CLASSIFY: Phase.INTAKE_SORT,
    Stage.EXTRACT: Phase.EXTRACTION_ADJUDICATION,
    Stage.RETRY_EXTRACT: Phase.EXTRACTION_ADJUDICATION,
    Stage.JUDGE_VERIFY: Phase.EXTRACTION_ADJUDICATION,
    Stage.ARBITER: Phase.EXTRACTION_ADJUDICATION,
    Stage.BOSS: Phase.EXTRACTION_ADJUDICATION,
    Stage.COMPILE_REPORT: Phase.REPORTING_ARCHIVE,
    Stage.CATALOG: Phase.REPORTING_ARCHIVE,
    Stage.ARCHIVE: Phase.REPORTING_ARCHIVE,
    Stage.ARCHIVED: Phase.TERMINAL,
    Stage.FAILED: Phase.TERMINAL,
    Stage.HUMAN_REVIEW: Phase.REVIEW,
    Stage.UNKNOWN: Phase.INTAKE_SORT,
}

# Node traversal order used to order spans into a routing path (mirrors the
# add_node wiring order in llm-mailroom graph/build_graph.py).
NODE_ORDER: list[Stage] = [
    Stage.INTAKE,
    Stage.CLASSIFY,
    Stage.RETRY_CLASSIFY,
    Stage.EXTRACT,
    Stage.RETRY_EXTRACT,
    Stage.JUDGE_VERIFY,
    Stage.ARBITER,
    Stage.BOSS,
    Stage.HUMAN_REVIEW,
    Stage.COMPILE_REPORT,
    Stage.CATALOG,
    Stage.ARCHIVE,
]

# Agent display roster: key -> (label, role). Mirrors src/agents/ of
# llm-mailroom (+ langchain_agents/sorter_agent.py for sorter/sorter_reviewer).
# Retired specialists (court opinions / due diligence) stay off this roster;
# the sorter emits `unknown` for those classes.
AGENTS: dict[str, dict[str, str]] = {
    "sorter": {"label": "Sorter", "role": "classify"},
    "intake": {"label": "Intake", "role": "prepare"},
    "sorter_reviewer": {"label": "Sorter Reviewer", "role": "review-classify"},
    "contracts_specialist": {"label": "Contracts", "role": "extract"},
    "corporate_records_specialist": {"label": "Corporate", "role": "extract"},
    "correspondence_specialist": {"label": "Correspondence", "role": "extract"},
    "insurance_claims_specialist": {"label": "Insurance Claims", "role": "extract"},
    "arbiter": {"label": "Arbiter", "role": "adjudicate"},
    "boss": {"label": "Boss", "role": "adjudicate"},
    # compile_report is procedural in llm-mailroom v0.6.0 (no get_llm).
    "reporter": {"label": "Reporter", "role": "report"},
    "judge": {"label": "Judge", "role": "evaluate"},
    "pdf_transcriber": {"label": "Transcriber", "role": "intake"},
    "image_extractor": {"label": "Image Extractor", "role": "intake"},
}

# Live taxonomy classes that dispatch to a specialist (llm-mailroom v0.6.0 /
# taxonomy.yaml doc_classes). ``merger_agreement`` is a live MAUD class (not
# an extract alias of CUAD ``contract``). ``unknown`` is a routing token.
LIVE_DOC_TYPES: tuple[str, ...] = (
    "contract",
    "merger_agreement",
    "corporate_record",
    "correspondence",
    "insurance_claim",
)
RETIRED_DOC_TYPES: tuple[str, ...] = ("court_opinion", "due_diligence", "compliance_filing")
UNKNOWN_DOC_TYPE = "unknown"
# Sorter / HF labels that extract through a live taxonomy specialist without
# adding a new doc_class row. Empty as of llm-mailroom v0.6.0 — MAUD is live.
EXTRACT_CLASS_ALIASES: dict[str, str] = {}

DOC_CLASSES: dict[str, str] = {
    "contract": "Contract / Agreement",
    "corporate_record": "Corporate Record",
    "correspondence": "Correspondence",
    "insurance_claim": "Insurance Claim",
    "merger_agreement": "Merger Agreement",
    "unknown": "Unknown",
}

DEFAULT_DOC_CLASSES: dict[str, str] = dict(DOC_CLASSES)

# llm-mailroom pipeline.failures (PR #53) — stamped on aborted state /
# manifest / audit. Trace output may carry the token, or embed it as
# ``run aborted [llm_timeout]: …`` in error_message.
FAILURE_CLASSES: tuple[str, ...] = (
    "llm_timeout",
    "llm_auth",
    "llm_rate_limit",
    "llm_transient",
    "io_error",
    "schema_error",
    "run_budget",
    "unexpected",
)
FAILURE_CLASS_LABELS: dict[str, str] = {
    "llm_timeout": "LLM timeout",
    "llm_auth": "LLM auth",
    "llm_rate_limit": "LLM rate limit",
    "llm_transient": "LLM transient",
    "io_error": "I/O error",
    "schema_error": "schema error",
    "run_budget": "run budget",
    "unexpected": "unexpected",
}

# Mirror of llm-mailroom schemas.documents EXTRACTION_SCHEMAS field names
# (v0.6.0 pared checklists; REVIEW Complete rejects foreign specialist keys).
_META_EXTRACT_KEYS = frozenset({"confidence", "reasoning", "mock_extraction"})
EXTRACTION_FIELD_KEYS_BY_CLASS: dict[str, frozenset[str]] = {
    "contract": frozenset({
        "document_name", "parties", "effective_date", "term_length",
        "governing_law", "contract_value", "renewal_terms", "cuad_family",
        "merger_consideration", "cuad_clauses", "maud_clauses", "reasoning",
    }),
    "corporate_record": frozenset({
        "entity_name", "record_type", "effective_date",
        "signatories", "jurisdiction", "filing_number",
        "intent", "subject_matter", "keywords",
    }),
    "correspondence": frozenset({
        "sender", "recipient", "additional_recipients", "communication_type",
        "communication_date", "demand_amount", "action_items",
        "urgency", "intent", "subject_matter", "keywords", "confidence",
    }),
    "insurance_claim": frozenset({
        "claim_number", "policy_number", "insurer", "insured_party",
        "claim_type", "date_of_loss", "date_filed", "claimed_amount",
        "adjuster", "damages_description", "coverage_determination",
        "denial_reasons", "supporting_documents",
        "intent", "subject_matter", "keywords", "claim_checklist", "confidence",
    }),
}
# MAUD shares the ContractExtraction field map but is its own live class.
EXTRACTION_FIELD_KEYS_BY_CLASS["merger_agreement"] = EXTRACTION_FIELD_KEYS_BY_CLASS["contract"]

_ABORT_CLASS_RE = re.compile(r"run aborted \[([a-z_]+)\]", re.I)


def all_specialist_field_keys() -> frozenset[str]:
    names: set[str] = set()
    for keys in EXTRACTION_FIELD_KEYS_BY_CLASS.values():
        names.update(keys)
    return frozenset(names) - _META_EXTRACT_KEYS


def normalize_failure_class(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    key = str(value).strip().lower().replace("-", "_")
    return key if key in FAILURE_CLASSES else None


def failure_class_from_text(text: Optional[str]) -> Optional[str]:
    """Parse ``run aborted [llm_timeout]: …`` from error / escalation text."""
    if not text:
        return None
    match = _ABORT_CLASS_RE.search(str(text))
    if not match:
        return None
    return normalize_failure_class(match.group(1))


def validate_operator_extraction(doc_type: str, extracted: dict) -> dict:
    """Reject Complete payloads whose keys belong to another specialist.

    Mirrors llm-mailroom ``pipeline.review_resolve.validate_operator_extraction``
    foreign-key check (PR #53). Full pydantic schema_valid stays on the
    producer when the live extra is present.
    """
    payload = dict(extracted)
    kind = EXTRACT_CLASS_ALIASES.get(doc_type, doc_type)
    allowed = (
        EXTRACTION_FIELD_KEYS_BY_CLASS.get(doc_type)
        or EXTRACTION_FIELD_KEYS_BY_CLASS.get(kind)
        or frozenset()
    ) | _META_EXTRACT_KEYS
    foreign = sorted(
        key
        for key in payload
        if key not in allowed
        and not str(key).startswith("_")
        and key in all_specialist_field_keys()
    )
    if foreign:
        raise ValueError(
            f"extracted_data fields {foreign} belong to another specialist, "
            f"not {doc_type}"
        )
    return payload


SPECIALIST_BY_DOC_CLASS: dict[str, str] = {
    "contract": "contracts_specialist",
    "merger_agreement": "contracts_specialist",
    "corporate_record": "corporate_records_specialist",
    "correspondence": "correspondence_specialist",
    "insurance_claim": "insurance_claims_specialist",
}

# Hub subclass catalogs (llm-dojo-scoring mailroom.HUB_SUBCLASS_INVENTORIES
# + CUAD contract_subtype keys + MAUD consideration types).
CONTRACT_SUBTYPE_KEYS: tuple[str, ...] = (
    "affiliate", "agency", "collaboration", "co_branding", "consulting",
    "development", "distributor", "endorsement", "franchise", "hosting",
    "ip", "joint_venture", "license", "maintenance", "manufacturing",
    "marketing", "non_compete_no_solicit", "outsourcing", "promotion",
    "reseller", "service", "sponsorship", "strategic_alliance", "supply",
    "transportation",
)
DOC_SUBCLASS_BY_CLASS: dict[str, tuple[str, ...]] = {
    "contract": CONTRACT_SUBTYPE_KEYS,
    "merger_agreement": (
        "all_cash", "all_stock", "mixed_cash_stock",
        "mixed_cash_stock_election", "other",
    ),
    "corporate_record": (
        "articles_of_incorporation", "board_resolution", "bylaws",
        "charter_amendment", "indenture", "officer_certificate", "other",
        "powers_of_attorney", "rights_instrument", "subsidiary_list",
    ),
    "correspondence": (
        "email", "letter", "memo", "notice", "demand", "attorney_demand",
        "press_release", "meeting_request",
    ),
    "insurance_claim": (
        "pde", "inpatient", "outpatient", "carrier", "property", "auto",
    ),
}

# Langfuse Cloud rejects score *config* names over 35 characters.
LANGFUSE_SCORE_NAME_ALIASES: dict[str, str] = {
    "extraction_overall_verified_precision": "extraction_verified_precision",
}
_CANONICAL_SCORE_NAMES: dict[str, str] = {
    alias: canonical for canonical, alias in LANGFUSE_SCORE_NAME_ALIASES.items()
}

# Dedicated specialist-suite extras (llm-mailroom suite_scoring.py / dojo 0.9.0).
SUITE_EXTRA_SCORES: tuple[str, ...] = (
    "content_topic_accuracy",
    "content_topic_f1_macro",
    "sentiment_accuracy",
    "sentiment_f1_macro",
    "maud_question_accuracy",
    "maud_question_macro_accuracy",
    "maud_clause_presence",
    "maud_valid_class_rate",
    "maud_category_accuracy",
)
SUITE_EXTRA_SCORE_SET = frozenset(SUITE_EXTRA_SCORES)

GROUND_TRUTH_KEYS: tuple[str, ...] = (
    "expected_hf_class",
    "expected_doc_class",
    "expected_subclass",
    "expected",
)


def resolve_extract_class(doc_type: Optional[str]) -> Optional[str]:
    """Live taxonomy class used for extraction, or None if parked."""
    if not doc_type:
        return None
    key = str(doc_type).strip().lower()
    if key == UNKNOWN_DOC_TYPE or key in RETIRED_DOC_TYPES:
        return None
    aliased = EXTRACT_CLASS_ALIASES.get(key, key)
    if aliased in LIVE_DOC_TYPES:
        return aliased
    return None


def langfuse_score_name(name: str) -> str:
    return LANGFUSE_SCORE_NAME_ALIASES.get(name, name)


def canonical_score_name(name: str) -> str:
    return _CANONICAL_SCORE_NAMES.get(name, name)


@dataclass
class PipelineSchema:
    """Loaded once per process; configurable thresholds from taxonomy.yaml."""

    # llm-mailroom v0.6.0 taxonomy.yaml global confidence defaults.
    confidence_high: float = 0.97
    confidence_low: float = 0.88
    retry_max: int = 2
    conflict_threshold: float = 0.3
    judge_band_high: float = 0.95   # Lane B ambiguous-band ceiling
    arbiter_retry_max: int = 2
    judge_max_passes: int = 3
    doc_classes: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_DOC_CLASSES))
    # Per-class severity overrides (taxonomy confidence.by_class).
    by_class: dict[str, dict[str, float]] = field(default_factory=dict)

    @classmethod
    def load(cls, taxonomy_path: Optional[str] = None) -> "PipelineSchema":
        schema = cls()
        path = taxonomy_path or os.environ.get("MAILROOM_TAXONOMY")
        if not path or not os.path.exists(path):
            return schema
        try:
            import yaml  # type: ignore
        except ImportError:
            return schema
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception:
            return schema
        conf = dict(cfg.get("confidence", {}) or {})
        by_class = conf.pop("by_class", None) or {}
        schema.confidence_high = float(conf.get("high", schema.confidence_high))
        schema.confidence_low = float(conf.get("low", schema.confidence_low))
        schema.retry_max = int(conf.get("retry_max", schema.retry_max))
        schema.conflict_threshold = float(conf.get("conflict_threshold", schema.conflict_threshold))
        schema.judge_band_high = float(conf.get("judge_band_high", schema.judge_band_high))
        schema.arbiter_retry_max = int(conf.get("arbiter_retry_max", schema.arbiter_retry_max))
        schema.judge_max_passes = int(conf.get("judge_max_passes", schema.judge_max_passes))
        if isinstance(by_class, dict):
            parsed: dict[str, dict[str, float]] = {}
            for key, overrides in by_class.items():
                if isinstance(overrides, dict):
                    parsed[str(key)] = {
                        str(k): float(v) for k, v in overrides.items() if v is not None
                    }
            schema.by_class = parsed
        classes = {}
        for dc in cfg.get("doc_classes", []) or []:
            if isinstance(dc, dict) and dc.get("key"):
                classes[dc["key"]] = dc.get("label", dc["key"])
        if classes:
            schema.doc_classes = classes
        return schema

    def thresholds_for(self, doc_type: Optional[str] = None) -> dict[str, float | int]:
        """Global confidence / Lane B budgets, optionally merged with by_class."""
        base: dict[str, float | int] = {
            "high": self.confidence_high,
            "low": self.confidence_low,
            "retry_max": self.retry_max,
            "conflict_threshold": self.conflict_threshold,
            "judge_band_high": self.judge_band_high,
            "arbiter_retry_max": self.arbiter_retry_max,
            "judge_max_passes": self.judge_max_passes,
        }
        if not doc_type:
            return base
        resolved = resolve_extract_class(doc_type) or doc_type
        overrides = self.by_class.get(resolved) or self.by_class.get(doc_type)
        if overrides:
            base.update(overrides)
        return base

    def specialist_for(self, doc_type: str) -> Optional[str]:
        if not doc_type:
            return None
        key = resolve_extract_class(doc_type) or doc_type
        return SPECIALIST_BY_DOC_CLASS.get(key) or SPECIALIST_BY_DOC_CLASS.get(doc_type)


def allowed_review_doc_types() -> frozenset[str]:
    return frozenset(DOC_CLASSES) | frozenset(LIVE_DOC_TYPES) | frozenset(EXTRACT_CLASS_ALIASES) | {
        UNKNOWN_DOC_TYPE,
    }


def doc_subclasses_payload() -> dict[str, list[str]]:
    return {key: list(values) for key, values in DOC_SUBCLASS_BY_CLASS.items()}


def normalize_review_doc_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    key = str(value).strip()
    if not key:
        return None
    allowed = allowed_review_doc_types()
    if key in allowed:
        return key
    lower = key.lower().replace(" ", "_")
    if lower in allowed:
        return lower
    raise ValueError(f"unknown doc_type: {value}")


def normalize_review_subclass(doc_type: Optional[str], value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    kind = str(doc_type or "")
    catalog = DOC_SUBCLASS_BY_CLASS.get(kind) or DOC_SUBCLASS_BY_CLASS.get(
        EXTRACT_CLASS_ALIASES.get(kind, kind), ()
    )
    if not catalog:
        return text
    compact = "".join(ch for ch in text.lower() if ch.isalnum())
    for token in catalog:
        if token == text:
            return token
        if "".join(ch for ch in token.lower() if ch.isalnum()) == compact:
            return token
    raise ValueError(f"unknown doc_subclass {value!r} for {kind}")
