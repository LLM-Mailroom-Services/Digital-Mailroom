"""A failed first source refresh must not suppress the remaining refresh."""
from argparse import Namespace

import pytest

from mailroom_sandbox import cli


@pytest.mark.parametrize("workspace", [True, False])
def test_all_sources_attempted_after_first_failure(monkeypatch, tmp_path, workspace):
    pins = (("first", "main", "https://invalid/first", "a" * 40),
            ("second", "main", "https://invalid/second", "b" * 40))
    monkeypatch.setattr(cli, "_VENDOR_PINS", pins)
    monkeypatch.setattr(cli, "_monorepo_workspace_pkg", lambda name: tmp_path if workspace else None)
    calls = []

    def refresh(name, *args):
        calls.append(name)
        return 1 if name == "first" else 0

    monkeypatch.setattr(cli, "_refresh_vendor_from_workspace", refresh)
    monkeypatch.setattr(cli, "_refresh_vendor", refresh)
    assert cli._cmd_fetch_deps(Namespace(visualizer=False)) == 1
    assert calls == ["first", "second"]


def test_visualizer_clone_attempted_after_source_failure(monkeypatch, tmp_path):
    from subprocess import CompletedProcess
    monkeypatch.setattr(cli, "_VENDOR_PINS", (("first", "main", "https://invalid/first", "a" * 40),))
    monkeypatch.setattr(cli, "_monorepo_workspace_pkg", lambda _: tmp_path)
    monkeypatch.setattr(cli, "_refresh_vendor_from_workspace", lambda *args: 1)
    monkeypatch.setattr(cli, "vendor_dir", lambda: tmp_path)
    calls = []
    def run(command, *args, **kwargs):
        calls.append(command)
        return CompletedProcess(command, 0)
    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli._cmd_fetch_deps(Namespace(visualizer=True)) == 1
    assert len(calls) == 1
    assert calls[0][:2] == ["git", "clone"]
    assert calls[0][-1] == str(tmp_path / "The-Mailroom")


def test_moved_source_ref_cannot_replace_tracked_vendor(monkeypatch, tmp_path):
    """Exercise real Git clone/HEAD validation before tracked bytes are touched."""
    import subprocess
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    def git(*args):
        return subprocess.run(["git", "-C", str(upstream), *args], check=True,
                              capture_output=True, text=True)
    git("init", "-b", "main")
    package = upstream / "llm_dojo_scoring"
    package.mkdir()
    (package / "__init__.py").write_text("NEW_SOURCE = True\n")
    git("add", "llm_dojo_scoring/__init__.py")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-m", "fixture source")
    vendor = tmp_path / "vendor"
    tracked = vendor / "llm-dojo-scoring" / "src"
    tracked.mkdir(parents=True)
    sentinel = tracked / "preserved.py"
    sentinel.write_text("REVIEWED_SOURCE = True\n")
    monkeypatch.setattr(cli, "vendor_dir", lambda: vendor)
    assert cli._refresh_vendor("llm-dojo-scoring", "main", str(upstream), "f" * 40) == 1
    assert sentinel.read_text() == "REVIEWED_SOURCE = True\n"
    assert list(tracked.iterdir()) == [sentinel]
    assert not (vendor / ".refresh" / "llm-dojo-scoring").exists()
