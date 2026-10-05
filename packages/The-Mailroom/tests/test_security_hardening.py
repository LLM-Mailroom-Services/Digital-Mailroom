"""Security hardening (0.5.0 audit): public binds fail closed, writes are
CSRF-safe and role-gated, headers are injection-safe."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from mailroom_ui.review_actions import content_disposition
from operator_desk.db import upsert_archive_entry
from server.main import create_app
from tests.fake_langfuse import FakeClient, make_trace


# Generated per run: a rotated (non-default) admin password for public-bind
# tests. Never a literal — secret scanners rightly flag hardcoded passwords.
ROTATED_ADMIN_PASSWORD = secrets.token_urlsafe(16)


def _app():
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    traces = [make_trace("t-rev", stage="review", base_time=now, verdict="PARTIAL")]
    return create_app(LangfuseSource(client=FakeClient(traces)))


def _login(c: TestClient, password: str = "changeme"):
    return c.post("/v1/auth/login", json={"username": "admin", "password": password})


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _forge(secret: str, payload: dict) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps(payload).encode())
    sig = hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64(sig)}"


# ------------------------------------------------------------ fail closed

def test_public_bind_with_default_secret_refuses_login(monkeypatch):
    monkeypatch.setenv("MAILROOM_EDITION", "hosted")
    monkeypatch.delenv("MAILROOM_OPERATOR_JWT_SECRET", raising=False)
    with TestClient(_app()) as c:
        assert _login(c).status_code == 503


def test_public_bind_with_default_admin_password_refuses_login(monkeypatch):
    monkeypatch.setenv("MAILROOM_HOST", "0.0.0.0")
    with TestClient(_app()) as c:  # conftest: admin/changeme
        assert _login(c).status_code == 503


def test_public_bind_with_real_credentials_logs_in(monkeypatch):
    monkeypatch.setenv("MAILROOM_EDITION", "hosted")
    monkeypatch.setenv("MAILROOM_OPERATOR_ADMIN_PASSWORD", ROTATED_ADMIN_PASSWORD)
    with TestClient(_app()) as c:
        assert _login(c, ROTATED_ADMIN_PASSWORD).status_code == 200


def test_forged_default_secret_token_rejected_on_public_bind(monkeypatch):
    monkeypatch.setenv("MAILROOM_EDITION", "hosted")
    monkeypatch.delenv("MAILROOM_OPERATOR_JWT_SECRET", raising=False)
    token = _forge("dev-secret-change-me", {"sub": "x", "role": "admin",
                                             "exp": int(time.time()) + 3600})
    with TestClient(_app()) as c:
        r = c.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


def test_token_without_exp_is_rejected():
    token = _forge("test-operator-secret", {"sub": "admin", "role": "admin"})
    with TestClient(_app()) as c:
        r = c.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


def test_unknown_user_login_is_401():
    with TestClient(_app()) as c:
        r = c.post("/v1/auth/login", json={"username": "ghost", "password": "x"})
        assert r.status_code == 401


# ------------------------------------------------------------ write guard

def test_cross_origin_browser_write_is_refused():
    with TestClient(_app()) as c:
        r = c.post("/api/review/resolve", json={"decision": "approve", "trace_id": "t-rev"},
                   headers={"Origin": "https://evil.example"})
        assert r.status_code == 403


def test_same_origin_write_passes_guard_locally():
    with TestClient(_app()) as c:
        r = c.post("/api/review/resolve", json={"decision": "approve", "trace_id": "t-rev"},
                   headers={"Origin": "http://testserver"})
        # Guard passed; the producer is unconfigured, so the proxy answers.
        assert r.status_code != 403


def test_public_bind_write_requires_reviewer_login(monkeypatch):
    monkeypatch.setenv("MAILROOM_EDITION", "hosted")
    monkeypatch.setenv("MAILROOM_OPERATOR_ADMIN_PASSWORD", ROTATED_ADMIN_PASSWORD)
    with TestClient(_app()) as c:
        anon = c.post("/api/review/resolve", json={"decision": "approve", "trace_id": "t-rev"})
        assert anon.status_code == 401
        up = c.post("/api/inbox/enqueue", files={"file": ("a.txt", b"hi", "text/plain")})
        assert up.status_code == 401
        token = _login(c, ROTATED_ADMIN_PASSWORD).json()["access_token"]
        ok = c.post("/api/review/resolve", json={"decision": "approve", "trace_id": "t-rev"},
                    headers={"Authorization": f"Bearer {token}"})
        assert ok.status_code not in (401, 403)


def test_wildcard_cors_does_not_preflight_posts():
    with TestClient(_app()) as c:
        r = c.options("/api/review/resolve", headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        })
        assert "POST" not in (r.headers.get("access-control-allow-methods") or "")


def test_debug_client_report_is_size_capped():
    with TestClient(_app()) as c:
        r = c.post("/api/debug/client", json={"events": ["x" * 1024] * 100})
        assert r.status_code == 413


def test_invalid_base64_upload_is_rejected():
    with TestClient(_app()) as c:
        r = c.post("/api/inbox/enqueue", json={"filename": "a.txt", "content_base64": "aGk!!@@"})
        assert r.status_code == 400


# ------------------------------------------------------------ archive roles

def test_viewer_cannot_download_archives(tmp_path):
    from operator_desk.auth import create_access_token

    doc = tmp_path / "archive" / "doc.txt"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("secret")
    with TestClient(_app()) as c:
        upsert_archive_entry(doc_id="d1", archive_path=str(doc), matter_id="M1",
                             doc_type="contract",
                             checksum_sha256=hashlib.sha256(b"secret").hexdigest())
        viewer = create_access_token("v", "viewer")
        r = c.get("/v1/archive/d1/download", headers={"Authorization": f"Bearer {viewer}"})
        assert r.status_code == 403


def test_archive_row_pointing_at_operator_db_is_refused(tmp_path):
    with TestClient(_app()) as c:
        token = _login(c).json()["access_token"]
        upsert_archive_entry(doc_id="d-db", archive_path=str(tmp_path / "operator.db"),
                             matter_id="M1", doc_type="contract")
        r = c.get("/v1/archive/d-db/download", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 400


# ------------------------------------------------------------ headers

def test_content_disposition_is_latin1_safe_and_quote_safe():
    header = content_disposition('résumé "final".pdf')
    header.encode("latin-1")
    assert '"final"' not in header
    assert "filename*=UTF-8''r%C3%A9sum%C3%A9" in header
