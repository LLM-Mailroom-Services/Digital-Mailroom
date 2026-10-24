import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# Sibling llm-mailroom's editable install puts `src/` on sys.path; that
# `scripts` package must not shadow this repo's `scripts/` directory.
# mailroom_ui.producer imports pipeline.review_resolve from site-packages
# (extra `[pipeline]`) or a temporary checkout path that is removed after load.
# In the mailroom-hub monorepo the llm-mailroom path on sys.path IS the
# workspace member (uv-managed editable install) — keep it so lazy imports in
# pipeline.review_resolve (observability.*) resolve; ROOT at sys.path[0] still
# protects `scripts/`. Standalone checkouts keep the full strip.
_MONOREPO = (ROOT.parent / "llm-mailroom").is_dir() and (
    (ROOT.parent.parent / "uv.lock").is_file() or (ROOT.parent / "uv.lock").is_file()
)
if not _MONOREPO:
    sys.path[:] = [p for p in sys.path if "llm-mailroom" not in Path(p).as_posix()]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolate_operator_desk(tmp_path, monkeypatch):
    """Each test gets its own operator SQLite + bins; never write repo ``data/``."""
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MAILROOM_OPERATOR_DB", str(tmp_path / "operator.db"))
    monkeypatch.setenv("MAILROOM_OPERATOR_JWT_SECRET", "test-operator-secret")
    monkeypatch.setenv("MAILROOM_OPERATOR_ADMIN_USER", "admin")
    monkeypatch.setenv("MAILROOM_OPERATOR_ADMIN_PASSWORD", "changeme")
    monkeypatch.setenv("MAILROOM_OPERATOR_AUTH", "1")
    monkeypatch.setenv("MAILROOM_OBSERVER", "0")
    monkeypatch.delenv("MAILROOM_OPERATOR_INGEST_TOKEN", raising=False)
    # Local (loopback) bind by default; public-bind tests opt in explicitly.
    monkeypatch.delenv("MAILROOM_EDITION", raising=False)
    monkeypatch.delenv("MAILROOM_HOST", raising=False)
    monkeypatch.delenv("MAILROOM_UI_DIST", raising=False)
    monkeypatch.setenv("MAILROOM_TRACE_CACHE_DIR", str(tmp_path / "trace-cache"))
