from __future__ import annotations

from datetime import datetime, timedelta, timezone

from mailroom_ui.models import NodeSpan, Phase, Stage
from mailroom_ui.trace_interpreter import (
    RUN_GAP_S,
    _latest_run_cut,
    build_routing_path,
    derive_stage,
    interpret_trace,
)
from tests.fake_langfuse import Obj, FakeClient, make_trace, make_trace_v4


def _run(trace: dict):
    return interpret_trace(
        trace,
        trace.get("observations", []),
        trace.get("scores", []),
    )


def test_v4_camelcase_observations():
    trace = make_trace_v4("t-v4")
    run = _run(trace)
    assert run.stage == Stage.ARCHIVED
    assert run.doc_type == "contract"
    assert run.matter_id == "MATTER-V4"
    assert run.classification_confidence == 0.97
    assert run.extraction_confidence == 0.88
    assert len(run.spans) == 5
    by_name = {s.name: s for s in run.spans}
    assert by_name["document-pipeline"].observation_type == "CHAIN"
    assert by_name["document-pipeline"].is_root is True
    assert by_name["classify-document"].observation_type == "AGENT"
    assert by_name["intake-document"].observation_type == "SPAN"
    assert [s.name for s in run.spans][-1] == "archive-document"
    gen = run.generations[0]
    assert gen.model == "deepseek/deepseek-v4-flash"
    assert gen.observation_type == "GENERATION"
    assert gen.usage_total_tokens == 1200
    assert gen.usage_input_tokens == 1000
    assert gen.usage_output_tokens == 200
    assert gen.cost_usd == 0.00015
    assert run.total_tokens == 1200
    assert run.cost_usd == 0.00015
    assert run.session_id == "MATTER-V4"
    assert run.user_id == "pilot-operator"
    assert run.release == "mailroom@test"


def test_archived_run_full():
    trace = make_trace("t-archived")
    run = _run(trace)
    assert run.trace_id == "t-archived"
    assert run.stage == Stage.ARCHIVED
    assert run.phase == Phase.TERMINAL
    assert run.doc_type == "contract"
    assert run.matter_id == "MATTER-001"
    assert run.session_id == "MATTER-001"
    assert run.classification_confidence == 0.98
    assert run.extraction_confidence == 0.91
    assert run.verdict == "CORRECT"
    assert run.quality == 0.9
    assert run.llm_call_count == 2
    assert run.total_tokens == 4600
    assert run.cost_usd == 0.00055
    assert len(run.spans) == 6
    assert {s.name: s.observation_type for s in run.spans} == {
        "intake-document": "SPAN",
        "classify-document": "AGENT",
        "extract-fields": "AGENT",
        "compile-report": "AGENT",
        "write-catalog": "SPAN",
        "archive-document": "SPAN",
    }
    assert run.routing_path == [
        "intake",
        "classify",
        "extract",
        "report",
        "catalog",
        "archive",
    ]
    assert run.needs_human is False


def test_pipeline_duration_score_overrides_reused_trace_latency():
    trace = make_trace("t-reused-latency")
    trace["latency"] = 1600.0
    trace["scores"].append(
        {"name": "run_duration_seconds", "value": 26.4, "data_type": "NUMERIC"}
    )

    run = _run(trace)

    assert run.latency == 26.4


def test_reused_trace_uses_newest_run_metric_scores():
    trace = make_trace("t-reused-scores")
    trace["scores"].extend([
        {
            "name": "run_duration_seconds",
            "value": 12.7,
            "data_type": "NUMERIC",
            "timestamp": "2026-08-25T04:42:36Z",
        },
        {
            "name": "total_tokens",
            "value": 10722,
            "data_type": "NUMERIC",
            "timestamp": "2026-08-25T04:42:36Z",
        },
        {
            "name": "estimated_cost_usd",
            "value": 0.0005,
            "data_type": "NUMERIC",
            "timestamp": "2026-08-25T04:42:36Z",
        },
        {
            "name": "llm_call_count",
            "value": 3,
            "data_type": "NUMERIC",
            "timestamp": "2026-08-25T04:42:36Z",
        },
        {
            "name": "run_duration_seconds",
            "value": 24.6,
            "data_type": "NUMERIC",
            "timestamp": "2026-08-25T04:38:26Z",
        },
        {
            "name": "total_tokens",
            "value": 7748,
            "data_type": "NUMERIC",
            "timestamp": "2026-08-25T04:38:26Z",
        },
    ])

    run = _run(trace)

    assert run.latency == 12.7
    assert run.total_tokens == 10722
    assert run.cost_usd == 0.0005
    assert run.llm_call_count == 3


def test_review_stage():
    trace = make_trace(
        "t-review",
        stage="review",
        span_names=["intake-document", "classify-document", "route-for-review"],
        verdict=None,
        quality=None,
    )
    run = _run(trace)
    assert run.stage == Stage.HUMAN_REVIEW
    assert run.phase == Phase.REVIEW
    assert run.needs_human is True


def test_failed_stage():
    trace = make_trace("t-failed", stage="failed", verdict=None)
    run = _run(trace)
    assert run.stage == Stage.FAILED
    assert run.phase == Phase.TERMINAL


def test_retry_detection():
    trace = make_trace(
        "t-retry",
        span_names=[
            "intake-document",
            "classify-document",
            "classify-document",
            "extract-fields",
            "extract-fields",
            "compile-report",
        ],
    )
    run = _run(trace)
    assert "retry_classify" in run.routing_path
    assert "retry_extract" in run.routing_path
    assert run.retried is True


def test_in_flight_derives_stage_from_last_span():
    trace = make_trace(
        "t-inflight",
        stage="processing",
        span_names=["intake-document", "classify-document"],
        verdict=None,
    )
    run = _run(trace)
    assert run.stage in (Stage.CLASSIFY, Stage.INTAKE)
    assert run.phase == Phase.INTAKE_SORT


def test_derive_stage_output_wins():
    trace = make_trace("t-x", stage="review")
    run = _run(trace)
    assert derive_stage(trace["output"], run.spans) == Stage.HUMAN_REVIEW


def test_light_interpretation_from_list_response():
    trace = make_trace("t-light", stage="archived")
    run = interpret_trace(trace)  # observations/scores embedded in trace dict
    assert run.stage == Stage.ARCHIVED
    assert run.spans and run.generations


def test_light_interpretation_without_embedded_observations():
    trace = make_trace("t-bare", stage="archived")
    trace.pop("observations")
    trace.pop("scores")
    run = interpret_trace(trace)
    assert run.stage == Stage.ARCHIVED
    assert run.spans == []
    assert run.generations == []
    assert run.total_tokens == 0
    assert run.cost_usd == 0.0


def _span(name, start, end=None, *, root=False):
    return NodeSpan(name=name, start_time=start, end_time=end or start, is_root=root)


def test_latest_run_cut_splits_on_idle_gap():
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    early = _span("intake-document", base)
    late = _span("intake-document", base + timedelta(seconds=RUN_GAP_S + 5))
    cut = _latest_run_cut([early, late], [])
    assert cut is not None and early.start_time < cut <= late.start_time


def test_latest_run_cut_keeps_single_run_untouched():
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    items = [_span(f"o{i}", base + timedelta(seconds=5 * i)) for i in range(3)]
    assert _latest_run_cut(items, []) is None


def test_slow_llm_call_does_not_split_one_run():
    """A generation longer than RUN_GAP_S used to cut intake/classify off."""
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    classify = _span("classify-document", base, base + timedelta(seconds=95))
    extract = _span("extract-fields", base + timedelta(seconds=96))
    assert _latest_run_cut([classify, extract], []) is None


def test_latest_run_cut_anchors_on_root_chain():
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    r1 = _span("document-pipeline", base, root=True)
    r2 = _span("document-pipeline", base + timedelta(seconds=30), root=True)
    cut = _latest_run_cut([r1, r2], [])
    assert cut is not None and r1.start_time < cut <= r2.start_time


def test_multi_run_trace_interprets_latest_run_only():
    base = datetime(2026, 1, 1, 12, 0, 0)
    rerun_obs = [
        Obj(
            id="rerun-gen",
            type="GENERATION",
            name="classify-document",
            model="qwen/qwen3.7-flash",
            start_time=base + timedelta(seconds=RUN_GAP_S + 60),
            end_time=base + timedelta(seconds=RUN_GAP_S + 69),
            latency=9.0,
            usage={"total": 500, "input": 400, "output": 100},
            cost_details={"total": 0.00005},
            level="DEFAULT",
        )
    ]
    trace = make_trace("t-multi", extra_observations=rerun_obs)
    run = _run(trace)
    assert run.llm_call_count == 1
    assert run.total_tokens == 500
    assert run.cost_usd == 0.00005


def test_unknown_span_skipped_from_routing_path():
    trace = make_trace(
        "t-unknown-span",
        stage="weird-stage",
        span_names=["intake-document", "mystery-node", "classify-document"],
        verdict=None,
    )
    run = _run(trace)
    assert run.stage == Stage.CLASSIFY
    assert "mystery-node" not in run.routing_path
    assert "classify" in run.routing_path


def test_error_span_status_and_message():
    trace = make_trace("t-err", error_spans=True)
    run = _run(trace)
    errored = [s for s in run.spans if s.status == "ERROR"]
    assert errored
    assert all(s.error_message == "boom" for s in errored)


def test_run_aborted_and_error_message_from_output():
    trace = make_trace(
        "t-abort",
        stage="failed",
        verdict=None,
        output_extra={"run_aborted": True, "error_message": "LLM timeout"},
    )
    run = _run(trace)
    assert run.run_aborted is True
    assert run.error_message == "LLM timeout"


def test_failure_class_from_output_and_tagged_error():
    from server.poller import floor_payload

    direct = _run(make_trace(
        "t-fail-out",
        stage="failed",
        verdict=None,
        output_extra={
            "run_aborted": True,
            "failure_class": "llm_timeout",
            "error_message": "run aborted [llm_timeout]: TimeoutError: deadline",
        },
    ))
    assert direct.failure_class == "llm_timeout"
    assert floor_payload(direct)["failure_class"] == "llm_timeout"
    assert floor_payload(direct)["run_aborted"] is True

    tagged = _run(make_trace(
        "t-fail-text",
        stage="failed",
        verdict=None,
        output_extra={
            "run_aborted": True,
            "error_message": "run aborted [llm_auth]: Unauthorized",
        },
    ))
    assert tagged.failure_class == "llm_auth"

    v4 = _run(make_trace_v4(
        "t-fail-v4",
        stage="failed",
        output_extra={
            "run_aborted": True,
            "failure_class": "run_budget",
            "error_message": "run aborted [run_budget]: RunDeadlineExceeded",
        },
    ))
    assert v4.failure_class == "run_budget"

    meta = _run(make_trace(
        "t-fail-meta",
        stage="failed",
        verdict=None,
        extra_metadata={"failure_class": "io_error"},
        output_extra={"error_message": "run aborted: PermissionError"},
    ))
    assert meta.failure_class == "io_error"


def test_review_decision_and_escalation_reason():
    trace = make_trace(
        "t-boss",
        stage="review",
        verdict=None,
        output_extra={"review_decision": "approved", "escalation_reason": "conflict detected"},
    )
    run = _run(trace)
    assert run.review_decision == "approved"
    assert run.escalation_reason == "conflict detected"


def test_doc_type_falls_back_to_input():
    trace = make_trace("t-in", stage="processing")
    trace["output"].pop("doc_type")
    trace["input"]["doc_type"] = "correspondence"
    run = _run(trace)
    assert run.doc_type == "correspondence"


def test_attempt_falls_back_to_metadata():
    trace = make_trace("t-att", stage="processing")
    trace["input"].pop("attempt")
    trace["metadata"]["attempt"] = 3
    run = _run(trace)
    assert run.attempt == 3


def test_partial_and_miss_verdicts():
    for verdict in ("PARTIAL", "MISS"):
        trace = make_trace(f"t-{verdict.lower()}", stage="archived", verdict=verdict)
        assert _run(trace).verdict == verdict


def test_score_objects_preserve_details():
    trace = make_trace("t-score-details", stage="archived", verdict=None)
    trace["scores"].append(
        Obj(
            name="custom-score",
            value=7,
            data_type="NUMERIC",
            comment="checked by reviewer",
            observation_id="span-1",
        )
    )
    run = _run(trace)
    assert run.scores["custom-score"] == 7
    score = next(s for s in run.score_objects if s.name == "custom-score")
    assert score.comment == "checked by reviewer"
    assert score.observation_id == "span-1"


def test_generation_detected_by_model_attribute():
    base = datetime(2026, 1, 1, 12, 0, 0)
    gen_obs = Obj(
        id="odd-gen",
        type="OBSERVATION",
        name="pipeline-result",
        model="qwen/qwen3.7-flash",
        start_time=base + timedelta(seconds=50),
        end_time=base + timedelta(seconds=58),
        usage={"total": 100},
        metadata={"langfuse_prompt": "mailroom-reporter:42"},
        level="DEFAULT",
    )
    trace = make_trace("t-genattr", stage="archived", extra_observations=[gen_obs])
    run = _run(trace)
    gens = [g for g in run.generations if g.name == "pipeline-result"]
    assert len(gens) == 1
    assert gens[0].model == "qwen/qwen3.7-flash"
    assert gens[0].prompt_version == "mailroom-reporter:42"
    assert gens[0].usage_total_tokens == 100


def test_quality_and_verdict_absent_without_scores():
    trace = make_trace("t-noscores", stage="archived", verdict=None, quality=None)
    trace["scores"] = []
    run = _run(trace)
    assert run.verdict is None
    assert run.quality is None
    assert run.scores == {}


# ---- KANBAN-062/063 sync: judge gate + arbiter + reviewer pass ----


def test_judge_and_arbiter_spans_route_and_order():
    trace = make_trace(
        "t-judge-arbiter",
        span_names=[
            "intake-document",
            "classify-document",
            "extract-fields",
            "judge-verify",
            "arbitrate-verdict",
            "compile-report",
            "write-catalog",
            "archive-document",
        ],
    )
    run = _run(trace)
    assert run.stage == Stage.ARCHIVED
    assert run.routing_path == [
        "intake",
        "classify",
        "extract",
        "judge_verify",
        "arbiter",
        "report",
        "catalog",
        "archive",
    ]


def test_judge_verify_inflight_derives_from_last_span():
    trace = make_trace(
        "t-judge-inflight",
        stage="processing",
        span_names=["intake-document", "classify-document", "extract-fields", "judge-verify"],
        verdict=None,
    )
    run = _run(trace)
    assert run.stage == Stage.JUDGE_VERIFY
    assert run.phase == Phase.EXTRACTION_ADJUDICATION


def test_arbiter_inflight_derives_from_last_span():
    trace = make_trace(
        "t-arbiter-inflight",
        stage="processing",
        span_names=["intake-document", "classify-document", "extract-fields",
                    "judge-verify", "arbitrate-verdict"],
        verdict=None,
    )
    run = _run(trace)
    assert run.stage == Stage.ARBITER


def test_reviewer_pass_does_not_stack_retry_classify():
    """KANBAN-062 Lane A emits a THIRD classify-document span; the displayed
    path must contain retry_classify exactly once."""
    trace = make_trace(
        "t-reviewer-pass",
        span_names=[
            "intake-document",
            "classify-document",
            "classify-document",
            "classify-document",
            "route-for-review",
        ],
        verdict=None,
    )
    run = _run(trace)
    assert run.routing_path.count("classify") == 1
    assert run.routing_path.count("retry_classify") == 1


def test_insurance_claim_doc_class_roundtrip():
    trace = make_trace(
        "t-insurance",
        doc_type="insurance_claim",
        span_names=["intake-document", "classify-document", "extract-fields",
                    "compile-report", "write-catalog", "archive-document"],
    )
    run = _run(trace)
    assert run.doc_type == "insurance_claim"
    assert run.stage == Stage.ARCHIVED


def test_schema_mirror_covers_upstream_contract():
    """The mirror must know every upstream agent/doc class/span (the #1
    maintenance duty per AGENTS.md)."""
    from mailroom_ui import pipeline_schema as ps

    for span in ("judge-verify", "arbitrate-verdict"):
        assert span in ps.SPAN_STAGE_MAP
    for agent in ("sorter_reviewer", "arbiter", "insurance_claims_specialist",
                  "image_extractor", "intake"):
        assert agent in ps.AGENTS
    assert "normalize-intake" in ps.SPAN_STAGE_MAP
    assert ps.SPAN_STAGE_MAP["normalize-intake"] == Stage.INTAKE
    assert "image-extractor" not in ps.AGENTS
    assert "compliance_filing" in ps.RETIRED_DOC_TYPES
    assert "compliance_filing" not in ps.LIVE_DOC_TYPES
    assert "merger_agreement" in ps.LIVE_DOC_TYPES
    assert "compliance_filing" not in ps.DOC_CLASSES
    assert "court_opinion" not in ps.DOC_CLASSES
    assert "due_diligence" not in ps.DOC_CLASSES
    assert ps.EXTRACT_CLASS_ALIASES == {}
    assert ps.resolve_extract_class("merger_agreement") == "merger_agreement"
    assert ps.resolve_extract_class("contract") == "contract"
    assert ps.resolve_extract_class("unknown") is None
    assert ps.resolve_extract_class("court_opinion") is None
    assert ps.resolve_extract_class("compliance_filing") is None
    assert ps.DOC_CLASSES["insurance_claim"] == "Insurance Claim"
    assert ps.DOC_CLASSES["merger_agreement"] == "Merger Agreement"
    assert ps.SPECIALIST_BY_DOC_CLASS["insurance_claim"] == "insurance_claims_specialist"
    # llm-mailroom #64: MAUD has its own specialist + MergerAgreementExtraction.
    assert ps.SPECIALIST_BY_DOC_CLASS["merger_agreement"] == "merger_agreement_specialist"
    assert "merger_agreement_specialist" in ps.AGENTS
    assert "effective_time" in ps.EXTRACTION_FIELD_KEYS_BY_CLASS["merger_agreement"]
    assert "cuad_clauses" not in ps.EXTRACTION_FIELD_KEYS_BY_CLASS["merger_agreement"]
    assert ps.SPAN_STAGE_MAP["intake-ml-triage"] == Stage.INTAKE
    assert ps.observation_type_for("intake-ml-triage") == "span"
    assert ps.PipelineSchema().thresholds_for("correspondence")["low"] == 0.85
    assert "license" in ps.DOC_SUBCLASS_BY_CLASS["contract"]
    assert "cuad_clauses" in ps.EXTRACTION_FIELD_KEYS_BY_CLASS["contract"]
    assert "key_obligations" not in ps.EXTRACTION_FIELD_KEYS_BY_CLASS["contract"]
    assert "claim_checklist" in ps.EXTRACTION_FIELD_KEYS_BY_CLASS["insurance_claim"]
    assert "intent" in ps.EXTRACTION_FIELD_KEYS_BY_CLASS["corporate_record"]
    assert ps.langfuse_score_name("extraction_overall_verified_precision") == "extraction_verified_precision"
    assert ps.canonical_score_name("extraction_verified_precision") == "extraction_overall_verified_precision"
    assert "content_topic_accuracy" in ps.SUITE_EXTRA_SCORES
    assert "maud_question_accuracy" in ps.SUITE_EXTRA_SCORES
    schema = ps.PipelineSchema.load()
    assert schema.judge_band_high == 0.95
    assert schema.confidence_high == 0.97
    assert schema.confidence_low == 0.88
    assert schema.retry_max == 2
    assert schema.arbiter_retry_max == 2
    assert schema.judge_max_passes == 3
    assert ps.NODE_OBSERVATION_TYPES["document-pipeline"] == "chain"
    assert ps.NODE_OBSERVATION_TYPES["classify-document"] == "agent"
    assert ps.NODE_OBSERVATION_TYPES["judge-verify"] == "evaluator"
    assert ps.NODE_OBSERVATION_TYPES["transcribe-pdf"] == "retriever"
    assert ps.NODE_OBSERVATION_TYPES["pipeline-result"] == "generation"
    assert ps.NODE_OBSERVATION_TYPES["answer-question"] == "generation"
    assert ps.observation_type_for("retry_classify") == "agent"
    assert ps.observation_type_for("judge_verify") == "evaluator"


def test_typed_datamodel_observations_keep_routing_and_generations():
    """llm-mailroom #29 types nodes as AGENT/EVALUATOR/RETRIEVER/CHAIN.
    Those must still build a routing path, keep judge-verify, and leave
    pipeline-result / answer-question as generations — not floor stations.
    """
    base = datetime(2026, 8, 26, 2, 42, 6)
    trace = make_trace(
        "t-datamodel",
        base_time=base,
        span_names=[
            "intake-document",
            "normalize-intake",
            "transcribe-pdf",
            "classify-document",
            "extract-fields",
            "judge-verify",
            "arbitrate-verdict",
            "compile-report",
            "write-catalog",
            "archive-document",
        ],
        include_root=True,
        user_id="mailroom-pilot",
        release="mailroom@0.9.0",
        extra_observations=[
            Obj(
                id="gen-result",
                type="GENERATION",
                name="pipeline-result",
                model="qwen/qwen3.7-flash",
                start_time=base + timedelta(seconds=70),
                end_time=base + timedelta(seconds=72),
                latency=2.0,
                usage={"total": 80, "input": 50, "output": 30},
                level="DEFAULT",
            ),
            Obj(
                id="gen-lb",
                type="GENERATION",
                name="answer-question",
                metadata={"task_id": "cuad_q1", "index": 0},
                model="qwen/qwen3.7-flash",
                start_time=base + timedelta(seconds=73),
                end_time=base + timedelta(seconds=74),
                latency=1.0,
                usage={"total": 40, "input": 30, "output": 10},
                level="DEFAULT",
            ),
        ],
    )
    run = _run(trace)
    by_name = {s.name: s for s in run.spans}
    assert by_name["document-pipeline"].observation_type == "CHAIN"
    assert by_name["document-pipeline"].is_root is True
    assert by_name["classify-document"].observation_type == "AGENT"
    assert by_name["extract-fields"].observation_type == "AGENT"
    assert by_name["judge-verify"].observation_type == "EVALUATOR"
    assert by_name["transcribe-pdf"].observation_type == "RETRIEVER"
    assert by_name["arbitrate-verdict"].observation_type == "AGENT"
    assert "document-pipeline" not in run.routing_path
    assert "judge_verify" in run.routing_path
    assert "arbiter" in run.routing_path
    assert run.user_id == "mailroom-pilot"
    assert run.release == "mailroom@0.9.0"
    gen_names = [g.name for g in run.generations]
    assert "pipeline-result" in gen_names
    assert "answer-question" in gen_names
    assert all(g.observation_type == "GENERATION" for g in run.generations
               if g.name in ("pipeline-result", "answer-question"))


def test_agent_type_without_model_is_not_dropped():
    """Pre-#29 interpreter only treated SPAN/EVENT as nodes; AGENT would
    fall through and, without model/usage, luckily become a span. Pin the
    explicit type path so a future fallback change cannot hide judge-verify.
    """
    now = datetime(2026, 8, 26, 3, 0, 0)
    run = interpret_trace(
        {
            "id": "t-agent-only",
            "name": "document-pipeline",
            "timestamp": now,
            "output": {"stage": "processing"},
            "observations": [
                {
                    "id": "o1",
                    "observationType": "AGENT",
                    "name": "classify-document",
                    "startTime": now.isoformat(),
                    "endTime": (now + timedelta(seconds=2)).isoformat(),
                    "latency": 2.0,
                },
                {
                    "id": "o2",
                    "observationType": "EVALUATOR",
                    "name": "judge-verify",
                    "startTime": (now + timedelta(seconds=3)).isoformat(),
                    "endTime": (now + timedelta(seconds=4)).isoformat(),
                    "latency": 1.0,
                },
            ],
        }
    )
    assert [s.name for s in run.spans] == ["classify-document", "judge-verify"]
    assert run.routing_path == ["classify", "judge_verify"]
    assert run.stage == Stage.JUDGE_VERIFY
    assert run.generations == []


def test_docclass_eval_trace_maps_to_classify_station():
    """Entity-repo docclass runner traces (name docclass_classification,
    output {"sorter": {...}}) display at the SORTER station with doc_type +
    classification confidence — pilot runs become floor-visible data."""
    from mailroom_ui.trace_interpreter import interpret_trace

    now = "2026-08-24T12:00:00Z"
    run = interpret_trace({
        "id": "dc-1", "name": "docclass_classification", "timestamp": now,
        "session_id": "qwen3.7-flash_sorter_docclass_pilot_v1_pilot140",
        "environment": "pilot",
        "tags": ["llm-dojo", "pilot"],
        "input": {"filename": "sample.pdf", "expected": "contract"},
        "output": {"sorter": {"doc_type": "contract", "contract_subtype": "license",
                              "doc_subclass": None, "confidence": 0.93,
                              "reasoning": "title says LICENSE"}},
    })
    assert run.stage.value == "classify"
    assert run.phase.value == "intake_sort"
    assert run.doc_type == "contract"
    assert abs(run.classification_confidence - 0.93) < 1e-9
    assert run.filename == "sample.pdf"
    assert run.contract_subtype == "license"
    assert run.doc_subclass == "license"
    assert run.expected_hf_class == "contract"


def test_compliance_filing_subclass_gt_intake_and_score_alias():
    """dojo 0.9.0 / mailroom #30: live compliance_filing, Hub subclass,
    HF GT metadata, normalize-intake span stats, and the 35-char
    verified-precision alias all land on PipelineRun (snake_case)."""
    intake = {
        "messy": True,
        "changed": True,
        "method": "deterministic",
        "chars": 412,
        "hyphen_unwraps": 2,
        "collapsed_blank_runs": 1,
    }
    trace = make_trace(
        "t-compliance",
        doc_type="compliance_filing",
        doc_subclass="10-K",
        extra_scores={
            "extraction_verified_precision": 0.81,
            "maud_question_accuracy": 0.7,
            "content_topic_accuracy": 0.9,
        },
        extra_metadata={"expected_hf_class": "compliance_filing",
                        "expected_subclass": "10-K"},
        extra_input={"ground_truth": {
            "expected_hf_class": "compliance_filing",
            "expected_subclass": "10-K",
        }},
        intake_output=intake,
    )
    run = _run(trace)
    assert run.doc_type == "compliance_filing"
    assert run.doc_subclass == "10-K"
    assert run.expected_hf_class == "compliance_filing"
    assert run.expected_subclass == "10-K"
    assert run.intake_messy is True
    assert run.intake_changed is True
    assert run.intake_method == "deterministic"
    assert run.intake_chars == 412
    assert run.scores["extraction_verified_precision"] == 0.81
    assert run.scores["extraction_overall_verified_precision"] == 0.81
    assert run.scores["maud_question_accuracy"] == 0.7


def test_v4_compliance_filing_subclass_and_intake():
    """Same contract on v4 camelCase observations."""
    trace = make_trace_v4(
        "t-v4-compliance",
        doc_type="compliance_filing",
        doc_subclass="8-K",
        extra_metadata={"expected_subclass": "8-K", "expected_hf_class": "compliance_filing"},
        extra_scores={"extraction_overall_verified_precision": 0.66,
                      "sentiment_accuracy": 0.55},
        intake_output={"messy": False, "changed": True, "method": "deterministic",
                       "chars": 88, "cleaned_chars": 88},
        classify_generation_output='{"doc_type": "compliance_filing", "doc_subclass": "8-K"}',
    )
    run = _run(trace)
    assert run.doc_type == "compliance_filing"
    assert run.doc_subclass == "8-K"
    assert run.expected_subclass == "8-K"
    assert run.expected_hf_class == "compliance_filing"
    assert run.intake_changed is True
    assert run.intake_messy is False
    assert run.intake_chars == 88
    assert run.scores["extraction_verified_precision"] == 0.66
    assert run.scores["extraction_overall_verified_precision"] == 0.66


def test_classify_generation_json_fills_subclass_when_span_summary_omits_it():
    """llm-mailroom _result_summary omits doc_subclass; mine classify JSON."""
    trace = make_trace("t-gen-sub", doc_type="contract")
    # Node-span output stays the curated summary (no subclass).
    for obs in trace["observations"]:
        if getattr(obs, "name", None) == "classify-document" and getattr(obs, "type", "") != "GENERATION":
            obs.output = {"stage": "ok", "doc_type": "contract"}
        if getattr(obs, "name", None) == "classify-document" and getattr(obs, "type", "") == "GENERATION":
            obs.output = '{"doc_type": "contract", "doc_subclass": "license", "contract_subtype": "license"}'
    trace["output"] = {"stage": "archived", "doc_type": "contract"}
    run = _run(trace)
    assert run.doc_subclass == "license"
    assert run.contract_subtype == "license"


def test_list_recent_runs_honors_trace_names_env(monkeypatch):
    """MAILROOM_TRACE_NAMES extends the floor's trace-name universe and
    merges results across names without duplicates."""
    from datetime import datetime, timedelta, timezone

    import mailroom_ui.langfuse_source as ls

    calls = []

    class StubSource:
        def list_traces(self, *, since=None, limit=200, name=None, tags=None, environments=None):
            calls.append(name)
            if name == "document-pipeline":
                return [{"id": "t1", "timestamp": "2026-08-24T12:00:00Z"}]
            if name == "docclass_classification":
                return [{"id": "t1", "timestamp": "2026-08-24T12:00:00Z"},   # duplicate
                        {"id": "t2", "timestamp": "2026-08-24T12:01:00Z"}]
            return []

        def get_score_configs(self):
            return {}

    monkeypatch.setattr(ls.os, "environ", {**ls.os.environ, "MAILROOM_TRACE_NAMES": "document-pipeline,docclass_classification"})
    runs = ls.list_recent_runs(StubSource(), since=datetime.now(timezone.utc), limit=10)
    assert sorted(calls) == ["docclass_classification", "document-pipeline"]
    assert [r.trace_id for r in runs] == ["t2", "t1"]


def test_intake_ml_triage_span_is_intake_on_both_sdk_shapes():
    """llm-mailroom #85 M6a: the ModernBERT triage SPAN (always emitted,
    fail-open) must land on INTAKE — never an `unknown` stage — for v2/v3
    snake_case and v4 camelCase observations alike."""
    triage = {"available": False, "reason": "flag_off", "route": None,
              "triage_class": None, "confidence": None, "latency_ms": 0.4}
    for trace in (make_trace("t-bert", ml_triage_output=triage),
                  make_trace_v4("t-bert-v4", ml_triage_output=triage)):
        run = interpret_trace(trace, trace["observations"], trace["scores"])
        span = next(s for s in run.spans if s.name == "intake-ml-triage")
        assert span.observation_type == "SPAN"
        assert span.output == triage
        assert run.stage != Stage.UNKNOWN
        assert run.routing_path[0] == "intake"
