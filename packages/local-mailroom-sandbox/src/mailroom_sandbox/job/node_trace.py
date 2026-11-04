"""Live per-node tracking for full-pipeline runs (SAND-076).

The vendored graph builds its own LangGraph config, so the sandbox cannot pass
callbacks into ``graph.invoke``. Instead a LangChain configure hook injects a
context-held handler into every run started inside :func:`track_nodes`. The
handler keeps only graph-node runs (``metadata.langgraph_node`` naming the run
itself), so LLM calls and LangGraph's internal writers inside a node are
ignored.

Each node emits a ``running`` record when it starts and a ``done`` / ``error``
record when it ends. Decision nodes (sorter, judge, arbiter, boss) also carry
one normalized *decision*, typed the way the incoming Decisions-API model
(``openai/gpt-6-luna-decisions``, Discussion #193) answers a named question:

* ``noul``   – yes/no: ``p`` is the probability of yes.
* ``choice`` – one option: ``answer`` is the most likely option, ``p`` its
  probability, ``options`` the per-option probabilities when known.
* ``score``  – ordered rubric: ``expected`` is the expected score, ``options``
  the per-level probabilities when known.

Today's agents return a label plus at most one confidence or score, so the
mapping fills ``answer`` and ``p`` / ``expected`` and leaves ``options`` empty.
A node whose output already carries ``decisions`` in this schema (a future
Decisions-API agent) is passed through as-is after validation.
"""

from __future__ import annotations

import math
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Iterable, Iterator
from uuid import UUID

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.tracers.context import register_configure_hook
except ImportError:
    BaseCallbackHandler = object
    register_configure_hook = None

DECISION_TYPES = ("noul", "choice", "score")
MAX_DECISIONS = 200  # one Decisions request carries at most 200 questions

# Node → the agent whose model answers it (``None``: deterministic node).
NODE_AGENTS: dict[str, str | None] = {
    "intake": None,
    "classify": "sorter",
    "retry_classify": "sorter",
    "review_classify": "sorter_reviewer",
    "extract": "specialist",
    "retry_extract": "specialist",
    "judge_verify": "judge",
    "arbiter": "arbiter",
    "human_review": None,
    "boss_escalation": "boss",
    "compile_report": None,
    "catalog_write": None,
    "archive": None,
}


def _prob(value: Any) -> float | None:
    try:
        p = float(value)
    except (TypeError, ValueError):
        return None
    return p if math.isfinite(p) and 0.0 <= p <= 1.0 else None


def _num(value: Any) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def normalize_decision(raw: Any) -> dict[str, Any] | None:
    """Validate one decision in the sandbox schema; ``None`` when unusable."""
    if not isinstance(raw, dict) or raw.get("type") not in DECISION_TYPES:
        return None
    options = raw.get("options")
    clean_options = None
    if isinstance(options, dict):
        clean_options = {str(k)[:60]: p for k, v in list(options.items())[:50] if (p := _prob(v)) is not None} or None
    answer = raw.get("answer")
    return {
        "question": str(raw.get("question") or "?")[:80],
        "type": raw["type"],
        "answer": answer if isinstance(answer, bool) or answer is None else str(answer)[:80],
        "p": _prob(raw.get("p")),
        "expected": _num(raw.get("expected")),
        "options": clean_options,
        "source": "decisions" if raw.get("source") == "decisions" else "agent",
    }


def decisions_for(node: str, out: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalized decisions a node's state update records."""
    native = out.get("decisions")
    if isinstance(native, list):
        return [d for d in (normalize_decision(r) for r in native[:MAX_DECISIONS]) if d]
    raw: dict[str, Any] | None = None
    if node in ("classify", "retry_classify") and out.get("doc_type"):
        raw = {"question": "doc_type", "type": "choice", "answer": out["doc_type"],
               "p": out.get("classification_confidence")}
    elif node == "review_classify" and out.get("review_verdict"):
        raw = {"question": "sorter_review", "type": "choice", "answer": out["review_verdict"],
               "p": out.get("classification_confidence")}
    elif node == "judge_verify" and out.get("judge_verdict"):
        raw = {"question": "extraction_verdict", "type": "score", "answer": out["judge_verdict"],
               "expected": out.get("judge_score")}
    elif node == "arbiter" and out.get("arbiter_decision"):
        raw = {"question": "arbiter_route", "type": "choice", "answer": out["arbiter_decision"]}
    elif node == "boss_escalation" and out.get("review_decision"):
        raw = {"question": "conflict_ruling", "type": "choice", "answer": out["review_decision"]}
    decision = normalize_decision(raw)
    return [decision] if decision else []


def agent_for(node: str, doc_type: str | None) -> str | None:
    agent = NODE_AGENTS.get(node)
    if agent == "specialist":
        from mailroom_sandbox.eval.primary import SPECIALISTS

        return SPECIALISTS.get(str(doc_type or "")) or "specialist"
    return agent


class NodeTracker(BaseCallbackHandler):
    """Report graph-node starts and ends for one document to ``sink``."""

    raise_error = False
    run_inline = True

    def __init__(self, doc_id: str, sink: Callable[[dict[str, Any]], None], *,
                 models: dict[str, str] | None = None) -> None:
        self.doc_id = doc_id
        self.sink = sink
        self.models = dict(models or {})
        self.doc_type: str | None = None
        self._open: dict[UUID, tuple[str, float]] = {}
        self._step = 0
        self._lock = threading.Lock()

    def _emit(self, node: str, status: str, **extra: Any) -> None:
        agent = agent_for(node, self.doc_type)
        rec = {"doc": self.doc_id, "node": node, "status": status, "agent": agent,
               "model": self.models.get(agent) if agent else None, "ts": time.time(), **extra}
        try:
            self.sink(rec)
        except Exception:  # noqa: BLE001 — tracking must never break a document
            pass

    def on_chain_start(self, serialized: Any, inputs: Any, *, run_id: UUID,
                       metadata: dict[str, Any] | None = None, name: str | None = None,
                       **kwargs: Any) -> None:
        node = (metadata or {}).get("langgraph_node")
        if not node or node != name or node not in NODE_AGENTS:
            return
        with self._lock:
            self._step += 1
            self._open[run_id] = (node, time.monotonic())
            step = self._step
        self._emit(node, "running", step=step)

    def on_chain_end(self, outputs: Any, *, run_id: UUID, **kwargs: Any) -> None:
        with self._lock:
            opened = self._open.pop(run_id, None)
        if opened is None:
            return
        node, t0 = opened
        out = outputs if isinstance(outputs, dict) else {}
        if out.get("doc_type"):
            self.doc_type = str(out["doc_type"])
        self._emit(node, "done", ms=round((time.monotonic() - t0) * 1000, 1),
                   stage=out.get("stage"), decisions=decisions_for(node, out))

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        with self._lock:
            opened = self._open.pop(run_id, None)
        if opened is None:
            return
        node, t0 = opened
        ms = round((time.monotonic() - t0) * 1000, 1)
        if type(error).__name__ == "GraphInterrupt":
            # interrupt() parks the document for a human; it is a pause, not a failure.
            self._emit(node, "paused", ms=ms)
            return
        self._emit(node, "error", ms=ms, error=f"{type(error).__name__}: {error}"[:200])


_TRACKER: ContextVar[NodeTracker | None] = ContextVar("sandbox_node_tracker", default=None)
if register_configure_hook is not None:
    register_configure_hook(_TRACKER, inheritable=True)


@contextmanager
def track_nodes(doc_id: str, sink: Callable[[dict[str, Any]], None], *,
                models: dict[str, str] | None = None) -> Iterator[NodeTracker]:
    """Track the graph nodes of every LangGraph run started in this context."""
    if register_configure_hook is None:
        raise RuntimeError("node tracking requires langchain_core and its configure hook")
    tracker = NodeTracker(doc_id, sink, models=models)
    token = _TRACKER.set(tracker)
    try:
        yield tracker
    finally:
        _TRACKER.reset(token)


class NodeTotals:
    """Run-wide per-node aggregates that can be fed records a batch at a time.

    :func:`summarize` builds one over the whole stream; a watcher keeps one and
    feeds it only the records appended since its last frame.
    """

    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.totals: dict[str, dict[str, Any]] = {}

    def add(self, rec: dict[str, Any]) -> None:
        self.seen.add(str(rec.get("doc")))
        if rec.get("status") != "running":
            node = str(rec.get("node"))
            t = self.totals.setdefault(node, {"node": node, "visits": 0, "errors": 0, "ms": 0.0})
            t["visits"] += 1
            t["errors"] += rec.get("status") == "error"
            t["ms"] += float(rec.get("ms") or 0.0)

    def update(self, records: Iterable[dict[str, Any]]) -> None:
        for rec in records:
            self.add(rec)

    def ranked(self) -> list[dict[str, Any]]:
        """Per-node totals in graph order, with the mean in place of the raw sum."""
        out = []
        for n in NODE_AGENTS:
            t = self.totals.get(n)
            if t is not None:
                mean = round(t["ms"] / t["visits"], 1) if t["visits"] else None
                out.append({"node": n, "visits": t["visits"], "errors": t["errors"], "mean_ms": mean})
        return out


def summarize(records: Iterable[dict[str, Any]], *, docs: int = 1,
              recent_records: Iterable[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Watch-frame view: the latest document's route plus per-node totals."""
    acc = NodeTotals()
    # When given a separate tail, aggregate the stream without retaining routes.
    # The fallback preserves the single-iterable helper API.
    if recent_records is None:
        recent_records = []
        for rec in records:
            acc.add(rec)
            recent_records.append(rec)
    else:
        acc.update(records)
    return summarize_totals(acc, docs=docs, recent_records=recent_records)


def summarize_totals(acc: NodeTotals, *, docs: int = 1,
                     recent_records: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    """:func:`summarize` over totals already accumulated, with routes from ``recent_records``."""
    if not acc.seen:
        return None
    routes: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for rec in recent_records:
        doc, node = str(rec.get("doc")), str(rec.get("node"))
        if doc not in routes:
            routes[doc] = []
            order.append(doc)
        route = routes[doc]
        if rec.get("status") == "running":
            if route and route[-1]["node"] == node and route[-1]["status"] == "running":
                continue  # a repeated start of the node already in flight
            route.append({"node": node, "status": "running", "agent": rec.get("agent"), "model": rec.get("model")})
            continue
        for hop in reversed(route):
            if hop["node"] == node and hop["status"] == "running":
                break
        else:
            hop = {"node": node, "agent": rec.get("agent"), "model": rec.get("model")}
            route.append(hop)
        hop.update(status=rec.get("status"), ms=rec.get("ms"), decisions=rec.get("decisions") or [],
                   error=rec.get("error"))
    recent = [{"doc": d, "route": routes[d]} for d in order[-max(1, docs):]]
    return {"current": recent[-1] if recent else None, "recent": recent, "nodes": acc.ranked(),
            "docs_seen": len(acc.seen)}


def route_text(route: list[dict[str, Any]]) -> str:
    marks = {"done": "✓", "error": "✗", "running": "…", "paused": "⏸"}
    return " → ".join(f"{h['node']}{marks.get(str(h.get('status')), '')}" for h in route)


def decision_text(d: dict[str, Any]) -> str:
    bits = [f"{d['question']} [{d['type']}] {d.get('answer')}"]
    if d.get("p") is not None:
        bits.append(f"p={d['p']:.2f}")
    if d.get("expected") is not None:
        bits.append(f"E={d['expected']:.2f}")
    if d.get("options"):
        top = sorted(d["options"].items(), key=lambda kv: -kv[1])[:3]
        bits.append(" ".join(f"{k}:{v:.2f}" for k, v in top))
    return " · ".join(bits)
