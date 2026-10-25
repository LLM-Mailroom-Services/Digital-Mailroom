"""Family-wide subagent manifest loading and package filtering."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from mailroom_sandbox.paths import repo_root

DEFAULT_PACKAGE = "local-mailroom-sandbox"

# Legacy HUB-era id (Exios66/mailroom-dev artifact) → org monorepo package id.
PACKAGE_ALIASES: dict[str, str] = {
    "mailroom-dev": "digital-mailroom",
}


def normalize_package_id(package: str) -> str:
    return PACKAGE_ALIASES.get(package, package)


def family_roster_path(root: Path | None = None) -> Path:
    base = root or repo_root()
    candidates = (
        base / "config" / "subagents" / "family-roster.yaml",
        base / "governance" / "subagents" / "family-roster.yaml",
    )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def load_family_document(root: Path | None = None) -> dict[str, Any]:
    path = family_roster_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"family roster not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def package_roster_dest(
    package: str,
    dest_root: Path,
    *,
    source_root: Path | None = None,
) -> Path:
    package = normalize_package_id(package)
    doc = load_family_document(source_root)
    packages = doc.get("packages") or {}
    if package not in packages:
        known = sorted(packages)
        raise KeyError(f"unknown package {package!r}; known: {known}")
    rel = packages[package].get("family_roster_dest") or "config/subagents/family-roster.yaml"
    return dest_root / rel


def list_packages(root: Path | None = None) -> list[str]:
    doc = load_family_document(root)
    return sorted((doc.get("packages") or {}).keys())


def resolve_package(package: str | None = None) -> str:
    raw = package or os.environ.get("SUBAGENT_PACKAGE") or DEFAULT_PACKAGE
    return normalize_package_id(raw)


def filter_subagent_rows(doc: dict[str, Any], package: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in doc.get("subagents") or []:
        packages = row.get("packages") or []
        if package in packages:
            rows.append(row)
    return rows
