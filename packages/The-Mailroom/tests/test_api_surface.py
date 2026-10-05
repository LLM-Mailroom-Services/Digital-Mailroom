"""Every display API endpoint responds with the documented shape.

The TUI, pixel console, and Observatory all share this surface — a silent
404 or HTML 500 here blanks a desk on every client.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from server.main import API_ENDPOINTS, create_app
from tests.fake_langfuse import FakeClient, make_trace


def _client():
    now = datetime.now(timezone.utc) - timedelta(minutes=20)
    traces = [
        make_trace("t-arch", filename="acme-msa.pdf", stage="archived",
                   base_time=now, verdict="CORRECT"),
        make_trace("t-rev", filename="claim-letter.pdf", stage="review",
                   doc_type="insurance_claim", extract_conf=0.62,
                   base_time=now - timedelta(minutes=5), verdict="PARTIAL"),
    ]
    return TestClient(create_app(LangfuseSource(client=FakeClient(traces))))


def test_every_meta_endpoint_is_reachable():
    skip = {
        "/ws",
        "/live",
        "/api/review/audit",
        "/v1/auth/me",
        "/v1/auth/logout",
        "/v1/archive/list",
        "/v1/ops/status",
        "/v1/ops/throughput",
        "/v1/ops/distribution",
        "/v1/ops/events",
        "/ws/pipeline",
        "/desk",
    }
    with _client() as c:
        meta = c.get("/api/meta").json()
        listed = [e["path"] for e in meta["endpoints"]]
        for spec in API_ENDPOINTS:
            path = spec["path"]
            assert path in listed
            if path in skip or "{" in path:
                continue
            method = spec["method"]
            if method == "GET":
                r = c.get(path if path != "/api/traces" else "/api/traces?since=3600")
                assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
            elif method == "POST" and path == "/api/debug/client":
                r = c.post(path, json={"href": "http://test", "events": []})
                assert r.status_code == 200 and r.json()["ok"] is True
            elif method == "POST" and path == "/v1/auth/login":
                r = c.post(path, json={"username": "admin", "password": "changeme"})
                assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
                assert r.json()["token_type"] == "bearer"


def test_trace_detail_and_404():
    with _client() as c:
        ok = c.get("/api/traces/t-arch")
        assert ok.status_code == 200
        assert ok.json()["filename"] == "acme-msa.pdf"
        assert "spans" in ok.json()
        missing = c.get("/api/traces/does-not-exist")
        assert missing.status_code == 404
        assert missing.json()["error"] == "trace not found"


def test_session_detail_and_review_and_debug_bundle():
    with _client() as c:
        sessions = c.get("/api/sessions?limit=10").json()
        assert sessions["count"] >= 1
        sid = sessions["sessions"][0]["id"]
        one = c.get(f"/api/sessions/{sid}")
        assert one.status_code == 200
        assert one.json()["count"] >= 1
        review = c.get("/api/review-queue").json()
        assert review["count"] == 1
        bundle = c.get("/api/debug/bundle").json()
        assert bundle["health"]["ok"] is True
        assert "how_to" in bundle
        logs = c.get("/api/debug/logs?limit=20").json()
        assert "events" in logs
        src = c.get("/api/debug/source").json()
        assert src["sources"] == ["langfuse"]


def test_health_and_root_and_live_pages():
    with _client() as c:
        h = c.get("/api/health").json()
        assert h.get("ok") or h.get("langfuse")
        root = c.get("/")
        assert root.status_code == 200
        assert "THE MAILROOM" in root.text
        live = c.get("/live")
        assert live.status_code == 200
        assert "Mailroom Observatory" in live.text


def test_default_traces_and_metrics_use_week_window():
    """Bare /api/traces used to default to 30 minutes and drop older runs
    that the Observatory already asked for with since=604800."""
    with _client() as c:
        traces = c.get("/api/traces").json()
        assert traces["count"] == 2
        metrics = c.get("/api/metrics").json()
        assert metrics["total_docs"] == 2
