"""Fake Langfuse client — deterministic in-memory data, no network."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from mailroom_ui.pipeline_schema import observation_type_for


def _node_type(name: str) -> str:
    return observation_type_for(name).upper()


@dataclass
class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def model_dump(self, mode="python"):
        out = {}
        for k, v in self.__dict__.items():
            if isinstance(v, datetime):
                v = v.isoformat()
            out[k] = v
        return out


def make_trace(
    trace_id: str,
    *,
    filename: str = "sample.txt",
    matter_id: str = "MATTER-001",
    environment: str = "pilot",
    tags: list[str] | None = None,
    stage: str = "archived",
    doc_type: str = "contract",
    class_conf: float = 0.98,
    extract_conf: float = 0.91,
    span_names: list[str] | None = None,
    session_id: str | None = None,
    attempt: int = 0,
    verdict: str | None = "CORRECT",
    quality: float | None = 0.9,
    latency: float = 12.5,
    base_time: datetime | None = None,
    error_spans: bool = False,
    output_extra: dict | None = None,
    extra_observations: list | None = None,
    user_id: str | None = None,
    release: str | None = None,
    include_root: bool = False,
    extra_scores: dict | None = None,
    extra_metadata: dict | None = None,
    extra_input: dict | None = None,
    intake_output: dict | None = None,
    classify_generation_output: object | None = None,
    doc_subclass: str | None = None,
    contract_subtype: str | None = None,
    ml_triage_output: dict | None = None,
) -> dict:
    base_time = base_time or datetime(2026, 1, 1, 12, 0, 0)
    span_names = list(span_names or [
        "intake-document",
        "classify-document",
        "extract-fields",
        "compile-report",
        "write-catalog",
        "archive-document",
    ])
    if intake_output and "normalize-intake" not in span_names:
        if "intake-document" in span_names:
            span_names.insert(span_names.index("intake-document") + 1, "normalize-intake")
        else:
            span_names.insert(0, "normalize-intake")
    if ml_triage_output is not None and "intake-ml-triage" not in span_names:
        # llm-mailroom #85 M6a: ModernBERT triage SPAN inside intake_node.
        at = span_names.index("intake-document") + 1 if "intake-document" in span_names else 0
        span_names.insert(at, "intake-ml-triage")
    obs = []
    if include_root:
        obs.append(
            Obj(
                id=f"chain-{trace_id}",
                type="CHAIN",
                name="document-pipeline",
                isRootObservation=True,
                start_time=base_time,
                end_time=base_time + timedelta(seconds=80),
                latency=80.0,
                level="DEFAULT",
                input={"filename": filename},
                output={"stage": stage},
            )
        )
    for i, name in enumerate(span_names):
        span_out = {"stage": "ok", "error": "boom"} if error_spans else {"stage": "ok"}
        if name == "normalize-intake" and intake_output:
            span_out = dict(intake_output)
        elif name == "intake-ml-triage" and ml_triage_output is not None:
            span_out = dict(ml_triage_output)
        elif name == "classify-document" and (doc_subclass or contract_subtype):
            span_out = {
                **span_out,
                "doc_type": doc_type,
                "doc_subclass": doc_subclass,
                "contract_subtype": contract_subtype,
            }
        obs.append(
            Obj(
                id=f"span-{trace_id}-{i}",
                type=_node_type(name),
                name=name,
                start_time=base_time + timedelta(seconds=10 * i),
                end_time=base_time + timedelta(seconds=10 * i + 8),
                latency=8.0,
                level="ERROR" if error_spans else "DEFAULT",
                input={"doc_id": filename},
                output=span_out,
            )
        )
    classify_out = classify_generation_output
    if classify_out is None and (doc_subclass or contract_subtype):
        classify_out = {
            "doc_type": doc_type,
            "doc_subclass": doc_subclass,
            "contract_subtype": contract_subtype,
        }
    if classify_out is None:
        classify_out = "contract"
    obs.append(
        Obj(
            id=f"gen-{trace_id}-0",
            type="GENERATION",
            name="classify-document",
            model="qwen/qwen3.7-flash",
            start_time=base_time + timedelta(seconds=11),
            end_time=base_time + timedelta(seconds=20),
            latency=9.0,
            input={"messages": "..."},
            output=classify_out,
            usage={"total": 1200, "input": 1000, "output": 200},
            cost_details={"total": 0.00015},
            level="DEFAULT",
        )
    )
    obs.append(
        Obj(
            id=f"gen-{trace_id}-1",
            type="GENERATION",
            name="extract-fields",
            model="qwen/qwen3.7-flash",
            start_time=base_time + timedelta(seconds=21),
            end_time=base_time + timedelta(seconds=40),
            latency=19.0,
            input={"messages": "..."},
            output='{"parties": ["Acme Corp"]}',
            usage={"total": 3400, "input": 3000, "output": 400},
            cost_details={"total": 0.0004},
            level="DEFAULT",
        )
    )
    scores = [
        Obj(name="classification_confidence", value=class_conf, data_type="NUMERIC"),
        Obj(name="extraction_confidence", value=extract_conf, data_type="NUMERIC"),
        Obj(name="stage_completed", value=stage == "archived", data_type="BOOLEAN"),
        Obj(name="estimated_cost_usd", value=0.00055, data_type="NUMERIC"),
        Obj(name="total_tokens", value=4600, data_type="NUMERIC"),
    ]
    if verdict:
        scores.append(Obj(name="mailroom-pipeline-judge", value=verdict, data_type="CATEGORICAL"))
    if quality is not None:
        scores.append(Obj(name="mailroom-pipeline-quality", value=quality, data_type="NUMERIC"))
    if extra_scores:
        for name, value in extra_scores.items():
            scores.append(Obj(name=name, value=value, data_type="NUMERIC"))
    output = {
        "stage": stage,
        "doc_type": doc_type,
        "classification_confidence": class_conf,
        "extraction_confidence": extract_conf,
    }
    if doc_subclass:
        output["doc_subclass"] = doc_subclass
    if contract_subtype:
        output["contract_subtype"] = contract_subtype
        output.setdefault("sorter", {})
        if isinstance(output.get("sorter"), dict):
            output["sorter"] = {
                **output["sorter"],
                "doc_type": doc_type,
                "doc_subclass": doc_subclass,
                "contract_subtype": contract_subtype,
                "confidence": class_conf,
            }
    if output_extra:
        output.update(output_extra)
    metadata = {"pipeline": "mailroom", "attempt": attempt}
    if extra_metadata:
        metadata.update(extra_metadata)
    inp = {"filename": filename, "matter_id": matter_id, "attempt": attempt}
    if extra_input:
        inp.update(extra_input)
    trace = {
        "id": trace_id,
        "name": "document-pipeline",
        "timestamp": base_time,
        "updated_at": base_time + timedelta(seconds=80),
        "latency": latency,
        "session_id": session_id or matter_id,
        "environment": environment,
        "user_id": user_id,
        "release": release,
        "tags": tags or ["mailroom", environment],
        "metadata": metadata,
        "input": inp,
        "output": output,
        "observations": obs,
        "scores": scores,
    }
    if extra_observations:
        trace["observations"] = [*obs, *extra_observations]
    return trace


def make_trace_v4(
    trace_id: str,
    *,
    filename: str = "v4-sample.pdf",
    matter_id: str = "MATTER-V4",
    stage: str = "archived",
    doc_type: str = "contract",
    extra_scores: dict | None = None,
    extra_metadata: dict | None = None,
    extra_input: dict | None = None,
    intake_output: dict | None = None,
    classify_generation_output: object | None = None,
    doc_subclass: str | None = None,
    contract_subtype: str | None = None,
    output_extra: dict | None = None,
    ml_triage_output: dict | None = None,
) -> dict:
    """A trace shaped like the Langfuse v4 SDK (camelCase observations).

    v4 returns camelCase at the observation level (`startTime`, `modelId`,
    `totalTokens`, `totalCost`, `observationType`); trace-level fields stay
    snake_case in the API responses. The interpreter must accept both shapes.
    Observation types follow llm-mailroom NODE_OBSERVATION_TYPES (AGENT /
    EVALUATOR / RETRIEVER / CHAIN), not a blanket SPAN.
    """
    base_time = datetime(2026, 3, 3, 9, 0, 0)
    span_names = ["intake-document", "classify-document", "extract-fields", "archive-document"]
    if intake_output:
        span_names.insert(1, "normalize-intake")
    if ml_triage_output is not None:
        span_names.insert(1, "intake-ml-triage")
    obs = [
        Obj(
            id=f"v4-chain-{trace_id}",
            observationType="CHAIN",
            name="document-pipeline",
            isRootObservation=True,
            startTime=base_time,
            endTime=base_time + timedelta(seconds=80),
            latency=80.0,
            level="DEFAULT",
        )
    ]
    for i, name in enumerate(span_names):
        span_out = {"stage": "ok"}
        if name == "normalize-intake" and intake_output:
            span_out = dict(intake_output)
        elif name == "intake-ml-triage" and ml_triage_output is not None:
            span_out = dict(ml_triage_output)
        elif name == "classify-document" and (doc_subclass or contract_subtype):
            span_out = {
                "stage": "ok",
                "doc_type": doc_type,
                "doc_subclass": doc_subclass,
                "contract_subtype": contract_subtype,
            }
        obs.append(
            Obj(
                id=f"v4-span-{trace_id}-{i}",
                observationType=_node_type(name),
                name=name,
                startTime=base_time + timedelta(seconds=10 * i),
                endTime=base_time + timedelta(seconds=10 * i + 8),
                latency=8.0,
                level="DEFAULT",
                output=span_out,
            )
        )
    classify_out = classify_generation_output
    if classify_out is None and (doc_subclass or contract_subtype):
        classify_out = {
            "doc_type": doc_type,
            "doc_subclass": doc_subclass,
            "contract_subtype": contract_subtype,
        }
    obs.append(
        Obj(
            id=f"v4-gen-{trace_id}-0",
            observationType="GENERATION",
            name="classify-document",
            modelId="deepseek/deepseek-v4-flash",
            startTime=base_time + timedelta(seconds=11),
            endTime=base_time + timedelta(seconds=20),
            latency=9.0,
            usage={"total": 1200, "input": 1000, "output": 200},
            totalTokens=1200,
            inputTokens=1000,
            outputTokens=200,
            totalCost=0.00015,
            level="DEFAULT",
            output=classify_out if classify_out is not None else "contract",
        )
    )
    output = {
        "stage": stage,
        "doc_type": doc_type,
        "classification_confidence": 0.97,
        "extraction_confidence": 0.88,
    }
    if doc_subclass:
        output["doc_subclass"] = doc_subclass
    if contract_subtype:
        output["contract_subtype"] = contract_subtype
        output["sorter"] = {
            "doc_type": doc_type,
            "doc_subclass": doc_subclass,
            "contract_subtype": contract_subtype,
            "confidence": 0.97,
        }
    scores = []
    if extra_scores:
        for name, value in extra_scores.items():
            scores.append(Obj(name=name, value=value, data_type="NUMERIC"))
    metadata = {"pipeline": "mailroom", "attempt": 0}
    if extra_metadata:
        metadata.update(extra_metadata)
    inp = {"filename": filename, "matter_id": matter_id, "attempt": 0}
    if extra_input:
        inp.update(extra_input)
    if output_extra:
        output.update(output_extra)
    return {
        "id": trace_id,
        "name": "document-pipeline",
        "timestamp": base_time,
        "updated_at": base_time + timedelta(seconds=80),
        "latency": 12.5,
        "session_id": matter_id,
        "environment": "pilot",
        "userId": "pilot-operator",
        "release": "mailroom@test",
        "tags": ["mailroom", "pilot"],
        "metadata": metadata,
        "input": inp,
        "output": output,
        "observations": obs,
        "scores": scores,
    }


@dataclass
class FakeList:
    data: list = field(default_factory=list)


class FakeTraceApi:
    def __init__(self, traces: list[dict]):
        self.traces = traces
        self.calls: list[dict] = []

    def list(self, **kw):
        self.calls.append(kw)
        out = self.traces
        if kw.get("name"):
            out = [t for t in out if t.get("name") == kw["name"]]
        if kw.get("tags"):
            tags = set(kw["tags"].split(","))
            out = [t for t in out if tags.issubset(set(t.get("tags") or []))]
        return FakeList(data=out)

    def get(self, trace_id: str, **kw):  # kw: request_options (real SDK contract)
        for t in self.traces:
            if t["id"] == trace_id:
                return Obj(**t)
        return None


class FakeObservationsApi:
    def __init__(self, traces: list[dict]):
        self.traces = traces

    def get_many(self, trace_id: str, **kw):
        for t in self.traces:
            if t["id"] == trace_id:
                return FakeList(data=t.get("observations", []))
        return FakeList(data=[])


class FakeScoresApi:
    def __init__(self, traces: list[dict]):
        self.traces = traces

    def get_many(self, trace_id: str, **kw):
        for t in self.traces:
            if t["id"] == trace_id:
                return FakeList(data=t.get("scores", []))
        return FakeList(data=[])


class FakeScoresV3Api:
    """v3 scores endpoint (label-resolved CATEGORICAL values, trace filter)."""

    def __init__(self, traces: list[dict]):
        self.traces = traces

    def get_many_v3(self, trace_id: str, **kw):
        for t in self.traces:
            if t["id"] == trace_id:
                return FakeList(data=t.get("scores", []))
        return FakeList(data=[])


class FakeSessionsApi:
    def __init__(self, traces: list[dict]):
        self.traces = traces

    def list(self, limit=100):
        seen = {}
        for t in self.traces:
            sid = t.get("session_id") or "DEFAULT"
            seen.setdefault(sid, {"id": sid, "name": sid})
            seen[sid]["created_at"] = t["timestamp"]
            seen[sid]["updated_at"] = t["updated_at"]
        return FakeList(data=list(seen.values()))

    def get(self, session_id: str, limit=100):
        return FakeList(data=[t for t in self.traces if (t.get("session_id") or "DEFAULT") == session_id])


class FakeClient:
    def __init__(self, traces: list[dict] | None = None):
        # `traces or []` would replace a caller-owned EMPTY list (falsy) with
        # a new one, so a later append never showed up on the API.
        self.traces = traces if traces is not None else []
        self.api = Obj(
            trace=FakeTraceApi(self.traces),
            observations=FakeObservationsApi(self.traces),
            scores=FakeScoresApi(self.traces),
            scores_v3=FakeScoresV3Api(self.traces),
            sessions=FakeSessionsApi(self.traces),
        )
