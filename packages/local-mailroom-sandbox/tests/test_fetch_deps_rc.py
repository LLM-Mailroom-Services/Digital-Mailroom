"""DMR-088 regression: ``fetch-deps`` must not short-circuit later vendors.

``rc = rc or _refresh_vendor(...)`` skipped every vendor after the first
failing one (and the visualizer clone) because ``or`` never evaluates its
right side once ``rc`` is truthy. Every refresh must run; the command exits
non-zero if ANY of them failed.
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from mailroom_sandbox import cli

_PINS = (
    ("alpha", "v1", "https://example.invalid/alpha.git", None),
    ("beta", "v2", "https://example.invalid/beta.git", None),
)


def _run(monkeypatch, results: dict[str, int], *, workspace: bool):
    calls: list[str] = []
    monkeypatch.setattr(cli, "_VENDOR_PINS", _PINS)
    monkeypatch.setattr(
        cli, "_monorepo_workspace_pkg", lambda name: Path("/ws") / name if workspace else None
    )

    def fake_ws(name, ws):
        calls.append(name)
        return results[name]

    def fake_tag(name, pin, url, sha):
        calls.append(name)
        return results[name]

    monkeypatch.setattr(cli, "_refresh_vendor_from_workspace", fake_ws)
    monkeypatch.setattr(cli, "_refresh_vendor", fake_tag)
    rc = cli._cmd_fetch_deps(types.SimpleNamespace(visualizer=False))
    return rc, calls


@pytest.mark.parametrize("workspace", [True, False], ids=["workspace", "tag"])
def test_first_failure_does_not_skip_second(monkeypatch, workspace):
    rc, calls = _run(monkeypatch, {"alpha": 1, "beta": 0}, workspace=workspace)
    assert calls == ["alpha", "beta"]
    assert rc != 0


@pytest.mark.parametrize("workspace", [True, False], ids=["workspace", "tag"])
def test_second_failure_still_nonzero(monkeypatch, workspace):
    rc, calls = _run(monkeypatch, {"alpha": 0, "beta": 3}, workspace=workspace)
    assert calls == ["alpha", "beta"]
    assert rc != 0


@pytest.mark.parametrize("workspace", [True, False], ids=["workspace", "tag"])
def test_all_ok_returns_zero(monkeypatch, workspace):
    rc, calls = _run(monkeypatch, {"alpha": 0, "beta": 0}, workspace=workspace)
    assert calls == ["alpha", "beta"]
    assert rc == 0


def test_visualizer_clone_runs_even_after_vendor_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_VENDOR_PINS", _PINS[:1])
    monkeypatch.setattr(cli, "_monorepo_workspace_pkg", lambda name: Path("/ws"))
    monkeypatch.setattr(cli, "_refresh_vendor_from_workspace", lambda n, w: 1)
    monkeypatch.setattr(cli, "vendor_dir", lambda: tmp_path)
    cloned: list[list[str]] = []

    def fake_run(cmd, *a, **k):
        cloned.append(list(cmd))
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    rc = cli._cmd_fetch_deps(types.SimpleNamespace(visualizer=True))
    assert any(c[:2] == ["git", "clone"] for c in cloned)
    assert rc != 0
