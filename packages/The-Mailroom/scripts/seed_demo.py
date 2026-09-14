"""Seed demo traces INTO Langfuse (env `demo`) for UI/UX play-testing.

The Mailroom never serves canned data — demo runs are written into the real
Langfuse project configured in .env (the same project the server reads), as
full `document-pipeline` traces with verb-first node spans, LLM generations
and judge scores. They land in the `demo` environment (tags `mailroom`,
`demo`, `run-N`), separable via `MAILROOM_TRACE_ENVIRONMENTS=demo`.

Usage:
    python scripts/seed_demo.py                  # seed the full demo set
    python scripts/seed_demo.py --list-scenarios
    python scripts/seed_demo.py --scenario contract-clean
    python scripts/seed_demo.py --check          # fetch + interpret back
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from langfuse.api.ingestion.types import (
    CreateGenerationBody,
    CreateSpanBody,
    IngestionEvent_GenerationCreate,
    IngestionEvent_SpanCreate,
    IngestionEvent_TraceCreate,
    ScoreBody,
    TraceBody,
)

# Models mirror llm-mailroom config/taxonomy.yaml `agents:` mapping:
# qwen/qwen3.7-flash everywhere except the offline judge (deepseek-v4-flash).
GEN_MODELS = {
    "classify": ("qwen/qwen3.7-flash", 1100, 220),
    "review_classify": ("qwen/qwen3.7-flash", 1300, 260),
    "extract": ("qwen/qwen3.7-flash", 2400, 620),
    "adjudicate": ("qwen/qwen3.7-flash", 1500, 480),
    "route": ("qwen/qwen3.7-flash", 900, 300),
    "report": ("qwen/qwen3.7-flash", 2100, 760),
    "catalog": ("qwen/qwen3.7-flash", 350, 500),
    # KANBAN-063 quality gate: judge is deepseek-v4-flash, arbiter is qwen.
    "judge": ("deepseek/deepseek-v4-flash", 1800, 240),
    "arbiter": ("qwen/qwen3.7-flash", 2600, 380),
}

SPAN_MS = {
    "intake-document": 3200,
    "classify-document": 7200,
    "judge-verify": 6400,
    "arbitrate-verdict": 7700,
    "extract-fields": 14000,
    "route-for-review": 4100,
    "adjudicate-conflict": 8300,
    "compile-report": 5100,
    "write-catalog": 2900,
    "archive-document": 1500,
}

# Prices mirror taxonomy.yaml cost_models (USD per 1M tokens).
MODEL_RATES = {
    "qwen/qwen3.7-flash": (0.03, 0.13),
    "deepseek/deepseek-v4-flash": (0.05, 0.25),
}


def gen_cost(model: str, inp: int, out: int) -> float:
    rate_in, rate_out = MODEL_RATES[model]
    return (inp * rate_in + out * rate_out) / 1_000_000


@dataclass
class DemoRun:
    tid: str
    trace: TraceBody
    spans: list[CreateSpanBody] = field(default_factory=list)
    gens: list[CreateGenerationBody] = field(default_factory=list)
    scores: list[ScoreBody] = field(default_factory=list)
    obs_counts: dict = field(default_factory=dict)


def _span(tid, name, start, end, *, level="DEFAULT", output=None, input=None, obs_id=None):
    return CreateSpanBody(
        id=obs_id or f"{tid}-{name}",
        trace_id=tid,
        name=name,
        start_time=start,
        end_time=end,
        level=level,
        input=input or {},
        output=output or {"status": "ok"},
        metadata={"seed": "seed_demo"},
    )


def _gen(tid, name, start, end, *, agent, model, inp, out, obs_id=None):
    return CreateGenerationBody(
        id=obs_id or f"{tid}-{name}-gen",
        trace_id=tid,
        name=name,
        model=model,
        start_time=start,
        end_time=end,
        level="DEFAULT",
        usage={"input": inp, "output": out, "total": inp + out},
        usage_details={"input": inp, "output": out, "total": inp + out},
        cost_details={"input": 0.0, "output": 0.0, "total": gen_cost(model, inp, out)},
        metadata={"agent": agent, "seed": "seed_demo"},
        input={"prompt_sha": "demo"},
        output={"reply_sha": "demo"},
    )


JUDGE_CONFIG_NAME = "mailroom-pipeline-judge"
JUDGE_CATEGORIES = [
    {"value": 0, "label": "CORRECT"},
    {"value": 1, "label": "PARTIAL"},
    {"value": 2, "label": "MISS"},
]


def ensure_score_configs(client) -> str:
    """Ensure the CATEGORICAL judge-verdict config exists; return its id.

    Langfuse stores CATEGORICAL score values as a numeric index into a score
    config's categories, so verdicts need a real config to survive the API.
    """
    cfg_api = client.api.score_configs
    existing = {}
    try:
        for cfg in cfg_api.get(limit=100, request_options={"timeout_in_seconds": 20}).data:
            existing[cfg.name] = cfg
    except Exception:
        pass
    cfg = existing.get(JUDGE_CONFIG_NAME)
    if cfg is not None:
        return cfg.id
    created = cfg_api.create(name=JUDGE_CONFIG_NAME, data_type="CATEGORICAL",
                             categories=JUDGE_CATEGORIES,
                             request_options={"timeout_in_seconds": 20})
    print(f"  created score config {JUDGE_CONFIG_NAME} ({created.id})")
    return created.id


def _score(tid, name, value, data_type="NUMERIC", comment=None, config_id=None):
    score_id = f"{tid}-{name}"
    return ScoreBody(id=score_id, name=name, value=value, trace_id=tid,
                     data_type=data_type, comment=comment, config_id=config_id)


def add_node(run, cursor, name, *, level="DEFAULT", output=None, gen=None, agent=None,
             gen_scale=0.85):
    ms = SPAN_MS[name]
    start = cursor
    end = cursor + timedelta(milliseconds=ms)
    # Retry nodes repeat a name — give each occurrence a unique observation id
    # or the ingestion upsert overwrites the earlier span.
    n = run.obs_counts.get(name, 0)
    run.obs_counts[name] = n + 1
    obs_id = f"{run.tid}-{name}" if n == 0 else f"{run.tid}-{name}-{n}"
    run.spans.append(_span(run.tid, name, start, end, level=level, output=output, obs_id=obs_id))
    if gen and agent:
        model, inp, out = GEN_MODELS[gen]
        run.gens.append(_gen(run.tid, name, start, start + timedelta(milliseconds=ms * gen_scale),
                             agent=agent, model=model, inp=inp, out=out, obs_id=f"{obs_id}-gen"))
    return end


def build_run(spec, start):
    tid = f"demo-{spec['slug']}"
    t0 = start
    t1 = t0 + timedelta(seconds=1)
    doc = spec["doc_type"]
    run = DemoRun(
        tid=tid,
        trace=TraceBody(
            id=tid,
            name="document-pipeline",
            timestamp=t0,
            environment=spec.get("env", "demo"),
            tags=["mailroom", spec.get("env", "demo"), f"run-{spec['run']}", "source-seed_demo"],
            session_id=spec["matter"],
            input={
                "filename": spec["filename"],
                "matter_id": spec["matter"],
                "attempt": spec.get("attempt", 1),
                "source": "docclass-pilot",
                # V-27: ground-truth labels (doc_type/subclass) are NEVER in
                # the trace input — the sorter and specialists are evaluated
                # AGAINST them, so agents must not see them. The pipeline's
                # own predicted class lives in trace output; the ground truth
                # itself only surfaces as evaluation scores (grounded block).
            },
            output=spec["trace_output"],
            metadata={
                "attempt": spec.get("attempt", 1),
                "run_id": tid,
                "run_deadline": (t1 + timedelta(minutes=45)).isoformat(),
                "seed": "seed_demo",
            },
        ),
    )
    cursor = t1
    cursor = add_node(run, cursor, "intake-document")
    cursor = add_node(run, cursor, "classify-document", gen="classify", agent="sorter")
    if spec.get("retry_classify"):
        cursor = add_node(run, cursor, "classify-document", gen="classify", agent="sorter")
    if spec.get("inflight"):
        run.spans.append(_span(run.tid, "extract-fields", cursor, cursor, output={"status": "running"}))
        return run
    cursor = add_node(run, cursor, "extract-fields", level=spec.get("extract_level", "DEFAULT"),
                      output=spec.get("extract_output"), gen="extract", agent=spec["specialist"])
    if spec.get("retry_extract"):
        cursor = add_node(run, cursor, "extract-fields", gen="extract", agent=spec["specialist"])
    if spec.get("failed"):
        return run
    # KANBAN-063 quality gate: judge-verify fires on the ambiguous extraction
    # band; a partial verdict detours through arbitrate-verdict before report.
    if spec.get("judge_verify"):
        cursor = add_node(run, cursor, "judge-verify", gen="judge", agent="judge",
                          output={"verdict": spec.get("judge_outcome", "partial")})
    if spec.get("arbiter"):
        cursor = add_node(run, cursor, "arbitrate-verdict", gen="arbiter", agent="arbiter",
                          output={"decision": "accept_with_caveats"})
    if spec.get("review"):
        cursor = add_node(run, cursor, "route-for-review", gen="route", agent=spec["specialist"],
                          output={"decision": "review", "reason": spec.get("escalation")})
        return run
    if spec.get("boss"):
        cursor = add_node(run, cursor, "adjudicate-conflict", gen="adjudicate", agent="boss",
                          output={"decision": "override", "conflict": True})
    cursor = add_node(run, cursor, "compile-report", gen="report", agent="reporter")
    cursor = add_node(run, cursor, "write-catalog", gen="catalog", agent="archivist")
    add_node(run, cursor, "archive-document")
    for name, value in spec.get("extra_scores", {}).items():
        run.scores.append(_score(run.tid, name, value))
    return run


SPECS = [
    # The scenario catalog mirrors the Lucius-Morningstar/docclass-pilot HF
    # dataset universe: 5 doc classes (contract / merger_agreement /
    # corporate_record / correspondence / insurance_claim) with their
    # subclasses. Filenames follow the dataset's naming style.
    {"slug": "contract-clean", "run": 1,
     "filename": "contract_service_agreement_03.pdf", "doc_type": "contract",
     "subclass": "Service", "matter": "demo-matter-acme-services",
     "specialist": "contracts_specialist",
     "verdict": "CORRECT", "quality": 0.97, "conf_cls": 0.98, "conf_ext": 0.96,
     "grounded": {"field": 0.95, "overall": 0.96, "list_p": 0.93, "list_r": 1.0, "halluc": 0.0},
     "trace_output": {"stage": "archived", "doc_type": "contract",
                      "classification_confidence": 0.98, "extraction_confidence": 0.96}},
    {"slug": "contract-partial", "run": 2,
     "filename": "contract_master_services_agreement_05.pdf", "doc_type": "contract",
     "subclass": "Consulting Agreements", "matter": "demo-matter-acme-services",
     "specialist": "contracts_specialist",
     "verdict": "PARTIAL", "quality": 0.58, "conf_cls": 0.97, "conf_ext": 0.63,
     "grounded": {"field": 0.55, "overall": 0.6, "list_p": 0.6, "list_r": 0.5, "halluc": 0.08},
     "trace_output": {"stage": "archived", "doc_type": "contract",
                      "classification_confidence": 0.97, "extraction_confidence": 0.63,
                      "error_message": "2 fields below confidence threshold"}},
    {"slug": "corporate-ok", "run": 3,
     "filename": "corporate_bylaws_amendment_04.pdf", "doc_type": "corporate_record",
     "subclass": "bylaws", "matter": "demo-matter-northwind",
     "specialist": "corporate_records_specialist",
     "verdict": "CORRECT", "quality": 0.95, "conf_cls": 0.99, "conf_ext": 0.97,
     "grounded": {"field": 0.98, "overall": 0.97, "list_p": None, "list_r": None, "halluc": 0.0},
     "trace_output": {"stage": "archived", "doc_type": "corporate_record",
                      "classification_confidence": 0.99, "extraction_confidence": 0.97}},
    # was due-diligence-review (class removed from the pilot universe):
    # human-review siding coverage now rides a merger agreement.
    {"slug": "merger-review", "run": 4,
     "filename": "maud_merger_agreement_all_stock_42.pdf", "doc_type": "merger_agreement",
     "subclass": "all_stock", "matter": "demo-matter-northwind",
     "specialist": "contracts_specialist",
     "verdict": "PARTIAL", "quality": 0.44, "conf_cls": 0.93, "conf_ext": 0.61,
     "review": True, "escalation": "low extraction confidence (0.61) on indemnification clause",
     "grounded": {"field": 0.48, "overall": 0.52, "list_p": 0.55, "list_r": 0.44, "halluc": 0.12},
     "trace_output": {"stage": "review", "doc_type": "merger_agreement",
                      "classification_confidence": 0.93, "extraction_confidence": 0.61,
                      "review_decision": "human review",
                      "escalation_reason": "low extraction confidence (0.61) on indemnification clause"}},
    {"slug": "correspondence-miss", "run": 5,
     "filename": "correspondence_demand_letter_09.pdf", "doc_type": "correspondence",
     "subclass": "demand", "matter": "demo-matter-harbor",
     "specialist": "correspondence_specialist",
     "verdict": "MISS", "quality": 0.31, "conf_cls": 0.93, "conf_ext": 0.88,
     "trace_output": {"stage": "archived", "doc_type": "correspondence",
                      "classification_confidence": 0.93, "extraction_confidence": 0.88,
                      "error_message": "judge: deadline field missed"}},
    # was compliance-failed (class removed): failed-bin coverage now rides a
    # corporate record whose extraction returned invalid JSON.
    {"slug": "corporate-failed", "run": 6,
     "filename": "corporate_articles_of_incorporation_02.pdf", "doc_type": "corporate_record",
     "subclass": "articles_of_incorporation", "matter": "demo-matter-harbor",
     "specialist": "corporate_records_specialist",
     "conf_cls": 0.91, "conf_ext": None,
     "extract_level": "ERROR", "extract_output": {"error": "extraction failed: LLM output not valid JSON"},
     "failed": True,
     "trace_output": {"stage": "failed", "doc_type": "corporate_record",
                      "classification_confidence": 0.91,
                      "error_message": "extraction failed: LLM output not valid JSON",
                      "run_aborted": True}},
    # was court-inflight (class removed): in-flight coverage now rides an
    # insurance claim mid-extraction.
    {"slug": "insurance-inflight", "run": 7,
     "filename": "insurance_claim_fnol_package_01.pdf", "doc_type": "insurance_claim",
     "subclass": "carrier", "matter": "demo-matter-harbor",
     "specialist": "insurance_claims_specialist",
     "conf_cls": 0.96, "conf_ext": None, "inflight": True,
     "trace_output": {"doc_type": "insurance_claim",
                      "classification_confidence": 0.96}},
    {"slug": "contract-retry", "run": 8,
     "filename": "contract_consulting_agreement_06.pdf", "doc_type": "contract",
     "subclass": "Consulting Agreements", "matter": "demo-matter-acme-services",
     "specialist": "contracts_specialist",
     "verdict": "CORRECT", "quality": 0.9, "conf_cls": 0.95, "conf_ext": 0.94,
     "retry_classify": True, "retry_extract": True,
     "grounded": {"field": 0.91, "overall": 0.92, "list_p": 0.85, "list_r": 0.9, "halluc": 0.03},
     "trace_output": {"stage": "archived", "doc_type": "contract",
                      "classification_confidence": 0.95, "extraction_confidence": 0.94}},
    {"slug": "boss-conflict", "run": 9,
     "filename": "contract_joint_venture_agreement_04.pdf", "doc_type": "contract",
     "subclass": "Joint Venture", "matter": "demo-matter-acme-services",
     "specialist": "contracts_specialist",
     "verdict": "PARTIAL", "quality": 0.66, "conf_cls": 0.94, "conf_ext": 0.72,
     "boss": True, "escalation": "conflicting specialist extraction on effective date",
     "extra_scores": {"conflict_detected": True, "conflict_threshold_breach": 0.41},
     "grounded": {"field": 0.7, "overall": 0.68, "list_p": 0.66, "list_r": 0.75, "halluc": 0.05},
     "trace_output": {"stage": "archived", "doc_type": "contract",
                      "classification_confidence": 0.94, "extraction_confidence": 0.72,
                      "escalation_reason": "conflicting specialist extraction on effective date"}},
    {"slug": "low-confidence", "run": 10,
     "filename": "correspondence_internal_memo_04.pdf", "doc_type": "correspondence",
     "subclass": "meeting_request", "matter": "demo-matter-northwind",
     "specialist": "correspondence_specialist",
     "verdict": "PARTIAL", "quality": 0.5, "conf_cls": 0.52, "conf_ext": 0.81,
     "trace_output": {"stage": "archived", "doc_type": "correspondence",
                      "classification_confidence": 0.52, "extraction_confidence": 0.81}},
    {"slug": "insurance-clean", "run": 11,
     "filename": "insurance_claim_coverage_determination_07.pdf", "doc_type": "insurance_claim",
     "subclass": "carrier", "matter": "demo-matter-harbor",
     "specialist": "insurance_claims_specialist",
     "verdict": "CORRECT", "quality": 0.94, "conf_cls": 0.97, "conf_ext": 0.95,
     "grounded": {"field": 0.93, "overall": 0.94, "list_p": None, "list_r": None, "halluc": 0.0},
     "trace_output": {"stage": "archived", "doc_type": "insurance_claim",
                      "classification_confidence": 0.97, "extraction_confidence": 0.95}},
    {"slug": "insurance-judge-gate", "run": 12,
     "filename": "insurance_claim_fnol_package_11.pdf", "doc_type": "insurance_claim",
     "subclass": "carrier", "matter": "demo-matter-harbor",
     "specialist": "insurance_claims_specialist",
     "verdict": "PARTIAL", "quality": 0.62, "conf_cls": 0.96, "conf_ext": 0.78,
     "judge_verify": True, "judge_outcome": "partial",
     "grounded": {"field": 0.64, "overall": 0.66, "list_p": None, "list_r": None, "halluc": 0.06},
     "trace_output": {"stage": "archived", "doc_type": "insurance_claim",
                      "classification_confidence": 0.96, "extraction_confidence": 0.78}},
    {"slug": "merger-arbitrated", "run": 13,
     "filename": "maud_merger_agreement_mixed_cash_stock_117.pdf",
     "doc_type": "merger_agreement",
     "subclass": "mixed_cash_stock", "matter": "demo-matter-acme-services",
     "specialist": "contracts_specialist",
     "verdict": "CORRECT", "quality": 0.83, "conf_cls": 0.98, "conf_ext": 0.74,
     "judge_verify": True, "judge_outcome": "partial", "arbiter": True,
     "extra_scores": {"arbiter_decision_score": 1},
     "grounded": {"field": 0.78, "overall": 0.8, "list_p": 0.72, "list_r": 0.81, "halluc": 0.04},
     "trace_output": {"stage": "archived", "doc_type": "merger_agreement",
                      "classification_confidence": 0.98, "extraction_confidence": 0.74}},
]

SCENARIO_FLAGS = {
    "merger-review": ["review siding"],
    "corporate-failed": ["failed"],
    "insurance-inflight": ["in-flight"],
    "contract-retry": ["retry"],
    "boss-conflict": ["boss adjudication"],
    "low-confidence": ["low confidence"],
    "insurance-judge-gate": ["judge gate"],
    "merger-arbitrated": ["judge gate", "arbiter"],
}


def _as_dict(value):
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value if isinstance(value, dict) else {}


def attach_scores(run, spec, judge_config_id=None):
    total_tokens = sum(_as_dict(g.usage).get("total") or 0 for g in run.gens)
    total_cost = sum(_as_dict(g.cost_details).get("total") or 0.0 for g in run.gens)
    # Core run metrics — mirror llm-mailroom observability/scores.py
    # SCORE_CONFIGS "core run metrics" block (emitted for EVERY run).
    run.scores.append(_score(run.tid, "classification_confidence", round(spec["conf_cls"], 3)))
    if spec["conf_ext"] is not None:
        run.scores.append(_score(run.tid, "extraction_confidence", round(spec["conf_ext"], 3)))
    run.scores.append(_score(run.tid, "estimated_cost_usd", round(total_cost, 5)))
    run.scores.append(_score(run.tid, "total_tokens", total_tokens))
    run.scores.append(_score(run.tid, "llm_call_count", len(run.gens)))
    run.scores.append(
        _score(run.tid, "classification_attempts", 2 if spec.get("retry_classify") else 1))
    run.scores.append(
        _score(run.tid, "extraction_attempts", 2 if spec.get("retry_extract") else 1))
    duration_s = round(6.4 + len(run.spans) * 3.1, 1)
    run.scores.append(_score(run.tid, "run_duration_seconds", duration_s))
    run.scores.append(_score(run.tid, "stage_completed", 1, "BOOLEAN"))
    # Deterministic field-type-aware extraction scoring — emitted for grounded
    # runs (mirrors the pilot's grounded docclass-pilot runs; see SCORE_CONFIGS).
    g = spec.get("grounded")
    if g:
        run.scores.append(_score(run.tid, "extraction_field_score", g["field"]))
        run.scores.append(_score(run.tid, "extraction_overall_score", g["overall"]))
        run.scores.append(_score(run.tid, "extraction_hallucination_rate", g["halluc"]))
        if g.get("list_p") is not None:
            run.scores.append(_score(run.tid, "entity_list_precision", g["list_p"]))
        if g.get("list_r") is not None:
            run.scores.append(_score(run.tid, "entity_list_recall", g["list_r"]))
        run.scores.append(_score(run.tid, "expected_field_presence", round(g["field"] + 0.02, 3)))
    if spec.get("verdict"):
        run.scores.append(_score(run.tid, JUDGE_CONFIG_NAME, spec["verdict"],
                                 "CATEGORICAL", comment="demo judge run",
                                 config_id=judge_config_id))
        run.scores.append(_score(run.tid, "mailroom-pipeline-quality", spec["quality"],
                                 comment="demo judge run"))


def make_events(run):
    """Ingestion events for the trace record + its observations (scores are
    attached separately via the SDK's `create_score` — the same path the
    pipeline's own scoring helpers use, and the only one that indexes
    CATEGORICAL config-linked scores reliably)."""
    ts = run.trace.timestamp.isoformat()
    events = [IngestionEvent_TraceCreate(id=f"{run.tid}-trace", timestamp=ts, metadata=None,
                                         body=run.trace)]
    for i, s in enumerate(run.spans):
        events.append(IngestionEvent_SpanCreate(id=f"{run.tid}-span-{i}", timestamp=ts,
                                                metadata=None, body=s))
    for i, g in enumerate(run.gens):
        events.append(IngestionEvent_GenerationCreate(id=f"{run.tid}-gen-{i}", timestamp=ts,
                                                      metadata=None, body=g))
    return events


def attach_scores_via_sdk(client, run, pace_s=0.5):
    """Attach the run's scores through the SDK (queued + flushed).

    The score ingestion queue drops batches under burst (rate limits), so
    scores are paced and the caller should run the repair pass afterwards.
    """
    for sc in run.scores:
        client.create_score(
            trace_id=sc.trace_id,
            name=sc.name,
            value=sc.value,
            data_type=sc.data_type,
            comment=sc.comment,
            config_id=sc.config_id,
            score_id=sc.id,
        )
        time.sleep(pace_s)
    client.flush()


def repair_missing_scores(client, runs, rounds=4, settle_s=25):
    """Re-attach any scores the ingestion queue dropped (verify + fix).

    Reads each run's attached scores back through the v3 scores API (label-
    resolved, correctly filtered) and re-creates missing ones. The ingestion
    pipeline rate-limits score bursts (400 "Bad request" drops), so rounds
    are spaced out until the burst window has passed.
    """
    v3 = client.api.scores_v3
    for round_no in range(1, rounds + 1):
        missing_by_run = []
        for run in runs:
            try:
                resp = v3.get_many_v3(trace_id=run.tid, limit=100,
                                      request_options={"timeout_in_seconds": 20})
                existing = {s.name for s in (resp.data or [])}
            except Exception:
                continue
            missing = [sc for sc in run.scores if sc.name not in existing]
            if missing:
                missing_by_run.append((run, missing))
        if not missing_by_run:
            return
        for run, missing in missing_by_run:
            for sc in missing:
                print(f"  re-attaching missing score {sc.name} on {run.tid}", file=sys.stderr)
                client.create_score(
                    trace_id=sc.trace_id,
                    name=sc.name,
                    value=sc.value,
                    data_type=sc.data_type,
                    comment=sc.comment,
                    config_id=sc.config_id,
                    score_id=sc.id,
                )
                time.sleep(1.0)
        client.flush()
        if round_no < rounds:
            time.sleep(settle_s)
    still_missing = sum(len(m) for _, m in missing_by_run)
    if still_missing:
        print(f"  WARNING: {still_missing} score(s) still missing after "
              f"{rounds} repair rounds", file=sys.stderr)


def cleanup_stale_traces(client, keep_tids: set[str], settle_s=5):
    """Delete demo traces that are no longer part of the scenario catalog.

    NEVER delete-then-recreate an id we are about to seed: Langfuse's async
    pipeline propagates deletes lazily, and a late tombstone can wipe the
    fresh re-seeded trace minutes later ("accepted" -> verified -> gone).
    Ingestion events upsert by deterministic id anyway, so re-seeding the
    SAME scenario needs no delete first.
    """
    trace_api = client.api.trace
    stale = []
    page = 1
    try:
        while True:
            resp = trace_api.list(limit=100, name="document-pipeline", page=page,
                                  request_options={"timeout_in_seconds": 20})
            batch = getattr(resp, "data", None) or []
            for t in batch:
                tid = getattr(t, "id", None)
                tags = getattr(t, "tags", None) or []
                if tid and tid.startswith("demo-") and "mailroom" in tags \
                        and tid not in keep_tids:
                    stale.append(tid)
            if len(batch) < 100 or page >= 20:
                break
            page += 1
    except Exception as exc:
        print(f"  WARNING: stale-trace scan failed ({str(exc)[:120]})", file=sys.stderr)
        return False
    for tid in stale:
        try:
            trace_api.delete(tid, request_options={"timeout_in_seconds": 20,
                                                    "max_retries": 0})
            print(f"  removed stale {tid}")
        except Exception:
            pass
    if stale:
        time.sleep(settle_s)
    return True


def make_langfuse_client():
    from langfuse import Langfuse

    missing = [k for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(f"missing env vars: {', '.join(missing)} (copy .env.example -> .env and fill in)")
    client = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=(os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL") or "https://us.cloud.langfuse.com"),
    )
    # Verify credentials before doing any work: a revoked/placeholder key
    # would otherwise surface as hundreds of confusing failures.
    try:
        client.api.trace.list(limit=1, request_options={"timeout_in_seconds": 20})
    except Exception as exc:
        client.shutdown()
        sys.exit(
            f"Langfuse rejected the configured credentials ({str(exc)[:120]}).\n"
            f"Check LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY in .env — "
            f"placeholder values like 'pk-lf-invalid' will not work."
        )
    return client


def _ingest_chunked(client, batch, *, chunk_size=25, max_retries=3):
    """Ingest events in small chunks WITH retries.

    A single large `max_retries: 0` POST is accepted (202) but its events can
    be silently dropped by Langfuse's async validation — 141 events "accepted",
    zero persisted. Small chunks + SDK retries make delivery observable, and
    the caller's verify pass catches whatever still slips through.
    """
    accepted = errors = 0
    for i in range(0, len(batch), chunk_size):
        chunk = batch[i : i + chunk_size]
        resp = client.api.ingestion.batch(
            batch=chunk,
            request_options={"timeout_in_seconds": 60, "max_retries": max_retries},
        )
        n_err = len(getattr(resp, "errors", None) or [])
        accepted += len(chunk) - n_err
        errors += n_err
        for err in (getattr(resp, "errors", None) or [])[:5]:
            print(f"  ingestion error: {err}", file=sys.stderr)
    return accepted, errors


def verify_seeded(client, runs, timeout_s=150):
    """Poll until every seeded trace is readable; re-ingest stragglers once.

    Returns the list of trace ids that never appeared. This closes the loop on
    delivery: 'accepted' is not 'persisted' with async ingestion.
    """
    trace_api = client.api.trace
    deadline = time.monotonic() + timeout_s
    pending = {r.tid for r in runs}
    reingested = False
    while pending and time.monotonic() < deadline:
        for tid in sorted(pending):
            try:
                trace_api.get(tid, request_options={"timeout_in_seconds": 15,
                                                     "max_retries": 1})
                pending.discard(tid)
            except Exception:
                pass
        if not pending:
            break
        if not reingested and deadline - time.monotonic() < timeout_s * 0.6:
            missing = [r for r in runs if r.tid in pending]
            print(f"  re-ingesting {len(missing)} unverified run(s)", file=sys.stderr)
            retry_batch = []
            for run in missing:
                retry_batch.extend(make_events(run))
            _ingest_chunked(client, retry_batch)
            reingested = True
        time.sleep(8)
    if pending:
        return sorted(pending)
    # Stability pass: a late-propagating delete tombstone can still wipe a
    # freshly seeded trace AFTER it was verified readable. Wait one quiet
    # period and confirm everything is STILL there; re-ingest survivors.
    time.sleep(20)
    unstable = []
    for run in runs:
        try:
            trace_api.get(run.tid, request_options={"timeout_in_seconds": 15,
                                                     "max_retries": 1})
        except Exception:
            unstable.append(run)
    if not unstable:
        return []
    print(f"  {len(unstable)} trace(s) vanished after verify — re-ingesting",
          file=sys.stderr)
    retry_batch = []
    for run in unstable:
        retry_batch.extend(make_events(run))
    _ingest_chunked(client, retry_batch)
    still = []
    for run in unstable:
        try:
            trace_api.get(run.tid, request_options={"timeout_in_seconds": 15,
                                                     "max_retries": 1})
        except Exception:
            still.append(run.tid)
        time.sleep(1)
    return still


def seed(client, specs, start_base, window, judge_config_id=None):
    batch = []
    runs = []
    step = window / max(1, len(specs))
    for i, spec in enumerate(specs):
        run = build_run(spec, start_base - step * i)
        attach_scores(run, spec, judge_config_id)
        runs.append(run)
        batch.extend(make_events(run))
    accepted, errors = _ingest_chunked(client, batch)
    print(f"ingestion accepted: {accepted} event(s), {errors} error(s)")
    never_landed = verify_seeded(client, runs)
    if never_landed:
        print(f"  WARNING: {len(never_landed)} trace(s) not readable after "
              f"verify window: {never_landed}", file=sys.stderr)
    for run in runs:
        attach_scores_via_sdk(client, run)
    repair_missing_scores(client, runs)
    return runs


_SKIP = object()  # expectation sentinel: field not verifiable from this source


def expected_values(spec):
    """Rebuild the exact run the seeder writes (same code path) so the
    readback can be asserted against it — verification, not fabrication."""
    expect = build_run(spec, datetime.now(timezone.utc))
    attach_scores(expect, spec)
    tokens = sum(_as_dict(g.usage).get("total") or 0 for g in expect.gens)
    cost = sum(_as_dict(g.cost_details).get("total") or 0.0 for g in expect.gens)
    if spec.get("failed"):
        stage = "failed"
    elif spec.get("review"):
        stage = "review"
    elif spec.get("inflight"):
        stage = "extract"
    else:
        stage = "archived"
    return {
        "tid": f"demo-{spec['slug']}",
        "filename": spec["filename"],
        "stage": stage,
        "doc_type": spec["doc_type"],
        "verdict": spec.get("verdict"),
        "quality": spec.get("quality"),
        "conf_cls": spec["conf_cls"],
        "conf_ext": spec["conf_ext"],
        "tokens": tokens,
        "cost": cost,
        # Langfuse v4 adds a root span named after the trace to every trace
        # that has observations — account for it in the span-count check.
        "spans": len(expect.spans) + 1,
        "gens": len(expect.gens),
    }


def _got_value(run, key):
    """Read a field off either a PipelineRun or the server's serialized dict."""
    if hasattr(run, key):
        value = getattr(run, key)
        if key == "stage":
            return value.value if hasattr(value, "value") else value
        return value
    return run.get(key) if isinstance(run, dict) else None


def assert_run(expect: dict, run, label: str) -> list[str]:
    """Assert an interpreted/displayed run against the seeded expectation.
    Returns a list of mismatch descriptions (empty == verified). Fields set
    to `_SKIP` are not verifiable from this source and are not asserted."""
    fails = []
    stage = _got_value(run, "stage")
    if expect["stage"] is not _SKIP and stage != expect["stage"]:
        fails.append(f"stage {stage!r} != {expect['stage']!r}")
    doc_type = _got_value(run, "doc_type")
    if expect["doc_type"] is not _SKIP and doc_type != expect["doc_type"]:
        fails.append(f"doc_type {doc_type!r} != {expect['doc_type']!r}")
    verdict = _got_value(run, "verdict")
    if expect["verdict"] is not _SKIP and verdict != expect["verdict"]:
        fails.append(f"verdict {verdict!r} != {expect['verdict']!r}")
    quality = _got_value(run, "quality")
    if (expect["quality"] is not _SKIP and expect["quality"] is not None
            and (quality is None or abs(float(quality) - expect["quality"]) > 0.02)):
        fails.append(f"quality {quality!r} != {expect['quality']}")
    conf_cls = _got_value(run, "classification_confidence")
    if expect["conf_cls"] is not _SKIP and (conf_cls is None
                                            or abs(float(conf_cls) - expect["conf_cls"]) > 0.01):
        fails.append(f"classification_confidence {conf_cls!r} != {expect['conf_cls']}")
    conf_ext = _got_value(run, "extraction_confidence")
    if expect["conf_ext"] is _SKIP:
        pass
    elif expect["conf_ext"] is None:
        if conf_ext is not None:
            fails.append(f"extraction_confidence {conf_ext!r} != None")
    elif conf_ext is None or abs(float(conf_ext) - expect["conf_ext"]) > 0.01:
        fails.append(f"extraction_confidence {conf_ext!r} != {expect['conf_ext']}")
    tokens = _got_value(run, "total_tokens")
    if expect["tokens"] is not _SKIP and tokens != expect["tokens"]:
        fails.append(f"total_tokens {tokens} != {expect['tokens']}")
    cost = _got_value(run, "cost_usd")
    if expect["cost"] is not _SKIP and (cost is None or abs(float(cost) - expect["cost"]) > 0.001):
        fails.append(f"cost_usd {cost!r} != {expect['cost']}")
    spans = _got_value(run, "spans")
    if expect["spans"] is not _SKIP and isinstance(spans, list) \
            and len(spans) not in (expect["spans"], expect["spans"] - 1):
        fails.append(f"span count {len(spans)} != {expect['spans']}")
    gens = _got_value(run, "generations")
    if expect["gens"] is not _SKIP and isinstance(gens, list) and len(gens) != expect["gens"]:
        fails.append(f"generation count {len(gens)} != {expect['gens']}")
    if fails:
        print(f"  FAIL {label} ({expect['tid']}): " + "; ".join(fails))
    else:
        print(f"  PASS {label} ({expect['tid']}) stage={expect['stage']} "
              f"verdict={expect['verdict'] or '-'} tokens={expect['tokens']} cost=${expect['cost']:.4f}")
    return fails


def reattach_missing_scores(specs) -> None:
    """Re-create any scores still missing for the given runs (fresh write
    client, paced). Idempotent: score ids upsert, so re-attaching what
    already landed is harmless."""
    from mailroom_ui.langfuse_source import LangfuseSource

    client = make_langfuse_client()
    cfg_id = ensure_score_configs(client)
    src = LangfuseSource()
    v3 = client.api.scores_v3
    for spec in specs:
        tid = f"demo-{spec['slug']}"
        try:
            resp = v3.get_many_v3(trace_id=tid, limit=100,
                                  request_options={"timeout_in_seconds": 20})
            existing = {s.name for s in (resp.data or [])}
        except Exception:
            continue
        run = build_run(spec, datetime.now(timezone.utc))
        attach_scores(run, spec, cfg_id)
        for sc in run.scores:
            if sc.name not in existing:
                print(f"  re-attaching missing score {sc.name} on {tid}", file=sys.stderr)
                client.create_score(
                    trace_id=tid, name=sc.name, value=sc.value,
                    data_type=sc.data_type, comment=sc.comment,
                    config_id=sc.config_id, score_id=sc.id,
                )
                time.sleep(1.0)
    client.flush()
    client.shutdown()


def run_check(specs, check_api: bool, api_base: str) -> None:
    from mailroom_ui.langfuse_source import LangfuseSource

    src = LangfuseSource()
    expects = [expected_values(s) for s in specs]
    tids = [e["tid"] for e in expects]
    found_runs: set = set()
    failed_runs: set = set()

    # Score ingestion lands eventually (minutes under backlog and burst
    # drops); poll the stored-log verification until it stabilizes, re-
    # attaching any missing scores between attempts.
    pending = list(expects)
    for attempt in (1, 2, 3, 4):
        if not pending:
            break
        print(f"\nVERIFY against stored Langfuse logs — attempt {attempt} "
              f"({len(pending)} run(s))...")
        still_pending = []
        for expect in pending:
            run = src.get_run(expect["tid"])
            if run is None:
                print(f"  FAIL stored (missing trace {expect['tid']})")
                failed_runs.add(expect["tid"])
                still_pending.append(expect)
                continue
            found_runs.add(expect["tid"])
            if assert_run(expect, run, "stored"):
                failed_runs.add(expect["tid"])
                still_pending.append(expect)
        pending = still_pending
        if pending and attempt < 4:
            pending_specs = [s for s in specs
                             if f"demo-{s['slug']}" in {e["tid"] for e in pending}]
            reattach_missing_scores(pending_specs)
            time.sleep(60)

    fails = len(failed_runs)
    if check_api:
        import urllib.request

        print(f"\nVERIFY against live server display API ({api_base})...")
        for expect in expects:
            payload = None
            for attempt in (1, 2, 3):
                try:
                    with urllib.request.urlopen(f"{api_base}/api/traces/{expect['tid']}",
                                                timeout=20) as resp:
                        payload = json.loads(resp.read().decode())
                    break
                except Exception as err:
                    if attempt == 3:
                        print(f"  FAIL api (unreachable: {err})")
                        fails += 1
                    else:
                        time.sleep(10)
            if payload is None:
                continue
            if payload.get("error"):
                print(f"  FAIL api ({payload['error']})")
                fails += 1
                continue
            if assert_run(expect, payload, "api"):
                fails += 1

    print(f"\n{len(found_runs)}/{len(tids)} traces present in the stored logs; "
          f"{'ALL CHECKS PASSED' if fails == 0 else f'{fails} MISMATCH(ES)'}")
    return fails


def run_check_logs(logs_dir: str, specs) -> None:
    """Verify the display interpretation against the run logs physically
    saved by llm-mailroom's `scripts/sync_langfuse_logs.py`
    (data/langfuse_logs/<run>/<trace_id>.json). Fields the log cannot prove
    (missing scores, no observations detail) are reported as unverifiable
    rather than assumed."""
    from mailroom_ui.langfuse_source import LangfuseSource
    from mailroom_ui.trace_interpreter import interpret_trace

    src = LangfuseSource()
    configs = src.get_score_configs()
    expects = [expected_values(s) for s in specs]
    print(f"\nVERIFY against physically saved run logs ({logs_dir})...")
    fails = 0
    checked = 0
    for expect in expects:
        path = os.path.join(logs_dir, f"{expect['tid']}.json")
        if not os.path.exists(path):
            print(f"  SKIP {expect['tid']} — no saved log at {os.path.basename(path)}")
            continue
        with open(path, encoding="utf-8") as f:
            dump = json.load(f)
        obs = dump.get("observations_detail") or dump.get("observations") or []
        scores = dump.get("scores_detail") or dump.get("scores") or []
        e = dict(expect)
        if not obs:
            for key in ("spans", "gens", "tokens", "cost"):
                e[key] = _SKIP
        judge_names = {s.get("name") for s in scores}
        if "mailroom-pipeline-judge" not in judge_names:
            e["verdict"] = _SKIP
        if "mailroom-pipeline-quality" not in judge_names:
            e["quality"] = _SKIP
        if "classification_confidence" not in judge_names:
            e["conf_cls"] = _SKIP
        if "extraction_confidence" not in judge_names:
            e["conf_ext"] = _SKIP
        run = interpret_trace(dump, obs, scores, score_configs=configs)
        if assert_run(e, run, "log"):
            fails += 1
        else:
            checked += 1
    print(f"\n{checked}/{len(expects)} demo runs verified against saved logs; "
          f"{'ALL LOG CHECKS PASSED' if fails == 0 else f'{fails} MISMATCH(ES)'}")
    return fails


def main():
    parser = argparse.ArgumentParser(description="Seed demo traces into Langfuse (env demo).")
    parser.add_argument("--list-scenarios", action="store_true", help="list available demo scenarios")
    parser.add_argument("--scenario", help="seed a single scenario by slug")
    parser.add_argument("--count", type=int, default=len(SPECS), help="number of demo runs to seed")
    parser.add_argument("--env", default="demo", help="environment tag (default: demo)")
    parser.add_argument("--window-hours", type=float, default=3.0,
                        help="spread runs across this many hours back from now")
    parser.add_argument("--check", action="store_true",
                        help="verify seeded traces against the stored Langfuse logs")
    parser.add_argument("--check-api", action="store_true",
                        help="also verify against a running server's display API "
                             "(implies --check)")
    parser.add_argument("--api-base", default="http://127.0.0.1:8001",
                        help="base URL of the running The-Mailroom server")
    parser.add_argument("--check-logs",
                        help="verify against physically saved run logs "
                             "(dir from llm-mailroom scripts/sync_langfuse_logs.py)")
    parser.add_argument("--keep", action="store_true",
                        help="do not delete previously seeded demo traces first")
    args = parser.parse_args()

    load_dotenv()

    if args.list_scenarios:
        for spec in SPECS:
            flags = ", ".join(SCENARIO_FLAGS.get(spec["slug"], [])) or "-"
            stage = spec["trace_output"].get("stage", "(in flight)")
            print(f"{spec['slug']:24} {spec['filename']:48} {stage:12} {flags}")
        return

    specs = [dict(s) for s in SPECS]
    if args.scenario:
        specs = [s for s in specs if s["slug"] == args.scenario]
        if not specs:
            sys.exit(f"unknown scenario '{args.scenario}' (see --list-scenarios)")
    specs = specs[: args.count]
    for i, spec in enumerate(specs):
        spec["env"] = args.env
        spec["run"] = i + 1

    client = make_langfuse_client()
    judge_config_id = ensure_score_configs(client)
    keep = {f"demo-{spec['slug']}" for spec in specs}
    if not args.keep:
        cleanup_stale_traces(client, keep)
    start_base = datetime.now(timezone.utc) - timedelta(minutes=1)
    print(f"seeding {len(specs)} demo run(s) into Langfuse (env={args.env}) ...")
    runs = seed(client, specs, start_base, timedelta(hours=args.window_hours),
                judge_config_id)
    verified = len(runs)
    print(f"seeded + readback-verified: {verified}/{len(specs)} run(s)")
    for spec in specs:
        tid = f"demo-{spec['slug']}"
        host = (os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL") or "https://us.cloud.langfuse.com").rstrip("/")
        print(f"  {spec['slug']:24} {host}/trace/{tid}")
    client.shutdown()

    if args.check or args.check_api:
        time.sleep(15)
        sys.exit(0 if run_check(specs, args.check_api, args.api_base) == 0 else 1)
    if args.check_logs:
        sys.exit(0 if run_check_logs(args.check_logs, specs) == 0 else 1)


if __name__ == "__main__":
    main()
