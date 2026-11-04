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

Standalone fallback (SAND-058): when this checkout is not inside the monorepo
(`WORKSPACE/packages` absent) but the sibling standalone dojo checkout
`../llm-dojo-scoring` EXISTS, the llm-dojo-scoring snapshot is drift-checked
against that checkout's `llm_dojo_scoring/` package dir instead of being
skipped — the vendored bytes must agree with the dojo source of truth
either way. The skip only stays when NEITHER reference exists (guarded by
existence, same conventions as above).

A sibling standalone checkout can sit on any branch, so its working tree says
nothing about the reviewed revision. When the pinned commit from `_VENDOR_PINS`
is in its object store, the snapshot is compared to that commit's exact bytes
(`git archive`, read-only). Without the commit the working tree is still
compared, so a clone that lacks the pin fails instead of skipping.
"""

from __future__ import annotations

import hashlib
import io
import subprocess
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from mailroom_sandbox.cli import _VENDOR_PINS

REPO = Path(__file__).resolve().parents[1]
VENDOR = REPO / "vendor"
WORKSPACE = REPO.parent.parent
# Standalone llm-dojo-scoring checkout (repo layout: .../Cold_Storage/
# {llm-dojo-scoring,local-mailroom-sandbox}) — its package ships at the ROOT,
# like the upstream clone the vendored snapshot normalizes (DMR-058).
_STANDALONE_DOJO = REPO.parent / "llm-dojo-scoring"
_STANDALONE_DOJO_PKG = _STANDALONE_DOJO / "llm_dojo_scoring"
_STANDALONE_MAILROOM_PKG = REPO.parent / "llm-mailroom" / "src"

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
# Runtime-generated report artifacts (llm-mailroom src/legalbench/reports/ is
# gitignored in the workspace and regenerated every run — it is neither vendored
# nor drift-checked; sync_vendor.py excludes the same path).
_EXCLUDE_REL_PREFIXES = {"legalbench/reports"}
# llm-mailroom vendored src excludes the tests/ subtree (VENDOR.md: "upstream
# src/ minus src/tests/") — test-only files are never imported by vendored
# modules, so they legitimately don't appear in the snapshot.
_EXCLUDE_TOP_LEVEL_DIRS = {"tests", "test"}
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
        if any(rel == Path(p) or Path(p) in rel.parents for p in _EXCLUDE_REL_PREFIXES):
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


@contextmanager
def _at_pin(package_root: Path, sha: str | None) -> Iterator[Path]:
    """Yield ``package_root`` as of commit ``sha``, or unchanged when the commit is unavailable."""
    repo = package_root.parent
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", str(sha), package_root.name],
        capture_output=True, check=False,
    ) if sha else None
    if archive is None or archive.returncode:
        yield package_root
        return
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        # ``filter`` arrived in 3.11.4 (and 3.12); the archive is our own git output.
        if hasattr(tarfile, "data_filter"):
            tar.extractall(tmp, filter="data")
        else:  # pragma: no cover - Python 3.11.0-3.11.3
            tar.extractall(tmp)  # noqa: S202 - trusted local git archive
        yield Path(tmp) / package_root.name


def test_pinned_comparison_reads_the_commit_not_the_checkout(tmp_path):
    def git(*args):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-C", str(tmp_path), *args],
            capture_output=True, text=True, check=True,
        ).stdout.strip()

    (tmp_path / "src").mkdir()
    module = tmp_path / "src" / "m.py"
    git("init", "-q")
    module.write_text("pinned\n")
    git("add", "-A")
    git("commit", "-qm", "pin")
    pin = git("rev-parse", "HEAD")
    module.write_text("feature branch\n")
    git("commit", "-qam", "ahead")

    vendored = tmp_path / "vendored"
    vendored.mkdir()
    (vendored / "m.py").write_text("pinned\n")
    with _at_pin(tmp_path / "src", pin) as root:
        assert _diff_vs_workspace(vendored, root) == []
    (vendored / "m.py").write_text("hand edit\n")
    with _at_pin(tmp_path / "src", pin) as root:
        assert _diff_vs_workspace(vendored, root) == ["drifted: m.py"]
    with _at_pin(tmp_path / "src", "0" * 40) as root:  # a clone without the pin still compares
        assert root == tmp_path / "src"


@pytest.mark.parametrize(
    "vendored_root,workspace_root,label",
    _SNAPSHOTS,
    ids=[s[2] for s in _SNAPSHOTS],
)
def test_vendor_tracks_workspace(vendored_root, workspace_root, label):
    """The vendored snapshot is byte-identical to the workspace package
    (excluding sandbox-local glue). A lagging vendor tree fails here.

    Standalone fallback (SAND-058): no monorepo workspace but the sibling
    standalone `../llm-dojo-scoring` checkout exists → drift-check against IT
    (the same file-hash machinery, same exclusions). Skips only when neither
    reference exists.
    """
    assert vendored_root.is_dir(), f"required vendor tree not present: {vendored_root}"
    if not workspace_root.is_dir():
        if label == "llm-dojo-scoring" and _STANDALONE_DOJO_PKG.is_dir():
            print(
                f"note [{label}]: no monorepo workspace ({workspace_root}) — "
                f"drift-checking the vendor snapshot against the standalone "
                f"checkout {_STANDALONE_DOJO} instead"
            )
            workspace_root = _STANDALONE_DOJO_PKG
    if not workspace_root.is_dir() and label == "llm-mailroom":
        workspace_root = _STANDALONE_MAILROOM_PKG
    if not workspace_root.is_dir():
        pytest.skip(f"workspace package not present: {workspace_root}")
    standalone = workspace_root in (_STANDALONE_DOJO_PKG, _STANDALONE_MAILROOM_PKG)
    pin = {name: sha for name, _, _, sha in _VENDOR_PINS}[label] if standalone else None
    with _at_pin(workspace_root, pin) as reference:
        problems = _diff_vs_workspace(vendored_root, reference)
    assert not problems, (
        f"{label} vendor snapshot drifted from the workspace package — refresh "
        f"it in this commit (hub#62):\n" + "\n".join(problems)
    )