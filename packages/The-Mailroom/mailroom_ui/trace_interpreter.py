"""Trace interpreter: Langfuse trace + observations + scores -> PipelineRun.

The mapping mirrors llm-mailroom's graph topology (see pipeline_schema.py).
The trace structure is: one `document-pipeline` CHAIN per document, verb-first
child observations typed to the Langfuse data model (AGENT / EVALUATOR /
RETRIEVER / SPAN), auto-traced LLM generations plus `pipeline-result` /
`answer-question` GENERATIONs, and scores (confidences, run metrics, judge
verdicts). v4 SDK payloads use `observationType` (camelCase) as well as
`type`.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional

from .models import Generation, NodeSpan, PipelineRun, Score, Stage
from .pipeline_schema import (
    NODE_ORDER,
    SPAN_STAGE_MAP,
    STAGE_PHASE,
    PipelineSchema,
    canonical_score_name,
    failure_class_from_text,
    langfuse_score_name,
    normalize_failure_class,
    observation_type_for,
)
from .reconsideration import collect_review_causes, format_causes

# Score names produced by observability/scores.py + Langfuse evaluators.
JUDGE_VERDICT_SCORES = ("mailroom-pipeline-judge",)
JUDGE_QUALITY_SCORES = ("mailroom-pipeline-quality",)

_OUTPUT_STAGE_MAP = {
    "archived": Stage.ARCHIVED,
    "failed": Stage.FAILED,
    "review": Stage.HUMAN_REVIEW,
    "processing": Stage.INTAKE,
    "classified": Stage.CLASSIFY,
    "extracting": Stage.EXTRACT,
    "reporting": Stage.COMPILE_REPORT,
    "inbox": Stage.INBOX,
}

_LIVE_STAGE_NAMES = {s.value for s in Stage}

DEFAULT_SCHEMA = PipelineSchema.load()


def parse_dt(value: Any) -> Optional[datetime]:
    """Parse to a tz-aware UTC datetime (V-6/V-7).

    Normalizes EVERY timestamp to UTC so downstream comparisons and sorts
    never mix naive and aware datetimes (which crashed the snapshot) and
    never relabel wall-clock time without converting (which shifted metric
    windows by the full UTC offset). Naive inputs are assumed UTC — Langfuse
    stores UTC.
    """
    from datetime import timezone as _tz

    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=_tz.utc)
        return value.astimezone(_tz.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_tz.utc)
    return dt.astimezone(_tz.utc)


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip() or None


# Producer doc_ids are uuid / slug tokens. Filenames with a dot (the fixture
# span input uses ``doc_id: filename``) must not be lifted as a catalog id.
_DOC_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _as_doc_id(value: Any) -> Optional[str]:
    text = _clean(value)
    if text and _DOC_ID_RE.match(text):
        return text
    return None


def _lift_doc_id(
    t_output: dict[str, Any],
    t_input: dict[str, Any],
    metadata: dict[str, Any],
    spans: list[NodeSpan],
) -> Optional[str]:
    for src in (t_output, t_input, metadata):
        found = _as_doc_id(src.get("doc_id"))
        if found:
            return found
    for span in reversed(spans):
        out = span.output if isinstance(span.output, dict) else {}
        found = _as_doc_id(out.get("doc_id"))
        if found:
            return found
    return None


def _pick(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return None


# Langfuse v4 returns camelCase at the trace/observation level; older SDK
# versions and the raw stored input/output payloads use snake_case. Both are
# accepted everywhere below.
def _both(d: dict[str, Any], snake: str, camel: str) -> Any:
    return _pick(d, snake, camel)


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except Exception:
            return value.model_dump()
    return value if isinstance(value, dict) else {}


def _usage_tokens(usage: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
    usage = _as_dict(usage)
    return (
        usage.get("total") or usage.get("total_tokens"),
        usage.get("input") or usage.get("prompt_tokens"),
        usage.get("output") or usage.get("completion_tokens"),
    )


def _cost_details(cost: Any) -> float:
    cost = _as_dict(cost)
    total = (
        cost.get("total")
        or cost.get("total_cost")
        or cost.get("totalPrice")
        or cost.get("totalCost")
    )
    if total is not None:
        return float(total)
    inp = (
        cost.get("input")
        or cost.get("input_cost")
        or cost.get("inputPrice")
        or 0
    )
    out = (
        cost.get("output")
        or cost.get("output_cost")
        or cost.get("outputPrice")
        or 0
    )
    try:
        return float(inp) + float(out)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _jsonish(value: Any) -> Any:
    """Parse a JSON object/array string; leave other values untouched."""
    if isinstance(value, str):
        s = value.strip()
        if s[:1] in "{[":
            try:
                return json.loads(s)
            except (TypeError, ValueError):
                return value
    return value


def _canonicalize_score_map(score_map: dict[str, Any]) -> dict[str, Any]:
    """Dual-write Langfuse 35-char aliases so metrics and inspector agree."""
    extra: dict[str, Any] = {}
    for name, value in list(score_map.items()):
        canon = canonical_score_name(name)
        wire = langfuse_score_name(name)
        if canon not in score_map and canon not in extra:
            extra[canon] = value
        if wire not in score_map and wire not in extra:
            extra[wire] = value
    score_map.update(extra)
    return score_map


def _payloads_for_subclass(
    t_output: dict[str, Any],
    spans: list[NodeSpan],
    generations: list[Generation],
) -> list[dict[str, Any]]:
    """Priority order for mining doc_subclass / contract_subtype.

    llm-mailroom ``_result_summary()`` still only writes stage/doc_type/
    confidences onto node spans, so curated I/O often omits subclass. Mine
    sorter output first, then classify-document generation JSON, then
    catalog/reporter payloads — and stay correct if upstream later adds
    ``doc_subclass`` to the span summary.
    """
    payloads: list[dict[str, Any]] = []
    sorter = _as_dict(t_output.get("sorter"))
    if sorter:
        payloads.append(sorter)
    payloads.append(t_output)

    classify_gens: list[dict[str, Any]] = []
    other_gens: list[dict[str, Any]] = []
    for gen in generations:
        parsed = _jsonish(gen.output)
        if not isinstance(parsed, dict):
            continue
        bucket = classify_gens if (gen.name or "") in (
            "classify-document", "classify", "retry_classify", "review_classify",
        ) else other_gens
        bucket.append(parsed)
        nested = _as_dict(parsed.get("sorter"))
        if nested:
            bucket.append(nested)
    payloads.extend(classify_gens)

    for span in spans:
        out = _as_dict(span.output)
        if not out:
            continue
        payloads.append(out)
        nested = _as_dict(out.get("sorter"))
        if nested:
            payloads.append(nested)
        extracted = _as_dict(out.get("extracted_data"))
        if extracted:
            payloads.append(extracted)
    payloads.extend(other_gens)
    return payloads


def _lift_subclass(
    t_output: dict[str, Any],
    spans: list[NodeSpan],
    generations: list[Generation],
) -> tuple[Optional[str], Optional[str]]:
    doc_subclass: Optional[str] = None
    contract_subtype: Optional[str] = None
    for payload in _payloads_for_subclass(t_output, spans, generations):
        if not doc_subclass:
            doc_subclass = _clean(payload.get("doc_subclass"))
        if not contract_subtype:
            contract_subtype = _clean(payload.get("contract_subtype"))
        if doc_subclass and contract_subtype:
            break
    # CUAD contract_subtype is the contract subclass when doc_subclass is empty.
    if not doc_subclass and contract_subtype:
        doc_subclass = contract_subtype
    return doc_subclass, contract_subtype


def _lift_ground_truth(
    t_input: dict[str, Any],
    t_output: dict[str, Any],
    metadata: dict[str, Any],
) -> tuple[Optional[str], Optional[str]]:
    blobs: list[dict[str, Any]] = []
    for src in (t_output, t_input, metadata):
        if not isinstance(src, dict):
            continue
        gt = src.get("ground_truth")
        if isinstance(gt, dict):
            blobs.append(gt)
        blobs.append(src)
    expected_hf: Optional[str] = None
    expected_subclass: Optional[str] = None
    for blob in blobs:
        if expected_hf is None:
            expected_hf = (
                _clean(blob.get("expected_hf_class"))
                or _clean(blob.get("expected_doc_class"))
                or _clean(blob.get("expected"))
            )
        if expected_subclass is None:
            expected_subclass = _clean(blob.get("expected_subclass"))
        if expected_hf and expected_subclass:
            break
    return expected_hf, expected_subclass


def _lift_intake(
    spans: list[NodeSpan],
    trace_output: Optional[dict] = None,
) -> dict[str, Any]:
    empty = {
        "intake_messy": None,
        "intake_changed": None,
        "intake_method": None,
        "intake_chars": None,
        # #111: the terminal manifest's ``intake`` block rides the trace
        # output and carries the BERT intake handoff (+ ``gate_outcome``)
        # the Observatory BERT lane panels read. Kept as-is (whitelisted
        # upstream in llm-mailroom bert_intake.py / _attach_gate_outcome);
        # None when the manifest predates the lane.
        "intake_bert": None,
    }
    intake_meta = _as_dict((trace_output or {}).get("intake"))
    bert = intake_meta.get("bert")
    if isinstance(bert, dict) and bert:
        empty["intake_bert"] = _as_dict(bert)
    for span in spans:
        if span.name != "normalize-intake":
            continue
        out = _as_dict(span.output)
        messy = out.get("messy")
        changed = out.get("changed")
        if changed is None:
            wraps = out.get("collapsed_blank_runs") or out.get("hyphen_unwraps")
            changed = bool(wraps) if wraps is not None else None
        chars = out.get("chars")
        if chars is None:
            chars = out.get("cleaned_chars")
        return {
            "intake_messy": bool(messy) if messy is not None else None,
            "intake_changed": bool(changed) if changed is not None else None,
            "intake_method": _clean(out.get("method")),
            "intake_chars": _int(chars),
            "intake_bert": empty["intake_bert"],
        }
    return empty


def derive_stage(
    output: dict[str, Any],
    spans: list[NodeSpan],
    *,
    schema: PipelineSchema = DEFAULT_SCHEMA,
) -> Stage:
    """Primary: trace output `stage`; fallback: last node span; else INBOX.

    The pipeline's generic in-flight marker ("processing") carries no node
    detail, so when it appears we refine with real span progress — otherwise
    a run sitting in the judge gate or arbiter displays as "intake" until it
    reaches a terminal stage.
    """
    raw = _clean(output.get("stage"))
    if not raw:
        # Docclass-eval traces (entity-repo runner): output is
        # {"sorter": {doc_type, confidence, ...}} with no pipeline stage —
        # they are classification runs; display them at the sorter station.
        sorter = _as_dict(output.get("sorter"))
        if _clean(sorter.get("doc_type")):
            return Stage.CLASSIFY
    else:
        mapped = _OUTPUT_STAGE_MAP.get(raw.lower(), None)
        if mapped is not None:
            if mapped is Stage.INTAKE and spans:
                for span in reversed(spans):
                    st = SPAN_STAGE_MAP.get(span.name)
                    if st is not None and st is not Stage.INTAKE:
                        return st
            return mapped
        if raw.lower() in _LIVE_STAGE_NAMES:
            return Stage(raw.lower())
    for span in reversed(spans):
        if span.name in SPAN_STAGE_MAP:
            return SPAN_STAGE_MAP[span.name]
    return Stage.INBOX


def build_routing_path(spans: list[NodeSpan]) -> list[str]:
    """Stable node sequence incl. retries (consecutive repeats).

    Repeats are idempotent: the retry variant is appended once per base
    stage, so the KANBAN-062 second-opinion pass (a third consecutive
    `classify-document` span from review_classify) cannot stack duplicate
    retry_classify entries into the displayed path.
    """
    staged: list[Stage] = []
    prev: Optional[Stage] = None
    for span in spans:
        if getattr(span, "is_root", False):
            continue
        stage = SPAN_STAGE_MAP.get(span.name)
        if stage is None:
            continue
        if prev is not None and stage == prev:
            retry = None
            if stage == Stage.CLASSIFY:
                retry = Stage.RETRY_CLASSIFY
            elif stage == Stage.EXTRACT:
                retry = Stage.RETRY_EXTRACT
            if retry is not None and retry not in staged:
                staged.append(retry)
            continue
        staged.append(stage)
        prev = stage
    staged.sort(key=lambda s: NODE_ORDER.index(s) if s in NODE_ORDER else 99)
    return [s.value for s in staged]


def _observation_name(obs: dict[str, Any]) -> Optional[str]:
    name = _clean(obs.get("name"))
    if name:
        return name
    return _clean(_both(obs, "type", "observationType"))


# Langfuse data-model types used as node observations (not LLM generations).
# llm-mailroom #29 types classify/extract as AGENT, judge-verify as
# EVALUATOR, intake OCR as RETRIEVER, and the document run as CHAIN.
_NODE_OBSERVATION_TYPES = frozenset({
    "SPAN",
    "EVENT",
    "AGENT",
    "EVALUATOR",
    "RETRIEVER",
    "CHAIN",
    "TOOL",
    "GUARDRAIL",
    "EMBEDDING",
})
_GENERATION_OBSERVATION_TYPES = frozenset({"GENERATION"})


def _declared_observation_type(obs: dict[str, Any]) -> str:
    raw = _both(obs, "type", "observationType")
    if raw is None:
        return ""
    return str(raw).strip().upper()


def _resolve_observation_type(obs: dict[str, Any]) -> str:
    """Prefer the SDK type; fall back to model/usage then the schema map."""
    declared = _declared_observation_type(obs)
    if declared:
        return declared
    if (
        _pick(obs, "model", "modelId") is not None
        or "usage" in obs
        or obs.get("totalTokens") is not None
        or obs.get("total_tokens") is not None
    ):
        return "GENERATION"
    name = _observation_name(obs) or ""
    return observation_type_for(name).upper()


def _is_root_observation(obs: dict[str, Any], *, name: str, obs_type: str) -> bool:
    flag = _both(obs, "is_root_observation", "isRootObservation")
    if flag is True or str(flag).strip().lower() in ("true", "1"):
        return True
    return obs_type == "CHAIN" and name == "document-pipeline"


def _span_error_message(obs: dict[str, Any]) -> Optional[str]:
    meta = _as_dict(obs.get("metadata"))
    return _clean(
        obs.get("error")
        or _as_dict(obs.get("output")).get("error")
        or meta.get("error")
    )


def _generation_from_obs(
    obs: dict[str, Any],
    *,
    start: Optional[datetime],
    end: Optional[datetime],
    latency: Optional[float],
    obs_type: str,
) -> Generation:
    usage_in, usage_out = _usage_tokens(obs.get("usage"))[1:]
    total = _usage_tokens(obs.get("usage"))[0]
    meta = _as_dict(obs.get("metadata"))
    return Generation(
        name=_observation_name(obs),
        agent=_clean(meta.get("agent")),
        model=_clean(_both(obs, "model", "modelId")),
        observation_type=obs_type or "GENERATION",
        latency=latency,
        input=obs.get("input"),
        output=obs.get("output"),
        usage_total_tokens=total or _int(obs.get("totalTokens")),
        usage_input_tokens=usage_in or _int(obs.get("inputTokens")),
        usage_output_tokens=usage_out or _int(obs.get("outputTokens")),
        cost_usd=_cost_details(_both(obs, "cost_details", "costDetails"))
        or _float(_pick(obs, "totalCost", "totalPrice", "total_cost")),
        prompt_version=_clean(
            _pick(meta, "langfuse_prompt", "prompt_id", "prompt_version")
        ),
        start_time=start,
        end_time=end,
    )


def _node_span_from_obs(
    obs: dict[str, Any],
    *,
    start: Optional[datetime],
    end: Optional[datetime],
    latency: Optional[float],
    is_error: bool,
    obs_type: str,
) -> NodeSpan:
    name = _observation_name(obs) or "observation"
    return NodeSpan(
        name=name,
        start_time=start,
        end_time=end,
        latency=latency,
        status="ERROR" if is_error else "SUCCESS",
        error_message=_span_error_message(obs),
        input=_as_dict(obs.get("input")) or None,
        output=_as_dict(obs.get("output")) or None,
        observation_type=obs_type or "SPAN",
        is_root=_is_root_observation(obs, name=name, obs_type=obs_type),
    )


# Pilot/attempt re-runs reuse the deterministic trace id, so a trace can carry
# several full runs of the same document. Observations are clustered by time
# gaps (> RUN_GAP_S between consecutive observations starts a new cluster) and
# only the latest cluster is displayed — one envelope per trace, latest run.
RUN_GAP_S = 60.0


def _latest_cluster(items: list[Any], *, get_start) -> list[Any]:
    """Keep only the trailing cluster of a chronological sequence."""
    if len(items) < 2:
        return items
    ordered = sorted(items, key=lambda i: get_start(i) or datetime.min)
    start_times = [get_start(i) for i in ordered]
    gap_at: Optional[int] = None
    prev: Optional[datetime] = None
    for idx, t in enumerate(start_times):
        if t is not None and prev is not None:
            try:
                if (t - prev).total_seconds() > RUN_GAP_S:
                    gap_at = idx
            except TypeError:
                pass
        if t is not None:
            prev = t
    if gap_at is None:
        return items
    return ordered[gap_at:]


def _resolve_failure_class(
    t_output: dict[str, Any],
    metadata: dict[str, Any],
    score_map: dict[str, Any],
) -> Optional[str]:
    """llm-mailroom PR #53: abort class on output, metadata, or tagged error."""
    for raw in (
        t_output.get("failure_class"),
        metadata.get("failure_class"),
        score_map.get("failure_class"),
    ):
        found = normalize_failure_class(_clean(raw) if not isinstance(raw, (int, float)) else str(raw))
        if found:
            return found
    return (
        failure_class_from_text(_clean(t_output.get("error_message")))
        or failure_class_from_text(_clean(t_output.get("escalation_reason")))
    )


def interpret_trace(
    trace: dict[str, Any],
    observations: Optional[list[dict[str, Any]]] = None,
    scores: Optional[list[dict[str, Any]]] = None,
    *,
    schema: PipelineSchema = DEFAULT_SCHEMA,
    score_configs: Optional[dict[str, dict[str, Any]]] = None,
) -> PipelineRun:
    """Interpret one Langfuse trace into a display-ready PipelineRun.

    `observations`/`scores` are optional: when omitted the run is a "light"
    interpretation (list-level data only) with no span/generation detail.
    `score_configs` (name -> {"data_type", "categories": [{"value", "label"}]})
    lets CATEGORICAL scores (e.g. judge verdicts) resolve their numeric value
    back to the label the pipeline assigned.
    """
    trace = _as_dict(trace)
    observations = observations or []
    scores = scores or []
    embedded_obs = trace.get("observations")
    if not observations and isinstance(embedded_obs, list):
        observations = [_as_dict(o) for o in embedded_obs]
    embedded_scores = trace.get("scores")
    if not scores and isinstance(embedded_scores, list):
        scores = [_as_dict(s) for s in embedded_scores]
    t_input = _as_dict(trace.get("input"))
    t_output = _as_dict(trace.get("output"))
    metadata = _as_dict(trace.get("metadata"))
    tags = [str(t) for t in (trace.get("tags") or []) if t]
    environment = _clean(trace.get("environment"))

    created = parse_dt(_pick(trace, "timestamp", "created_at", "createdAt"))
    latency = trace.get("latency")
    if latency is not None:
        try:
            latency = float(latency)
        except (TypeError, ValueError):
            latency = None

    spans: list[NodeSpan] = []
    generations: list[Generation] = []
    for raw in observations:
        obs = _as_dict(raw)
        obs_type = _resolve_observation_type(obs)
        start = parse_dt(_both(obs, "start_time", "startTime"))
        end = parse_dt(_both(obs, "end_time", "endTime"))
        obs_latency = obs.get("latency")
        try:
            obs_latency = float(obs_latency) if obs_latency is not None else None
        except (TypeError, ValueError):
            obs_latency = None
        is_error = str(obs.get("level") or "").upper() in ("ERROR", "WARNING") or bool(
            obs.get("error") or _as_dict(obs.get("output")).get("error")
        )
        gen_kwargs = dict(start=start, end=end, latency=obs_latency, obs_type=obs_type)
        if obs_type in _GENERATION_OBSERVATION_TYPES:
            generations.append(_generation_from_obs(obs, **gen_kwargs))
        elif obs_type in _NODE_OBSERVATION_TYPES:
            spans.append(
                _node_span_from_obs(
                    obs, start=start, end=end, latency=obs_latency,
                    is_error=is_error, obs_type=obs_type,
                )
            )
        else:
            # `OBSERVATION` type or no type at all: the pipeline's auto-traced
            # generations arrive as OBSERVATION + model; classify by
            # model/usage presence. v4 SPANs (zeroed `usage`) never get here.
            if (
                _pick(obs, "model", "modelId") is not None
                or "usage" in obs
                or obs.get("totalTokens") is not None
            ):
                generations.append(_generation_from_obs(obs, **gen_kwargs))
            else:
                spans.append(
                    _node_span_from_obs(
                        obs, start=start, end=end, latency=obs_latency,
                        is_error=is_error, obs_type=obs_type or "SPAN",
                    )
                )

    spans.sort(key=lambda s: s.start_time or datetime.min)
    generations.sort(key=lambda g: g.start_time or datetime.min)
    # A trace may carry several runs (deterministic trace ids are reused by
    # pilot/attempt re-runs). Keep only the latest run's observations.
    spans = _latest_cluster(spans, get_start=lambda s: s.start_time)
    generations = _latest_cluster(generations, get_start=lambda g: g.start_time)

    score_map: dict[str, Any] = {}
    score_stamps: dict[str, datetime | None] = {}
    score_objects: list[Score] = []
    for raw in scores:
        s = _as_dict(raw)
        name = _clean(s.get("name"))
        if not name:
            continue
        stamp = parse_dt(_pick(s, "timestamp", "created_at", "createdAt"))
        value = s.get("value")
        data_type = _clean(_both(s, "data_type", "dataType"))
        score_objects.append(
            Score(
                name=name,
                value=value,
                data_type=data_type,
                comment=_clean(s.get("comment")),
                observation_id=_clean(_both(s, "observation_id", "observationId")),
            )
        )
        # CATEGORICAL scores (judge verdicts) are stored as a numeric index
        # into their score config's categories; resolve back to the label.
        cfg = (score_configs or {}).get(name)
        if cfg and data_type == "CATEGORICAL" and isinstance(value, (int, float)):
            for cat in cfg.get("categories") or []:
                if float(cat.get("value")) == float(value):
                    value = cat.get("label")
                    break
        if name in score_map:
            previous = score_stamps.get(name)
            # Langfuse returns scores newest-first. Timestamps make this
            # explicit; timestamp-less duplicate fixtures retain first-wins.
            if stamp is None or (previous is not None and stamp <= previous):
                continue
        score_map[name] = value
        score_stamps[name] = stamp
    score_map = _canonicalize_score_map(score_map)

    scored_duration = _float(score_map.get("run_duration_seconds"))
    if scored_duration is not None:
        # Deterministic trace IDs are reused across pilot runs. The trace-level
        # latency can therefore span multiple attempts and later evaluator
        # updates; this score is the end-to-end duration of the latest run.
        latency = scored_duration

    stage = derive_stage(t_output, spans, schema=schema)
    routing_path = build_routing_path(spans)

    sorter_out = _as_dict(t_output.get("sorter"))
    doc_type = (_clean(sorter_out.get("doc_type")) or _clean(t_output.get("doc_type"))
                or _clean(t_input.get("doc_type")))
    doc_subclass, contract_subtype = _lift_subclass(t_output, spans, generations)
    expected_hf_class, expected_subclass = _lift_ground_truth(t_input, t_output, metadata)
    intake = _lift_intake(spans, t_output)
    attempt = _pick(t_input, "attempt", "run_attempt")
    if attempt is None:
        attempt = metadata.get("attempt")
    filename = _clean(t_input.get("filename")) or _clean(t_input.get("file"))
    doc_id = _lift_doc_id(t_output, t_input, metadata, spans)
    matter_id = _clean(t_input.get("matter_id"))
    session_id = _clean(_both(trace, "session_id", "sessionId"))
    if matter_id is None:
        matter_id = session_id
    user_id = (
        _clean(_both(trace, "user_id", "userId"))
        or _clean(metadata.get("user_id"))
        or _clean(metadata.get("userId"))
    )
    release = (
        _clean(_pick(trace, "release", "version"))
        or _clean(metadata.get("release"))
        or _clean(metadata.get("langfuse_release"))
    )

    verdict: Optional[str] = None
    quality: Optional[float] = None
    for name in JUDGE_VERDICT_SCORES:
        v = score_map.get(name)
        if v is not None:
            verdict = _clean(v)
            break
    for name in JUDGE_QUALITY_SCORES:
        v = score_map.get(name)
        if v is not None:
            try:
                quality = float(v)
            except (TypeError, ValueError):
                quality = None
            break

    scored_tokens = _int(score_map.get("total_tokens"))
    generated_tokens = sum(g.usage_total_tokens or 0 for g in generations)
    total_tokens = (
        scored_tokens
        if scored_tokens is not None
        and (score_stamps.get("total_tokens") is not None or generated_tokens == 0)
        else generated_tokens
    )
    scored_cost = _float(score_map.get("estimated_cost_usd"))
    generated_cost = sum(g.cost_usd or 0 for g in generations)
    cost = (
        scored_cost
        if scored_cost is not None
        and (score_stamps.get("estimated_cost_usd") is not None or generated_cost == 0)
        else generated_cost
    )
    scored_calls = _int(score_map.get("llm_call_count"))
    llm_call_count = (
        scored_calls
        if scored_calls is not None
        and (score_stamps.get("llm_call_count") is not None or not generations)
        else len(generations)
    )

    run = PipelineRun(
        trace_id=str(trace.get("id") or ""),
        name=_clean(trace.get("name")) or "document-pipeline",
        filename=filename,
        doc_id=doc_id,
        matter_id=matter_id,
        session_id=session_id,
        environment=environment,
        user_id=user_id,
        release=release,
        tags=tags,
        attempt=int(attempt) if attempt is not None else None,
        created_at=created,
        updated_at=parse_dt(_both(trace, "updated_at", "updatedAt")) or created,
        latency=latency,
        stage=stage,
        phase=STAGE_PHASE.get(stage, STAGE_PHASE[Stage.UNKNOWN]),
        doc_type=doc_type,
        doc_subclass=doc_subclass,
        contract_subtype=contract_subtype,
        expected_hf_class=expected_hf_class,
        expected_subclass=expected_subclass,
        intake_messy=intake["intake_messy"],
        intake_changed=intake["intake_changed"],
        intake_method=intake["intake_method"],
        intake_chars=intake["intake_chars"],
        intake_bert=intake["intake_bert"],
        classification_confidence=_float(score_map.get("classification_confidence"))
        or _float(t_output.get("classification_confidence"))
        or _float(sorter_out.get("confidence")),
        extraction_confidence=_float(score_map.get("extraction_confidence"))
        or _float(t_output.get("extraction_confidence")),
        review_decision=_clean(t_output.get("review_decision")),
        escalation_reason=_clean(t_output.get("escalation_reason")),
        review_causes=[],
        error_message=_clean(t_output.get("error_message")),
        run_aborted=bool(t_output.get("run_aborted") or score_map.get("run_aborted")),
        failure_class=_resolve_failure_class(t_output, metadata, score_map),
        spans=spans,
        generations=generations,
        scores=score_map,
        score_objects=score_objects,
        routing_path=routing_path,
        verdict=verdict,
        quality=quality,
        llm_call_count=llm_call_count,
        total_tokens=total_tokens,
        cost_usd=cost,
    )
    run.review_causes = collect_review_causes(
        doc_type=run.doc_type,
        doc_subclass=run.doc_subclass,
        contract_subtype=run.contract_subtype,
        expected_hf_class=run.expected_hf_class,
        expected_subclass=run.expected_subclass,
        scores=score_map,
        verdict=run.verdict,
    )
    if not run.escalation_reason and run.review_causes:
        run.escalation_reason = format_causes(run.review_causes)
    return run


def _float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
