"""Materialize + sync subagents across family checkouts."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.subagents.family import list_packages, normalize_package_id
from mailroom_sandbox.subagents.materialize import materialize_package
from mailroom_sandbox.subagents.sync import sync_harness


@dataclass
class PackagePropagateResult:
    package: str
    dest_root: Path
    materialized: bool
    sync_written: int
    skipped: list[str]
    error: str | None = None


@dataclass
class PropagateResult:
    source_root: Path
    monorepo_root: Path | None
    packages: list[PackagePropagateResult] = field(default_factory=list)


def checkout_map_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "config" / "subagents" / "checkout-map.yaml"


def load_checkout_map(root: Path | None = None) -> dict[str, Any]:
    path = checkout_map_path(root)
    if not path.is_file():
        raise FileNotFoundError(path)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def discover_monorepo_root(source_root: Path | None = None) -> Path | None:
    explicit = (
        os.environ.get("DIGITAL_MAILROOM_ROOT")
        or os.environ.get("MONOREPO_ROOT")
        or os.environ.get("MAILROOM_DEV_ROOT")
    )
    if explicit:
        path = Path(explicit).expanduser().resolve()
        return path if path.is_dir() else None

    base = source_root or repo_root()
    doc = load_checkout_map(base)
    sibling = doc.get("default_monorepo_sibling") or "Digital-Mailroom"
    candidate = (base.parent / sibling).resolve()
    marker = candidate / "packages" / "local-mailroom-sandbox"
    if marker.is_dir():
        return candidate
    return None


def checkout_roots(
    *,
    source_root: Path | None = None,
    monorepo_root: Path | None = None,
) -> dict[str, Path]:
    base = source_root or repo_root()
    doc = load_checkout_map(base)
    checkouts = doc.get("checkouts") or {}
    roots: dict[str, Path] = {}

    mono = monorepo_root if monorepo_root is not None else discover_monorepo_root(base)
    for package_id, spec in checkouts.items():
        rel = spec.get("monorepo_relative")
        if not rel:
            continue
        if spec.get("standalone"):
            roots[package_id] = base.resolve()
        if mono is not None:
            roots[package_id] = (mono / rel).resolve()
    return roots


def propagate_family_checkouts(
    *,
    source_root: Path | None = None,
    monorepo_root: Path | None = None,
    packages: list[str] | None = None,
    dry_run: bool = False,
    skip_missing: bool = True,
) -> PropagateResult:
    """Run materialize + sync for each mapped family checkout."""
    src = (source_root or repo_root()).resolve()
    mono = monorepo_root if monorepo_root is not None else discover_monorepo_root(src)
    if monorepo_root is not None:
        mono = Path(monorepo_root).expanduser().resolve()

    targets = packages or list_packages(src)
    roots = checkout_roots(source_root=src, monorepo_root=mono)
    result = PropagateResult(source_root=src, monorepo_root=mono)

    for package_id in targets:
        package_id = normalize_package_id(package_id)
        if package_id not in roots:
            continue
        dest = roots[package_id]
        if not dest.is_dir():
            if skip_missing:
                result.packages.append(
                    PackagePropagateResult(
                        package=package_id,
                        dest_root=dest,
                        materialized=False,
                        sync_written=0,
                        skipped=[],
                        error="checkout missing",
                    )
                )
                continue
            raise FileNotFoundError(f"checkout for {package_id} not found: {dest}")

        try:
            materialize_package(package_id, dest_root=dest, source_root=src, dry_run=dry_run)
            sync_out = sync_harness("all", root=dest, package=package_id, dry_run=dry_run)
            written = 0
            skipped: list[str] = []
            if isinstance(sync_out, list):
                for block in sync_out:
                    written += len(block.written)
                    skipped.extend(block.skipped)
            else:
                written = len(sync_out.written)
                skipped = list(sync_out.skipped)
            result.packages.append(
                PackagePropagateResult(
                    package=package_id,
                    dest_root=dest,
                    materialized=True,
                    sync_written=written,
                    skipped=skipped,
                )
            )
        except Exception as exc:  # noqa: BLE001 — aggregate per-package errors for CLI
            result.packages.append(
                PackagePropagateResult(
                    package=package_id,
                    dest_root=dest,
                    materialized=False,
                    sync_written=0,
                    skipped=[],
                    error=str(exc),
                )
            )
    return result
