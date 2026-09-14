#!/usr/bin/env python3
"""Refresh the sandbox vendor snapshots from the workspace packages (hub#62).

The sandbox ships llm-mailroom + llm-dojo-scoring as TRACKED snapshots under
``vendor/`` (DMR-057 self-containment). The workspace monorepo packages are
the source of truth; after a workspace change the vendor tree must be
refreshed in the same commit or the drift guard
(``tests/test_vendor_drift.py``) fails.

This script copies the workspace trees into ``vendor/`` with the sandbox
layout (llm-mailroom src minus tests/; llm-dojo-scoring package dir under
src/), mirroring what ``sandbox fetch-deps`` produces from the pinned tags.

Usage:
    python scripts/sync_vendor.py            # both snapshots
    python scripts/sync_vendor.py llm-mailroom
    python scripts/sync_vendor.py llm-dojo-scoring
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent  # local-mailroom-sandbox
WORKSPACE = REPO.parent.parent  # monorepo root
VENDOR = REPO / "vendor"

# (vendor name, vendored dest, workspace source, copy predicate)
_SNAPSHOTS = [
    (
        "llm-mailroom",
        VENDOR / "llm-mailroom" / "src",
        WORKSPACE / "packages" / "llm-mailroom" / "src",
    ),
    (
        "llm-dojo-scoring",
        VENDOR / "llm-dojo-scoring" / "src" / "llm_dojo_scoring",
        WORKSPACE / "packages" / "llm-dojo-scoring" / "llm_dojo_scoring",
    ),
]

_EXCLUDE_DIRS = {"__pycache__"}
_EXCLUDE_REL = {"tests", "test"}  # llm-mailroom vendored src minus tests/
# Runtime-generated report artifacts: the workspace copies are gitignored
# (llm-mailroom .gitignore src/legalbench/reports/) and drift every run, so
# they must not be pinned into a tracked snapshot.
_EXCLUDE_SUFFIXES = {"legalbench/reports"}


def _excluded(rel: Path) -> bool:
    if any(part in _EXCLUDE_DIRS or part.endswith(".egg-info") for part in rel.parts):
        return True
    if rel.parts[0] in _EXCLUDE_REL:
        return True
    return any("/".join(rel.parts).startswith(s) for s in _EXCLUDE_SUFFIXES)


def _refresh(name: str, dest: Path, source: Path) -> int:
    if not source.is_dir():
        print(f"error: workspace source missing: {source}", file=sys.stderr)
        return 1
    # Wipe + re-copy so deleted files are removed from the snapshot.
    if dest.is_dir():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in source.rglob("*"):
        rel = path.relative_to(source)
        if _excluded(rel):
            continue
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    print(f"refreshed {name}: {copied} files -> {dest.relative_to(REPO)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "snapshot", nargs="?", choices=[s[0] for s in _SNAPSHOTS], default=None
    )
    args = ap.parse_args()

    rc = 0
    for name, dest, source in _SNAPSHOTS:
        if args.snapshot and name != args.snapshot:
            continue
        rc = rc or _refresh(name, dest, source)
    return rc


if __name__ == "__main__":
    sys.exit(main())