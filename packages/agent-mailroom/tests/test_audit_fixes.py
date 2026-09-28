"""Regression pins for the 2026-09-28 agent-mailroom bug sweep."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from agent_mailroom.api.app import create_app


def _upload(client, samples: Path, name: str, matter: str = "DEFAULT", headers=None):
    return client.post(
        "/upload",
        files={"file": (name, (samples / name).read_bytes(), "text/plain")},
        data={"matter_id": matter},
        headers=headers or {},
    )


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.mark.parametrize("matter", ["../../../ESCAPED", "/abs/path", "..", "a/b"])
def test_upload_rejects_path_like_matter_id(client, samples, matter):
    res = _upload(client, samples, "acme_claim.txt", matter=matter)
    assert res.status_code == 400
    base = Path(os.environ["MAILROOM_BASE_DIR"])
    assert not any("ESCAPED" in str(p) for p in base.parent.rglob("*"))


def test_archive_dir_refuses_traversal():
    from agent_mailroom.pipeline.bins import archive_dir

    with pytest.raises(ValueError):
        archive_dir("../x", "contract")
    assert archive_dir("MATTER-1", "contract").is_dir()


def test_ws_requires_api_token_when_set(monkeypatch):
    monkeypatch.setenv("MAILROOM_API_TOKEN", "sekret")
    with TestClient(create_app()) as c:
        with pytest.raises(WebSocketDisconnect) as exc:
            with c.websocket_connect("/ws"):
                pass
        assert exc.value.code == 1008
        with c.websocket_connect("/ws?token=sekret"):
            pass


def test_resume_moves_parked_file_out_of_review(client, samples):
    from agent_mailroom.pipeline.bins import locate_document, review_dir

    doc_id = _upload(client, samples, "ambiguous_memo.txt").json()["doc_id"]
    assert client.get(f"/status/{doc_id}").json()["stage"] == "review"
    client.post(
        f"/review/{doc_id}/resolve",
        json={"decision": "approved", "disposition": "resume", "doc_type": "correspondence"},
    )
    stage = client.get(f"/status/{doc_id}").json()["stage"]
    assert stage != "review"
    assert not list(review_dir().glob(f"{doc_id}--*"))
    assert locate_document(doc_id)["bin"] != "review"
    if stage == "archived":
        # A reject after the resume must not flip the archived doc to failed.
        res = client.post(f"/review/{doc_id}/resolve", json={"decision": "rejected"})
        assert res.status_code == 409
        assert client.get(f"/status/{doc_id}").json()["stage"] == "archived"


def test_resolve_non_review_doc_is_409_but_record_still_works(client, samples):
    doc_id = _upload(client, samples, "acme_claim.txt").json()["doc_id"]
    assert client.get(f"/status/{doc_id}").json()["stage"] == "archived"
    res = client.post(f"/review/{doc_id}/resolve", json={"decision": "approved", "disposition": "resume"})
    assert res.status_code == 409
    res = client.post(
        f"/review/{doc_id}/resolve",
        json={"decision": "approved", "disposition": "record", "notes": "annotated"},
    )
    assert res.status_code == 200


def test_requeue_keeps_original_filename(client, samples):
    doc_id = _upload(client, samples, "ambiguous_memo.txt").json()["doc_id"]
    new = client.post(
        f"/review/{doc_id}/resolve", json={"decision": "approved", "disposition": "requeue"}
    ).json()
    assert client.get(f"/status/{new['doc_id']}").json()["original_filename"] == "ambiguous_memo.txt"


def test_glob_metacharacters_in_doc_id_match_nothing(client, samples):
    _upload(client, samples, "ambiguous_memo.txt")
    assert client.get("/documents/*/source").status_code == 404


def test_stuck_documents_detected_same_day():
    from agent_mailroom.schemas.manifest import DocumentManifest, PipelineStage
    from agent_mailroom.storage.catalog import stuck_documents, upsert_document
    from agent_mailroom.storage.db import connect

    upsert_document(
        DocumentManifest(
            doc_id="stuck-doc",
            matter_id="M",
            original_filename="a.txt",
            stage=PipelineStage.PROCESSING,
        )
    )
    old = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
    with connect() as conn:
        conn.execute("UPDATE documents SET updated_at = ? WHERE doc_id = 'stuck-doc'", (old,))
        conn.commit()
    assert [row["doc_id"] for row in stuck_documents(15)] == ["stuck-doc"]
