#!/usr/bin/env python3
"""sync_vendor.py — refresh the sandbox vendor snapshots from the workspace
packages (DMR-057 / hub#62 / DMR-070).

The sandbox ships llm-mailroom + llm-dojo-scoring as TRACKED snapshots under
``packages/local-mailroom-sandbox/vendor/`` (DMR-057 self-containment). The
drift guard (``packages/local-mailroom-sandbox/tests/test_vendor_drift.py``)
requires the vendored trees to stay byte-identical to the workspace packages —
the monorepo is the development source of truth. This script is the refresh
leg the drift guard's docstring documents.

DMR-070 lesson: a copy-only refresh never deletes — that is how the
docclass-era compliance files survived their upstream removal (59c47401) and
kept resurfacing as ``only in vendor`` drift. This mirror carries BOTH
content updates AND deletions: after a run, the vendored tree is an exact
image of the workspace package (minus the exclusions below), so a subsequent
drift-guard run passes.

Exclusions mirror the drift guard exactly (keep the two lists in sync):
  - ``__pycache__/`` dirs and ``*.pyc`` files (build detritus)
  - ``legalbench/reports/`` (runtime-generated, gitignored in the workspace)
  - top-level ``tests/`` (test-only files are never imported by vendored
    modules; VENDOR.md documents ``src/`` minus ``src/tests/``)
  - ``*.egg-info/`` (workspace build artifacts, never vendored)

Usage (monorepo root):

    python scripts/sync_vendor.py           # apply the refresh
    python scripts/sync_vendor.py --check   # exit 1 if a refresh is due

Hermetic: stdlib only, no network, operates only inside the repo.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# (label, workspace package root, vendored root) — relative to REPO_ROOT.
# The mappings mirror tests/test_vendor_drift.py's _SNAPSHOTS exactly:
# - llm-mailroom: workspace src/ mirrored onto vendor/llm-mailroom/src/
#   (upstream src-layout, tests/ excluded by the exclusion rules).
# - llm-dojo-scoring: workspace package dir relocated under src/.
SNAPSHOTS: tuple[tuple[str, str, str], ...] = (
    (
        "llm-mailroom",
        "packages/llm-mailroom/src",
        "packages/local-mailroom-sandbox/vendor/llm-mailroom/src",
    ),
    (
        "llm-dojo-scoring",
        "packages/llm-dojo-scoring/llm_dojo_scoring",
        "packages/local-mailroom-sandbox/vendor/llm-dojo-scoring/src/llm_dojo_scoring",
    ),
)

# Keep in sync with packages/local-mailroom-sandbox/tests/test_vendor_drift.py.
_EXCLUDE_NAMES = {"__pycache__"}
_EXCLUDE_SUFFIXES = {".pyc"}
_EXCLUDE_REL_PREFIXES = {"legalbench/reports"}
_EXCLUDE_TOP_LEVEL_DIRS = {"tests"}
_EGG_INFO_SUFFIX = ".egg-info"


def _excluded(rel: Path) -> bool:
    if any(part in _EXCLUDE_NAMES for part in rel.parts):
        return True
    if rel.parts[0] in _EXCLUDE_TOP_LEVEL_DIRS:
        return True
    if any(part.endswith(_EGG_INFO_SUFFIX) for part in rel.parts):
        return True
    if rel.suffix in _EXCLUDE_SUFFIXES:
        return True
    if any("/".join(rel.parts).startswith(p) for p in _EXCLUDE_REL_PREFIXES):
        return True
    return False


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _files(root: Path) -> dict[str, str]:
    """rel-path -> sha256 for every non-excluded file under root."""
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if _excluded(rel):
            continue
        out[str(rel)] = _sha256(path)
    return out


def plan_refresh(workspace_root: Path, vendor_root: Path) -> tuple[list[str], list[str], list[str]]:
    """Compute the mirror plan: (copy, overwrite, delete) rel-path lists.

    ``copy`` = new in workspace, absent from vendor. ``overwrite`` = present
    both sides but drifted. ``delete`` = only in vendor (e.g. files removed
    workspace-side — the compliance-residue class; a copy-only refresh would
    leave these behind forever).
    """
    ws = _files(workspace_root)
    vd = _files(vendor_root)
    copy = sorted(set(ws) - set(vd))
    overwrite = sorted(r for r in set(ws) & set(vd) if ws[r] != vd[r])
    delete = sorted(set(vd) - set(ws))
    return copy, overwrite, delete


def _prune_empty_dirs(root: Path) -> int:
    """Remove now-empty dirs under root (after deletions); returns count."""
    pruned = 0
    if not root.is_dir():
        return pruned
    # Bottom-up: deepest first, never the root itself.
    dirs = sorted((p for p in root.rglob("*") if p.is_dir()),
                  key=lambda p: len(p.parts), reverse=True)
    for d in dirs:
        try:
            next(d.iterdir())
        except StopIteration:
            d.rmdir()
            pruned += 1
        except OSError:
            continue
    return pruned


def apply_refresh(workspace_root: Path, vendor_root: Path) -> tuple[list[str], list[str], list[str]]:
    """Apply the mirror plan; returns the applied (copy, overwrite, delete)."""
    copy, overwrite, delete = plan_refresh(workspace_root, vendor_root)
    for rel in copy + overwrite:
        src = workspace_root / rel
        dst = vendor_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for rel in delete:
        dst = vendor_root / rel
        try:
            dst.unlink()
        except FileNotFoundError:
            pass
    _prune_empty_dirs(vendor_root)
    return copy, overwrite, delete


def _print_plan(label: str, copy: list[str], overwrite: list[str], delete: list[str]) -> None:
    print(f"== {label}: copy={len(copy)} overwrite={len(overwrite)} delete={len(delete)}")
    for rel in copy:
        print(f"   + {rel}")
    for rel in overwrite:
        print(f"   ~ {rel}")
    for rel in delete:
        print(f"   - {rel}  (deleted workspace-side)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true",
        help="do not modify anything; exit 1 if a refresh is due (drift)",
    )
    args = parser.parse_args(argv)

    worst = 0
    for label, ws_rel, vd_rel in SNAPSHOTS:
        ws = REPO_ROOT / ws_rel
        vd = REPO_ROOT / vd_rel
        if not ws.is_dir():
            print(f"!! {label}: workspace package missing: {ws_rel}", file=sys.stderr)
            worst = 2
            continue
        copy, overwrite, delete = plan_refresh(ws, vd)
        due = bool(copy or overwrite or delete)
        if args.check:
            if due:
                _print_plan(label, copy, overwrite, delete)
                worst = 1
            else:
                print(f"== {label}: vendor snapshot is current (0 drift)")
            continue
        if not due:
            print(f"== {label}: vendor snapshot is current (nothing to do)")
            continue
        _print_plan(label, copy, overwrite, delete)
        apply_refresh(ws, vd)
        # Verify the applied state is an exact mirror.
        c2, o2, d2 = plan_refresh(ws, vd)
        if c2 or o2 or d2:
            print(f"!! {label}: refresh did NOT converge — residual drift: "
                  f"copy={len(c2)} overwrite={len(o2)} delete={len(d2)}",
                  file=sys.stderr)
            worst = 2
        else:
            print(f"== {label}: refreshed — vendor now mirrors the workspace exactly")
    if args.check and worst == 1:
        print("!! vendor drift detected — run: python scripts/sync_vendor.py",
              file=sys.stderr)
    return worst


if __name__ == "__main__":
    sys.exit(main())
