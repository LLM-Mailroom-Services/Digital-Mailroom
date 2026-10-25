"""Source-derived credential policy regressions; offline real auth and SQLite."""
import secrets

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from mailroom_ui.langfuse_source import LangfuseSource
from operator_desk import auth, db
from server.main import create_app
from tests.fake_langfuse import FakeClient


def client():
    return TestClient(create_app(LangfuseSource(client=FakeClient([]))))


def login(c, password="changeme"):
    return c.post("/v1/auth/login", json={"username": "admin", "password": password})


def no_dev(monkeypatch):
    monkeypatch.delenv("MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS", raising=False)


def unconfigured(monkeypatch):
    no_dev(monkeypatch)
    for name in ("MAILROOM_OPERATOR_JWT_SECRET", "JWT_SECRET", "MAILROOM_OPERATOR_ADMIN_PASSWORD"):
        monkeypatch.delenv(name, raising=False)


def test_unconfigured_loopback_preserves_display_but_refuses_login(monkeypatch):
    unconfigured(monkeypatch)
    with client() as c:
        assert c.get("/health").status_code == 200
        assert c.get("/api/traces").status_code == 200
        assert c.get("/").status_code == 200
        assert login(c).status_code == 503
        assert db.lookup_user("admin") is None


@pytest.mark.parametrize("password", [None, "", "   ", "changeme"])
def test_unsafe_bootstrap_password_is_not_persisted_without_dev_optin(monkeypatch, password):
    no_dev(monkeypatch)
    if password is None:
        monkeypatch.delenv("MAILROOM_OPERATOR_ADMIN_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("MAILROOM_OPERATOR_ADMIN_PASSWORD", password)
    db.migrate()
    assert db.lookup_user("admin") is None


@pytest.mark.parametrize("secret", [None, "", "   ", "dev-secret-change-me"])
def test_missing_or_published_secret_cannot_mint_without_dev_optin(monkeypatch, secret):
    no_dev(monkeypatch)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    if secret is None:
        monkeypatch.delenv("MAILROOM_OPERATOR_JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("MAILROOM_OPERATOR_JWT_SECRET", secret)
    with pytest.raises(HTTPException) as caught:
        auth.create_access_token("admin", "admin")
    assert caught.value.status_code == 503


def test_explicit_loopback_dev_optin_can_login_with_published_defaults(monkeypatch):
    unconfigured(monkeypatch)
    monkeypatch.setenv("MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS", "1")
    with client() as c:
        response = login(c)
        assert response.status_code == 200
        assert db.verify_password("changeme", db.lookup_user("admin")["password_hash"])
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        assert c.get("/v1/auth/me", headers=headers).status_code == 200


@pytest.mark.parametrize("public_env", [("MAILROOM_EDITION", "hosted"), ("MAILROOM_HOST", "0.0.0.0"), ("MAILROOM_HOST", "")])
def test_public_dev_flag_cannot_seed_or_use_defaults(monkeypatch, public_env):
    unconfigured(monkeypatch)
    monkeypatch.setenv("MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS", "1")
    monkeypatch.setenv(*public_env)
    with client() as c:
        assert c.get("/health").status_code == 200
        assert login(c).status_code == 503
        assert db.lookup_user("admin") is None


def test_disabling_dev_optin_does_not_rotate_existing_default_admin(monkeypatch):
    monkeypatch.setenv("MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS", "1")
    db.migrate()
    before = db.lookup_user("admin")["password_hash"]
    no_dev(monkeypatch)
    with client() as c:
        assert login(c).status_code == 503
        assert db.lookup_user("admin")["password_hash"] == before


def test_nondefault_credentials_work_without_dev_optin_and_seed_env_cannot_rotate(monkeypatch):
    no_dev(monkeypatch)
    password = secrets.token_urlsafe(24)
    monkeypatch.setenv("MAILROOM_OPERATOR_ADMIN_PASSWORD", password)
    db.migrate()
    before = db.lookup_user("admin")["password_hash"]
    monkeypatch.delenv("MAILROOM_OPERATOR_ADMIN_PASSWORD", raising=False)
    with client() as c:
        assert login(c, password).status_code == 200
        assert db.lookup_user("admin")["password_hash"] == before


def test_legacy_jwt_secret_alias_with_rotated_credentials_still_works(monkeypatch):
    no_dev(monkeypatch)
    monkeypatch.delenv("MAILROOM_OPERATOR_JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_SECRET", secrets.token_urlsafe(32))
    password = secrets.token_urlsafe(24)
    monkeypatch.setenv("MAILROOM_OPERATOR_ADMIN_PASSWORD", password)
    with client() as c:
        assert login(c, password).status_code == 200


def test_default_admin_blocks_login_token_use_and_ws_on_public_bind_even_with_dev_flag(monkeypatch):
    monkeypatch.setenv("MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS", "1")
    db.migrate()
    token = auth.create_access_token("admin", "admin")
    monkeypatch.setenv("MAILROOM_HOST", "0.0.0.0")
    headers = {"Authorization": "Bearer " + token}
    with client() as c:
        assert login(c).status_code == 503
        assert c.get("/v1/auth/me", headers=headers).status_code == 401
        assert c.post("/api/review/resolve", json={"decision": "approve", "trace_id": "x"}, headers=headers).status_code == 401
        with pytest.raises(WebSocketDisconnect) as caught:
            with c.websocket_connect("/ws/pipeline?token=" + token):
                pass
        assert caught.value.code == 4401
