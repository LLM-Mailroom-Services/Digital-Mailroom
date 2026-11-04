"""Pytest hooks for the sandbox suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mailroom_sandbox.paths import repo_root

# Set before any test, so subprocesses inherit it too: a key in .env can bill real calls.
os.environ["SANDBOX_SKIP_DOTENV"] = "1"
os.environ.pop("OPENROUTER_API_KEY", None)
# A commit hook exports these, and `git init` in a test would then rewrite the real repo's config.
for _name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX"):
    os.environ.pop(_name, None)


@pytest.fixture(autouse=True)
def _sandbox_root(monkeypatch):
    monkeypatch.setenv("SANDBOX_ROOT", str(repo_root()))
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "none")
    monkeypatch.setenv("PHOENIX_TRACING", "disabled")
    # Child interpreters must import this checkout, not whichever one the venv's
    # editable install happens to point at (pytest's `pythonpath` is in-process only).
    src = str(Path(__file__).resolve().parents[1] / "src")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [src, os.environ.get("PYTHONPATH")])))


@pytest.fixture
def fake_bin(tmp_path, monkeypatch):
    """Fake external CLIs on an isolated ``PATH`` (see ``tests/_fakebin.py``).

    ``PATH`` holds only the shim directory, so a tool a test did not ``add`` is genuinely
    missing and no real ``modal``/``hf``/``docker``/``ssh`` on the host can be reached.
    """
    from _fakebin import FakeBin

    fake = FakeBin(tmp_path / "fakebin")
    fake.isolate_path(monkeypatch)
    return fake


@pytest.fixture
def job_data_dir(monkeypatch, tmp_path):
    """Point run-store writes at tmp (DMR-027 tests)."""
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    return tmp_path


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "local_llm: live test against a local OpenAI-compatible server",
    )


def pytest_collection_modifyitems(config, items):
    if os.environ.get("SANDBOX_LOCAL_LLM", "").strip() in {"1", "true", "yes"}:
        return
    skip = pytest.mark.skip(reason="SANDBOX_LOCAL_LLM not set")
    for item in items:
        if "local_llm" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _isolated_run_ledger(tmp_path, monkeypatch):
    """Signed test runs must not append to the tracked reports/run-ledger.md."""
    monkeypatch.setenv("SANDBOX_RUN_LEDGER", str(tmp_path / "_ledger" / "run-ledger.md"))


@pytest.fixture(autouse=True)
def _isolated_beacon_dir(tmp_path, monkeypatch):
    """Runs started in tests publish mailroom beacons — keep them out of ~/.mailroom/jobs."""
    monkeypatch.setenv("MAILROOM_BEACON_DIR", str(tmp_path / "_beacons"))


@pytest.fixture(autouse=True)
def _no_leaked_prompt_selection():
    """The active eval-environment prompt selection is process-wide; never leak it across tests."""
    from mailroom_sandbox import prompt_versions

    prompt_versions.clear_active_selection()
    yield
    prompt_versions.clear_active_selection()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item):
    """Join the vendored pipeline's fire-and-forget scan threads before the next test.

    ``pipeline.relations`` starts daemon ``relations-scan`` threads that write to the
    default DB; ``ensure_schema`` logs ``schema_ready`` the first time it sees a URL.
    Left running, that line lands in whichever later test is capturing stdout and
    corrupts its JSON. ``tryfirst`` joins them before fixtures (and env) are undone.
    """
    import threading

    for t in threading.enumerate():
        if t.name == "relations-scan" and t is not threading.current_thread():
            t.join(timeout=10)
