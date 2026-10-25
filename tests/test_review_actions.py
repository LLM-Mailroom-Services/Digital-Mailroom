"""Human-review resolve proxy: visualizer never holds producer keys in the browser."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from mailroom_ui.review_actions import ReviewActionError, resolve_review, review_context
from server.main import create_app
from tests.fake_langfuse import FakeClient, make_trace
from tests.test_interpreter import _run


def test_interpreter_lifts_doc_id_from_output_and_input():
    run = _run(make_trace(
        "t-doc",
        output_extra={"doc_id": "doc-abc"},
        extra_input={"doc_id": "doc-abc"},
    ))
    assert run.doc_id == "doc-abc"


def test_interpreter_ignores_filename_shaped_span_doc_id():
    run = _run(make_trace("t-file", filename="sample.txt"))
    assert run.doc_id is None


def test_floor_payload_includes_doc_id():
    from server.poller import floor_payload

    run = _run(make_trace("t-pay", output_extra={"doc_id": "doc-pay"}))
    assert floor_payload(run)["doc_id"] == "doc-pay"


def test_inbox_enqueue_unconfigured_is_503(monkeypatch):
    from mailroom_ui.review_actions import enqueue_inbox

    monkeypatch.delenv("MAILROOM_PIPELINE_URL", raising=False)
    monkeypatch.delenv("MAILROOM_PIPELINE_API", raising=False)
    monkeypatch.delenv("MAILROOM_PIPELINE_TOKEN", raising=False)
    try:
        enqueue_inbox(filename="a.pdf")
        assert False, "expected ReviewActionError"
    except ReviewActionError as exc:
        assert exc.status == 503
        assert "MAILROOM_PIPELINE_URL" in exc.message
    src = LangfuseSource(client=FakeClient([make_trace("t1")]))
    with TestClient(create_app(src)) as c:
        r = c.post("/api/inbox/enqueue", json={"filename": "a.pdf"})
        assert r.status_code == 503
        assert r.json()["configured"] is False
        assert "queue" in r.json()["error"].lower()


def test_inbox_enqueue_configured_without_file_is_400(monkeypatch):
    from mailroom_ui.review_actions import enqueue_inbox

    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://producer.test")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "tok")
    try:
        enqueue_inbox(filename="a.pdf", matter_id="M-1")
        assert False, "expected ReviewActionError"
    except ReviewActionError as exc:
        assert exc.status == 400
        assert "file" in exc.message.lower()
    src = LangfuseSource(client=FakeClient([make_trace("t-nofile")]))
    with TestClient(create_app(src)) as c:
        r = c.post("/api/inbox/enqueue", json={"filename": "a.pdf", "matter_id": "M-1"})
        assert r.status_code == 400
        assert r.json()["configured"] is True


def test_inbox_enqueue_proxies_multipart_to_producer_upload(monkeypatch):
    from tests.fake_producer import DEMO_TOKEN, create_fake_producer, serve_in_thread, stop_server

    producer = create_fake_producer()
    server, port, _thread = serve_in_thread(producer)
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", DEMO_TOKEN)
    monkeypatch.delenv("MAILROOM_PIPELINE_API_PREFIX", raising=False)
    src = LangfuseSource(client=FakeClient([make_trace("t-up")]))
    try:
        with TestClient(create_app(src)) as c:
            r = c.post(
                "/api/inbox/enqueue",
                files={"file": ("nda.txt", b"hello-nda", "text/plain")},
                data={"matter_id": "MATTER-9"},
            )
            assert r.status_code == 202
            body = r.json()
            assert body["status"] == "accepted"
            assert body["file"] == "nda.txt"
            assert body["matter_id"] == "MATTER-9"
            assert body["upload_id"]
            queued = producer.state.store.queued
            assert queued[-1]["file"] == "nda.txt"
            assert queued[-1]["matter_id"] == "MATTER-9"
            assert queued[-1]["upload_id"] == body["upload_id"]
    finally:
        stop_server(server)


def test_review_context_unconfigured(monkeypatch):
    monkeypatch.delenv("MAILROOM_PIPELINE_URL", raising=False)
    monkeypatch.delenv("MAILROOM_PIPELINE_API", raising=False)
    monkeypatch.delenv("MAILROOM_PIPELINE_TOKEN", raising=False)
    monkeypatch.delenv("MAILROOM_API_TOKEN", raising=False)
    ctx = review_context(trace_id="t1")
    assert ctx["configured"] is False
    assert ctx["document"] is None
    assert "MAILROOM_PIPELINE" in ctx["error"]


def test_resolve_unconfigured_raises(monkeypatch):
    monkeypatch.delenv("MAILROOM_PIPELINE_URL", raising=False)
    monkeypatch.delenv("MAILROOM_PIPELINE_API", raising=False)
    try:
        resolve_review(decision="approved", trace_id="t1")
        assert False, "expected ReviewActionError"
    except ReviewActionError as exc:
        assert exc.status == 503


def test_api_review_context_unconfigured():
    src = LangfuseSource(client=FakeClient([make_trace("t1", stage="review")]))
    with TestClient(create_app(src)) as c:
        r = c.get("/api/review/context")
        assert r.status_code == 200
        body = r.json()
        assert body["configured"] is False


def test_api_review_resolve_unconfigured():
    src = LangfuseSource(client=FakeClient([make_trace("t1", stage="review")]))
    with TestClient(create_app(src)) as c:
        r = c.post("/api/review/resolve", json={
            "trace_id": "t1", "decision": "approved", "disposition": "record",
        })
        assert r.status_code == 503
        assert "MAILROOM_PIPELINE" in (r.json().get("error") or "")


def test_api_review_resolve_proxies(monkeypatch):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    calls = []

    def fake_request(method, url, *, token="", body=None, timeout=8.0):
        calls.append({"method": method, "url": url, "token": token, "body": body})
        if method == "GET" and "/v1/lookup?" in url:
            return {"document": {"doc_id": "doc-xyz", "trace_id": "t-rev"}}
        if method == "POST" and "/v1/review/" in url:
            return {
                "status": "ok",
                "doc_id": "doc-xyz",
                "decision": body["decision"],
                "disposition": body["disposition"],
                "notes": body["notes"],
                "class_override": {
                    k: body[k] for k in ("override_doc_type", "doc_subclass") if k in body
                },
            }
        raise AssertionError(url)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([
        make_trace("t-rev", stage="review", filename="claim.txt", output_extra={"doc_id": "doc-xyz"}),
    ]))
    with patch.object(review_actions, "_request_json", side_effect=fake_request):
        with TestClient(create_app(src)) as c:
            r = c.post("/api/review/resolve", json={
                "trace_id": "t-rev",
                "filename": "claim.txt",
                "decision": "approved",
                "disposition": "resume",
                "notes": "looks good",
                "doc_type": "insurance_claim",
                "doc_subclass": "pde",
            })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["doc_id"] == "doc-xyz"
    assert body["disposition"] == "resume"
    assert any(c["method"] == "POST" and c["url"].endswith("/v1/review/doc-xyz/resolve") for c in calls)
    posted = next(c for c in calls if c["method"] == "POST")
    assert posted["token"] == "secret-token"
    assert posted["body"]["notes"] == "looks good"
    assert posted["body"]["override_doc_type"] == "insurance_claim"
    assert "doc_type" not in posted["body"]
    assert posted["body"]["doc_subclass"] == "pde"
    assert any(c["method"] == "GET" and "/v1/lookup?" in c["url"] for c in calls)


def test_api_review_resolve_rejects_unknown_class(monkeypatch):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")
    src = LangfuseSource(client=FakeClient([make_trace("t1", stage="review")]))
    with TestClient(create_app(src)) as c:
        r = c.post("/api/review/resolve", json={
            "trace_id": "t1", "decision": "approved", "doc_type": "spaceship",
        })
    assert r.status_code == 400
    assert "unknown doc_type" in (r.json().get("error") or "")


def test_api_review_resolve_passes_parked_noncatalog_subclass(monkeypatch):
    """Producer main does not catalog-gate subclass; parked tokens like fnol must resolve."""
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    posted = {}

    def fake_request(method, url, *, token="", body=None, timeout=8.0):
        if method == "GET" and "/v1/lookup?" in url:
            return {"document": {"doc_id": "doc-fnol"}}
        if method == "POST" and "/v1/review/" in url:
            posted.update(body or {})
            return {"status": "ok", "doc_id": "doc-fnol", "disposition": "complete"}
        raise AssertionError(url)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-fnol", stage="review")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_request):
        with TestClient(create_app(src)) as c:
            r = c.post("/api/review/resolve", json={
                "doc_id": "doc-fnol",
                "decision": "approved",
                "disposition": "complete",
                "doc_type": "insurance_claim",
                "doc_subclass": "fnol",
                "extracted_data": {"claim_number": "CL-4419"},
            })
    assert r.status_code == 200, r.text
    assert posted["doc_subclass"] == "fnol"
    assert posted["override_doc_type"] == "insurance_claim"


def test_api_review_source_unconfigured():
    src = LangfuseSource(client=FakeClient([make_trace("t1", stage="review")]))
    with TestClient(create_app(src)) as c:
        r = c.get("/api/review/source")
        assert r.status_code == 200
        body = r.json()
        assert body["configured"] is False
        assert "MAILROOM_PIPELINE" in (body.get("error") or "")


def test_api_review_source_proxies(monkeypatch):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    def fake_request(method, url, *, token="", body=None, timeout=8.0):
        if method == "GET" and "/v1/lookup?" in url:
            return {"document": {"doc_id": "doc-src", "original_filename": "claim.txt"}}
        if method == "GET" and "/v1/documents/doc-src/source" in url and "download" not in url:
            return {
                "status": "ok",
                "doc_id": "doc-src",
                "filename": "claim.txt",
                "content_type": "text/plain; charset=utf-8",
                "text": "Dear claims adjuster",
                "truncated": False,
                "bytes": 20,
                "readable": True,
            }
        raise AssertionError(url)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-src", stage="review")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_request):
        with TestClient(create_app(src)) as c:
            r = c.get("/api/review/source", params={"trace_id": "t-src", "filename": "claim.txt"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configured"] is True
    assert "Dear claims adjuster" in body["text"]
    assert body["filename"] == "claim.txt"


def test_api_review_source_download(monkeypatch):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    def fake_json(method, url, *, token="", body=None, timeout=8.0):
        if method == "GET" and "/v1/lookup?" in url:
            return {"document": {"doc_id": "doc-dl", "original_filename": "msa.pdf"}}
        raise AssertionError(url)

    def fake_bytes(method, url, *, token="", timeout=8.0):
        assert "download=1" in url
        assert url.endswith("/v1/documents/doc-dl/source?download=1")
        return b"%PDF-1.4 test", "application/pdf", "msa.pdf"

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-dl")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_json):
        with patch.object(review_actions, "_request_bytes", side_effect=fake_bytes):
            with TestClient(create_app(src)) as c:
                r = c.get("/api/review/source", params={"doc_id": "doc-dl", "download": True})
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
    assert "pdf" in (r.headers.get("content-type") or "")


def test_health_and_meta_surface_pipeline_configured():
    src = LangfuseSource(client=FakeClient([make_trace("t1")]))
    with TestClient(create_app(src)) as c:
        h = c.get("/api/health").json()
        m = c.get("/api/meta").json()
    assert h["pipeline_configured"] is False
    assert m["pipeline_configured"] is False
    assert "insurance_claim" in m["doc_classes"]
    assert "contract" in m["doc_subclasses"]
    assert "license" in m["doc_subclasses"]["contract"]


def test_review_queue_includes_doc_id():
    src = LangfuseSource(client=FakeClient([
        make_trace("t-rev", stage="review", output_extra={"doc_id": "doc-q"}),
    ]))
    with TestClient(create_app(src)) as c:
        r = c.get("/api/review-queue").json()
    assert r["count"] == 1
    assert r["runs"][0]["doc_id"] == "doc-q"


def test_api_review_source_falls_back_to_lookup(monkeypatch):
    """llm-mailroom main has no GET /documents/{id}/source — use catalog JSON."""
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    from mailroom_ui.review_actions import ReviewActionError

    def fake_request(method, url, *, token="", body=None, timeout=8.0):
        if method == "GET" and "/v1/lookup?" in url:
            return {
                "document": {
                    "doc_id": "doc-fb",
                    "original_filename": "claim.txt",
                    "extracted_data": {"claim_number": "CL-9"},
                    "escalation_reason": "low extraction confidence",
                }
            }
        if method == "GET" and "/v1/documents/doc-fb/source" in url:
            raise ReviewActionError("Not Found", status=404)
        raise AssertionError(url)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-fb", stage="review")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_request):
        with TestClient(create_app(src)) as c:
            r = c.get("/api/review/source", params={"trace_id": "t-fb", "filename": "claim.txt"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configured"] is True
    assert body["source"] == "lookup"
    assert body["filename"] == "claim.txt"
    assert "CL-9" in (body.get("text") or "")
    assert "low extraction confidence" in (body.get("text") or "")


def test_api_review_source_download_404_is_honest(monkeypatch):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    from mailroom_ui.review_actions import ReviewActionError

    def fake_json(method, url, *, token="", body=None, timeout=8.0):
        if method == "GET" and "/v1/lookup?" in url:
            return {"document": {"doc_id": "doc-nf", "original_filename": "gone.pdf"}}
        raise AssertionError(url)

    def fake_bytes(method, url, *, token="", timeout=8.0):
        raise ReviewActionError("Not Found", status=404)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-nf")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_json):
        with patch.object(review_actions, "_request_bytes", side_effect=fake_bytes):
            with TestClient(create_app(src)) as c:
                r = c.get("/api/review/source", params={"doc_id": "doc-nf", "download": True})
    assert r.status_code == 404
    assert "no GET /documents" in (r.json().get("error") or "")


def test_api_review_source_catalog_miss_is_200_lookup_miss(monkeypatch):
    """Producer catalog has no record (lookup 404) — tray gets a per-item 200
    state, not a hard HTTP 404 that trips the global error banner."""

    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    from mailroom_ui.review_actions import ReviewActionError

    def fake_request(method, url, *, token="", body=None, timeout=8.0):
        if method == "GET" and "/v1/lookup?" in url:
            raise ReviewActionError("Document not found", status=404)
        raise AssertionError(url)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-miss", stage="review")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_request):
        with TestClient(create_app(src)) as c:
            r = c.get("/api/review/source", params={"trace_id": "t-miss", "filename": "outpatient_1.txt"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configured"] is True
    assert body["readable"] is False
    assert body["source"] == "lookup-miss"
    assert body["text"] is None
    assert "no catalog record" in (body.get("error") or "")


def test_api_review_source_catalog_miss_with_doc_id_falls_back_honestly(monkeypatch):
    """An explicit doc_id the catalog does not know keeps the honest fallback:
    a 200 text-pane payload that says there is no source (download stays 404).

    The lookup-miss payload only applies to trace/filename tray probes — an
    explicit doc_id miss still goes through the source route + catalog fallback.
    """

    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    from mailroom_ui.review_actions import ReviewActionError

    def fake_request(method, url, *, token="", body=None, timeout=8.0):
        if method == "GET" and "/v1/lookup?" in url:
            raise ReviewActionError("Document not found", status=404)
        if method == "GET" and "/v1/documents/doc-unknown/source" in url:
            raise ReviewActionError("Not Found", status=404)
        raise AssertionError(url)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-miss2")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_request):
        with TestClient(create_app(src)) as c:
            r = c.get("/api/review/source", params={"doc_id": "doc-unknown"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["readable"] is False
    assert "no GET /documents" in (body.get("error") or "")


def test_api_review_resolve_complete_forwards_extracted_data(monkeypatch):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    posted = {}

    def fake_request(method, url, *, token="", body=None, timeout=8.0):
        if method == "GET" and "/v1/lookup?" in url:
            return {"document": {"doc_id": "doc-c"}}
        if method == "POST" and url.endswith("/v1/review/doc-c/resolve"):
            posted.update(body or {})
            return {"status": "ok", "doc_id": "doc-c", "disposition": "complete"}
        raise AssertionError(url)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-c", stage="review")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_request):
        with TestClient(create_app(src)) as c:
            r = c.post("/api/review/resolve", json={
                "doc_id": "doc-c",
                "decision": "approved",
                "disposition": "complete",
                "override_doc_type": "contract",
                "extracted_data": {"parties": ["A", "B"]},
            })
    assert r.status_code == 200, r.text
    assert posted["disposition"] == "complete"
    assert posted["override_doc_type"] == "contract"
    assert posted["extracted_data"] == {"parties": ["A", "B"]}


def test_api_review_resolve_complete_rejects_foreign_specialist_fields(monkeypatch):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")

    posted = {}

    def fake_request(method, url, *, token="", body=None, timeout=8.0):
        if method == "GET" and "/v1/lookup?" in url:
            return {"document": {"doc_id": "doc-c", "doc_type": "contract"}}
        if method == "POST":
            posted.update(body or {})
            return {"status": "ok"}
        raise AssertionError(url)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-c", stage="review")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_request):
        with TestClient(create_app(src)) as c:
            r = c.post("/api/review/resolve", json={
                "doc_id": "doc-c",
                "decision": "approved",
                "disposition": "complete",
                "override_doc_type": "contract",
                "extracted_data": {"sender": "A Corp", "parties": ["A", "B"]},
            })
    assert r.status_code == 400, r.text
    assert "another specialist" in (r.json().get("error") or r.text)
    assert posted == {}


def test_producer_urls_honor_empty_api_prefix(monkeypatch):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://pipeline.test:8000")
    monkeypatch.setenv("MAILROOM_PIPELINE_TOKEN", "secret-token")
    monkeypatch.setenv("MAILROOM_PIPELINE_API_PREFIX", "")

    urls = []

    def fake_request(method, url, *, token="", body=None, timeout=8.0):
        urls.append(url)
        if method == "GET" and "/lookup?" in url:
            return {"document": {"doc_id": "doc-u"}}
        if method == "POST" and url.endswith("/review/doc-u/resolve"):
            return {"status": "ok", "doc_id": "doc-u", "disposition": "record"}
        raise AssertionError(url)

    from mailroom_ui import review_actions

    src = LangfuseSource(client=FakeClient([make_trace("t-u")]))
    with patch.object(review_actions, "_request_json", side_effect=fake_request):
        with TestClient(create_app(src)) as c:
            r = c.post("/api/review/resolve", json={
                "doc_id": "doc-u", "decision": "approved", "disposition": "record",
            })
    assert r.status_code == 200, r.text
    assert any(u.endswith("/lookup?doc_id=doc-u") for u in urls)
    assert any(u.endswith("/review/doc-u/resolve") for u in urls)
    assert not any("/v1/" in u for u in urls)
