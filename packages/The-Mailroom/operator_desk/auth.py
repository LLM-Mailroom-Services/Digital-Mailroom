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
import threading
from functools import lru_cache
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .credentials import (
    DEFAULT_ADMIN_PASSWORD, DEFAULT_JWT_SECRET, configured_jwt_secret,
    dev_defaults_allowed, public_bind,
)
from .db import admin_users, lookup_user, migrate, verify_password, write_audit

log = logging.getLogger("mailroom.operator.auth")

router = APIRouter(prefix="/v1/auth", tags=["operator-auth"])
security = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"
ROLE_RANK = {"viewer": 0, "reviewer": 1, "admin": 2}
_warned_default_secret = False


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


def _configured_secret() -> str:
    return configured_jwt_secret()


_ADMIN_HASH_LOCK = threading.RLock()


@lru_cache(maxsize=256)
def _uses_default_admin_password(stored_hash: str) -> bool:
    """Cache only an exact stored hash; password rotation changes the key."""
    return verify_password(DEFAULT_ADMIN_PASSWORD, stored_hash)


def insecure_config_reasons() -> list[str]:
    """Unsafe persisted/configured credentials, independent of seed settings."""
    reasons: list[str] = []
    secret = _configured_secret()
    if not secret or secret == DEFAULT_JWT_SECRET:
        reasons.append("MAILROOM_OPERATOR_JWT_SECRET is unset (public default secret)")
    # Seed environment values never rotate existing accounts. Check the
    # actual admins even if a later restart changes the seed name/password.
    try:
        rows = admin_users()
        if not rows:
            reasons.append("operator store has no admin account")
    except Exception:  # store unavailable: assume the worst
        rows = []
        reasons.append("operator store unreadable")
    # Serialize cache misses so concurrent anonymous requests cannot repeat
    # the same expensive KDF. Read current rows every time; rotations and
    # added admins therefore invalidate by their exact new stored hashes.
    with _ADMIN_HASH_LOCK:
        for row in rows:
            if _uses_default_admin_password(row["password_hash"]):
                reasons.append(f"operator user {row['username']!r} still has the default password")
    return reasons


def locked_down() -> bool:
    """Defaults are usable only with explicit loopback development opt-in."""
    return not dev_defaults_allowed() and bool(insecure_config_reasons())


def jwt_secret() -> str:
    global _warned_default_secret
    secret = _configured_secret()
    if secret and secret != DEFAULT_JWT_SECRET:
        return secret
    if not dev_defaults_allowed():
        raise HTTPException(
            status_code=503,
            detail="Operator auth is not configured (set MAILROOM_OPERATOR_JWT_SECRET).",
        )
    if not _warned_default_secret:
        log.warning(
            "Operator development credentials explicitly enabled on loopback; "
            "set MAILROOM_OPERATOR_JWT_SECRET for regular use."
        )
        _warned_default_secret = True
    return DEFAULT_JWT_SECRET


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
    try:
        secret = jwt_secret()
    except HTTPException as exc:
        raise HTTPException(status_code=401, detail="Operator auth not configured on this host") from exc
    if locked_down():
        # A previously issued token cannot bypass unsafe persisted admin credentials.
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
        log.error("operator login refused: %s", "; ".join(reasons))
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
