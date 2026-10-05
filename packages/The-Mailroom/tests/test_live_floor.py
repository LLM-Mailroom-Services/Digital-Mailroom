"""Live-floor freshness: in-flight traces, pipeline ops, graph node aliases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from mailroom_ui.models import Stage
from mailroom_ui.pipeline_schema import SPAN_STAGE_MAP
from server.main import create_app
from server.poller import PollHub, is_conveyor_hot, run_fingerprint
from tests.fake_langfuse import FakeClient, make_trace
from tests.test_interpreter import _run


def test_graph_node_names_map_to_stations():
    assert SPAN_STAGE_MAP["retry_classify"] is Stage.RETRY_CLASSIFY
    assert SPAN_STAGE_MAP["review_classify"] is Stage.RETRY_CLASSIFY
    assert SPAN_STAGE_MAP["judge_verify"] is Stage.JUDGE_VERIFY
    assert SPAN_STAGE_MAP["boss_escalation"] is Stage.BOSS
    assert SPAN_STAGE_MAP["catalog_write"] is Stage.CATALOG
    run = _run(make_trace(
        "t-graph-ids",
        stage="processing",
        span_names=["intake", "classify", "extract", "judge_verify"],
    ))
    assert run.stage is Stage.JUDGE_VERIFY
    assert "judge_verify" in run.routing_path


def test_poller_refreshes_inflight_when_spans_advance():
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    first = make_trace(
        "t-live",
        stage="processing",
        span_names=["intake-document"],
        base_time=now,
        verdict=None,
        quality=None,
    )
    client = FakeClient([first])
    src = LangfuseSource(client=client, cache_ttl=60, poll_cache_ttl=60, run_cache_ttl=60)
    hub = PollHub(src, interval=3, window=3600, limit=10, inflight_ttl=0)
    snap1 = hub._fetch()
    assert snap1 is not None
    assert snap1[0]["stage"] == "intake"

    advanced = make_trace(
        "t-live",
        stage="processing",
        span_names=["intake-document", "classify-document", "extract-fields"],
        base_time=now,
        verdict=None,
        quality=None,
        latency=20.0,
    )
    client.traces[:] = [advanced]
    snap2 = hub._fetch()
    assert snap2[0]["stage"] == "extract"


def test_poller_keeps_terminal_detail_when_fingerprint_matches():
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    tr = make_trace("t-done", stage="archived", base_time=now)
    client = FakeClient([tr])
    src = LangfuseSource(client=client, cache_ttl=60, poll_cache_ttl=60, run_cache_ttl=60)
    hub = PollHub(src, interval=3, window=3600, limit=10)
    first = hub._fetch()
    assert first[0]["stage"] == "archived"
    cached_at = hub._details["t-done"][0]
    second = hub._fetch()
    assert second[0]["stage"] == "archived"
    assert hub._details["t-done"][0] == cached_at


def test_get_run_force_refresh_bypasses_run_cache():
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    client = FakeClient([make_trace(
        "t-force", stage="processing", span_names=["intake-document"],
        base_time=now, verdict=None, quality=None,
    )])
    src = LangfuseSource(client=client, cache_ttl=60, poll_cache_ttl=60, run_cache_ttl=60)
    first = src.get_run("t-force")
    assert first.stage is Stage.INTAKE
    client.traces[:] = [make_trace(
        "t-force", stage="processing",
        span_names=["intake-document", "classify-document"],
        base_time=now, verdict=None, quality=None,
    )]
    stale = src.get_run("t-force")
    assert stale.stage is Stage.INTAKE
    fresh = src.get_run("t-force", force_refresh=True)
    assert fresh.stage is Stage.CLASSIFY


def test_pipeline_endpoint_unconfigured():
    src = LangfuseSource(client=FakeClient([make_trace("t1")]))
    with TestClient(create_app(src)) as c:
        r = c.get("/api/pipeline")
        assert r.status_code == 200
        body = r.json()
        assert body["configured"] is False
        meta = c.get("/api/meta").json()
    assert "poll_interval_s" in meta
    assert any(e["path"] == "/api/pipeline" for e in meta["endpoints"])


def test_pipeline_ops_reads_health(monkeypatch):
    from mailroom_ui import pipeline_ops

    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")

    def fake_get(url, *, timeout=1.5, token=""):
        assert url.endswith("/v1/health")
        return {
            "status": "ok",
            "checks": {
                "watcher_heartbeat_seconds_ago": 0.4,
                "inbox_pending": 2,
                "ingestion_paused": False,
            },
        }

    monkeypatch.setattr(pipeline_ops, "_get_json", fake_get)
    ops = pipeline_ops.fetch_pipeline_ops()
    assert ops["configured"] is True
    assert ops["watcher"] == "live"
    assert ops["inbox_pending"] == 2
    assert ops["ok"] is True


def test_pipeline_ops_queue_uses_v1(monkeypatch):
    from mailroom_ui import pipeline_ops

    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "tok")
    urls = []

    def fake_get(url, *, timeout=1.5, token=""):
        urls.append((url, token))
        if url.endswith("/v1/health"):
            return {"status": "ok", "checks": {"watcher": "live", "watcher_heartbeat_seconds_ago": 0.1}}
        if url.endswith("/v1/queue"):
            return {"queued": [{"file": "a.pdf", "matter_id": "M", "uploaded_at": "t"}]}
        raise AssertionError(url)

    monkeypatch.setattr(pipeline_ops, "_get_json", fake_get)
    ops = pipeline_ops.fetch_pipeline_ops()
    assert ops["queued"][0]["file"] == "a.pdf"
    assert any(u.endswith("/v1/queue") and t == "tok" for u, t in urls)


def test_producer_url_prefix_helpers(monkeypatch):
    from mailroom_ui.pipeline_ops import pipeline_api_prefix, producer_url

    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.delenv("MAILROOM_PIPELINE_API_PREFIX", raising=False)
    assert pipeline_api_prefix() == "/v1"
    assert producer_url("/lookup") == "http://pipeline.test:8000/v1/lookup"
    monkeypatch.setenv("MAILROOM_PIPELINE_API_PREFIX", "")
    assert pipeline_api_prefix() == ""
    assert producer_url("health") == "http://pipeline.test:8000/health"


def test_ws_snapshot_includes_pipeline_and_poll_interval():
    src = LangfuseSource(client=FakeClient([make_trace("t1")]))
    hub = PollHub(src, interval=2.5, window=3600, limit=10)
    msg = hub._snapshot_message(stale=False)
    assert msg["type"] == "snapshot"
    assert msg["poll_interval_s"] == 2.5
    assert "pipeline" in msg
    assert is_conveyor_hot(_run(make_trace(
        "hot", stage="processing", span_names=["classify-document"],
        verdict=None, quality=None,
    )))
    done = _run(make_trace("done", stage="archived"))
    assert not is_conveyor_hot(done)
    assert run_fingerprint(done)[1] == "archived"


def test_pipeline_ops_prefers_declared_watcher(monkeypatch):
    from mailroom_ui import pipeline_ops

    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")

    def fake_get(url, *, timeout=1.5, token=""):
        return {
            "status": "ok",
            "checks": {
                "watcher": "live",
                "watcher_heartbeat_seconds_ago": 40.0,
                "inbox_pending": 0,
            },
        }

    monkeypatch.setattr(pipeline_ops, "_get_json", fake_get)
    ops = pipeline_ops.fetch_pipeline_ops()
    assert ops["watcher"] == "live"
    assert ops["inbox_pending"] == 0
    assert ops["ok"] is True


def test_pipeline_ops_reads_top_level_inbox(monkeypatch):
    from mailroom_ui import pipeline_ops

    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")

    def fake_get(url, *, timeout=1.5, token=""):
        return {
            "status": "ok",
            "watcher_heartbeat_seconds_ago": 1.0,
            "inbox_pending": 3,
            "ingestion_paused": True,
        }

    monkeypatch.setattr(pipeline_ops, "_get_json", fake_get)
    ops = pipeline_ops.fetch_pipeline_ops()
    assert ops["watcher"] == "live"
    assert ops["inbox_pending"] == 3
    assert ops["ingestion_paused"] is True
    assert ops["ok"] is True


def test_server_source_ttl_follows_poll_interval():
    from pathlib import Path

    from server import main as server_main

    text = Path(server_main.__file__).read_text()
    assert "cache_ttl=ttl" in text
    assert "poll_cache_ttl=ttl" in text
    assert "ttl = max(0.0, POLL_INTERVAL)" in text


def test_poller_overlays_light_session_on_reused_trace_id():
    """HF pilots reuse deterministic Langfuse ids; list session_id is live."""
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    first = make_trace(
        "t-reuse",
        stage="archived",
        session_id="pilot-old",
        matter_id="pilot-old",
        base_time=now,
    )
    client = FakeClient([first])
    src = LangfuseSource(client=client, cache_ttl=0, poll_cache_ttl=0, run_cache_ttl=60)
    hub = PollHub(src, interval=3, window=3600, limit=10, inflight_ttl=0)
    snap1 = hub._fetch()
    assert snap1 is not None
    assert hub.runs[0].session_id == "pilot-old"
    assert snap1[0]["session_id"] == "pilot-old"

    later = now + timedelta(minutes=3)
    client.traces[:] = [make_trace(
        "t-reuse",
        stage="review",
        doc_type="insurance_claim",
        session_id="pilot-hf-50",
        matter_id="pilot-hf-50",
        base_time=later,
    )]
    snap2 = hub._fetch()
    assert snap2[0]["session_id"] == "pilot-hf-50"
    assert snap2[0]["stage"] == "review"
    assert hub.runs[0].session_id == "pilot-hf-50"
    assert hub.runs[0].needs_human is True


def test_list_traces_merges_into_harvest():
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    src = LangfuseSource(
        client=FakeClient([make_trace("t-h", session_id="s1", base_time=now)]),
        cache_ttl=60, poll_cache_ttl=60, run_cache_ttl=60,
    )
    src.list_traces(since=now - timedelta(hours=1), limit=10)
    harvest = src.cache.get("list-harvest")
    assert isinstance(harvest, dict)
    assert harvest["t-h"]["session_id"] == "s1"


def test_pipeline_ops_unconfigured_without_url(monkeypatch):
    from mailroom_ui.pipeline_ops import fetch_pipeline_ops

    monkeypatch.delenv("MAILROOM_PIPELINE_URL", raising=False)
    monkeypatch.delenv("MAILROOM_PIPELINE_API", raising=False)
    ops = fetch_pipeline_ops()
    assert ops["configured"] is False


def test_inflight_mode_enriches_parked_runs_once_within_budget(monkeypatch):
    """Runs already parked/finished at startup used to stay LIGHT forever
    ($0 cost, no verdict) in the default inflight mode."""
    monkeypatch.setenv("MAILROOM_POLL_ENRICH", "inflight")
    monkeypatch.setenv("MAILROOM_POLL_ENRICH_BUDGET", "2")
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    traces = [make_trace(f"t-old-{i}", stage="archived", base_time=now - timedelta(minutes=i))
              for i in range(3)]
    src = LangfuseSource(client=FakeClient(traces), cache_ttl=60, poll_cache_ttl=60)
    calls: list[str] = []
    real = src.get_run

    def counting(trace_id, **kw):
        calls.append(trace_id)
        return real(trace_id, **kw)

    src.get_run = counting
    hub = PollHub(src, interval=3, window=3600, limit=10)
    hub._fetch()
    assert len(calls) == 2          # budget
    hub._fetch()
    assert len(calls) == 3          # the remaining run
    hub._fetch()
    assert len(calls) == 3          # enrich-once: nothing changed
    assert set(hub._enriched_fp) == {t["id"] for t in traces}


def test_trace_detail_prefers_live_langfuse_over_disk_cache():
    """The disk snapshot used to win whenever it had spans, hiding late scores."""
    from mailroom_ui.trace_cache import persist_run

    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    tr = make_trace("t-late", stage="archived", base_time=now, verdict="CORRECT")
    persist_run("t-late", {"trace_id": "t-late", "verdict": "MISS", "spans": [], "generations": []})
    src = LangfuseSource(client=FakeClient([tr]))
    with TestClient(create_app(src)) as c:
        body = c.get("/api/traces/t-late").json()
    assert body["verdict"] == "CORRECT"
