"""Fake llm-mailroom producer + working REVIEW-tray demo."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.fake_producer import DEMO_TOKEN, FakeProducerStore, create_fake_producer


def _auth():
    return {"Authorization": f"Bearer {DEMO_TOKEN}"}


def test_fake_producer_v1_lookup_and_resolve():
    store = FakeProducerStore()
    with TestClient(create_fake_producer(store)) as c:
        assert c.get("/v1/health").json()["status"] == "ok"
        r = c.get("/v1/lookup", params={"trace_id": "tray-review"}, headers=_auth())
        assert r.status_code == 200
        doc = r.json()["document"]
        assert doc["doc_id"] == "doc-merger-42"
        assert doc["original_filename"].endswith(".pdf")
        assert "extracted_data" in doc
        assert c.get("/v1/documents/doc-merger-42/source", headers=_auth()).status_code == 404
        posted = c.post(
            "/v1/review/doc-merger-42/resolve",
            headers=_auth(),
            json={
                "decision": "approved",
                "disposition": "resume",
                "override_doc_type": "merger_agreement",
                "notes": "ok",
            },
        )
        assert posted.status_code == 200, posted.text
        body = posted.json()
        assert body["disposition"] == "resume"
        assert body["resume"]["doc_type"] == "merger_agreement"


def test_fake_producer_complete_requires_extracted_data():
    store = FakeProducerStore()
    with TestClient(create_fake_producer(store)) as c:
        missing = c.post(
            "/v1/review/doc-claim-fnol/resolve",
            headers=_auth(),
            json={"decision": "approved", "disposition": "complete"},
        )
        assert missing.status_code == 400
        ok = c.post(
            "/v1/review/doc-claim-fnol/resolve",
            headers=_auth(),
            json={
                "decision": "approved",
                "disposition": "complete",
                "extracted_data": {
                    "claim_number": "CL-4419",
                    "coverage_determination": "approved",
                },
            },
        )
        assert ok.status_code == 200
        assert ok.json()["disposition"] == "complete"
        assert store.documents["doc-claim-fnol"]["stage"] == "archived"


def test_fake_producer_complete_rejects_foreign_specialist_fields():
    store = FakeProducerStore()
    with TestClient(create_fake_producer(store)) as c:
        bad = c.post(
            "/v1/review/doc-merger-42/resolve",
            headers=_auth(),
            json={
                "decision": "approved",
                "disposition": "complete",
                "extracted_data": {"sender": "A Corp", "parties": ["A", "B"]},
            },
        )
        assert bad.status_code == 400
        assert "another specialist" in (bad.json().get("detail") or bad.text)


def test_fake_producer_record_on_reconsider():
    with TestClient(create_fake_producer()) as c:
        r = c.post(
            "/v1/review/doc-claim-miss/resolve",
            headers=_auth(),
            json={"decision": "approved", "disposition": "record", "notes": "paper"},
        )
        assert r.status_code == 200
        audit = c.get("/v1/audit/doc-claim-miss", headers=_auth()).json()
        assert audit["count"] >= 1


def test_demo_review_tray_check_mode(capsys):
    import sys
    import scripts.demo_review_tray as mod

    old = sys.argv
    sys.argv = ["demo_review_tray.py", "--check"]
    try:
        mod.main()
    finally:
        sys.argv = old
    out = capsys.readouterr().out
    assert "check ok" in out
    assert "tray-review" in out
    assert "doc-merger-42" in out
    assert "doc-claim-fnol" in out


def test_demo_review_tray_check_api(capsys):
    import sys
    import scripts.demo_review_tray as mod

    old = sys.argv
    sys.argv = ["demo_review_tray.py", "--check-api"]
    try:
        mod.main()
    finally:
        sys.argv = old
    out = capsys.readouterr().out
    assert "check-api ok" in out
    assert "complete" in out
