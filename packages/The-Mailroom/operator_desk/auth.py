"""JWT auth for the operator desk.

Mount: ``app.include_router(router)`` → ``/v1/auth``. Display ``/api/*``
routes stay open — this gate is only for archive / ops / pipeline WS.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .db import lookup_user, migrate, verify_password, write_audit

log = logging.getLogger("mailroom.operator.auth")

router = APIRouter(prefix="/v1/auth", tags=["operator-auth"])
security = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"
DEFAULT_JWT_SECRET = "dev-secret-change-me"
DEFAULT_ADMIN_PASSWORD = "changeme"
ROLE_RANK = {"viewer": 0, "reviewer": 1, "admin": 2}
_warned_default_secret = False
_LOOPBACK_HOSTS = {"", "127.0.0.1", "localhost", "::1", "[::1]"}


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserProfile(BaseModel):
    username: str
    role: str
    user_id: Optional[int] = None


def auth_required() -> bool:
    raw = os.environ.get("MAILROOM_OPERATOR_AUTH", "1").strip().lower()
    return raw not in ("0", "false", "off", "no")


def public_bind() -> bool:
    """True when this process is reachable beyond the local machine.

    The hosted edition (Observatory, HF Space, Railway) and any non-loopback
    ``MAILROOM_HOST`` count as public: local-dev defaults are refused there.
    """
    edition = os.environ.get("MAILROOM_EDITION", "console").strip().lower()
    if edition in ("hosted", "live", "observatory"):
        return True
    host = os.environ.get("MAILROOM_HOST", "127.0.0.1").strip().lower()
    return host not in _LOOPBACK_HOSTS


def _configured_secret() -> str:
    return (
        os.environ.get("MAILROOM_OPERATOR_JWT_SECRET")
        or os.environ.get("JWT_SECRET")
        or ""
    ).strip()


def insecure_config_reasons() -> list[str]:
    """Local-dev defaults that make operator auth forgeable when public."""
    reasons: list[str] = []
    secret = _configured_secret()
    if not secret or secret == DEFAULT_JWT_SECRET:
        reasons.append("MAILROOM_OPERATOR_JWT_SECRET is unset (public default secret)")
    password = os.environ.get("MAILROOM_OPERATOR_ADMIN_PASSWORD")
    if password is None or password.strip() in ("", DEFAULT_ADMIN_PASSWORD):
        # Env unset means the seeded admin (if still present) uses the
        # published default unless it was rotated in the store.
        username = os.environ.get("MAILROOM_OPERATOR_ADMIN_USER", "admin").strip() or "admin"
        try:
            row = lookup_user(username)
        except Exception:  # store unavailable: assume the worst
            row = None
            reasons.append("operator store unreadable")
        if row is not None and verify_password(DEFAULT_ADMIN_PASSWORD, row["password_hash"]):
            reasons.append(f"operator user {username!r} still has the default password")
    return reasons


def locked_down() -> bool:
    """Public bind + forgeable defaults: refuse to issue or honour tokens."""
    return auth_required() and public_bind() and bool(insecure_config_reasons())


def jwt_secret() -> str:
    global _warned_default_secret
    secret = _configured_secret()
    if not secret:
        secret = DEFAULT_JWT_SECRET
        if not _warned_default_secret:
            log.warning(
                "MAILROOM_OPERATOR_JWT_SECRET unset — using the local-dev default. "
                "Set a dedicated secret; do not reuse MAILROOM_PIPELINE_TOKEN."
            )
            _warned_default_secret = True
    return secret


def jwt_expiry_hours() -> int:
    try:
        return max(1, int(os.environ.get("MAILROOM_OPERATOR_JWT_HOURS", "24")))
    except ValueError:
        return 24


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def create_access_token(username: str, role: str, user_id: Optional[int] = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "uid": user_id,
        "exp": int((now + timedelta(hours=jwt_expiry_hours())).timestamp()),
        "iat": int(now.timestamp()),
    }
    try:
        import jwt

        return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM)
    except ImportError:
        header = _b64url(json.dumps({"alg": JWT_ALGORITHM, "typ": "JWT"}).encode())
        body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
        signing = f"{header}.{body}"
        sig = hmac.new(jwt_secret().encode("utf-8"), signing.encode("ascii"), hashlib.sha256).digest()
        return f"{signing}.{_b64url(sig)}"


def decode_token(token: str) -> UserProfile:
    secret = jwt_secret()
    if public_bind() and secret == DEFAULT_JWT_SECRET:
        # Anyone can mint a token with the published default secret.
        raise HTTPException(status_code=401, detail="Operator auth not configured on this host")
    try:
        import jwt
        from jwt import ExpiredSignatureError, InvalidTokenError

        try:
            payload = jwt.decode(
                token, secret, algorithms=[JWT_ALGORITHM],
                options={"require": ["exp", "sub"]},
            )
        except ExpiredSignatureError as exc:
            raise HTTPException(status_code=401, detail="Token expired") from exc
        except InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc
    except ImportError:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=401, detail="Invalid token")
        signing = f"{parts[0]}.{parts[1]}"
        expected = hmac.new(secret.encode("utf-8"), signing.encode("ascii"), hashlib.sha256).digest()
        try:
            actual = _b64url_decode(parts[2])
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc
        if not hmac.compare_digest(expected, actual):
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            payload = json.loads(_b64url_decode(parts[1]))
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc
        exp = payload.get("exp") if isinstance(payload, dict) else None
        if not isinstance(exp, (int, float)):
            # Tokens without an expiry would be valid forever.
            raise HTTPException(status_code=401, detail="Invalid token")
        if datetime.now(timezone.utc).timestamp() > float(exp):
            raise HTTPException(status_code=401, detail="Token expired")
    username = str(payload.get("sub") or "")
    role = str(payload.get("role") or "viewer")
    if role not in ROLE_RANK:
        role = "viewer"
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = payload.get("uid")
    return UserProfile(
        username=username,
        role=role,
        user_id=int(uid) if isinstance(uid, int) else None,
    )


def ingest_token() -> str:
    return os.environ.get("MAILROOM_OPERATOR_INGEST_TOKEN", "").strip()


def _anonymous() -> UserProfile:
    return UserProfile(username="anonymous", role="viewer")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserProfile:
    if not auth_required():
        if credentials:
            try:
                return decode_token(credentials.credentials)
            except HTTPException:
                return _anonymous()
        return _anonymous()
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    return decode_token(credentials.credentials)


async def get_current_user_or_ingest(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserProfile:
    """Bearer JWT *or* the shared ingest token used by mailroom-observer."""
    token = ingest_token()
    if credentials and token and hmac.compare_digest(credentials.credentials, token):
        return UserProfile(username="observer", role="admin")
    return await get_current_user(credentials)


def require_role(min_role: str):
    """Dependency factory: the caller's role must rank at least ``min_role``.

    With auth disabled (``MAILROOM_OPERATOR_AUTH=0``, a local-trust setting)
    the anonymous caller is allowed through, as before.
    """
    needed = ROLE_RANK[min_role]

    async def _dep(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> UserProfile:
        user = await get_current_user_or_ingest(credentials)
        if not auth_required():
            return user
        if ROLE_RANK.get(user.role, 0) < needed:
            raise HTTPException(status_code=403, detail=f"{min_role} role required")
        return user

    return _dep


# Verified against when the username does not exist, so a miss costs the same
# as a wrong password (no username enumeration through response timing).
_DUMMY_HASH: Optional[str] = None


def _dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        from .db import hash_password

        _DUMMY_HASH = hash_password("not-a-real-account-" + os.urandom(8).hex())
    return _DUMMY_HASH


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    migrate()
    if locked_down():
        reasons = insecure_config_reasons()
        log.error("operator login refused on a public bind: %s", "; ".join(reasons))
        raise HTTPException(
            status_code=503,
            detail="Operator auth is not configured on this host "
                   "(set MAILROOM_OPERATOR_JWT_SECRET and rotate the admin password).",
        )
    row = lookup_user(req.username)
    if not row:
        verify_password(req.password, _dummy_hash())
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(row["username"], row["role"], user_id=row["id"])
    write_audit(action="login", user_id=row["id"], metadata={"username": row["username"]})
    return TokenResponse(access_token=token, role=row["role"])


@router.get("/me", response_model=UserProfile)
async def me(user: UserProfile = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(user: UserProfile = Depends(get_current_user)):
    write_audit(action="logout", user_id=user.user_id, metadata={"username": user.username})
    return {"message": "Logged out"}
