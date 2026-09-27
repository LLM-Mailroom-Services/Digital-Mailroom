"""Load and query the family subagent roster for a package."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.subagents.family import (
    filter_subagent_rows,
    load_family_document,
    resolve_package,
)


@dataclass(frozen=True)
class SubagentEntry:
    id: str
    title: str
    description: str
    tags: tuple[str, ...] = ()
    harnesses: tuple[str, ...] = ("cursor", "opencode")
    family_source: str | None = None
    home_package: str | None = None
    packages: tuple[str, ...] = ()
    cursor_invoke_hint: str | None = None
    opencode_mode: str | None = None
    opencode_description: str | None = None
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def opencode_path(self, root: Path | None = None) -> Path:
        base = root or repo_root()
        return base / ".opencode" / "agents" / f"{self.id}.md"

    def cursor_path(self, root: Path | None = None) -> Path:
        base = root or repo_root()
        return base / ".cursor" / "agents" / f"{self.id}.md"


def roster_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "config" / "subagents" / "roster.yaml"


def _row_to_entry(row: dict[str, Any]) -> SubagentEntry:
    cursor = row.get("cursor") or {}
    opencode = row.get("opencode") or {}
    return SubagentEntry(
        id=row["id"],
        title=row.get("title") or row["id"],
        description=row.get("description") or "",
        tags=tuple(row.get("tags") or ()),
        harnesses=tuple(row.get("harnesses") or ("cursor", "opencode")),
        family_source=row.get("family_source"),
        home_package=row.get("home_package"),
        packages=tuple(row.get("packages") or ()),
        cursor_invoke_hint=cursor.get("invoke_hint"),
        opencode_mode=opencode.get("mode"),
        opencode_description=opencode.get("description"),
        raw=row,
    )


def load_roster(root: Path | None = None, package: str | None = None) -> list[SubagentEntry]:
    base = root or repo_root()
    pkg = resolve_package(package)
    doc = load_family_document(base)
    return [_row_to_entry(row) for row in filter_subagent_rows(doc, pkg)]


def get_subagent(subagent_id: str, root: Path | None = None, package: str | None = None) -> SubagentEntry | None:
    for entry in load_roster(root, package):
        if entry.id == subagent_id:
            return entry
    return None


def harness_config(harness: str, root: Path | None = None) -> dict[str, Any]:
    data = load_family_document(root)
    harnesses = data.get("harnesses") or {}
    if harness not in harnesses:
        raise KeyError(f"unknown harness {harness!r}; known: {sorted(harnesses)}")
    return harnesses[harness]
