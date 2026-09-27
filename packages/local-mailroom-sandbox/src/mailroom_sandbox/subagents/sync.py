"""Render harness-specific agent stubs from the central roster."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.subagents.parse_opencode import parse_opencode_markdown
from mailroom_sandbox.subagents.doctor import expand_agents_dir
from mailroom_sandbox.subagents.roster import SubagentEntry, harness_config, load_roster


@dataclass
class SyncResult:
    written: list[Path]
    skipped: list[str]
    harness: str


def _cursor_description(entry: SubagentEntry, doc_description: str) -> str:
    parts: list[str] = []
    if entry.cursor_invoke_hint:
        parts.append(entry.cursor_invoke_hint.strip())
    if doc_description and doc_description not in (parts[0] if parts else ""):
        if not parts:
            flat = " ".join(doc_description.split())
            if len(flat) > 1200:
                flat = flat[:1197] + "..."
            parts.append(flat)
    if not parts:
        parts.append(f"Subagent {entry.title}.")
    return " ".join(parts)


def _opencode_frontmatter(entry: SubagentEntry, doc) -> dict:
    description = entry.opencode_description or doc.description
    front: dict = {}
    if description:
        front["description"] = description
    mode = entry.opencode_mode or doc.frontmatter.get("mode") or "all"
    front["mode"] = mode
    front["title"] = entry.title
    if entry.tags:
        front["tags"] = list(entry.tags)
    if entry.home_package:
        front["home_package"] = entry.home_package
    front["roster_id"] = entry.id
    return front


def render_cursor_agent(entry: SubagentEntry, root: Path | None = None) -> str:
    base = root or repo_root()
    src = entry.opencode_path(base)
    text = src.read_text(encoding="utf-8")
    doc = parse_opencode_markdown(text)
    description = _cursor_description(entry, doc.description)
    header = {
        "name": entry.id,
        "description": description,
    }
    yaml_block = yaml.safe_dump(header, sort_keys=False, allow_unicode=True).strip()
    harness_note = (
        f"> **Harness note:** Canonical OpenCode prompt lives at "
        f"`.opencode/agents/{entry.id}.md`. Edit there, then run "
        f"`sandbox subagents sync --harness all`.\n\n"
    )
    return f"---\n{yaml_block}\n---\n\n{harness_note}{doc.body}"


def render_opencode_agent(entry: SubagentEntry, root: Path | None = None) -> str:
    base = root or repo_root()
    src = entry.opencode_path(base)
    text = src.read_text(encoding="utf-8")
    doc = parse_opencode_markdown(text)
    front = _opencode_frontmatter(entry, doc)
    yaml_block = yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=1000).strip()
    return f"---\n{yaml_block}\n---\n\n{doc.body}"


def _sync_one_harness(
    harness: str,
    *,
    base: Path,
    package: str | None,
    dry_run: bool,
) -> SyncResult:
    cfg = harness_config(harness, base)
    if harness == "opencode-global":
        agents_dir = expand_agents_dir(cfg["agents_dir"])
    else:
        agents_dir = base / cfg["agents_dir"]
    written: list[Path] = []
    skipped: list[str] = []

    agents_dir.mkdir(parents=True, exist_ok=True)
    for entry in load_roster(base, package):
        if harness not in entry.harnesses:
            skipped.append(entry.id)
            continue
        if not entry.opencode_path(base).is_file():
            skipped.append(entry.id)
            continue
        if harness == "cursor":
            content = render_cursor_agent(entry, base)
            dest = entry.cursor_path(base)
        elif harness in ("opencode", "opencode-global"):
            content = render_opencode_agent(entry, base)
            if harness == "opencode-global":
                gdir = expand_agents_dir(cfg["agents_dir"])
                dest = gdir / f"{entry.id}.md"
            else:
                dest = entry.opencode_path(base)
        else:
            raise ValueError(harness)
        if dry_run:
            written.append(dest)
            continue
        dest.write_text(content, encoding="utf-8")
        written.append(dest)
    return SyncResult(written=written, skipped=skipped, harness=harness)


def sync_harness(
    harness: str,
    *,
    root: Path | None = None,
    package: str | None = None,
    dry_run: bool = False,
) -> SyncResult | list[SyncResult]:
    base = root or repo_root()
    if harness == "all":
        return [
            _sync_one_harness("opencode", base=base, package=package, dry_run=dry_run),
            _sync_one_harness("cursor", base=base, package=package, dry_run=dry_run),
            _sync_one_harness("opencode-global", base=base, package=package, dry_run=dry_run),
        ]
    if harness not in ("cursor", "opencode", "opencode-global"):
        raise KeyError(f"unknown harness {harness!r}")
    return _sync_one_harness(harness, base=base, package=package, dry_run=dry_run)
