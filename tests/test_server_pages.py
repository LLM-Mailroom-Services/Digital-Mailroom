"""GH Pages edition: CORS, debug endpoints, multi-source aggregation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from mailroom_ui.multi_source import MultiSource
from mailroom_ui.phoenix_source import PhoenixSource
from server.main import create_app, _source_names
from tests.fake_langfuse import FakeClient, make_trace
from tests.fake_phoenix import FakePhoenixClient, make_phoenix_trace


def _lf():
    return LangfuseSource(client=FakeClient([make_trace("t1")]))


def test_cors_headers_present_for_pages_origin():
    app = create_app(_lf())
    with TestClient(app) as c:
        r = c.get("/api/health", headers={"Origin": "https://example.github.io"})
    assert r.headers.get("access-control-allow-origin") == "*"


def test_debug_logs_ring_buffer_records_requests():
    with TestClient(create_app(_lf())) as c:
        c.get("/api/health")
        c.get("/api/debug/logs?limit=10")
        evs = c.get("/api/debug/logs").json()["events"]
    assert any(e["path"] == "/api/health" and e["status"] == 200 for e in evs)
    assert all("ms" in e for e in evs)


def test_debug_source_reports_selector_and_sources():
    with TestClient(create_app(_lf())) as c:
        info = c.get("/api/debug/source").json()
    assert info["sources"] == ["langfuse"]
    assert info["selector"] in ("langfuse", "phoenix", "both")


def test_meta_carries_version_mode_and_endpoint_index():
    with TestClient(create_app(_lf())) as c:
        m = c.get("/api/meta").json()
    assert m["mode"] == "api"
    assert m["version"]
    paths = [e["path"] for e in m["endpoints"]]
    assert "/api/traces" in paths and "/ws" in paths


def test_multi_source_merges_and_health_aggregates():
    lf = _lf()
    px = PhoenixSource(client=FakePhoenixClient([make_phoenix_trace("p1", base_time=datetime.now(timezone.utc) - timedelta(minutes=10))]))
    src = MultiSource([lf, px])
    assert _source_names(src) == "langfuse+phoenix"
    traces = src.list_traces(limit=50)
    ids = {t["id"] for t in traces}
    assert {"t1", "p1"} <= ids
    h = src.health()
    assert h["langfuse"] is True and h["phoenix"] is True and h["ok"] is True
    # drill-down delegates to whichever source holds the trace
    assert src.get_run("p1") is not None
    assert src.get_run("t1") is not None


def test_multi_source_survives_one_dead_side():
    class DeadSource:
        def health(self):
            return {"ok": False, "langfuse": False, "source": "langfuse"}

        def __getattr__(self, name):
            def fail(*a, **kw):
                raise RuntimeError("dead source")
            return fail

    dead = DeadSource()
    live = PhoenixSource(client=FakePhoenixClient([make_phoenix_trace("p2", base_time=datetime.now(timezone.utc) - timedelta(minutes=10))]))
    src = MultiSource([dead, live])
    h = src.health()
    assert h["ok"] is True and h["langfuse"] is False and h["phoenix"] is True
    assert [t["id"] for t in src.list_traces(limit=10)] == ["p2"]
