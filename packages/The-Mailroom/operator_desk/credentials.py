"""Fail-closed operator secrets outside explicit DEV / unsafe mode.

Compose already refuses to start without
``MAILROOM_OPERATOR_JWT_SECRET`` / ``MAILROOM_OPERATOR_ADMIN_PASSWORD``
(``${VAR:?}``). This module is the same gate for bare ``docker run``,
k8s, and ``mailroom-web``: guessable defaults are never used unless the
operator opts in.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("mailroom.operator.credentials")

DEV_JWT_SECRET = "dev-secret-change-me"
DEV_ADMIN_PASSWORD = "changeme"

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_DEV_ENVS = frozenset({"development", "dev", "local"})

_UNSET_JWT_MSG = (
    "MAILROOM_OPERATOR_JWT_SECRET is required outside explicit DEV mode. "
    "Set MAILROOM_OPERATOR_JWT_SECRET (or JWT_SECRET), or opt in with "
    "MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS=1 or MAILROOM_ENV=development."
)
_UNSAFE_JWT_MSG = (
    "MAILROOM_OPERATOR_JWT_SECRET is the known-unsafe local-dev default "
    f"({DEV_JWT_SECRET!r}). Set a dedicated secret, or opt in with "
    "MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS=1 or MAILROOM_ENV=development."
)
_UNSET_PASSWORD_MSG = (
    "MAILROOM_OPERATOR_ADMIN_PASSWORD is required to seed the operator "
    "store outside explicit DEV mode. Set MAILROOM_OPERATOR_ADMIN_PASSWORD, "
    "or opt in with MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS=1 or "
    "MAILROOM_ENV=development."
)
_UNSAFE_PASSWORD_MSG = (
    "MAILROOM_OPERATOR_ADMIN_PASSWORD is the known-unsafe local-dev default "
    f"({DEV_ADMIN_PASSWORD!r}). Set a dedicated password, or opt in with "
    "MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS=1 or MAILROOM_ENV=development."
)


class UnsafeOperatorCredentials(RuntimeError):
    """Missing or guessable operator secrets outside explicit DEV mode."""


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def allow_dev_defaults() -> bool:
    """True only with an explicit local-DX opt-in.

    ``MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS=1`` is the dedicated switch.
    ``MAILROOM_ENV`` / ``MAILROOM_DEPLOY_MODE`` / ``ENV`` in
    ``{development, dev, local}`` also opt in so a local checkout can keep
    a fallback without duplicating compose secrets.
    """
    if _flag("MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS"):
        return True
    env = (
        os.environ.get("MAILROOM_ENV")
        or os.environ.get("MAILROOM_DEPLOY_MODE")
        or os.environ.get("ENV")
        or ""
    ).strip().lower()
    return env in _DEV_ENVS


def configured_jwt_secret() -> str:
    """Return the JWT signing secret, or raise outside DEV mode."""
    secret = (
        os.environ.get("MAILROOM_OPERATOR_JWT_SECRET")
        or os.environ.get("JWT_SECRET")
        or ""
    ).strip()
    if secret == DEV_JWT_SECRET:
        if allow_dev_defaults():
            return DEV_JWT_SECRET
        raise UnsafeOperatorCredentials(_UNSAFE_JWT_MSG)
    if not secret:
        if allow_dev_defaults():
            return DEV_JWT_SECRET
        raise UnsafeOperatorCredentials(_UNSET_JWT_MSG)
    return secret


def configured_admin_password() -> str:
    """Return the admin seed password, or raise outside DEV mode."""
    password = os.environ.get("MAILROOM_OPERATOR_ADMIN_PASSWORD", "").strip()
    if password == DEV_ADMIN_PASSWORD:
        if allow_dev_defaults():
            return DEV_ADMIN_PASSWORD
        raise UnsafeOperatorCredentials(_UNSAFE_PASSWORD_MSG)
    if not password:
        if allow_dev_defaults():
            log.warning(
                "MAILROOM_OPERATOR_ADMIN_PASSWORD unset — seeding the local-dev "
                "default. Set a dedicated password; do not ship with %r.",
                DEV_ADMIN_PASSWORD,
            )
            return DEV_ADMIN_PASSWORD
        raise UnsafeOperatorCredentials(_UNSET_PASSWORD_MSG)
    return password
