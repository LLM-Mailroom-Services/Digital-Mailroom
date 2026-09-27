"""Central subagent roster + harness sync (network-free)."""

from __future__ import annotations

import shutil

from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.subagents import load_roster, materialize_package, sync_harness
from mailroom_sandbox.subagents.parse_opencode import parse_opencode_markdown
from mailroom_sandbox.subagents.roster import get_subagent


def test_roster_entries_have_opencode_prompts():
    for entry in load_roster():
        path = entry.opencode_path()
        assert path.is_file(), f"missing OpenCode prompt for {entry.id}: {path}"
        doc = parse_opencode_markdown(path.read_text(encoding="utf-8"))
        assert doc.description or entry.cursor_invoke_hint


def test_meta_subagents_present():
    assert get_subagent("harness-doctor") is not None
    assert get_subagent("adversarial-reviewer") is not None


def test_family_package_filter():
    sandbox = load_roster(package="local-mailroom-sandbox")
    mailroom = load_roster(package="llm-mailroom")
    eval_env = load_roster(package="eval-environment")
    assert len(sandbox) == 8
    assert len(eval_env) == 8
    assert {e.id for e in eval_env} == {
        "prompt-engineer",
        "experiment-log-sync",
        "eval-runner",
        "corpus-curator",
        "trace-auditor",
        "calibration-analyst",
        "harness-doctor",
        "adversarial-reviewer",
    }
    assert len(mailroom) == 4
    assert {e.id for e in mailroom} == {
        "trace-log-analyst",
        "mailroom-arch-optimizer",
        "legal-changelog-auditor",
        "adversarial-reviewer",
    }


def test_sync_cursor_writes_agents(tmp_path):
    (tmp_path / "config" / "subagents").mkdir(parents=True)
    shutil.copy(
        repo_root() / "config" / "subagents" / "family-roster.yaml",
        tmp_path / "config" / "subagents" / "family-roster.yaml",
    )
    for entry in load_roster():
        dest_dir = tmp_path / ".opencode" / "agents"
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(entry.opencode_path(), dest_dir / f"{entry.id}.md")

    result = sync_harness("cursor", root=tmp_path)
    assert result.written
    sample = get_subagent("harness-doctor")
    assert sample is not None
    cursor_file = sample.cursor_path(tmp_path)
    assert cursor_file.is_file()
    text = cursor_file.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: harness-doctor" in text


def test_sync_opencode_merges_roster_frontmatter(tmp_path):
    (tmp_path / "config" / "subagents").mkdir(parents=True)
    shutil.copy(
        repo_root() / "config" / "subagents" / "family-roster.yaml",
        tmp_path / "config" / "subagents" / "family-roster.yaml",
    )
    entry = get_subagent("harness-doctor")
    assert entry is not None
    dest_dir = tmp_path / ".opencode" / "agents"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(entry.opencode_path(), dest_dir / "harness-doctor.md")

    sync_harness("opencode", root=tmp_path)
    doc = parse_opencode_markdown((dest_dir / "harness-doctor.md").read_text(encoding="utf-8"))
    assert doc.frontmatter.get("roster_id") == "harness-doctor"
    assert doc.frontmatter.get("home_package") == "local-mailroom-sandbox"
    assert doc.frontmatter.get("mode") == "all"
    assert "Harness Doctor" in doc.body


def test_propagate_local_checkout_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    for rel in (
        "config/subagents/family-roster.yaml",
        "config/subagents/checkout-map.yaml",
        "config/subagents/roster.yaml",
    ):
        path = sandbox / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo_root() / rel, path)
    for entry in load_roster():
        dest = sandbox / ".opencode" / "agents"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(entry.opencode_path(), dest / f"{entry.id}.md")

    from mailroom_sandbox.subagents.propagate import propagate_family_checkouts

    monkeypatch.setenv("MAILROOM_DEV_ROOT", str(tmp_path / "missing-monorepo"))
    result = propagate_family_checkouts(source_root=sandbox, monorepo_root=None)
    assert len(result.packages) == 1
    assert result.packages[0].package == "local-mailroom-sandbox"
    assert result.packages[0].error is None


def test_propagate_monorepo_layout(tmp_path):
    mono = tmp_path / "Digital-Mailroom"
    sandbox = mono / "packages" / "local-mailroom-sandbox"
    mailroom = mono / "packages" / "llm-mailroom"
    sandbox.mkdir(parents=True)
    mailroom.mkdir(parents=True)
    for rel in (
        "config/subagents/family-roster.yaml",
        "config/subagents/checkout-map.yaml",
    ):
        path = sandbox / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo_root() / rel, path)
    for entry in load_roster():
        dest = sandbox / ".opencode" / "agents"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(entry.opencode_path(), dest / f"{entry.id}.md")

    from mailroom_sandbox.subagents.propagate import propagate_family_checkouts

    result = propagate_family_checkouts(source_root=sandbox, monorepo_root=mono)
    pkg_ids = {row.package for row in result.packages}
    assert "local-mailroom-sandbox" in pkg_ids
    assert "llm-mailroom" in pkg_ids
    assert (mailroom / "config" / "subagents" / "family-roster.yaml").is_file()


def test_package_alias_mailroom_dev():
    from mailroom_sandbox.subagents.family import normalize_package_id

    assert normalize_package_id("mailroom-dev") == "digital-mailroom"


def test_sync_opencode_global_writes_home_config(tmp_path, monkeypatch):
    home_agents = tmp_path / "global_agents"
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "opencode" / "agents").mkdir(parents=True)

    (tmp_path / "checkout" / "config" / "subagents").mkdir(parents=True)
    shutil.copy(
        repo_root() / "config" / "subagents" / "family-roster.yaml",
        tmp_path / "checkout" / "config" / "subagents" / "family-roster.yaml",
    )
    checkout = tmp_path / "checkout"
    for entry in load_roster():
        dest_dir = checkout / ".opencode" / "agents"
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(entry.opencode_path(), dest_dir / f"{entry.id}.md")

    # Point global harness at temp home via family-roster override in checkout only if needed;
    # default roster uses ~/.config/opencode/agents which respects HOME.
    result = sync_harness("opencode-global", root=checkout)
    assert result.written
    global_file = tmp_path / ".config" / "opencode" / "agents" / "harness-doctor.md"
    assert global_file.is_file()


def test_materialize_mailroom_package(tmp_path):
    pkg_root = tmp_path / "llm-mailroom"
    pkg_root.mkdir()
    result = materialize_package("llm-mailroom", dest_root=pkg_root)
    assert result.family_roster_written.is_file()
    assert (pkg_root / "config" / "subagents" / "family-roster.yaml").is_file()
    assert len(result.prompts_copied) == 4
