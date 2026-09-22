"""Pydantic models for The-Mailroom.

Everything here is derived exclusively from Langfuse API data (traces,
observations, scores, sessions). Nothing is fabricated by the interface.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Stage(str, Enum):
    INBOX = "inbox"
    INTAKE = "intake"
    CLASSIFY = "classify"
    RETRY_CLASSIFY = "retry_classify"
    EXTRACT = "extract"
    RETRY_EXTRACT = "retry_extract"
    JUDGE_VERIFY = "judge_verify"   # KANBAN-063: ambiguous-band judge gate
    ARBITER = "arbiter"             # KANBAN-063: judgment arbitration
    BOSS = "boss"
    HUMAN_REVIEW = "review"
    COMPILE_REPORT = "report"
    CATALOG = "catalog"
    ARCHIVE = "archive"
    ARCHIVED = "archived"
    FAILED = "failed"
    UNKNOWN = "unknown"


class Phase(str, Enum):
    INTAKE_SORT = "intake_sort"            # intake + classify
    EXTRACTION_ADJUDICATION = "extraction"  # extract + retries + boss
    REPORTING_ARCHIVE = "reporting"         # report + catalog + archive
    REVIEW = "review"                       # human review siding
    TERMINAL = "terminal"                   # archived / failed


class NodeSpan(BaseModel):
    """One node observation from the Langfuse trace (verb-first names).

    `observation_type` is the Langfuse data-model type (SPAN / AGENT /
    EVALUATOR / RETRIEVER / CHAIN / EVENT). The root `document-pipeline`
    chain is retained for the inspector but skipped when building the
    floor routing path.
    """

    name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    latency: Optional[float] = None          # seconds
    status: str = "unknown"                  # PENDING / SUCCESS / ERROR
    error_message: Optional[str] = None
    input: Optional[dict[str, Any]] = None
    output: Optional[dict[str, Any]] = None
    observation_type: str = "SPAN"
    is_root: bool = False


class Generation(BaseModel):
    """One LLM generation observation (auto-traced by langfuse.openai)."""

    name: Optional[str] = None
    agent: Optional[str] = None              # inferred from span name
    model: Optional[str] = None
    observation_type: str = "GENERATION"
    latency: Optional[float] = None
    input: Optional[Any] = None
    output: Optional[Any] = None
    usage_total_tokens: Optional[int] = None
    usage_input_tokens: Optional[int] = None
    usage_output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    prompt_version: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class Score(BaseModel):
    """One Langfuse score attached to the trace."""

    name: str
    value: Any
    data_type: Optional[str] = None
    comment: Optional[str] = None
    observation_id: Optional[str] = None


class PipelineRun(BaseModel):
    """A fully interpreted mailroom pipeline run for one document trace."""

    trace_id: str
    name: str = "document-pipeline"
    filename: Optional[str] = None
    doc_id: Optional[str] = None
    matter_id: Optional[str] = None
    session_id: Optional[str] = None
    environment: Optional[str] = None
    user_id: Optional[str] = None            # MAILROOM_TRACE_USER_ID on producer
    release: Optional[str] = None            # LANGFUSE_RELEASE / mailroom@version
    tags: list[str] = Field(default_factory=list)
    attempt: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    latency: Optional[float] = None           # total trace latency s

    stage: Stage = Stage.UNKNOWN
    phase: Phase = Phase.INTAKE_SORT
    doc_type: Optional[str] = None
    doc_subclass: Optional[str] = None
    contract_subtype: Optional[str] = None
    expected_hf_class: Optional[str] = None
    expected_subclass: Optional[str] = None
    intake_messy: Optional[bool] = None
    intake_changed: Optional[bool] = None
    intake_method: Optional[str] = None
    intake_chars: Optional[int] = None
    # #111: terminal-manifest ``intake.bert`` block (BERT handoff fields +
    # gate_outcome) lifted for the Observatory BERT lane panels. None on
    # runs whose manifest predates the lane or carries no bert block.
    intake_bert: Optional[dict] = None
    classification_confidence: Optional[float] = None
    extraction_confidence: Optional[float] = None
    review_decision: Optional[str] = None
    escalation_reason: Optional[str] = None
    review_causes: list[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    run_aborted: bool = False
    failure_class: Optional[str] = None  # llm-mailroom PR #53 abort class

    spans: list[NodeSpan] = Field(default_factory=list)
    generations: list[Generation] = Field(default_factory=list)
    scores: dict[str, Any] = Field(default_factory=dict)
    score_objects: list[Score] = Field(default_factory=list)
    routing_path: list[str] = Field(default_factory=list)

    verdict: Optional[str] = None             # CORRECT / PARTIAL / MISS
    quality: Optional[float] = None           # 0..1
    llm_call_count: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def retried(self) -> bool:
        return Stage.RETRY_CLASSIFY.value in self.routing_path or Stage.RETRY_EXTRACT.value in self.routing_path

    @property
    def needs_reconsideration(self) -> bool:
        """Archived/cataloged but objective misses say it should not stay done."""
        from .reconsideration import should_reconsider

        return should_reconsider(self.stage.value if self.stage else None, self.review_causes)

    @property
    def needs_human(self) -> bool:
        if self.stage == Stage.HUMAN_REVIEW:
            return True
        if self.stage == Stage.FAILED:
            return False
        return self.needs_reconsideration


class SessionSummary(BaseModel):
    """One Langfuse session (matter in live runs, run-scoped in pilots)."""

    id: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    trace_count: int = 0
    runs: list[PipelineRun] = Field(default_factory=list)


class Metrics(BaseModel):
    total_docs: int = 0
    archived: int = 0
    review: int = 0
    failed: int = 0
    in_flight: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    avg_cost_usd: float = 0.0
    avg_latency_s: float = 0.0
    p95_generation_latency_s: float = 0.0
    verdict_counts: dict[str, int] = Field(default_factory=dict)
    avg_quality: Optional[float] = None
    per_doc_type: dict[str, int] = Field(default_factory=dict)
    llm_calls: int = 0
    # Extraction-quality aggregates over the pilot's grounded runs — mined
    # from trace scores (llm-mailroom SCORE_CONFIGS); None when no grounded
    # run is in the window (never fabricated).
    n_grounded_runs: int = 0
    avg_extraction_field_score: Optional[float] = None
    avg_extraction_overall_score: Optional[float] = None
    avg_entity_list_precision: Optional[float] = None
    avg_entity_list_recall: Optional[float] = None
    avg_hallucination_rate: Optional[float] = None
    avg_expected_field_presence: Optional[float] = None
    # Ops aggregates mirroring the pipeline's core run metrics.
    avg_run_duration_s: Optional[float] = None
    avg_classification_attempts: Optional[float] = None
    avg_extraction_attempts: Optional[float] = None
    # Wire alias extraction_verified_precision (35-char Langfuse cap) is
    # resolved onto this field; None when no run in the window carries it.
    avg_extraction_verified_precision: Optional[float] = None
    # Dedicated specialist-suite extras (Enron topic/sentiment, MAUD).
    avg_content_topic_accuracy: Optional[float] = None
    avg_content_topic_f1_macro: Optional[float] = None
    avg_sentiment_accuracy: Optional[float] = None
    avg_sentiment_f1_macro: Optional[float] = None
    avg_maud_question_accuracy: Optional[float] = None
    avg_maud_question_macro_accuracy: Optional[float] = None
    avg_maud_clause_presence: Optional[float] = None
    avg_maud_valid_class_rate: Optional[float] = None
    avg_maud_category_accuracy: Optional[float] = None
    per_doc_subclass: dict[str, int] = Field(default_factory=dict)
    reconsideration: int = 0
