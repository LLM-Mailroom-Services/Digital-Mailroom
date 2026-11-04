"""DMR-111: reproducible frozen refreshes with real, network-free Git repos."""
from __future__ import annotations

import importlib.util
import stat
import subprocess
from pathlib import Path

import pytest

from mailroom_sandbox import cli


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), "-c", "core.autocrlf=false",
         "-c", "filter.lfs.required=false", "-c", "filter.lfs.process=",
         "-c", "filter.lfs.clean=", "-c", "filter.lfs.smudge=", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def commit(root, files):
    for rel, body in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    git(root, "-c", "filter.lfs.required=false", "-c", "filter.lfs.process=", "-c", "filter.lfs.clean=", "add", "-f", "--", *files)
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    git(root, "init", "-b", "main")
    return root


@pytest.fixture
def vendor(monkeypatch, tmp_path):
    root = tmp_path / "vendor"
    root.mkdir()
    monkeypatch.setattr(cli, "vendor_dir", lambda: root)
    return root


def fingerprint(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), bool(p.stat().st_mode & stat.S_IXUSR))
            for p in root.rglob("*") if p.is_file()}


def seed_vendor(vendor):
    tree = vendor / "llm-mailroom"
    (tree / "src").mkdir(parents=True)
    (tree / "src" / "preserved.py").write_text("reviewed\n")
    (tree / "VENDOR.md").write_text("pin metadata\n")
    return tree


def test_full_commit_fetch_still_works_after_main_advances(source, vendor):
    reviewed = commit(source, {"src/pipeline.py": "REVIEWED = True\n"})
    tip = commit(source, {"src/pipeline.py": "UNREVIEWED = True\n"})
    assert reviewed != tip
    assert cli._refresh_vendor("llm-mailroom", reviewed, str(source), reviewed) == 0
    assert (vendor / "llm-mailroom/src/pipeline.py").read_text() == "REVIEWED = True\n"
    assert not list((vendor / ".refresh").iterdir())


def test_annotated_tag_is_compared_as_commit(source, vendor):
    reviewed = commit(source, {"llm_dojo_scoring/__init__.py": "REVIEWED = True\n"})
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "tag", "-a", "v0.24.0", "-m", "release")
    assert git(source, "rev-parse", "refs/tags/v0.24.0") != reviewed
    assert cli._refresh_vendor("llm-dojo-scoring", "refs/tags/v0.24.0", str(source), reviewed) == 0
    assert (vendor / "llm-dojo-scoring/src/llm_dojo_scoring/__init__.py").read_text() == "REVIEWED = True\n"


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/tags/reviewed"])
def test_moved_ref_rejects_before_replacing_vendor(source, vendor, ref):
    reviewed = commit(source, {"src/pipeline.py": "reviewed\n"})
    if ref.startswith("refs/tags/"):
        git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "tag", "-a", "reviewed", "-m", "reviewed")
    commit(source, {"src/pipeline.py": "unreviewed\n"})
    if ref.startswith("refs/tags/"):
        git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "tag", "-f", "-a", "reviewed", "-m", "moved")
    tree = seed_vendor(vendor)
    before = fingerprint(tree)
    assert cli._refresh_vendor("llm-mailroom", ref, str(source), reviewed) == 1
    assert fingerprint(tree) == before
    assert not list((vendor / ".refresh").iterdir())


@pytest.mark.parametrize("failure", ["missing-ref", "missing-source", "layout"])
def test_failed_fetch_or_layout_keeps_all_vendor_bytes(source, vendor, failure):
    reviewed = commit(source, {"unexpected/file.txt" if failure == "layout" else "src/pipeline.py": "reviewed\n"})
    tree = seed_vendor(vendor)
    before = fingerprint(tree)
    pin = "refs/heads/absent" if failure == "missing-ref" else reviewed
    url = str(source / "absent") if failure == "missing-source" else str(source)
    assert cli._refresh_vendor("llm-mailroom", pin, url, reviewed) == 1
    assert fingerprint(tree) == before


def test_copy_failure_keeps_all_vendor_bytes(monkeypatch, source, vendor):
    import shutil
    reviewed = commit(source, {"src/pipeline.py": "reviewed\n"})
    tree = seed_vendor(vendor)
    before = fingerprint(tree)
    def fail(*args, **kwargs):
        raise OSError("simulated storage failure")
    monkeypatch.setattr(shutil, "copytree", fail)
    assert cli._refresh_vendor("llm-mailroom", reviewed, str(source), reviewed) == 1
    assert fingerprint(tree) == before


def test_source_refresh_carries_content_deletions_modes_and_shared_exclusions(source, vendor, monkeypatch):
    files = {
        "src/pipeline/new.py": "NEW = True\n",
        "src/scripts/runner": "#!/bin/sh\nexit 0\n",
        "src/legalbench/reports/generated.json": "excluded\n",
        "src/legalbench/reports_helpers.py": "KEPT = True\n",
        "src/tests/test_top.py": "excluded\n",
        "src/test/test_top.py": "excluded\n",
        "src/pipeline/tests/runtime.py": "KEPT = True\n",
        "src/pipeline/__pycache__/a.pyc": "excluded\n",
        "src/pipeline/loose.pyc": "excluded\n",
        "src/mailroom.egg-info/PKG-INFO": "excluded\n",
    }
    commit(source, files)
    (source / "src/scripts/runner").chmod(0o755)
    git(source, "add", "src/scripts/runner")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "executable")
    reviewed = git(source, "rev-parse", "HEAD")
    tree = seed_vendor(vendor)
    assert cli._refresh_vendor("llm-mailroom", "main", str(source), reviewed) == 0
    expected = {"pipeline/new.py", "scripts/runner", "legalbench/reports_helpers.py", "pipeline/tests/runtime.py"}
    assert set(fingerprint(tree / "src")) == expected
    assert (tree / "src/scripts/runner").stat().st_mode & stat.S_IXUSR
    assert (tree / "VENDOR.md").read_text() == "pin metadata\n"
    assert cli._refresh_vendor_from_workspace("workspace-copy", source / "src") == 0
    assert fingerprint(vendor / "workspace-copy/src") == fingerprint(tree / "src")


def test_cli_script_and_drift_guard_apply_identical_exclusions(tmp_path):
    root = Path(__file__).resolve().parents[1]
    modules = []
    for name, path in [("sync_vendor", root / "scripts/sync_vendor.py"),
                       ("vendor_drift", root / "tests/test_vendor_drift.py")]:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    script, drift = modules
    expected = set()
    for rel, excluded in [("a.pyc", True), ("a/__pycache__/x", True), ("a.egg-info/x", True),
                          ("legalbench/reports/x", True), ("tests/x", True), ("test/x", True),
                          ("legalbench/reports_helpers.py", False), ("a/tests/runtime.py", False)]:
        path = Path(rel)
        assert cli._vendor_rel_excluded(path) is excluded
        assert script._excluded(path) is excluded
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture\n")
        if not excluded:
            expected.add(rel)
    assert set(drift._files(tmp_path)) == expected


def test_visualizer_fetches_exact_old_commit_without_lfs_payload(source, vendor):
    pointer = "version https://git-lfs.github.com/spec/v1\noid sha256:" + "a" * 64 + "\nsize 1000000000\n"
    reviewed = commit(source, {"index.html": "reviewed\n", "large.bin": pointer,
                               ".gitattributes": "*.bin filter=lfs diff=lfs merge=lfs -text\n"})
    commit(source, {"index.html": "unreviewed\n"})
    assert cli._refresh_visualizer(reviewed, str(source), reviewed) == 0
    dest = vendor / "The-Mailroom"
    assert git(dest, "rev-parse", "HEAD") == reviewed
    assert (dest / "index.html").read_text() == "reviewed\n"
    assert (dest / "large.bin").read_text() == pointer
    assert not (dest / ".git/FETCH_HEAD").exists()
    symbolic = subprocess.run(["git", "-C", str(dest), "symbolic-ref", "-q", "HEAD"], capture_output=True)
    assert symbolic.returncode != 0
    # An unchanged reviewed checkout can be checked again without replacement.
    assert cli._refresh_visualizer(reviewed, str(source), reviewed) == 0


@pytest.mark.parametrize("failure", ["missing-ref", "moved-tag"])
def test_visualizer_missing_or_moved_ref_creates_no_checkout(source, vendor, failure):
    reviewed = commit(source, {"index.html": "reviewed\n"})
    git(source, "tag", "reviewed")
    if failure == "moved-tag":
        commit(source, {"index.html": "unreviewed\n"})
        git(source, "tag", "-f", "reviewed")
    pin = "refs/tags/reviewed" if failure == "moved-tag" else "refs/tags/absent"
    assert cli._refresh_visualizer(pin, str(source), reviewed) == 1
    assert not (vendor / "The-Mailroom").exists()


@pytest.mark.parametrize("kind", ["tracked", "untracked", "ignored", "local-commit", "non-repo"])
def test_visualizer_preserves_all_local_work(source, vendor, kind):
    reviewed = commit(source, {"index.html": "reviewed\n", ".gitignore": "local.tmp\n"})
    dest = vendor / "The-Mailroom"
    if kind == "non-repo":
        dest.mkdir()
        (dest / "mine.txt").write_text("local\n")
    else:
        assert cli._refresh_visualizer(reviewed, str(source), reviewed) == 0
        if kind == "tracked":
            (dest / "index.html").write_text("my edits\n")
        elif kind in {"untracked", "ignored"}:
            (dest / ("local.tmp" if kind == "ignored" else "mine.txt")).write_text("local\n")
        else:
            commit(dest, {"index.html": "my commit\n"})
    before = fingerprint(dest)
    assert cli._refresh_visualizer(reviewed, str(source), reviewed) == 1
    assert fingerprint(dest) == before


def test_visualizer_updates_clean_older_reviewed_checkout(source, vendor):
    """A clean checkout at an earlier reviewed commit is refreshed, not refused."""
    old = commit(source, {"index.html": "old\n"})
    new = commit(source, {"index.html": "new\n"})
    assert cli._refresh_visualizer(old, str(source), old) == 0
    dest = vendor / "The-Mailroom"
    assert git(dest, "rev-parse", "HEAD") == old
    assert cli._refresh_visualizer(new, str(source), new) == 0
    assert git(dest, "rev-parse", "HEAD") == new
    assert (dest / "index.html").read_text() == "new\n"


def test_visualizer_existing_checkout_survives_remote_failure(source, vendor):
    reviewed = commit(source, {"index.html": "reviewed\n"})
    assert cli._refresh_visualizer(reviewed, str(source), reviewed) == 0
    dest = vendor / "The-Mailroom"
    before = fingerprint(dest)
    assert cli._refresh_visualizer("refs/heads/absent", str(source), reviewed) == 1
    assert fingerprint(dest) == before


@pytest.mark.parametrize("rollback_fails", [False, True])
def test_install_rename_failure_preserves_original_snapshot(monkeypatch, source, vendor, capsys, rollback_fails):
    reviewed = commit(source, {"src/pipeline.py": "reviewed\n"})
    tree = seed_vendor(vendor)
    before = fingerprint(tree)
    original_rename = Path.rename
    attempts = []

    def rename(path, target):
        if Path(target) == tree / "src":
            restoring = (path / "preserved.py").is_file()
            attempts.append("restore" if restoring else "install")
            if not restoring or rollback_fails:
                raise OSError("simulated restore failure" if restoring else "simulated install failure")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", rename)
    assert cli._refresh_vendor("llm-mailroom", reviewed, str(source), reviewed) == 1
    assert attempts == ["install", "restore"]
    recoveries = list((vendor / ".refresh").rglob("preserved.py"))
    if rollback_fails:
        assert len(recoveries) == 1
        assert fingerprint(recoveries[0].parent) == {"preserved.py": before["src/preserved.py"]}
        assert (tree / "VENDOR.md").read_bytes() == before["VENDOR.md"][0]
        assert str(recoveries[0].parent) in capsys.readouterr().err
    else:
        assert fingerprint(tree) == before
        assert recoveries == []
