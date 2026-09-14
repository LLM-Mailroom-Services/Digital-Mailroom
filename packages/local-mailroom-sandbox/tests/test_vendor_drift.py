"""hub#62: sandbox vendor drift guard — the tracked vendor snapshots cannot
silently age relative to the workspace packages.

The sandbox ships llm-mailroom + llm-dojo-scoring as TRACKED snapshots under
``vendor/`` (DMR-057 self-containment). When the workspace packages change
(the source of truth in the monorepo), the vendored copies MUST be refreshed
in the same commit — otherwise the sandbox scores/runs against stale code.

This test walks both vendored trees and hash-compares every tracked file
against the workspace package it mirrors. Refresh procedure:

    python scripts/sync_vendor.py            # copy workspace -> vendor/

The drift guard fails (correctly) when the vendor tree lags the workspace.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VENDOR = REPO / "vendor"
WORKSPACE = REPO.parent.parent

# (vendored dir, workspace package root, relative subdir to compare)
# - llm-mailroom: workspace src/ minus tests/ (VENDOR.md notes test-only files
#   are never imported by vendored modules).
# - llm-dojo-scoring: workspace package dir relocated under src/.
_SNAPSHOTS = [
    (
        VENDOR / "llm-mailroom" / "src",
        WORKSPACE / "packages" / "llm-mailroom" / "src",
        "llm-mailroom",
    ),
    (
        VENDOR / "llm-dojo-scoring" / "src" / "llm_dojo_scoring",
        WORKSPACE / "packages" / "llm-dojo-scoring" / "llm_dojo_scoring",
        "llm-dojo-scoring",
    ),
]

# Files allowed to differ between vendor and workspace (sandbox-local glue).
_EXCLUDE_NAMES = {"__pycache__"}
_EXCLUDE_SUFFIXES = {".pyc"}
# llm-mailroom vendored src excludes the tests/ subtree (VENDOR.md: "upstream
# src/ minus src/tests/") — test-only files are never imported by vendored
# modules, so they legitimately don't appear in the snapshot.
_EXCLUDE_TOP_LEVEL_DIRS = {"tests"}
# Build detritus in the workspace src/ (mailroom.egg-info) is never vendored.
_EGG_INFO_SUFFIX = ".egg-info"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _files(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in _EXCLUDE_NAMES for part in rel.parts):
            continue
        if rel.parts[0] in _EXCLUDE_TOP_LEVEL_DIRS:
            continue
        if any(part.endswith(_EGG_INFO_SUFFIX) for part in rel.parts):
            continue
        if path.suffix in _EXCLUDE_SUFFIXES:
            continue
        out[str(rel)] = _sha256(path)
    return out


def _diff_vs_workspace(vendored_root: Path, workspace_root: Path) -> list[str]:
    vendor_files = _files(vendored_root)
    workspace_files = _files(workspace_root)
    problems: list[str] = []
    for rel, vhash in vendor_files.items():
        wpath = workspace_root / rel
        if not wpath.is_file():
            problems.append(f"only in vendor: {rel}")
            continue
        if _sha256(wpath) != vhash:
            problems.append(f"drifted: {rel}")
    for rel in workspace_files:
        if not (vendored_root / rel).is_file():
            problems.append(f"missing from vendor: {rel}")
    return problems


@pytest.mark.parametrize(
    "vendored_root,workspace_root,label",
    _SNAPSHOTS,
    ids=[s[2] for s in _SNAPSHOTS],
)
def test_vendor_tracks_workspace(vendored_root, workspace_root, label):
    """The vendored snapshot is byte-identical to the workspace package
    (excluding sandbox-local glue). A lagging vendor tree fails here."""
    if not vendored_root.is_dir():
        pytest.skip(f"vendor tree not present: {vendored_root}")
    if not workspace_root.is_dir():
        pytest.skip(f"workspace package not present: {workspace_root}")
    problems = _diff_vs_workspace(vendored_root, workspace_root)
    assert not problems, (
        f"{label} vendor snapshot drifted from the workspace package — refresh "
        f"it in this commit (hub#62):\n" + "\n".join(problems)
    )