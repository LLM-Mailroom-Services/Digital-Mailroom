"""PhoenixSource tests: mapping contract + failure isolation (no network)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mailroom_ui.phoenix_source import PhoenixSource, PhoenixUnavailable
from server.main import create_app
from tests.fake_phoenix import FakePhoenixClient, make_phoenix_trace, make_reloaded_trace


def _source(traces=None) -> PhoenixSource:
    return PhoenixSource(client=FakePhoenixClient(traces))


def test_list_traces_groups_roots_and_maps_fields():
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    src = _source([
        make_phoenix_trace("p1", base_time=now),
        make_phoenix_trace("p2", base_time=now - timedelta(minutes=5)),
    ])
    traces = src.list_traces(since=now - timedelta(hours=2), limit=10)
    assert [t["id"] for t in traces] == ["p1", "p2"]
    t = traces[0]
    assert t["name"] == "document-pipeline"
    assert t["session_id"] == "MATTER-001"
    assert "mailroom" in t["tags"] and "pilot" in t["tags"]
    assert t["environment"] == "pilot"
    assert t["input"]["filename"] == "sample.txt"
    assert t["output"]["stage"] == "archived"


def test_get_run_full_interpretation():
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    src = _source([make_phoenix_trace("p-full", base_time=now)])
    run = src.get_run("p-full")
    assert run is not None
    assert run.stage.value == "archived"
    assert run.doc_type == "contract"
    assert run.filename == "sample.txt"
    assert run.matter_id == "MATTER-001"
    # LLM child span -> generation with model/usage/cost
    assert run.llm_call_count == 1
    assert run.total_tokens == 1200
    assert abs(run.cost_usd - 0.0021) < 1e-9
    assert any(g.model == "qwen2.5:7b" for g in run.generations)
    # node observations mapped through SPAN_STAGE_MAP + NODE_OBSERVATION_TYPES
    names = [s.name for s in run.spans]
    assert "intake-document" in names and "archive-document" in names
    by_name = {s.name: s.observation_type for s in run.spans}
    assert by_name["intake-document"] == "SPAN"
    # index 1 of the fixture is the LLM child (same name as classify-document
    # in some traces, but here it is a GENERATION — nodes stay typed).
    assert by_name["extract-fields"] == "AGENT"
    assert by_name["compile-report"] == "AGENT"
    assert by_name["write-catalog"] == "SPAN"
    assert by_name["archive-document"] == "SPAN"
    assert all(s.observation_type != "GENERATION" for s in run.spans)
    # annotations -> scores -> verdict/quality
    assert run.verdict == "CORRECT"
    assert run.quality == 0.88


def test_unknown_spans_degrade_not_crash():
    """Spans outside the llm-mailroom contract must interpret to a run with
    unknown/inbox staging — never an exception."""
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    spans = make_phoenix_trace(
        "p-unknown", base_time=now,
        span_names=["my-agent-plan", "my-agent-act"],
        stage="still-running", doc_type="", verdict=None, quality=None,
    )
    src = _source([spans])
    run = src.get_run("p-unknown")
    assert run is not None
    assert run.stage.value in ("inbox", "unknown", "classify", "extract")


def test_error_span_surfaces_message():
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    src = _source([make_phoenix_trace("p-err", base_time=now, error_span=True,
                                      verdict=None, quality=None)])
    run = src.get_run("p-err")
    assert run.error_message and "bad JSON" in run.error_message


def test_unavailable_client_raises_contract_error():
    src = _source([])
    src.available = False
    with pytest.raises(PhoenixUnavailable):
        src.list_traces(limit=5)


def test_health_reflects_reachability():
    ok = _source([make_phoenix_trace("h1")])
    assert ok.health()["phoenix"] is True
    down = _source([])
    down.available = False
    h = down.health()
    assert h["phoenix"] is False and h["ok"] is False


def test_serves_through_display_api():
    """The FastAPI app must accept a PhoenixSource unchanged."""
    from fastapi.testclient import TestClient

    now = datetime.now(timezone.utc) - timedelta(minutes=50)
    src = _source([make_phoenix_trace("p-api", base_time=now)])
    with TestClient(create_app(src)) as c:
        listing = c.get("/api/traces?since=3600").json()
        health = c.get("/api/health").json()
        meta = c.get("/api/meta").json()
    assert listing["count"] == 1
    assert listing["source"] == "phoenix"
    assert health["phoenix"] is True
    assert meta["source"] == "phoenix"
    assert any(e["path"] == "/api/debug/logs" for e in meta["endpoints"])


# --- mailroom-reloaded runs (mailroom.document / mailroom.node.*) ---------


def test_reloaded_archived_run_maps_stages_and_types():
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    src = _source([make_reloaded_trace("r1", base_time=now)])
    t = src.list_traces(since=now - timedelta(hours=2))[0]
    assert t["name"] == "mailroom.document"
    assert t["session_id"] == "eval-20261009"  # falls back to mailroom.run_id
    assert t["input"] == {"doc_id": "doc-0001", "filename": "lease.pdf", "run_id": "eval-20261009"}
    assert t["output"] == {"stage": "archived", "doc_type": "contract"}
    run = src.get_run("r1")
    assert run is not None
    assert run.stage.value == "archived"
    assert run.doc_id == "doc-0001"
    assert run.filename == "lease.pdf"
    assert run.doc_type == "contract"
    by_name = {s.name: s.observation_type for s in run.spans}
    assert by_name["mailroom.node.sort"] == "AGENT"
    assert by_name["mailroom.node.ingest"] == "SPAN"
    assert by_name["mailroom.node.report_catalog_archive"] == "SPAN"
    assert run.routing_path[:3] == ["intake", "classify", "extract"]


def test_reloaded_parked_run_lands_on_review_station():
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    src = _source([make_reloaded_trace(
        "r2", base_time=now, status="parked", doc_type=None,
        nodes=["ingest", "bert_primary", "sort", "human_review"],
    )])
    run = src.get_run("r2")
    assert run.stage.value == "review"


def test_reloaded_failed_run_and_judge_detour():
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    src = _source([make_reloaded_trace(
        "r3", base_time=now, status="failed",
        nodes=["ingest", "sort", "extract", "verify", "boss"],
    )])
    run = src.get_run("r3")
    assert run.stage.value == "failed"
    types = {s.name: s.observation_type for s in run.spans}
    assert types["mailroom.node.verify"] == "EVALUATOR"
    assert "judge_verify" in run.routing_path and "boss" in run.routing_path


def test_reloaded_retry_loop_is_folded_into_retry_stage():
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    src = _source([make_reloaded_trace(
        "r4", base_time=now,
        nodes=["ingest", "sort", "sort", "extract", "extract", "report_catalog_archive"],
    )])
    run = src.get_run("r4")
    assert "retry_classify" in run.routing_path
    assert "retry_extract" in run.routing_path


def test_reloaded_in_flight_without_status_degrades_to_span_progress():
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    spans = make_reloaded_trace("r5", base_time=now, nodes=["ingest", "sort"])
    del spans[0]["attributes"]["mailroom.status"]
    del spans[0]["attributes"]["mailroom.doc_type"]
    run = _source([spans]).get_run("r5")
    assert run is not None
    assert run.stage.value == "classify"


def test_reloaded_explicit_io_wins_over_attributes():
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    spans = make_reloaded_trace("r6", base_time=now, status="failed")
    spans[0]["attributes"]["output.value"] = '{"stage": "archived"}'
    t = _source([spans]).list_traces(since=now - timedelta(hours=2))[0]
    assert t["output"]["stage"] == "archived"
