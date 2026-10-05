"""Langfuse-derived snapshot cache — never fabricated rows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from mailroom_ui.trace_cache import (
    CACHE_SOURCE,
    persist_floor,
    persist_run,
    snapshot_bundle,
)
from server.main import create_app
from tests.fake_langfuse import FakeClient, make_trace


class _DeadClient:
    api = None


def _down_source():
    return LangfuseSource(client=_DeadClient())


def test_snapshot_export_is_empty_not_canned():
    bundle = snapshot_bundle()
    assert bundle["source"] == CACHE_SOURCE
    assert bundle["traces"]["runs"] == []


def test_traces_fall_back_to_cache_when_langfuse_down():
    persist_floor(
        [{"trace_id": "t-cached", "filename": "kept.pdf", "stage": "archived"}],
        source="langfuse",
    )
    persist_run("t-cached", {
        "trace_id": "t-cached",
        "filename": "kept.pdf",
        "spans": [],
        "generations": [],
        "scores": {},
    })
    with TestClient(create_app(_down_source())) as c:
        listing = c.get("/api/traces?since=3600")
        assert listing.status_code == 200
        body = listing.json()
        assert body["source"] == CACHE_SOURCE
        assert body["runs"][0]["trace_id"] == "t-cached"
        detail = c.get("/api/traces/t-cached")
        assert detail.status_code == 200
        assert detail.json()["filename"] == "kept.pdf"
        health = c.get("/api/health").json()
        assert health["ok"] is True
        assert health["source"] == CACHE_SOURCE
        snap = c.get("/api/snapshot").json()
        assert snap["traces"]["runs"][0]["trace_id"] == "t-cached"


def test_empty_cache_and_langfuse_down_stays_closed():
    with TestClient(create_app(_down_source())) as c:
        listing = c.get("/api/traces?since=3600")
        assert listing.status_code == 503
        health = c.get("/api/health").json()
        assert health.get("langfuse") is False
        assert health.get("source") != CACHE_SOURCE or not health.get("cache", {}).get("has_snapshot")


def test_live_traces_still_hit_langfuse():
    now = datetime.now(timezone.utc) - timedelta(minutes=10)
    src = LangfuseSource(client=FakeClient([make_trace("t-live", filename="live.pdf", base_time=now)]))
    with TestClient(create_app(src)) as c:
        listing = c.get("/api/traces?since=3600").json()
        assert listing["source"] == "langfuse"
        assert listing["runs"][0]["filename"] == "live.pdf"
        assert listing["runs"][0]["primary_outcome"]
