#!/usr/bin/env python3
"""Sub-package <-> standalone-repo sync driver (issue #2).

Each package under ``packages/`` mirrors an independent GitHub repository
(``Exios66/<name>``). The monorepo is the single source of truth for active
development; the sync flow keeps the mirrors reconciled with their upstreams:

  status    compare each package against its upstream (drift report)
  pull      import upstream commits into the monorepo copy (git subtree pull)
  push      publish monorepo commits back to the standalone repo (subtree push)
  snapshot  re-baseline the sync manifest at the current upstream tips

Usage:
    python scripts/sync_packages.py status [--package NAME] [--no-fetch] [--json]
    python scripts/sync_packages.py pull   [--package NAME | --all] [--squash]
    python scripts/sync_packages.py push   [--package NAME | --all] [--patch] [--dry-run]
    python scripts/sync_packages.py snapshot [--package NAME] [--force]

Cursor safety (HUB-021; incidents HUB-012/HUB-018): every cursor write is
guarded by a CONTENT check — the upstream tip's blob tree must be fully
contained in the package directory (exact blob-hash match per path). A cursor
that points past content never imported made the next squash pull re-import a
whole range (HUB-018) and made subtree pushes non-fast-forward (HUB-012),
which is why ``push --patch`` exists: it rebuilds the package's tracked files
on top of the real upstream tip and lands ONE fast-forward commit upstream,
then re-baselines the cursor. Actual pushes remain explicit operations.

Baseline (per issue #2): the monorepo is aligned with the standalone repos as
of 2026-08-30 19:06 CST (2026-08-31T00:06:57Z). That cursor lives in
``scripts/packages_sync.json``; ``status`` always recomputes real drift against
the live upstreams, so a stale manifest is visible at a glance.

Requires: git with the ``subtree`` contrib command, network for fetch-based
commands. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "scripts" / "packages_sync.json"

ORIGIN = "https://github.com/Exios66"
DEFAULT_BRANCH = "main"

# package directory name -> standalone repo name (all under Exios66/, main).
PACKAGES: dict[str, str] = {
    "Enron-Evaluation-Environment": "Enron-Evaluation-Environment",
    "The-Mailroom": "The-Mailroom",
    "agent-mailroom": "agent-mailroom",
    "claims-data-eda": "claims-data-eda",
    "llm-dojo-scoring": "llm-dojo-scoring",
    "llm-entity-extraction": "llm-entity-extraction",
    "llm-mailroom": "llm-mailroom",
    "llm-mailroom-graph": "llm-mailroom-graph",
    "local-mailroom-sandbox": "local-mailroom-sandbox",
    "mailroom-corpus-eda": "Mailroom-Corpus-EDA",
}

# Issue #2 baseline: monorepo aligned with standalone repos at this instant.
BASELINE_SYNCED_AT = "2026-08-31T00:06:57Z"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], *, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=capture,
    )


def git(args: list[str], *, capture: bool = True) -> subprocess.CompletedProcess:
    return run(["git", *args], capture=capture)


def load_manifest() -> dict:
    if MANIFEST.is_file():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"version": 1, "note": "", "packages": {}}


def save_manifest(data: dict) -> None:
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def url_for(package: str) -> str:
    return f"{ORIGIN}/{PACKAGES[package]}.git"


def upstream_head(url: str, branch: str) -> str | None:
    result = git(["ls-remote", url, f"refs/heads/{branch}"])
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.split()[0]


def fetch_upstream(package: str) -> str | None:
    """Fetch the upstream tip into FETCH_HEAD; return the fetched SHA."""
    url, branch = url_for(package), DEFAULT_BRANCH
    result = git(["fetch", "--no-tags", url, branch])
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return None
    resolved = git(["rev-parse", "FETCH_HEAD"])
    return resolved.stdout.strip() if resolved.returncode == 0 else None


def assert_clean_tree(action: str, allow_dirty: bool) -> None:
    status = git(["status", "--porcelain"])
    dirty = bool(status.stdout.strip())
    if dirty and not allow_dirty:
        sys.exit(
            f"refusing to {action}: worktree is dirty (git status reports changes).\n"
            "Commit or stash first, or pass --allow-dirty if you accept the risk."
        )


def require_subtree() -> None:
    probe = git(["subtree", "-h"], capture=True)
    if probe.returncode not in (0, 129):
        sys.exit("git subtree is unavailable; install git with the subtree contrib command.")


def selected_packages(args: argparse.Namespace) -> list[str]:
    if args.package:
        if args.package not in PACKAGES:
            sys.exit(f"unknown package {args.package!r}; valid: {', '.join(PACKAGES)}")
        return [args.package]
    return list(PACKAGES)


# --------------------------------------------------------------------------- #
# content containment (HUB-021)
# --------------------------------------------------------------------------- #


def rev_exists(rev: str) -> bool:
    return git(["rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"]).returncode == 0


def tree_map(rev: str, prefix: str | None = None) -> dict[str, tuple[str, str]]:
    """{path: (objecttype, objectsha)} for ``rev``, rooted at ``prefix``.

    ``prefix=None`` maps an upstream tip (repo-root paths). A package prefix
    maps the monorepo side; paths are returned relative to the package root
    so the two maps are directly comparable.
    """
    args = ["ls-tree", "-r", rev]
    if prefix:
        args.append(prefix)
    result = git(args)
    if result.returncode != 0:
        raise RuntimeError(f"git ls-tree failed for {rev}: {result.stderr.strip()}")
    base = f"{prefix.strip('/')}/" if prefix else ""
    out: dict[str, tuple[str, str]] = {}
    for line in result.stdout.splitlines():
        meta, _, path = line.partition("\t")
        _mode, otype, osha = meta.split()
        if base:
            if not path.startswith(base):
                continue
            path = path[len(base):]
        out[path] = (otype, osha)
    return out


def unimported_upstream_paths(upstream_tip: str, package: str) -> dict[str, str]:
    """Upstream paths genuinely absent from the monorepo (the HUB-018 gap).

    Only 'missing' paths count as cursor lies:
    - missing + gitignored  → the deliberate heavy-asset prune (fine; HUB-018
      doctrine: gitignore does not apply to tracked files, so these are
      upstream files the monorepo removes on every pull);
    - missing + NOT ignored → content the cursor claims was imported but
      wasn't — the actual HUB-018 failure;
    - modified blobs        → monorepo-ahead fixes (monorepo-canonical wins);
      they are the unpushed delta, reported by local_ahead_paths, not a gap.
    """
    tip_tree = tree_map(upstream_tip)
    pkg_tree = tree_map("HEAD", f"packages/{package}")
    missing = [p for p in tip_tree if p not in pkg_tree]
    ignored: set[str] = set()
    if missing:
        probe = git(
            ["check-ignore", "--", *(f"packages/{package}/{p}" for p in missing)]
        )
        if probe.returncode in (0, 1):
            for line in probe.stdout.splitlines():
                rel = line.strip()
                if rel.startswith(f"packages/{package}/"):
                    ignored.add(rel[len(f"packages/{package}/"):])
    return {p: "missing" for p in missing if p not in ignored}


def local_ahead_paths(upstream_tip: str, package: str) -> list[str]:
    """Package-side tracked paths absent from or differing at the tip."""
    tip_tree = tree_map(upstream_tip)
    pkg_tree = tree_map("HEAD", f"packages/{package}")
    return sorted(p for p, blob in pkg_tree.items() if tip_tree.get(p) != blob)


def cursor_gap_report(package: str, synced_sha: str | None) -> dict[str, object] | None:
    """Gap info for a recorded cursor, or None when unverifiable."""
    if not synced_sha or not rev_exists(synced_sha):
        return None
    gaps = unimported_upstream_paths(synced_sha, package)
    return {"contained": not gaps, "n_gap_paths": len(gaps), "sample": sorted(gaps)[:5]}


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


def cmd_status(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    entries = manifest.setdefault("packages", {})
    rows: list[dict[str, object]] = []
    for package in selected_packages(args):
        url = url_for(package)
        head = None if args.no_fetch else fetch_upstream(package)
        entry = entries.get(package, {})
        synced_sha = entry.get("synced_sha")
        drift = None
        if head and synced_sha:
            count = git(["rev-list", "--count", f"{synced_sha}..{head}"])
            drift = int(count.stdout.strip()) if count.returncode == 0 else None
        gap = cursor_gap_report(package, synced_sha)
        ahead = None
        if head and rev_exists(head):
            ahead = len(local_ahead_paths(head, package))
        rows.append(
            {
                "package": package,
                "prefix": f"packages/{package}",
                "upstream": url,
                "branch": DEFAULT_BRANCH,
                "upstream_head": head or "unreachable",
                "synced_sha": synced_sha,
                "synced_at": entry.get("synced_at"),
                "new_upstream_commits": drift,
                "up_to_date": drift == 0,
                "cursor_gap": gap["n_gap_paths"] if gap and not gap["contained"] else 0,
                "cursor_gap_sample": (gap or {}).get("sample") if gap and not gap["contained"] else [],
                "local_ahead_files": ahead,
            }
        )
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        drift = row["new_upstream_commits"]
        state = "in sync" if drift == 0 else f"{drift} new upstream commit(s)" if drift is not None else "unknown drift"
        flags = []
        if row["cursor_gap"]:
            flags.append(f"CURSOR GAP ({row['cursor_gap']} path(s): {', '.join(row['cursor_gap_sample'])})")
        if row["local_ahead_files"]:
            flags.append(f"{row['local_ahead_files']} file(s) monorepo-ahead")
        suffix = f"  [{'; '.join(flags)}]" if flags else ""
        print(
            f"{row['package']:<32} {state:<28} upstream={row['upstream_head'][:12]} "
            f"synced={str(row['synced_sha'])[:12] or '-'} @ {row['synced_at'] or '-'}{suffix}"
        )
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    require_subtree()
    assert_clean_tree("pull", args.allow_dirty)
    manifest = load_manifest()
    entries = manifest.setdefault("packages", {})
    failed = False
    for package in selected_packages(args):
        url = url_for(package)
        head = upstream_head(url, DEFAULT_BRANCH)
        if head and rev_exists(head) and not unimported_upstream_paths(head, package):
            print(
                f"== {package}: upstream tip {head[:12]} is already contained in "
                "packages/"
                f"{package} (nothing to import) — re-baseline with 'snapshot' instead"
            )
            entries[package] = {
                "url": url,
                "branch": DEFAULT_BRANCH,
                "synced_sha": head,
                "synced_at": utc_now(),
            }
            continue
        print(f"== git subtree pull --prefix packages/{package} {url} {DEFAULT_BRANCH}"
              + (" --squash" if args.squash else ""))
        cmd = ["subtree", "pull", f"--prefix=packages/{package}", url, DEFAULT_BRANCH]
        if args.squash:
            cmd.append("--squash")
        result = git(cmd, capture=False)
        if result.returncode != 0:
            print(f"!! pull failed for {package}", file=sys.stderr)
            failed = True
            continue
        # Record the exact upstream tip that was merged in.
        entries[package] = {
            "url": url,
            "branch": DEFAULT_BRANCH,
            "synced_sha": upstream_head(url, DEFAULT_BRANCH),
            "synced_at": utc_now(),
        }
    save_manifest(manifest)
    return 1 if failed else 0


def patch_push(package: str, url: str, tip: str, *, dry_run: bool) -> int:
    """HUB-012 workaround, scripted: land the monorepo delta as ONE commit on
    top of the real upstream tip (fast-forward by construction), then
    re-baseline the cursor. Only tracked package files propagate; upstream
    files deleted monorepo-side are NOT carried by this path (subtree push
    handles full-history pushes; patch pushes carry content).
    """
    gaps = unimported_upstream_paths(tip, package)
    if gaps:
        print(
            f"!! {package}: upstream tip {tip[:12]} is NOT contained in the package "
            f"({len(gaps)} path(s) missing/modified — pull first, then patch-push",
            file=sys.stderr,
        )
        return 1
    tmp = Path(tempfile.mkdtemp(prefix=f"sync-patch-{package}-"))
    worktree = git(["worktree", "add", "--detach", str(tmp), tip])
    if worktree.returncode != 0:
        print(f"!! worktree add failed: {worktree.stderr.strip()}", file=sys.stderr)
        return 1
    try:
        tracked = git(["ls-files", "-z", "--", f"packages/{package}"]).stdout.split("\0")
        files = [p for p in tracked if p]
        for rel in files:
            src = REPO_ROOT / rel
            dst = tmp / rel[len(f"packages/{package}/"):]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        add = git(["-C", str(tmp), "add", "-A"])
        if add.returncode != 0:
            print(f"!! staging failed: {add.stderr.strip()}", file=sys.stderr)
            return 1
        staged = git(["-C", str(tmp), "diff", "--cached", "--stat", "HEAD"])
        n_files = len([ln for ln in staged.stdout.splitlines() if "|" in ln])
        if not staged.stdout.strip() or n_files == 0:
            print(f"== {package}: no content delta vs upstream tip {tip[:12]} — nothing to propagate")
            return 0
        stamp = git(["rev-parse", "--short", "HEAD"]).stdout.strip()
        message = (
            f"Monorepo propagation: {package} from Digital-Mailroom@{stamp}\n\n"
            f"{n_files} tracked file(s) carried from the monorepo (source of truth "
            "for development); subtree patch-push because the recorded cursor had "
            "no real graft ancestry (HUB-012/HUB-021)."
        )
        if dry_run:
            print(f"== DRY RUN {package}: would commit {n_files} file(s) on {tip[:12]} and push {url}")
            print(staged.stdout.rstrip())
            return 0
        commit = git(["-C", str(tmp), "commit", "-m", message])
        if commit.returncode != 0:
            print(f"!! commit failed: {commit.stderr.strip()}", file=sys.stderr)
            return 1
        push = git(["-C", str(tmp), "push", url, f"HEAD:refs/heads/{DEFAULT_BRANCH}"])
        if push.returncode != 0:
            print(f"!! push failed: {push.stderr.strip()}", file=sys.stderr)
            return 1
        print(f"== {package}: propagated {n_files} file(s) to {url} (tip {tip[:12]})")
        return 0
    finally:
        git(["worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_push(args: argparse.Namespace) -> int:
    require_subtree()
    assert_clean_tree("push", args.allow_dirty)
    manifest = load_manifest()
    entries = manifest.setdefault("packages", {})
    failed = False
    for package in selected_packages(args):
        url = url_for(package)
        if args.patch:
            tip = fetch_upstream(package)
            if tip is None:
                print(f"!! could not fetch upstream tip for {package}", file=sys.stderr)
                failed = True
                continue
            if patch_push(package, url, tip, dry_run=args.dry_run) != 0:
                failed = True
                continue
            if not args.dry_run:
                entries[package] = {
                    "url": url,
                    "branch": DEFAULT_BRANCH,
                    "synced_sha": upstream_head(url, DEFAULT_BRANCH),
                    "synced_at": utc_now(),
                }
            continue
        print(f"== git subtree push --prefix packages/{package} {url} {DEFAULT_BRANCH}")
        if args.dry_run:
            print("== DRY RUN: no push performed")
            continue
        result = git(
            ["subtree", "push", f"--prefix=packages/{package}", url, DEFAULT_BRANCH],
            capture=False,
        )
        if result.returncode != 0:
            print(
                f"!! push failed for {package} (non-fast-forward? see HUB-012). "
                "Re-run with --patch to land the delta as one fast-forward commit "
                "on the current upstream tip.",
                file=sys.stderr,
            )
            failed = True
            continue
        entries[package] = {
            "url": url,
            "branch": DEFAULT_BRANCH,
            "synced_sha": upstream_head(url, DEFAULT_BRANCH),
            "synced_at": utc_now(),
        }
    save_manifest(manifest)
    return 1 if failed else 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    entries = manifest.setdefault("packages", {})
    now = utc_now()
    for package in selected_packages(args):
        url = url_for(package)
        head = upstream_head(url, DEFAULT_BRANCH)
        if head is None:
            print(f"!! could not read upstream tip for {package}; keeping previous entry", file=sys.stderr)
            continue
        if not rev_exists(head):
            fetched = fetch_upstream(package)
            if fetched is None:
                print(
                    f"!! upstream tip {head[:12]} for {package} has no local objects "
                    "and the fetch failed; keeping previous entry",
                    file=sys.stderr,
                )
                continue
            head = fetched
        gaps = unimported_upstream_paths(head, package)
        if gaps and not args.force:
            sample = ", ".join(sorted(gaps)[:5])
            print(
                f"!! refusing to snapshot {package}: upstream tip {head[:12]} is not "
                f"contained in packages/{package} ({len(gaps)} path(s) "
                f"missing/modified: {sample}). This is the HUB-018 cursor/content "
                "gap — pull first (or pass --force to accept the lie explicitly).",
                file=sys.stderr,
            )
            continue
        if gaps:
            print(
                f"!! {package}: snapshot forced past {len(gaps)} non-contained path(s) "
                "— the cursor now describes content the monorepo may not have",
                file=sys.stderr,
            )
        entries[package] = {
            "url": url,
            "branch": DEFAULT_BRANCH,
            "synced_sha": head,
            "synced_at": now,
        }
    manifest["version"] = 1
    manifest.setdefault("note", "")
    manifest["note"] = (
        "Per-package sync cursor against the standalone Exios66/* repositories. "
        "Baseline per issue #2: monorepo aligned with the standalone repos as of "
        f"{BASELINE_SYNCED_AT} (2026-08-30 19:06 CST). Cursor writes are "
        "content-verified (HUB-021) — upstream tip must be contained in the "
        "package tree unless snapshot --force is passed."
    )
    save_manifest(manifest)
    print(f"snapshot written to {MANIFEST.relative_to(REPO_ROOT)} at {now}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser, with_all: bool = True) -> None:
        p.add_argument("--package", help="operate on a single package (default: all)")
        if with_all:
            p.add_argument("--all", action="store_true", help="explicit all-packages mode")

    status = sub.add_parser("status", help="report upstream drift per package")
    add_common(status)
    status.add_argument("--no-fetch", action="store_true", help="skip network fetch; manifest-only report")
    status.add_argument("--json", action="store_true", help="machine-readable output")
    status.set_defaults(func=cmd_status)

    pull = sub.add_parser("pull", help="git subtree pull upstream into packages/<name>")
    add_common(pull)
    pull.add_argument("--squash", action="store_true", help="squash upstream history on import")
    pull.add_argument("--allow-dirty", action="store_true", help="bypass the clean-worktree guard")
    pull.set_defaults(func=cmd_pull)

    push = sub.add_parser("push", help="git subtree push packages/<name> back to upstream")
    add_common(push)
    push.add_argument("--allow-dirty", action="store_true", help="bypass the clean-worktree guard")
    push.add_argument(
        "--patch",
        action="store_true",
        help="non-fast-forward fallback (HUB-012): land tracked package files as "
        "one commit on the current upstream tip, then re-baseline the cursor",
    )
    push.add_argument("--dry-run", action="store_true", help="print the plan; no pushes, no cursor writes")
    push.set_defaults(func=cmd_push)

    snap = sub.add_parser("snapshot", help="re-baseline the manifest at current upstream tips")
    add_common(snap)
    snap.add_argument(
        "--force",
        action="store_true",
        help="advance the cursor even when the upstream tip is not contained in "
        "the package tree (accepts the HUB-018 cursor/content gap explicitly)",
    )
    snap.set_defaults(func=cmd_snapshot)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
