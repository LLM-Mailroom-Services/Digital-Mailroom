"""Operator desk (auth, archive, ops, observer) — isolated SQLite, no Langfuse writes."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from operator_desk.db import migrate, upsert_archive_entry
from operator_desk.observer import PipelineEventHandler
from operator_desk.ops import compute_ops_status
from server.main import create_app
from tests.fake_langfuse import FakeClient, make_trace


def _client():
    now = datetime.now(timezone.utc) - timedelta(minutes=10)
    traces = [
        make_trace("t-arch", filename="acme-msa.pdf", stage="archived",
                   base_time=now, verdict="CORRECT"),
        make_trace("t-rev", filename="claim-letter.pdf", stage="review",
                   doc_type="insurance_claim", extract_conf=0.62,
                   base_time=now - timedelta(minutes=5), verdict="PARTIAL"),
    ]
    return TestClient(create_app(LangfuseSource(client=FakeClient(traces))))


def _login(client: TestClient, password: str = "changeme") -> dict:
    r = client.post("/v1/auth/login", json={"username": "admin", "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_login_me_logout_and_rejects_bad_password():
    with _client() as c:
        bad = c.post("/v1/auth/login", json={"username": "admin", "password": "nope"})
        assert bad.status_code == 401
        headers = _login(c)
        me = c.get("/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["username"] == "admin"
        assert me.json()["role"] == "admin"
        denied = c.get("/v1/auth/me")
        assert denied.status_code == 401
        out = c.post("/v1/auth/logout", headers=headers)
        assert out.status_code == 200
        assert out.json()["message"] == "Logged out"


def test_archive_list_download_preview_verify(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MAILROOM_OPERATOR_DB", str(tmp_path / "operator.db"))
    migrate()
    archive = tmp_path / "archive"
    archive.mkdir()
    body = b"hello archive"
    path = archive / "doc-msa.txt"
    path.write_bytes(body)
    upsert_archive_entry(
        doc_id="doc-msa",
        matter_id="matter-1",
        doc_type="contract",
        archive_path=str(path),
        file_size_bytes=len(body),
        checksum_sha256=hashlib.sha256(body).hexdigest(),
    )
    with _client() as c:
        headers = _login(c)
        listed = c.get("/v1/archive/list", headers=headers)
        assert listed.status_code == 200
        rows = listed.json()
        assert len(rows) == 1
        assert rows[0]["doc_id"] == "doc-msa"
        preview = c.get("/v1/archive/doc-msa/preview", headers=headers)
        assert preview.status_code == 200
        assert preview.json()["content"] == "hello archive"
        download = c.get("/v1/archive/doc-msa/download", headers=headers)
        assert download.status_code == 200
        assert download.content == body
        verify = c.get("/v1/archive/doc-msa/verify", headers=headers)
        assert verify.status_code == 200
        assert verify.json()["valid"] is True
        missing = c.get("/v1/archive/no-such/preview", headers=headers)
        assert missing.status_code == 404


def test_archive_path_escape_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MAILROOM_OPERATOR_DB", str(tmp_path / "operator.db"))
    migrate()
    outside = tmp_path.parent / "escaped.txt"
    outside.write_text("nope", encoding="utf-8")
    upsert_archive_entry(
        doc_id="evil",
        matter_id="m",
        doc_type="contract",
        archive_path=str(outside),
    )
    with _client() as c:
        headers = _login(c)
        r = c.get("/v1/archive/evil/preview", headers=headers)
        assert r.status_code == 400


def test_ops_status_from_langfuse_runs_not_documents_table():
    with _client() as c:
        headers = _login(c)
        health = c.get("/v1/ops/health")
        assert health.status_code == 200
        assert health.json()["ok"] is True
        status = c.get("/v1/ops/status", headers=headers)
        assert status.status_code == 200
        body = status.json()
        assert body["source"] == "langfuse"
        assert body["total_docs"] == 2
        assert body["queue_depth"] >= 1
        assert 0 <= body["accuracy"] <= 1
        dist = c.get("/v1/ops/distribution", headers=headers)
        assert dist.status_code == 200
        types = {row["type"] for row in dist.json()["types"]}
        assert "contract" in types or "insurance_claim" in types
        thru = c.get("/v1/ops/throughput", headers=headers)
        assert thru.status_code == 200
        assert len(thru.json()["history"]) == 24


def test_ops_empty_runs_are_zeros_not_perfect_accuracy():
    status = compute_ops_status([])
    assert status.accuracy == 0.0
    assert status.queue_depth == 0
    assert status.total_docs == 0
    assert status.source == "langfuse"


def test_ingest_event_broadcasts_on_pipeline_ws():
    with _client() as c:
        headers = _login(c)
        token = headers["Authorization"].split(" ", 1)[1]
        with c.websocket_connect(f"/ws/pipeline?token={token}") as ws:
            ws.send_json({"action": "subscribe", "matter_id": "matter-9"})
            ack = ws.receive_json()
            assert ack["type"] == "subscribed"
            posted = c.post(
                "/v1/ops/events",
                headers=headers,
                json={
                    "type": "stage_change",
                    "doc_id": "doc-1",
                    "from_stage": "inbox",
                    "to_stage": "processing",
                    "document": {"matter_id": "matter-9"},
                },
            )
            assert posted.status_code == 200
            assert posted.json()["ok"] is True
            event = ws.receive_json()
            assert event["type"] == "stage_change"
            assert event["doc_id"] == "doc-1"


def test_pipeline_ws_rejects_missing_token():
    from starlette.websockets import WebSocketDisconnect

    with _client() as c:
        try:
            with c.websocket_connect("/ws/pipeline"):
                raise AssertionError("unauthenticated websocket should not connect")
        except WebSocketDisconnect as exc:
            assert exc.code == 4401


def test_observer_bin_move_indexes_archive(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MAILROOM_OPERATOR_DB", str(tmp_path / "operator.db"))
    migrate()
    inbox = tmp_path / "pipeline" / "inbox"
    archive = tmp_path / "archive"
    inbox.mkdir(parents=True)
    archive.mkdir(parents=True)
    dest = archive / "doc-inbox.txt"
    dest.write_text("parked", encoding="utf-8")
    events: list[dict] = []
    handler = PipelineEventHandler(events.append)
    handler.on_created(type("E", (), {"src_path": str(inbox / "doc-inbox.txt")})())
    handler.on_moved(type("E", (), {
        "src_path": str(inbox / "doc-inbox.txt"),
        "dest_path": str(dest),
    })())
    kinds = [e["type"] for e in events]
    assert "new_document" in kinds
    assert "stage_change" in kinds
    from operator_desk.db import connect

    conn = connect()
    row = conn.execute("SELECT * FROM archive_index WHERE doc_id = ?", ("doc-inbox",)).fetchone()
    conn.close()
    assert row is not None
    assert Path(row["archive_path"]).is_file()


def test_health_and_meta_surface_operator_module():
    with _client() as c:
        health = c.get("/api/health").json()
        assert health["operator"]["module"] == "operator_desk"
        meta = c.get("/api/meta").json()
        assert meta["operator"]["module"] == "operator_desk"
        paths = {e["path"] for e in meta["endpoints"]}
        assert "/v1/auth/login" in paths
        assert "/ws/pipeline" in paths
        src = c.get("/api/debug/source").json()
        assert src["operator"]["auth"] is True
