"""Fake Phoenix data — OpenTelemetry/OpenInference-shaped spans, no network.

Mirrors what `arize-phoenix-client`'s `client.spans.get_spans` returns
(dict spans with context/parent_id/span_kind/status_code/attributes) plus
`get_span_annotations`. Used by tests AND as the shape reference for the
PhoenixSource mapping contract.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def make_phoenix_span(
    name: str,
    trace_id: str,
    span_id: str,
    *,
    parent_id: str | None = None,
    span_kind: str = "CHAIN",
    status_code: str = "OK",
    start_time: datetime | None = None,
    duration_s: float = 1.5,
    attributes: dict | None = None,
    events: list[dict] | None = None,
) -> dict:
    start_time = start_time or datetime(2026, 1, 1, 12, 0, 0)
    start_time = _utc(start_time)
    end_time = start_time + timedelta(seconds=duration_s)
    return {
        "name": name,
        "context": {"trace_id": trace_id, "span_id": span_id},
        "parent_id": parent_id,
        "span_kind": span_kind,
        "status_code": status_code,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "attributes": attributes or {},
        "events": events or [],
    }


def _io(value: dict) -> str:
    return json.dumps(value)


def make_phoenix_trace(
    trace_id: str,
    *,
    filename: str = "sample.txt",
    matter_id: str = "MATTER-001",
    session_id: str | None = None,
    tags: list[str] | None = None,
    environment: str | None = "pilot",
    stage: str = "archived",
    doc_type: str = "contract",
    class_conf: float = 0.97,
    extract_conf: float = 0.9,
    span_names: list[str] | None = None,
    model: str = "qwen2.5:7b",
    total_tokens: int = 1200,
    prompt_tokens: int = 900,
    completion_tokens: int = 300,
    cost_total: float = 0.0021,
    verdict: str | None = "CORRECT",
    quality: float | None = 0.88,
    base_time: datetime | None = None,
    error_span: bool = False,
) -> list[dict]:
    """A root 'document-pipeline' chain span + node/LLM children (Phoenix shape)."""
    base_time = base_time or datetime(2026, 1, 1, 12, 0, 0)
    session_id = session_id or matter_id
    span_names = span_names or [
        "intake-document",
        "classify-document",
        "extract-fields",
        "compile-report",
        "write-catalog",
        "archive-document",
    ]
    root_attrs = {
        "openinference.span.kind": "CHAIN",
        "input.value": _io({"filename": filename, "matter_id": matter_id, "attempt": 1}),
        "output.value": _io({
            "stage": stage,
            "doc_type": doc_type,
            "classification_confidence": class_conf,
            "extraction_confidence": extract_conf,
            **({"error_message": "extraction failed: bad JSON"} if error_span else {}),
        }),
        "session.id": session_id,
        "mailroom.tags": ",".join(tags or ["mailroom", "pilot"]),
    }
    if environment:
        root_attrs["mailroom.environment"] = environment
    spans = [
        make_phoenix_span(
            "document-pipeline", trace_id, f"{trace_id}-root",
            parent_id=None, span_kind="CHAIN",
            start_time=base_time, duration_s=12.5, attributes=root_attrs,
        )
    ]
    prev_end = base_time
    for i, name in enumerate(span_names):
        start = prev_end + timedelta(seconds=1)
        attrs = {
            "openinference.span.kind": "LLM" if name.endswith("(llm)") else "CHAIN",
            "input.value": _io({"node": name}),
            "output.value": _io({"ok": not error_span and i == len(span_names) - 1}),
        }
        kind = "LLM"
        if error_span:
            spans.append(
                make_phoenix_span(
                    name.replace(" (llm)", ""), trace_id, f"{trace_id}-s{i}",
                    parent_id=f"{trace_id}-root", span_kind="CHAIN",
                    status_code="ERROR", start_time=start, duration_s=0.4,
                    attributes=attrs,
                    events=[{
                        "name": "exception",
                        "attributes": {"exception.message": "extraction failed: bad JSON"},
                        "time_unix_nano": 0,
                    }],
                )
            )
            break
        if i == 1:  # one LLM call mid-trace so tokens/cost/model surface
            attrs.update({
                "llm.model_name": model,
                "llm.token_count.total": total_tokens,
                "llm.token_count.prompt": prompt_tokens,
                "llm.token_count.completion": completion_tokens,
                "llm.cost.total": cost_total,
                "input.value": _io({"prompt": "classify this document"}),
                "output.value": _io({"doc_type": doc_type}),
            })
        else:
            kind = "CHAIN"
            attrs["openinference.span.kind"] = "CHAIN"
        spans.append(
            make_phoenix_span(
                name.replace(" (llm)", ""), trace_id, f"{trace_id}-s{i}",
                parent_id=f"{trace_id}-root", span_kind=kind,
                start_time=start, duration_s=1.2, attributes=attrs,
            )
        )
        prev_end = start + timedelta(seconds=1.2)
    annotations = []
    if verdict is not None:
        annotations.append({
            "span_id": f"{trace_id}-root",
            "name": "mailroom-pipeline-judge",
            "label": verdict,
            "annotator_kind": "LLM",
        })
    if quality is not None:
        annotations.append({
            "span_id": f"{trace_id}-root",
            "name": "mailroom-pipeline-quality",
            "score": quality,
            "annotator_kind": "LLM",
        })
    for a in annotations:
        spans[-1].setdefault("_annotations", []).append(a)
    return spans


def make_reloaded_trace(
    trace_id: str,
    *,
    doc_id: str = "doc-0001",
    filename: str = "lease.pdf",
    run_id: str | None = "eval-20261009",
    status: str = "archived",
    doc_type: str | None = "contract",
    nodes: list[str] | None = None,
    base_time: datetime | None = None,
) -> list[dict]:
    """mailroom-reloaded shape: ``mailroom.document`` root + ``mailroom.node.*``
    children, no ``input.value`` / ``output.value`` on the root."""
    base_time = base_time or datetime(2026, 10, 9, 12, 0, 0)
    nodes = nodes or [
        "ingest", "bert_primary", "sort", "extract", "report_catalog_archive",
    ]
    root_attrs = {
        "openinference.span.kind": "CHAIN",
        "mailroom.doc_id": doc_id,
        "mailroom.status": status,
    }
    if filename:
        root_attrs["mailroom.filename"] = filename
    if run_id:
        root_attrs["mailroom.run_id"] = run_id
    if doc_type:
        root_attrs["mailroom.doc_type"] = doc_type
    spans = [
        make_phoenix_span(
            "mailroom.document", trace_id, f"{trace_id}-root",
            parent_id=None, start_time=base_time, duration_s=20.0,
            attributes=root_attrs,
        )
    ]
    for i, node in enumerate(nodes):
        spans.append(
            make_phoenix_span(
                f"mailroom.node.{node}", trace_id, f"{trace_id}-n{i}",
                parent_id=f"{trace_id}-root",
                start_time=base_time + timedelta(seconds=1 + 2 * i),
                duration_s=1.5,
                attributes={"mailroom.doc_id": doc_id},
            )
        )
    return spans


class FakePhoenixSpans:
    """`client.spans` stand-in: get_spans + get_span_annotations."""

    def __init__(self, store: list[dict]) -> None:
        self.store = store

    def get_spans(self, *, project_identifier: str = "default", **kw):
        spans = [s for s in self.store if s["context"]["trace_id"]]
        # Honor trace_ids / start_time filters loosely (tests use small sets).
        trace_ids = kw.get("trace_ids")
        if trace_ids:
            spans = [s for s in spans if s["context"]["trace_id"] in set(trace_ids)]
        start_time = kw.get("start_time")
        if start_time is not None:
            spans = [
                s for s in spans
                if datetime.fromisoformat(s["start_time"]) >= start_time
            ]
        limit = kw.get("limit") or 100
        return {"data": spans[:limit], "next_cursor": None}

    def get_span_annotations(self, *, span_ids: list[str], project_identifier: str = "default"):
        ids = set(span_ids)
        out = []
        for s in self.store:
            for ann in s.get("_annotations", []):
                if s["context"]["span_id"] in ids:
                    out.append({**ann, "span_id": s["context"]["span_id"]})
        return out


class FakePhoenixClient:
    """Duck-typed `phoenix.client.Client` over an in-memory span store."""

    def __init__(self, traces: list[list[dict]] | None = None) -> None:
        self.store: list[dict] = [s for t in (traces or []) for s in t]
        self.spans = FakePhoenixSpans(self.store)
