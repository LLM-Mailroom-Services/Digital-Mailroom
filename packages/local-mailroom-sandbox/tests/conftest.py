"""Pytest hooks for the sandbox suite."""

from __future__ import annotations

import os

import pytest

from mailroom_sandbox.paths import repo_root


@pytest.fixture(autouse=True)
def _sandbox_root(monkeypatch):
    monkeypatch.setenv("SANDBOX_ROOT", str(repo_root()))
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "none")
    monkeypatch.setenv("PHOENIX_TRACING", "disabled")


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
