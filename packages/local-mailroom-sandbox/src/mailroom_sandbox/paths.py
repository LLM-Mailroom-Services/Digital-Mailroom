"""Filesystem roots for the local-mailroom-sandbox checkout."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Resolve the sandbox checkout root.

    Walks up from this file looking for ``pyproject.toml``. ``SANDBOX_ROOT``
    wins when set (tests, relocated installs).
    """
    env = os.environ.get("SANDBOX_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "config").is_dir():
            return candidate
    return Path.cwd()


def config_dir() -> Path:
    return repo_root() / "config"


def profiles_dir() -> Path:
    return config_dir() / "profiles"


def prompts_dir() -> Path:
    return config_dir() / "prompts"


def deploy_dir() -> Path:
    return repo_root() / "deploy"


def data_dir() -> Path:
    return Path(os.environ.get("MAILROOM_BASE_DIR") or (repo_root() / "data")).resolve()


def fixtures_dir() -> Path:
    return repo_root() / "data" / "fixtures"


def runtime_dir() -> Path:
    path = data_dir() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def reports_dir() -> Path:
    path = repo_root() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def vendor_dir() -> Path:
    return repo_root() / "vendor"


def vendored_mailroom_src() -> Path | None:
    """Tracked llm-mailroom snapshot (DMR-057) or None when pruned."""
    cand = vendor_dir() / "llm-mailroom" / "src"
    return cand if (cand / "pipeline" / "config.py").is_file() else None


def vendored_dojo_src() -> Path | None:
    """Tracked llm-dojo-scoring snapshot (DMR-057) or None when pruned."""
    cand = vendor_dir() / "llm-dojo-scoring" / "src"
    return cand if (cand / "llm_dojo_scoring" / "__init__.py").is_file() else None
