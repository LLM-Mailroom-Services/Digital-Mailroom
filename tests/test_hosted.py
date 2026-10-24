"""Hosted Observatory edition: public /live UI, distinct from the pixel console."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from server.main import create_app
from tests.fake_langfuse import FakeClient, make_trace


def _client(monkeypatch=None, edition="console"):
    if monkeypatch is not None:
        monkeypatch.setenv("MAILROOM_EDITION", edition)
    src = LangfuseSource(client=FakeClient([make_trace("t1")]))
    return TestClient(create_app(src))


def test_live_ui_is_served_on_every_edition():
    with _client() as c:
        r = c.get("/live")
    assert r.status_code == 200
    body = r.text
    assert "Mailroom Observatory" in body
    assert 'href="#pipeline"' in body
    assert 'class="skip-link"' in body
    assert 'id="main"' in body
    assert "no-store" in r.headers.get("cache-control", "")


def test_live_assets_are_mounted():
    with _client() as c:
        css = c.get("/live/static/css/app.css")
        js = c.get("/live/static/js/app.js")
        client = c.get("/live/static/js/client.js")
        debug = c.get("/live/static/js/debug.js")
    assert js.status_code == 200 and "startReplay" in js.text
    assert "Observations" in js.text and "observation_type" in js.text
    assert "Subclass" in js.text
    assert "Expected subclass" in js.text
    assert "Suite extras" in js.text
    assert "content_topic_accuracy" in js.text
    assert css.status_code == 200 and "skip-link" in css.text and ".obs-type" in css.text
    assert client.status_code == 200 and "reviewQueue" in client.text
    assert "reviewResolve" in client.text
    assert "reviewSource" in client.text
    assert "reviewForm" in js.text and "data-decision" in js.text
    assert 'name="doc_type"' in js.text
    assert "review-source-text" in js.text
    assert 'name="extracted_data"' in js.text
    assert 'data-disposition="complete"' in js.text
    assert "Failure class" in js.text
    assert "run.failure_class" in js.text
    assert ".review-source" in css.text
    assert debug.status_code == 200 and "__OBSERVATORY_DEBUG__" in debug.text


def test_observatory_html_has_debug_desk_and_replay_bar():
    with _client() as c:
        body = c.get("/live").text
    assert 'id="view-debug"' in body
    assert 'id="replay-bar"' in body
    assert 'hosted/js/debug.js' in body or "/live/static/js/debug.js" in body
    assert 'data-view="debug"' in body


def test_debug_bundle_is_one_pull():
    with _client() as c:
        r = c.get("/api/debug/bundle")
    assert r.status_code == 200
    body = r.json()
    assert "health" in body and "source" in body
    assert "server_logs" in body and "client_reports" in body
    assert body["how_to"]["browser_dump"].startswith("window.__OBSERVATORY_DEBUG__")
    assert body["source"]["sources"] == ["langfuse"]


def test_debug_client_accepts_pixel_location_field():
    """Pixel dumps used `location` while Observatory dumps used `href`;
    the store must keep the page URL from either shape."""
    with _client() as c:
        posted = c.post("/api/debug/client", json={
            "location": "http://test/?debug=1",
            "eventCount": 1,
            "events": [{"kind": "boot"}],
        })
        assert posted.status_code == 200
        listed = c.get("/api/debug/client").json()
        assert listed["reports"][0]["href"] == "http://test/?debug=1"


def test_debug_client_roundtrip():
    with _client() as c:
        posted = c.post("/api/debug/client", json={
            "href": "http://test/live#debug",
            "eventCount": 2,
            "lastError": {"kind": "review-error", "message": "HTTP 503"},
            "events": [
                {"t": "2026-08-25T00:00:00Z", "kind": "boot"},
                {"t": "2026-08-25T00:00:01Z", "kind": "review-error", "message": "HTTP 503"},
            ],
        })
        assert posted.status_code == 200
        assert posted.json()["ok"] is True
        listed = c.get("/api/debug/client").json()
        assert listed["count"] == 1
        assert listed["reports"][0]["href"] == "http://test/live#debug"
        bundle = c.get("/api/debug/bundle").json()
        assert bundle["client_reports"][0]["last_error"]["kind"] == "review-error"


def test_hosted_js_visual_and_debug_contracts():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    js = (root / "hosted/js/app.js").read_text()
    css = (root / "hosted/css/app.css").read_text()
    html = (root / "hosted/index.html").read_text()
    dbg = (root / "hosted/js/debug.js").read_text()
    assert '<span class="card-title">' in js
    assert '<p class="card-title">' not in js
    assert '<dl class="metrics">' in js
    assert "palette" in js and "CORRECT" in js
    assert "setReplayBar" in js and "overlayReplay" in js
    assert "replay.terminal" in js
    assert "if (!socketLive)" in js
    assert 'dbg("review-error"' in js
    assert "repeat(4, minmax(0, 1fr))" in css
    assert 'id="replay-bar"' in html and 'id="view-debug"' in html
    assert "__OBSERVATORY_DEBUG__" in dbg and "KINDS" in dbg
    assert 'lastError = null' in dbg
    assert "or returned HTTP status >= 400" in dbg
    assert "Obs.api.reviewContext()" in js
    with _client() as c:
        m = c.get("/api/meta").json()
    paths = [e["path"] for e in m["endpoints"]]
    assert "/api/debug/bundle" in paths
    assert "/api/debug/client" in paths


def test_default_root_remains_pixel_console():
    with _client() as c:
        r = c.get("/")
    assert r.status_code == 200
    assert "THE MAILROOM" in r.text
    assert "Mailroom Observatory" not in r.text


def test_hosted_edition_puts_observatory_on_root(monkeypatch):
    monkeypatch.setenv("MAILROOM_EDITION", "hosted")
    src = LangfuseSource(client=FakeClient([make_trace("t1")]))
    with TestClient(create_app(src)) as c:
        r = c.get("/")
        live = c.get("/live")
    assert "Mailroom Observatory" in r.text
    assert "Mailroom Observatory" in live.text


def test_meta_advertises_hosted_ui():
    with _client() as c:
        m = c.get("/api/meta").json()
    assert m["edition"] == "console"
    assert m["ui"]["hosted"] == "/live"
    paths = [e["path"] for e in m["endpoints"]]
    assert "/live" in paths
