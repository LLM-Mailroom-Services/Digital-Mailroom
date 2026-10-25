"""Pure credential policy shared by auth and empty-store bootstrap.

Published defaults require explicit loopback development opt-in. Neither
credential validation nor import of this module prevents display startup.
"""
from __future__ import annotations

import os
from typing import Optional

DEFAULT_JWT_SECRET = "dev-secret-change-me"
DEFAULT_ADMIN_PASSWORD = "changeme"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]"}
_TRUE_VALUES = {"1", "true", "yes", "on"}


def public_bind() -> bool:
    """Hosted editions and non-loopback configured binds are public."""
    edition = os.environ.get("MAILROOM_EDITION", "console").strip().lower()
    if edition in ("hosted", "live", "observatory"):
        return True
    host = os.environ.get("MAILROOM_HOST", "127.0.0.1").strip().lower()
    return host not in _LOOPBACK_HOSTS


def dev_defaults_allowed() -> bool:
    """A development flag can never relax a public bind."""
    enabled = os.environ.get("MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS", "").strip().lower()
    return enabled in _TRUE_VALUES and not public_bind()


def configured_jwt_secret() -> str:
    return (
        os.environ.get("MAILROOM_OPERATOR_JWT_SECRET")
        or os.environ.get("JWT_SECRET")
        or ""
    ).strip()


def bootstrap_password() -> Optional[str]:
    """Unsafe/missing seed settings leave the empty store unconfigured."""
    password = os.environ.get("MAILROOM_OPERATOR_ADMIN_PASSWORD", "")
    if password.strip() and password.strip() != DEFAULT_ADMIN_PASSWORD:
        return password
    if dev_defaults_allowed():
        return password if password.strip() else DEFAULT_ADMIN_PASSWORD
    return None
