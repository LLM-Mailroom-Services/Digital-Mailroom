"""Every edge of the compiled mailroom graph, walked end to end (SAND-085).

Model-calling nodes are scripted; the compiled graph, every router, intake,
human review, report compilation, catalog, archive, bins and the SQLite
checkpoint are real. ``test_every_graph_edge_was_walked`` fails when an edge is
added upstream without a scenario here.
"""
from __future__ import annotations

import pytest

from mailroom_sandbox.runtime import activate

MODEL_NODES = ("classify", "retry_classify", "review_classify", "extract", "retry_extract",
               "judge_verify", "arbiter", "boss_escalation", "classification_arbiter")
REAL_NODES = ("intake", "human_review", "compile_report", "catalog_write", "archive")
WALKED: set[tuple[str, str]] = set()
DATA = {"entity_name": "Cedar Sample Ltd", "record_type": "minutes", "confidence": 0.99}


@pytest.fixture
def graph(tmp_path, monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.runtime._load_dotenv", lambda: None)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'catalog.db'}")
    monkeypatch.setenv("MAILROOM_CHECKPOINTER", "sqlite")
    for flag in ("MAILROOM_RELATIONS", "MAILROOM_RELATIONS_EMBEDDINGS", "MAILROOM_BERT_INTAKE",
                 "MAILROOM_LLM_INTAKE", "MAILROOM_LLM_CACHE"):
        monkeypatch.setenv(flag, "0")
    activate("ollama", load_env_file=False)
    import graph.build_graph as bg

    bg.reset_compiled_graph()
    yield bg
    bg.reset_compiled_graph()


def thresholds():
    from pipeline.config import get_confidence_thresholds

    return get_confidence_thresholds("corporate_record")


def sorted_as(confidence, *, doc_type="corporate_record", attempt=1):
    return {"doc_type": doc_type, "doc_subclass": "minutes", "classification_confidence": confidence,
            "classification_attempts": attempt, "stage": "classified", "transient_error": False}


def extracted(confidence=0.99, *, data=DATA, attempt=1, **extra):
    return {"extracted_data": data, "extraction_confidence": confidence, "extraction_attempts": attempt,
            "stage": "extracted", "transient_error": False, **extra}


def transient(node):
    return {"transient_error": True, f"transient_retries_{node}": 1, "error_message": "provider blip"}


def walk(bg, monkeypatch, tmp_path, script, *, ground_truth=None):
    """Run one document under ``script`` ({node: [updates]}); return (result, nodes visited)."""
    from pipeline.bins import inbox_dir

    visited: list[str] = []
    queues = {name: list(updates) for name, updates in script.items()}

    def wrap(name, real):
        def node(state):
            visited.append(name)
            if queues.get(name):
                update = queues[name].pop(0)
                return update(state) if callable(update) else update
            return real(state)
        return node

    for name in MODEL_NODES:
        monkeypatch.setattr(bg, f"{name}_node", wrap(
            name, lambda state, name=name: pytest.fail(f"unscripted model node {name}")))
    for name in REAL_NODES:
        monkeypatch.setattr(bg, f"{name}_node", wrap(name, getattr(bg, f"{name}_node")))
    bg.reset_compiled_graph()
    inbox_dir().mkdir(parents=True, exist_ok=True)
    source = inbox_dir() / "exhibit.txt"
    source.write_text("Cedar Sample Ltd board minutes: the directors adopt the annual budget.")
    result = bg.run_pipeline(source, "ROUTING-MATRIX", ground_truth=ground_truth)
    return result, visited


def record(visited, *, stop=None):
    WALKED.update(zip(visited, visited[1:]))
    if stop:
        WALKED.add((visited[-1], stop))


HIGH, LOW = 0.995, 0.1


def medium():
    limits = thresholds()
    return (limits["low"] + limits["high"]) / 2


def judged():
    limits = thresholds()
    return (limits["low"] + float(limits.get("judge_band_high", 0.85))) / 2


def scenarios():
    medium_sort, band = medium(), judged()
    arbiter_retry = {"arbiter_decision": "retry_extraction", "arbiter_retry_count": 1, "transient_error": False}
    judge = lambda verdict, passes=1: {"judge_verdict": verdict, "judge_pass_count": passes, "transient_error": False}  # noqa: E731
    accept = {"review_verdict": "reviewer_agrees_high", "reviewer_confidence": 0.99,
              "reviewer_doc_type": "corporate_record", "transient_error": False}
    parked = {"review_verdict": "decision_parks", "review_route": "human_review", "reviewer_confidence": 0.4,
              "reviewer_doc_type": "corporate_record", "reviewer_causes": ["reviewer_low_confidence"],
              "transient_error": False}
    return {
        "happy_path": ({"classify": [sorted_as(HIGH)], "extract": [extracted()]}, "archived"),
        "unknown_class": ({"classify": [sorted_as(HIGH, doc_type="unknown")]}, "review"),
        "low_confidence": ({"classify": [sorted_as(LOW)], "retry_classify": [sorted_as(LOW, attempt=2)]}, "review"),
        "low_then_recovered": ({"classify": [sorted_as(LOW)], "retry_classify": [sorted_as(HIGH, attempt=2)],
                                "extract": [extracted()]}, "archived"),
        "reviewer_accepts": ({"classify": [sorted_as(medium_sort)], "retry_classify": [sorted_as(medium_sort, attempt=2)],
                              "review_classify": [accept], "extract": [extracted()]}, "archived"),
        "reviewer_rejects": ({"classify": [sorted_as(medium_sort)], "retry_classify": [sorted_as(medium_sort, attempt=2)],
                              "review_classify": [{"review_verdict": "reviewer_disagrees", "reviewer_confidence": 0.5,
                                                   "transient_error": False}]}, "review"),
        "transient_loops": ({"classify": [transient("classify"), sorted_as(LOW)],
                             "retry_classify": [transient("retry_classify"), sorted_as(medium_sort, attempt=2)],
                             "review_classify": [transient("review_classify"), accept],
                             "extract": [transient("extract"), extracted(LOW)],
                             "retry_extract": [transient("retry_extract"), extracted(band, attempt=2)],
                             "judge_verify": [transient("judge_verify"), judge("partial")],
                             "arbiter": [transient("arbiter"), {"arbiter_decision": "accept_with_caveats",
                                                                "transient_error": False}]}, "archived"),
        "extraction_exhausted": ({"classify": [sorted_as(HIGH)], "extract": [extracted(LOW, attempt=3)],
                                  "judge_verify": [judge("complete")]}, "review"),
        "extraction_verified": ({"classify": [sorted_as(HIGH)], "extract": [extracted(LOW, attempt=3)],
                                 "judge_verify": [{**judge("complete"), "judge_source_verified": True}]}, "archived"),  # a0ed476: a full-source check clears it
        "extraction_empty": ({"classify": [sorted_as(HIGH)], "extract": [extracted(LOW, data={}, attempt=3)]}, "review"),
        "retry_extract_recovers": ({"classify": [sorted_as(HIGH)], "extract": [extracted(LOW)],
                                    "retry_extract": [extracted(attempt=2)]}, "archived"),
        "retry_extract_exhausted": ({"classify": [sorted_as(HIGH)], "extract": [extracted(LOW)],
                                     "retry_extract": [extracted(LOW, attempt=3)],
                                     "judge_verify": [judge("complete")]}, "review"),
        "retry_extract_empty": ({"classify": [sorted_as(HIGH)], "extract": [extracted(LOW)],
                                 "retry_extract": [extracted(LOW, data={}, attempt=3)]}, "review"),
        "retry_extract_conflict": ({"classify": [sorted_as(HIGH)], "extract": [extracted(LOW)],
                                    "retry_extract": [extracted(attempt=2, conflict_detected=True)],
                                    "boss_escalation": [{"review_decision": "approved", "conflict_detected": False,
                                                         "transient_error": False}]}, "archived"),
        "boss_rejects": ({"classify": [sorted_as(HIGH)], "extract": [extracted(conflict_detected=True)],
                          "boss_escalation": [transient("boss_escalation"),
                                              {"review_decision": "rejected", "transient_error": False}]}, "review"),
        "judge_clean": ({"classify": [sorted_as(HIGH)], "extract": [extracted(band)],
                         "judge_verify": [judge("complete")]}, "archived"),
        "judge_error": ({"classify": [sorted_as(HIGH)], "extract": [extracted(band)],
                         "judge_verify": [judge("judge_error")]}, "review"),
        "arbiter_retries": ({"classify": [sorted_as(HIGH)], "extract": [extracted(band)],
                             "judge_verify": [judge("partial")], "arbiter": [arbiter_retry],
                             "retry_extract": [extracted(attempt=2)]}, "archived"),
        # Decision review parks below its cutoff -> classification arbiter -> extract / a person.
        "classification_arbiter_accepts": ({"classify": [sorted_as(medium_sort)],
                                            "retry_classify": [sorted_as(medium_sort, attempt=2)],
                                            "review_classify": [parked],
                                            "classification_arbiter": [{"classification_arbiter_decision": "accept_sorter",
                                                                        "classification_arbiter_confidence": 0.99,
                                                                        "transient_error": False}],
                                            "extract": [extracted()]}, "archived"),
        "classification_arbiter_escalates": ({"classify": [sorted_as(medium_sort)],
                                              "retry_classify": [sorted_as(medium_sort, attempt=2)],
                                              "review_classify": [parked],
                                              "classification_arbiter": [{"classification_arbiter_decision": "human_review",
                                                                          "transient_error": False}]}, "review"),
        "arbiter_escalates": ({"classify": [sorted_as(HIGH)], "extract": [extracted(band)],
                               "judge_verify": [judge("incomplete")],
                               "arbiter": [{"arbiter_decision": "escalate", "transient_error": False}]}, "review"),
    }


@pytest.mark.parametrize("name", [
    "happy_path", "unknown_class", "low_confidence", "low_then_recovered", "reviewer_accepts",
    "reviewer_rejects", "transient_loops", "extraction_exhausted", "extraction_verified", "extraction_empty",
    "retry_extract_recovers", "retry_extract_exhausted", "retry_extract_empty", "retry_extract_conflict", "boss_rejects", "judge_clean",
    "judge_error", "arbiter_retries", "arbiter_escalates", "classification_arbiter_accepts",
    "classification_arbiter_escalates"])
def test_route(name, graph, monkeypatch, tmp_path):
    script, stage = scenarios()[name]
    result, visited = walk(graph, monkeypatch, tmp_path, script)
    record(visited, stop="__end__" if stage == "archived" else None)
    assert result["stage"] == stage, visited
    assert visited[0] == "intake"
    assert visited[-1] == ("archive" if stage == "archived" else "human_review"), visited


def test_ground_truth_class_miss_reaches_the_reviewer_at_full_confidence(graph, monkeypatch, tmp_path):
    result, visited = walk(graph, monkeypatch, tmp_path, {
        "classify": [sorted_as(HIGH)],
        "review_classify": [{"review_verdict": "reviewer_disagrees", "transient_error": False}],
    }, ground_truth={"expected_doc_class": "contract"})
    record(visited)
    assert visited == ["intake", "classify", "review_classify", "human_review"]
    assert result["stage"] == "review"


def test_failed_report_is_withheld_from_the_catalog(graph, monkeypatch, tmp_path):
    def broken(state):
        return {"report_error": True, "extracted_data": {**state["extracted_data"], "_report": {"error": True}}}

    result, visited = walk(graph, monkeypatch, tmp_path, {
        "classify": [sorted_as(HIGH)], "extract": [extracted()], "compile_report": [broken]})
    record(visited)
    assert result["stage"] == "review"
    assert visited[-2:] == ["compile_report", "human_review"]


def test_judge_pass_budget_escalates(graph, monkeypatch, tmp_path):
    passes = int(thresholds().get("judge_max_passes") or 3)
    result, visited = walk(graph, monkeypatch, tmp_path, {
        "classify": [sorted_as(HIGH)], "extract": [extracted(judged())],
        "judge_verify": [{"judge_verdict": "partial", "judge_pass_count": passes, "transient_error": False}]})
    record(visited)
    assert result["stage"] == "review"


@pytest.mark.parametrize("decision,stage", [("approved", "archived"), ("rejected", "failed")])
def test_human_decision_resumes_the_parked_graph(decision, stage, graph, monkeypatch, tmp_path):
    from langgraph.types import Command

    result, visited = walk(graph, monkeypatch, tmp_path, {
        "classify": [sorted_as(HIGH)], "extract": [extracted(LOW, attempt=3), extracted()],
        "judge_verify": [{"judge_verdict": "complete", "judge_pass_count": 1, "transient_error": False}]})
    config = {"configurable": {"thread_id": result["checkpoint_thread_id"]}}
    outcome = graph.get_compiled_graph().invoke(Command(resume={"decision": decision}), config)
    record(visited, stop=None if decision == "approved" else "__end__")
    assert outcome["stage"] == stage


def test_stateless_resume_enters_at_extract_after_the_checkpoint_is_gone(graph, monkeypatch, tmp_path):
    from pipeline.bins import load_manifest, review_file_path

    result, visited = walk(graph, monkeypatch, tmp_path, {
        "classify": [sorted_as(HIGH)], "extract": [extracted(LOW, attempt=3), extracted()],
        "judge_verify": [{"judge_verdict": "complete", "judge_pass_count": 1, "transient_error": False}]})
    manifest = load_manifest(result["doc_id"])
    monkeypatch.setenv("MAILROOM_CHECKPOINTER", "memory")
    graph.reset_compiled_graph()  # a restart without the durable checkpoint
    visited.clear()
    outcome = graph.resume_from_review(manifest, review_file_path(manifest))
    assert visited[0] == "extract"
    assert outcome["stage"] == "archived"
    WALKED.add(("__start__", "extract"))
    record(visited)


def test_every_graph_edge_was_walked(graph):
    """Must run last: the union of the scenarios above covers the compiled graph."""
    if not WALKED:
        pytest.skip("needs the scenarios above in the same pytest run")
    edges = {(edge.source, edge.target) for edge in graph.build_graph().get_graph().edges}
    WALKED.add(("__start__", "intake"))
    assert not edges - WALKED, sorted(edges - WALKED)
