#!/usr/bin/env python3
"""Sub-package <-> standalone-repo sync driver (issue #2, DMR-064).

Each package under ``packages/`` mirrors an independent GitHub repository
(``Exios66/<name>``). The monorepo is the single source of truth for active
development; the sync flow keeps the mirrors reconciled with their upstreams:

  status    compare each package against its upstream (drift report)
  pull      import upstream commits into the monorepo copy (git subtree pull)
  push      publish monorepo commits back to the standalone repo (subtree push)
  snapshot  re-baseline the sync manifest at the current upstream tips

Usage:
    python scripts/sync_packages.py [--manifest PATH] [--repo-root PATH] \\
        status [--package NAME | --all] [--no-fetch] [--json]
    python scripts/sync_packages.py [--manifest PATH] [--repo-root PATH] \\
        pull [--package NAME | --all] [--squash] [--allow-dirty] [--verify-suite] \\
             [--open-pr [--resolve ours|theirs] | --keep-conflicts] [--json]
    python scripts/sync_packages.py [--manifest PATH] [--repo-root PATH] \\
        push [--package NAME | --all] [--allow-dirty] [--patch] [--verify-suite] \\
             [--dry-run] [--json]
    python scripts/sync_packages.py [--manifest PATH] [--repo-root PATH] \\
        snapshot [--package NAME | --all] [--force] [--json]

Exit codes (DMR-064 taxonomy, +5 DMR-070):
  0  ok
  1  network/fetch failure  — upstream unreachable (ls-remote / fetch failed)
  2  dirty worktree refusal at entry, or a merge conflict LEFT in place
     (--keep-conflicts / --allow-dirty blocked the auto-abort)
  3  merge conflict — aborted cleanly (worktree restored to the pre-pull state)
  4  other git/internal failure — unknown package, corrupt manifest, missing
     git subtree, worktree add/remove failure, gh missing, abort failure
  5  verification refused (DMR-070) — ``--verify-suite`` ran the touched
     package's suite and it FAILED, or the patch-push deletion guard refused
     to content-push a package whose monorepo tree deletes tracked upstream
     paths (content pushes can never carry deletions)

Multi-package runs return the highest (most severe) code observed
(severity order 5 > 4 > 3 > 2 > 1 > 0).

Conflict handling (pull): a nonzero ``git subtree pull`` is probed for real
merge state (MERGE_HEAD present AND unmerged paths via ``diff --diff-filter=U``
+ ``git ls-files -u`` + ``git status --porcelain=v1``). When a conflict is
real, the default is ``git merge --abort`` (only when the script verified a
clean entry state) plus a structured per-path summary and exit 3.
``--keep-conflicts`` leaves the merge in place for manual resolution;
``--allow-dirty`` also blocks the auto-abort (it would clobber the user's
pre-existing uncommitted work).

PR branch flow (pull --open-pr): on conflict the pull is aborted, a branch
``sync/<package>/import-<upstream12>`` is created from main, the upstream is
fetched and merged with ``git merge --no-ff -s recursive
-X subtree=packages/<package> -X <ours|theirs> FETCH_HEAD`` (git-subtree has
no ``-X`` passthrough; ours = monorepo content wins, the HUB-021 containment
doctrine — ``theirs`` drops monorepo content), remaining add/add /
modify-delete paths are taken via ``git checkout --ours/--theirs`` (or
``git rm -f`` to keep a deletion), the merge is committed, pushed, and a PR
against main is opened via ``gh``. The sync cursor is NEVER advanced from a
branch/PR state — it bounces only when the import lands on main
(``unimported_upstream_paths`` stays the containment safety net).

Post-import verification (DMR-070, the v0.6.0 lessons): (a) every resolved
conflict path is blob-compared against BOTH merge sides — a resolution that
matches neither side (the v0.6 ``corpus.py`` else-branch mangling class) is
reported loudly on stderr, carried as ``resolution_divergences`` in the JSON
record, and appended to the PR body; (b) ``--verify-suite`` runs the touched
package's test suite (default: ``pytest packages/<pkg>/[src/]tests -q -x``;
``SYNC_VERIFY_CMD`` overrides) — pull refuses to advance the cursor, the
branch flow refuses to push/open the PR, and ``push --patch`` refuses to
push, whenever the suite fails; (c) ``push --patch`` REFUSES (exit 5,
``deleted_paths``) any package whose monorepo tree deletes tracked upstream
paths — content pushes cannot carry deletions; use the full subtree-push leg.

--json parity: each of pull/push/snapshot emits one JSON document per package
(JSON Lines on stdout, even on failure — human text goes to stderr):
{command, package, ok, exit_code, error_class: "network"|"dirty"|"conflict"
|"git"|"verify"|"ok", conflicted_paths: [{path, kind}], remediation,
cursor_updated, branch, pr_url}  (+ upstream_tip/resolution/aborted where
relevant; DMR-070 additions: ``deleted_paths`` on a refused patch push,
``resolution_divergences`` on a resolved import, ``verify_detail_tail`` on a
failed --verify-suite).

Cursor safety (HUB-021; incidents HUB-012/HUB-018): every cursor write is
guarded by a CONTENT check — the upstream tip's blob tree must be fully
contained in the package directory (exact blob-hash match per path). A cursor
that points past content never imported made the next squash pull re-import a
whole range (HUB-018) and made subtree pushes non-fast-forward (HUB-012),
which is why ``push --patch`` exists: it rebuilds the package's tracked files
on top of the real upstream tip and lands ONE fast-forward commit upstream,
then re-baselines the cursor. Actual pushes remain explicit operations. The
manifest is written atomically (temp file + ``os.replace``); a corrupt
manifest is never overwritten (exit 4 with a repair hint). ``push --patch``
saves each package's cursor entry immediately after its push so an interrupt
cannot desync one package's cursor.

Baseline (per issue #2): the monorepo is aligned with the standalone repos as
of 2026-08-30 19:06 CST (2026-08-31T00:06:57Z). That cursor lives in
``scripts/packages_sync.json``; ``status`` always recomputes real drift against
the live upstreams, so a stale manifest is visible at a glance.

Test seams (hermetic harness in scripts/tests/): ``--manifest`` and
``--repo-root`` override the manifest path and the git working directory;
``SYNC_PACKAGES_ORIGIN`` overrides the upstream URL prefix (default
https://github.com/Exios66) so local fixtures can stand in for the remotes.

Requires: git with the ``subtree`` contrib command, network for fetch-based
commands. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

E_OK, E_NETWORK, E_DIRTY, E_CONFLICT, E_GIT, E_VERIFY = 0, 1, 2, 3, 4, 5
ERROR_CLASS = {
    E_OK: "ok",
    E_NETWORK: "network",
    E_DIRTY: "dirty",
    E_CONFLICT: "conflict",
    E_GIT: "git",
    E_VERIFY: "verify",
}

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "scripts" / "packages_sync.json"

ORIGIN = os.environ.get("SYNC_PACKAGES_ORIGIN", "https://github.com/Exios66")
DEFAULT_BRANCH = "main"

# JSON Lines mode: records go to stdout, human progress to stderr.
JSON_MODE = False

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


def _rel_or_abs(path: Path) -> str:
    """Manifest path for humans — relative to the repo root when possible."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def run(cmd: list[str], *, capture: bool = True, binary: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        check=False,
        text=not binary,
        capture_output=capture,
    )


def git(args: list[str], *, capture: bool = True, binary: bool = False) -> subprocess.CompletedProcess:
    return run(["git", *args], capture=capture, binary=binary)


def git_foreground(args: list[str]) -> subprocess.CompletedProcess:
    """Live-output git call; under --json the output is replayed to stderr so
    stdout stays pure JSON Lines."""
    if JSON_MODE:
        result = git(args, capture=True)
        if result.stdout:
            sys.stderr.write(result.stdout)
            sys.stderr.flush()
        return result
    return git(args, capture=False)


def info(msg: str) -> None:
    """Progress line: stdout in human mode, stderr in --json mode."""
    print(msg, file=sys.stderr if JSON_MODE else sys.stdout)


def warn(msg: str) -> None:
    print(msg, file=sys.stderr)


# --------------------------------------------------------------------------- #
# JSON records (DMR-064)
# --------------------------------------------------------------------------- #


def base_record(command: str, package: str | None) -> dict:
    return {
        "command": command,
        "package": package,
        "ok": False,
        "exit_code": E_GIT,
        "error_class": "git",
        "conflicted_paths": [],
        "remediation": None,
        "cursor_updated": False,
        "branch": None,
        "pr_url": None,
    }


def record_ok(command: str, package: str, *, cursor_updated: bool = False, branch: str | None = None,
              pr_url: str | None = None) -> dict:
    return {
        "command": command,
        "package": package,
        "ok": True,
        "exit_code": E_OK,
        "error_class": "ok",
        "conflicted_paths": [],
        "remediation": None,
        "cursor_updated": cursor_updated,
        "branch": branch,
        "pr_url": pr_url,
    }


def emit(record: dict) -> None:
    """Machine record: stdout JSONL under --json, no-op in human mode."""
    if JSON_MODE:
        print(json.dumps(record, sort_keys=True))


def fail(command: str, code: int, message: str, *, package: str | None = None,
         remediation: str | None = None, extra: dict | None = None) -> None:
    """Emit a failure record and raise SystemExit(code) (human text on stderr)."""
    record = base_record(command, package)
    record["exit_code"] = code
    record["error_class"] = ERROR_CLASS[code]
    record["remediation"] = remediation
    if extra:
        record.update(extra)
    emit(record)
    if remediation:
        warn(message + f"\n  Remediation: {remediation}")
    else:
        warn(message)
    raise SystemExit(code)


# --------------------------------------------------------------------------- #
# manifest (atomic writes, repair hint on corruption)
# --------------------------------------------------------------------------- #


def load_manifest(command: str) -> dict:
    if not MANIFEST.is_file():
        return {"version": 1, "note": "", "packages": {}}
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        fail(
            command,
            E_GIT,
            f"sync manifest is corrupt: {MANIFEST} ({exc.__class__.__name__}: {exc})",
            remediation=(
                f"restore the last good cursor: git checkout -- {_rel_or_abs(MANIFEST)} "
                "(or repair the file by hand); the sync tool refuses to overwrite a corrupt cursor"
            ),
            extra={"manifest": str(MANIFEST)},
        )
    if not isinstance(data, dict):
        fail(
            command,
            E_GIT,
            f"sync manifest {MANIFEST} is not a JSON object ({type(data).__name__})",
            remediation=f"repair {_rel_or_abs(MANIFEST)} by hand or restore: git checkout -- {_rel_or_abs(MANIFEST)}",
            extra={"manifest": str(MANIFEST)},
        )
    return data


def save_manifest(data: dict) -> None:
    """Atomic manifest write: temp file + os.replace (no partial reads ever)."""
    tmp = Path(str(MANIFEST) + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, MANIFEST)


# --------------------------------------------------------------------------- #
# upstream plumbing
# --------------------------------------------------------------------------- #


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
        warn(result.stderr.strip())
        return None
    resolved = git(["rev-parse", "FETCH_HEAD"])
    return resolved.stdout.strip() if resolved.returncode == 0 else None


# --------------------------------------------------------------------------- #
# entry guards (DMR-064: real exit codes + leftover-merge recovery)
# --------------------------------------------------------------------------- #


def assert_clean_tree(command: str, action: str, allow_dirty: bool) -> None:
    if merge_in_progress():
        cs = classify_conflicts()
        fail(
            command,
            E_DIRTY,
            f"refusing to {action}: leftover merge state from a previous failed sync "
            f"(MERGE_HEAD present, {len(cs)} unmerged path(s)). A stale merge is NOT a "
            "plain dirty tree — --allow-dirty does not bypass it.",
            remediation=(
                "resolve or discard the stale merge first: run `git merge --abort` "
                "(or finish/reset manually), then re-run"
            ),
            extra={"conflicted_paths": [{"path": p["path"], "kind": p["kind"]} for p in cs],
                   "leftover_merge": True},
        )
    status = git(["status", "--porcelain"])
    dirty = bool(status.stdout.strip())
    if dirty and not allow_dirty:
        fail(
            command,
            E_DIRTY,
            f"refusing to {action}: worktree is dirty (git status reports changes).",
            remediation="commit or stash first, or pass --allow-dirty if you accept the risk",
        )


def require_subtree(command: str) -> None:
    probe = git(["subtree", "-h"], capture=True)
    if probe.returncode not in (0, 129):
        fail(
            command,
            E_GIT,
            "git subtree is unavailable; install git with the subtree contrib command.",
            remediation="install git-subtree (shipped with git contrib; on macOS: brew install git)",
        )


def selected_packages(command: str, args: argparse.Namespace) -> list[str]:
    if args.package:
        if args.package not in PACKAGES:
            fail(
                command,
                E_GIT,
                f"unknown package {args.package!r}; valid: {', '.join(PACKAGES)}",
                remediation="check the package name against PACKAGES in scripts/sync_packages.py",
            )
        return [args.package]
    return list(PACKAGES)


# --------------------------------------------------------------------------- #
# conflict detection / classification / abort (DMR-064)
# --------------------------------------------------------------------------- #


def merge_in_progress() -> bool:
    return git(["rev-parse", "-q", "--verify", "MERGE_HEAD"]).returncode == 0


def unmerged_paths() -> list[str]:
    out = git(["diff", "--name-only", "--diff-filter=U"])
    return [ln for ln in out.stdout.splitlines() if ln]


def classify_conflicts() -> list[dict]:
    """Per-path classification from `git ls-files -u` stage info + porcelain codes.

    Stage sets per path determine the kind:
      {1,2,3} both-modified | {2,3} add/add | otherwise modify-delete
      (modify/delete = the blob is missing from one side's stage).
    """
    stages: dict[str, list[int]] = {}
    out = git(["ls-files", "-u", "-z"])
    for rec in out.stdout.split("\0"):
        if not rec:
            continue
        meta, _, path = rec.partition("\t")  # meta never contains tabs
        pieces = meta.split()
        if len(pieces) != 3:
            continue
        stages.setdefault(path, []).append(int(pieces[2]))
    porc: dict[str, str] = {}
    st = git(["status", "--porcelain=v1"])
    for ln in st.stdout.splitlines():
        if len(ln) >= 4 and ln[0] in "UAD" and ln[1] in "UAD":
            path = ln[3:]
            if path.startswith('"') and path.endswith('"'):
                path = path[1:-1]
            porc[path] = ln[:2]
    result = []
    for path, ss in sorted(stages.items()):
        sset = set(ss)
        if 1 in sset and 2 in sset and 3 in sset:
            kind = "both-modified"
        elif 2 in sset and 3 in sset:
            kind = "add/add"
        else:
            kind = "modify-delete"
        result.append(
            {"path": path, "kind": kind, "stages": sorted(sset), "status": porc.get(path)}
        )
    return result


def conflict_state() -> dict | None:
    """Real conflict class: MERGE_HEAD present AND unmerged paths. Else None."""
    if not merge_in_progress():
        return None
    paths = classify_conflicts()
    if not paths:
        return None
    return {"paths": paths}


def abort_merge() -> bool:
    r = git(["merge", "--abort"])
    if r.returncode != 0:
        return False
    if merge_in_progress():
        return False
    if git(["status", "--porcelain"]).stdout.strip():
        return False
    return True


def conflict_remediation_hint(kind: str) -> str:
    return {
        "both-modified": "both sides edited this file; resolve by hand or re-run with "
                         "--open-pr --resolve ours|theirs (ours = monorepo content wins)",
        "add/add": "both sides added this path; --open-pr resolves via checkout --ours/--theirs",
        "modify-delete": "one side modified, the other deleted; --open-pr resolves via "
                         "checkout --ours/--theirs (or keeps the deletion with git rm)",
    }.get(kind, "resolve manually")


def render_conflict_summary(package: str, head: str, cs: dict, *, aborted: bool,
                            pr_url: str | None = None) -> None:
    warn(f"!! CONFLICT importing {package} upstream {head[:12]} into packages/{package}")
    warn(f"   Merge state detected (MERGE_HEAD) with {len(cs['paths'])} unmerged path(s):")
    for p in cs["paths"]:
        warn(f"     - {p['path']:<50} {p['kind']:<15} stages={p['stages']} "
             f"status={p['status'] or '-'}")
        warn(f"         {conflict_remediation_hint(p['kind'])}")
    if aborted:
        warn("   The pull was ABORTED (git merge --abort): the worktree is restored to its")
        warn("   pre-pull state. Remediation: re-run with --open-pr to land the import via")
        warn("   a PR branch (--resolve ours|theirs), or resolve by hand with a manual pull.")
        if pr_url:
            warn(f"   Import PR opened: {pr_url} — main untouched; the cursor does not advance")
            warn("   until the PR merges.")
    else:
        warn("   The merge was LEFT in place (--keep-conflicts / --allow-dirty blocked the")
        warn("   auto-abort). Remediation: git merge --abort to restore, or resolve the")
        warn("   paths above manually.")


def conflict_record(command: str, package: str, head: str, cs: dict, *, aborted: bool,
                    exit_code: int) -> dict:
    rec = base_record(command, package)
    rec.update(
        {
            "exit_code": exit_code,
            "error_class": "conflict",
            "upstream_tip": head[:12],
            "aborted": aborted,
            "conflicted_paths": [{"path": p["path"], "kind": p["kind"]} for p in cs["paths"]],
            "remediation": (
                "pull aborted cleanly; re-run with --open-pr to import via a PR branch, "
                "or resolve manually"
                if aborted
                else "merge left in the worktree; run `git merge --abort` or resolve the "
                     "conflicting paths manually"
            ),
        }
    )
    return rec


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
    manifest = load_manifest(args.command)
    entries = manifest.setdefault("packages", {})
    rows: list[dict[str, object]] = []
    for package in selected_packages(args.command, args):
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
    require_subtree(args.command)
    assert_clean_tree(args.command, "pull", args.allow_dirty)
    manifest = load_manifest(args.command)
    entries = manifest.setdefault("packages", {})
    worst = E_OK
    for package in selected_packages(args.command, args):
        url = url_for(package)
        head = upstream_head(url, DEFAULT_BRANCH)
        if head is None:
            rec = base_record(args.command, package)
            rec.update(
                {
                    "exit_code": E_NETWORK,
                    "error_class": "network",
                    "remediation": "check connectivity / upstream URL; verify with: "
                                   "git ls-remote <url> main",
                }
            )
            emit(rec)
            warn(f"!! {package}: could not read upstream head (ls-remote failed)")
            worst = max(worst, E_NETWORK)
            continue
        if rev_exists(head) and not unimported_upstream_paths(head, package):
            entries[package] = {
                "url": url,
                "branch": DEFAULT_BRANCH,
                "synced_sha": head,
                "synced_at": utc_now(),
            }
            save_manifest(manifest)
            info(
                f"== {package}: upstream tip {head[:12]} is already contained in "
                "packages/"
                f"{package} (nothing to import) — re-baseline with 'snapshot' instead"
            )
            emit(record_ok(args.command, package, cursor_updated=True))
            continue
        info(
            f"== git subtree pull --prefix packages/{package} {url} {DEFAULT_BRANCH}"
            + (" --squash" if args.squash else "")
        )
        cmd = ["subtree", "pull", f"--prefix=packages/{package}", url, DEFAULT_BRANCH]
        if args.squash:
            cmd.append("--squash")
        result = git_foreground(cmd)
        if result.returncode == 0:
            # DMR-070: --verify-suite gates cursor advance on the touched
            # package's suite. The merge is already committed here; a red
            # suite leaves the merge in place (fix or revert it) and the
            # cursor untouched.
            if getattr(args, "verify_suite", False):
                ok, detail = run_verify_suite(package)
                if not ok:
                    rec = base_record(args.command, package)
                    rec.update(
                        {
                            "exit_code": E_VERIFY,
                            "error_class": ERROR_CLASS[E_VERIFY],
                            "remediation": "verify-suite failed on the imported merge — fix or revert "
                                           f"the merge commit (git reset --hard ORIG_HEAD), then re-run; "
                                           "the cursor was NOT advanced",
                            "verify_detail_tail": detail[-1500:],
                            "upstream_tip": head[:12],
                        }
                    )
                    emit(rec)
                    worst = max(worst, E_VERIFY)
                    continue
            entries[package] = {
                "url": url,
                "branch": DEFAULT_BRANCH,
                "synced_sha": upstream_head(url, DEFAULT_BRANCH),
                "synced_at": utc_now(),
            }
            save_manifest(manifest)
            emit(record_ok(args.command, package, cursor_updated=True))
            continue
        cs = conflict_state()
        if cs is None:
            # Not a merge conflict: probe whether the network is the cause.
            probe = git(["fetch", "--no-tags", url, DEFAULT_BRANCH])
            if probe.returncode != 0:
                rec = base_record(args.command, package)
                rec.update(
                    {
                        "exit_code": E_NETWORK,
                        "error_class": "network",
                        "remediation": "check connectivity / upstream URL; verify with: "
                                       "git ls-remote <url> main",
                    }
                )
                emit(rec)
                warn(
                    f"!! {package}: subtree pull failed (exit {result.returncode}) and the "
                    "upstream is unreachable; the worktree was NOT modified by the pull"
                )
                worst = max(worst, E_NETWORK)
            else:
                rec = base_record(args.command, package)
                rec.update(
                    {
                        "exit_code": E_GIT,
                        "error_class": "git",
                        "remediation": "subtree pull failed WITHOUT a merge conflict — read "
                                       "the git output above (typical causes: missing graft "
                                       "ancestry, untracked-file collisions); the worktree "
                                       "was NOT modified by the pull",
                    }
                )
                emit(rec)
                warn(
                    f"!! {package}: subtree pull failed (exit {result.returncode}) without "
                    "a merge conflict — see the git output above"
                )
                worst = max(worst, E_GIT)
            continue
        # ---- real merge conflict ----
        entry_clean = not args.allow_dirty
        if args.keep_conflicts or not entry_clean:
            # Neither abort (would clobber pre-existing dirt) nor PR branch (needs clean main).
            code = E_DIRTY
            emit(conflict_record(args.command, package, head, cs, aborted=False, exit_code=code))
            render_conflict_summary(package, head, cs, aborted=False)
            worst = max(worst, code)
            continue
        if not abort_merge():
            fail(
                args.command,
                E_GIT,
                f"!! {package}: git merge --abort FAILED to restore a clean tree — the "
                "worktree is in an unknown state",
                remediation=(
                    "run `git merge --abort` manually; inspect `git status`; a hard "
                    "`git reset --hard HEAD` is the destructive last resort"
                ),
                package=package,
                extra={
                    "conflicted_paths": [{"path": p["path"], "kind": p["kind"]} for p in cs["paths"]],
                    "upstream_tip": head[:12],
                },
            )
        # Aborted cleanly — the worktree is back on the pre-pull state.
        if args.open_pr:
            rc, rec = pr_branch_flow(args, package, url, head, cs)
            emit(rec)
            if rc == E_OK:
                render_conflict_summary(package, head, cs, aborted=True, pr_url=rec["pr_url"])
                info(
                    f"== {package}: import PR opened at {rec['pr_url']}; main untouched; "
                    "the cursor does not advance until the PR merges"
                )
            else:
                render_conflict_summary(package, head, cs, aborted=True)
            worst = max(worst, rc)
            continue
        emit(conflict_record(args.command, package, head, cs, aborted=True, exit_code=E_CONFLICT))
        render_conflict_summary(package, head, cs, aborted=True)
        worst = max(worst, E_CONFLICT)
    return worst


def resolve_remaining_ours_theirs(paths: list[dict], side: str) -> bool:
    """Take one side for leftover add/add + modify/delete paths.

    Under a deletion on the preferred side, `git rm -f` keeps the deletion;
    otherwise `git checkout --<side>` + `git add`. Returns False on failure.
    """
    for p in paths:
        path = p["path"]
        stages = p.get("stages") or []
        blob_on_us = 2 in stages
        blob_on_them = 3 in stages
        prefer_deletion = (side == "ours" and not blob_on_us) or (side == "theirs" and not blob_on_them)
        if prefer_deletion:
            rm = git(["rm", "-f", "--", path])
            if rm.returncode != 0:
                warn(f"!! could not keep the deletion for {path} under {side}: {rm.stderr.strip()}")
                return False
            warn(f"   resolved {path}: kept deletion under {side}")
            continue
        co = git(["checkout", f"--{side}", "--", path])
        if co.returncode != 0:
            warn(f"!! checkout --{side} failed for {path}: {co.stderr.strip()}")
            return False
        add = git(["add", "--", path])
        if add.returncode != 0:
            warn(f"!! git add failed for {path}: {add.stderr.strip()}")
            return False
        warn(f"   resolved {path}: took {side} version")
    return True


def pr_body(package: str, url: str, head: str, cs: dict, resolve: str) -> str:
    lines = [
        f"Import upstream `{url}` tip `{head}` into `packages/{package}` via the "
        "DMR-064 PR branch flow (auto-generated by `scripts/sync_packages.py pull --open-pr`).",
        "",
        f"- package: `{package}`",
        f"- upstream: `{url}`",
        f"- upstream tip: `{head}`",
        f"- resolution strategy: `{resolve}`",
        "  - `ours` (default): monorepo content wins — the monorepo is the development "
        "source of truth; per the HUB-021 containment doctrine, modified blobs are "
        "monorepo-ahead fixes, so monorepo versions win.",
        "  - `theirs`: upstream content wins and DROPS monorepo content at the "
        "conflicting paths.",
        "",
        f"Conflicted paths ({len(cs['paths'])}):",
        "",
    ]
    for p in cs["paths"]:
        lines.append(f"- `{p['path']}` — {p['kind']}: {conflict_remediation_hint(p['kind'])}")
    lines += [
        "",
        "Merge executed on the branch:",
        "",
        f"    git merge --no-ff -s recursive -X subtree=packages/{package} -X {resolve} FETCH_HEAD",
        "",
        "Review the merge commit on this branch; main was left untouched. The sync "
        "cursor is not advanced by this PR — it bounces only after the import lands "
        "on main (containment guard: `unimported_upstream_paths`).",
        "",
        "Remediation if something looks wrong: `git merge --abort` on the branch, or "
        "close this PR and re-run with `--resolve theirs`.",
    ]
    return "\n".join(lines)


def pr_branch_flow(args: argparse.Namespace, package: str, url: str, head: str,
                   cs: dict) -> tuple[int, dict]:
    """Import the upstream tip onto a PR branch (`pull --open-pr`).

    Precondition: main clean + the conflicting merge aborted (cmd_pull verified
    a clean entry state). Always ENDS back on main with the local branch
    deleted (a pushed copy survives for the PR). The sync cursor is never
    touched from this flow.
    """
    command = args.command
    sha12 = head[:12]
    branch = f"sync/{package}/import-{sha12}"
    record = base_record(command, package)
    record.update(
        {
            "branch": branch,
            "upstream_tip": sha12,
            "resolution": args.resolve,
            "conflicted_paths": [{"path": p["path"], "kind": p["kind"]} for p in cs["paths"]],
        }
    )

    def teardown(code: int, message: str, remediation: str) -> tuple[int, dict]:
        restore = git(["switch", "-f", "main"])
        if restore.returncode != 0:
            warn("!! could not return to main after the failed branch flow (run: git switch -f main)")
        git(["branch", "-D", branch])
        record.update({"ok": False, "exit_code": code, "error_class": ERROR_CLASS[code],
                       "remediation": remediation})
        warn(message)
        return code, record

    # Drop any stale branch from an earlier interrupted run.
    if git(["rev-parse", "--verify", "--quiet", branch]).returncode == 0:
        git(["branch", "-D", branch])
    made = git(["switch", "-c", branch])
    if made.returncode != 0:
        return teardown(E_GIT, f"!! {package}: could not create branch {branch}",
                        f"inspect git state; branch create failed: {made.stderr.strip()}")
    fetched = git(["fetch", "--no-tags", url, DEFAULT_BRANCH])
    if fetched.returncode != 0:
        return teardown(E_NETWORK, f"!! {package}: fetch of {url} failed",
                        "check connectivity to the upstream repo")
    # DMR-070(a): capture both merge sides BEFORE merging — pre_head is the
    # "ours" blob source, FETCH_HEAD (pinned to a sha NOW, before any other
    # git op can move it) is the "theirs" side (upstream paths carry NO
    # packages/<pkg>/ prefix).
    theirs = git(["rev-parse", "FETCH_HEAD"]).stdout.strip()
    pre_head = git(["rev-parse", "HEAD"]).stdout.strip()
    msg = (
        f"sync: import {package} upstream {sha12} ({args.resolve} resolution) "
        "from Digital-Mailroom — DMR-064 branch flow"
    )
    merged = git_foreground(
        ["merge", "--no-ff", "-m", msg, "-s", "recursive",
         f"-Xsubtree=packages/{package}", f"-X{args.resolve}", "FETCH_HEAD"],
    )
    resolved_paths: list[str] = []
    if merged.returncode != 0:
        cs2 = conflict_state()
        if cs2 is None:
            return teardown(E_GIT, f"!! {package}: strategy merge failed WITHOUT conflicts",
                            f"not a conflicts issue; inspect the merge output above: {merged.stderr.strip()}")
        ok = resolve_remaining_ours_theirs(cs2["paths"], args.resolve)
        if not ok:
            return teardown(E_GIT, f"!! {package}: could not auto-resolve remaining paths under {args.resolve}",
                            "resolve manually on the branch, or abandon: git switch -f main && git branch -D "
                            + branch)
        if conflict_state() is not None:
            return teardown(E_GIT, f"!! {package}: unmerged paths remain after resolution",
                            "resolve manually on the branch, or abandon (git switch -f main)")
        done = git(["commit", "-m", msg])
        if done.returncode != 0:
            return teardown(E_GIT, f"!! {package}: could not commit the resolved merge",
                            f"inspect the commit failure: {done.stderr.strip()}")
        resolved_paths = [p["path"] for p in cs2["paths"]]
    if merge_in_progress():
        return teardown(E_GIT, f"!! {package}: merge state still present after the branch merge",
                        "inspect git status on the branch")
    # DMR-070(a): post-resolution divergence audit — every ladder-resolved
    # path is blob-compared against BOTH merge sides. A resolution matching
    # neither side is resolution-introduced content (the v0.6 corpus.py
    # else-branch mangling shipped exactly this way, silently). The clean
    # -X-strategy path is skipped: its fusion blobs legitimately match
    # neither pure side, so auditing it would only produce false positives.
    divergences = resolution_divergences(package, pre_head, theirs, resolved_paths)
    for d in divergences:
        warn(f"!! {package}: RESOLUTION DIVERGENCE (DMR-070): {d['path']} — "
             f"resolved blob {d['resolved']} matches NEITHER merge side "
             f"(ours {d['ours']}, theirs {d['theirs']}) — review before merging this import")
    record["resolution_divergences"] = divergences
    # DMR-070: --verify-suite gates the push/PR on the touched package's
    # suite. A red suite refuses to push the branch and open the PR.
    if getattr(args, "verify_suite", False):
        ok, detail = run_verify_suite(package)
        if not ok:
            record["verify_detail_tail"] = detail[-1500:]
            return teardown(
                E_VERIFY,
                f"!! {package}: verify-suite FAILED on the import branch — not pushing, not opening a PR",
                "fix the suite on the branch, or abandon it (git switch -f main && git branch -D "
                + branch + ") and re-run",
            )
    pushed = git(["push", "-u", "origin", branch])
    if pushed.returncode != 0:
        return teardown(
            E_GIT,
            f"!! {package}: push of {branch} failed\n{pushed.stderr.strip()}",
            f"push failed (auth/remote?); the branch stays local — resolve and push manually, "
            f"then: gh pr create --base main --head {branch} --title \"sync({package}): "
            f"import upstream {sha12}\"",
        )
    gh = shutil.which("gh")
    if gh is None:
        cmd_hint = (
            f"gh pr create --base main --head {branch} --title \"sync({package}): "
            f"import upstream {sha12}\" --body '<conflict description>'"
        )
        return teardown(E_GIT, f"!! {package}: gh CLI not found — branch {branch} was pushed "
                               f"to origin but no PR was opened.\n    Manual PR:\n    {cmd_hint}",
                        f"run the gh command above (or install gh): {cmd_hint}")
    title = f"sync({package}): import upstream {sha12}"
    body = pr_body(package, url, head, cs, args.resolve)
    if divergences:
        lines = [
            "", "## DMR-070 resolution divergences", "",
            "Resolved paths whose blob matches NEITHER merge side — resolution-"
            "introduced content. Review each before merging this import:",
        ]
        for d in divergences:
            lines.append(
                f"- `{d['path']}` — resolved {d['resolved']} vs ours {d['ours']} "
                f"/ theirs {d['theirs']}"
            )
        body += "\n".join(lines)
    pr = run([gh, "pr", "create", "--base", "main", "--head", branch,
              "--title", title, "--body", body])
    if pr.returncode != 0:
        hint = (f"gh pr create --base main --head {branch} --title \"{title}\" --body "
                "'<conflict description>'")
        return teardown(E_GIT, f"!! {package}: gh pr create failed\n{pr.stderr.strip()}",
                        f"run manually: {hint}")
    pr_url = None
    for line in (pr.stdout or "").splitlines() + (pr.stderr or "").splitlines():
        line = line.strip()
        if line.startswith("http"):
            pr_url = line
            break
    restore = git(["switch", "-f", "main"])
    if restore.returncode != 0:
        return teardown(E_GIT, f"!! {package}: could not return to main after opening the PR",
                        "run: git switch -f main")
    git(["branch", "-D", branch])
    record.update(
        {"ok": True, "exit_code": E_OK, "error_class": "ok", "pr_url": pr_url,
         "cursor_updated": False, "remediation": None, "aborted": True}
    )
    return E_OK, record


# --------------------------------------------------------------------------- #
# DMR-070: post-import verification seams
# --------------------------------------------------------------------------- #


def _blob_sha(rev: str, path: str) -> str | None:
    """Blob sha of ``path`` at ``rev`` (absolute), or None when absent."""
    res = git(["rev-parse", "--verify", "--quiet", f"{rev}:{path}"])
    if res.returncode != 0:
        return None
    return res.stdout.strip() or None


def classify_resolution(resolved: str | None, ours: str | None,
                        theirs: str | None) -> str:
    """Classify a conflict resolution against its two merge sides (DMR-070a).

    Returns "ours" | "theirs" | "both" (identical sides) | "absent" (a
    deletion was kept) | "divergent" — the resolved blob matches NEITHER side,
    the resolution-introduced-content class (the v0.6 ``corpus.py``
    else-branch mangling shipped exactly this way, silently).
    """
    if resolved is None:
        return "absent"
    if ours is not None and theirs is not None and resolved == ours == theirs:
        return "both"
    if ours is not None and resolved == ours:
        return "ours"
    if theirs is not None and resolved == theirs:
        return "theirs"
    return "divergent"


def resolution_divergences(package: str, pre_head: str, upstream: str,
                           paths: list[str]) -> list[dict]:
    """Report resolved paths whose blob matches neither merge side (DMR-070a).

    ``pre_head`` is the monorepo HEAD before the import merge (the "ours"
    side); ``upstream`` is the fetched upstream tip sha (the "theirs" side —
    NOTE the upstream tree has NO ``packages/<pkg>/`` prefix; paths are
    addressed relative to the package root there). Only the DIVERGENT verdict
    is reported — "ours"/"theirs"/"both" are faithful resolutions and
    "absent" is a kept deletion.
    """
    prefix = f"packages/{package}/"
    out: list[dict] = []
    for path in paths:
        rel = path[len(prefix):] if path.startswith(prefix) else path
        resolved = _blob_sha("HEAD", path)
        ours = _blob_sha(pre_head, path)
        theirs = _blob_sha(upstream, rel)
        verdict = classify_resolution(resolved, ours, theirs)
        if verdict == "divergent":
            out.append({
                "path": path,
                "verdict": verdict,
                "resolved": (resolved or "")[:12],
                "ours": (ours or "")[:12],
                "theirs": (theirs or "")[:12],
            })
    return out


def monorepo_deleted_paths(tip: str, package: str) -> list[str]:
    """Tracked upstream paths (repo-root-relative at ``tip``) absent from the
    monorepo package tree — the deletion class a content push can NEVER carry
    (DMR-070b: patch pushes rebuild monorepo blobs ON TOP of the tip, so
    upstream-only paths silently survive the push). Gitignored missing paths
    are excluded (the deliberate heavy-asset prune is not a deletion)."""
    return sorted(unimported_upstream_paths(tip, package))


def _verify_cmd(package: str) -> list[str] | None:
    """Verify-suite command for a package (DMR-070 --verify-suite).

    Default: the package's pytest suite (``packages/<pkg>/tests`` or
    ``packages/<pkg>/src/tests``). ``SYNC_VERIFY_CMD`` (shlex-split)
    overrides — the hermetic tests inject stubs through it. None when the
    package ships no recognizable tests dir (trivially green).
    """
    override = os.environ.get("SYNC_VERIFY_CMD", "").strip()
    if override:
        import shlex

        return shlex.split(override)
    for tests_dir in (f"packages/{package}/tests", f"packages/{package}/src/tests"):
        if (REPO_ROOT / tests_dir).is_dir():
            return [sys.executable, "-m", "pytest", tests_dir, "-q", "--no-header", "-x"]
    return None


def run_verify_suite(package: str, *, dry_run: bool = False) -> tuple[bool, str]:
    """Run the touched package's test suite (DMR-070 --verify-suite).

    Returns (ok, detail_tail). Callers refuse to advance cursors / push /
    open PRs when ok is False.
    """
    cmd = _verify_cmd(package)
    if cmd is None:
        info(f"== {package}: no tests dir found — verify-suite trivially green")
        return True, "no tests dir"
    if dry_run:
        info(f"== DRY RUN {package}: would run verify-suite: {' '.join(cmd)}")
        return True, "dry-run"
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, text=True,
                              capture_output=True, timeout=3600)
    except subprocess.TimeoutExpired:
        warn(f"!! {package}: verify-suite TIMED OUT after 3600s — refusing to advance")
        return False, "verify-suite timed out"
    detail = ((proc.stdout or "")[-4000:] + "\n" + (proc.stderr or "")[-2000:]).strip()
    if proc.returncode != 0:
        warn(f"!! {package}: verify-suite FAILED (exit {proc.returncode}) — "
             "refusing to advance (DMR-070 --verify-suite)")
        return False, detail[-2000:]
    info(f"== {package}: verify-suite green ({' '.join(cmd)})")
    return True, detail[-500:]


def patch_push(package: str, url: str, tip: str, *, dry_run: bool,
               verify_suite: bool = False) -> tuple[int, dict]:
    """HUB-012 workaround, scripted: land the monorepo delta as ONE commit on
    top of the real upstream tip (fast-forward by construction), then
    re-baseline the cursor. Only tracked package files propagate; upstream
    files deleted monorepo-side are NOT carried by this path (subtree push
    handles full-history pushes; patch pushes carry content).

    Returns (exit_code, JSON record).
    """
    command = "push"
    # DMR-070(b): patch pushes carry CONTENT, never deletions — the worktree
    # is rebuilt from monorepo blobs ON TOP of the tip, so upstream paths the
    # monorepo deleted would silently survive the push (the v0.6.0 compliance
    # removal needed the full subtree-push leg for exactly this reason).
    # Checked BEFORE the containment guard: a deletion-bearing package also
    # fails containment, but with a misleading "pull first" remediation — a
    # deliberate removal cannot be fixed by pulling. Refuse with the leg that
    # actually carries deletions (full subtree push).
    if deleted := monorepo_deleted_paths(tip, package):
        prefixed = [f"packages/{package}/{p}" for p in deleted]
        rec = base_record(command, package)
        rec.update(
            {
                "exit_code": E_VERIFY,
                "error_class": ERROR_CLASS[E_VERIFY],
                "remediation": f"{len(deleted)} tracked upstream path(s) deleted monorepo-side; "
                               "content pushes cannot carry deletions — use the full "
                               f"subtree-push leg: python scripts/sync_packages.py push --package {package}",
                "deleted_paths": prefixed,
                "upstream_tip": tip[:12],
            }
        )
        warn(f"!! {package}: patch-push REFUSED — the monorepo deletes "
             f"{len(deleted)} tracked upstream path(s), which a content push "
             "would silently resurrect upstream (DMR-070):")
        for p in prefixed:
            warn(f"   - {p}")
        warn(f"   use the full subtree-push leg: python scripts/sync_packages.py push --package {package}")
        return E_VERIFY, rec
    if gaps := unimported_upstream_paths(tip, package):
        rec = base_record(command, package)
        rec.update(
            {
                "exit_code": E_GIT,
                "error_class": "git",
                "remediation": "upstream tip is not contained in the package tree — "
                               "pull first, then patch-push",
                "upstream_tip": tip[:12],
            }
        )
        warn(
            f"!! {package}: upstream tip {tip[:12]} is NOT contained in the package "
            f"({len(gaps)} path(s) missing/modified — pull first, then patch-push"
        )
        return E_GIT, rec
    tmp: Path | None = None
    try:
        # DMR-064: mkdtemp INSIDE the try — a failed worktree add must not leak it.
        tmp = Path(tempfile.mkdtemp(prefix=f"sync-patch-{package}-"))
        worktree = git(["worktree", "add", "--detach", str(tmp), tip])
        if worktree.returncode != 0:
            rec = base_record(command, package)
            rec.update(
                {
                    "exit_code": E_GIT,
                    "error_class": "git",
                    "remediation": "git worktree add failed — see the git error below",
                    "upstream_tip": tip[:12],
                }
            )
            warn(f"!! worktree add failed: {worktree.stderr.strip()}")
            return E_GIT, rec
        # DMR-028 fix: extract committed blobs (HEAD) instead of copying from
        # the working tree.  Previously `git ls-files` + `shutil.copy2` would
        # propagate uncommitted changes — a race when concurrent edits exist.
        tracked = git(["ls-tree", "-r", "-z", "HEAD", "--", f"packages/{package}"]).stdout.split("\0")
        for entry in tracked:
            if not entry or "\t" not in entry:
                continue
            # ls-tree -z emits "<mode> <type> <sha>\t<path>"; the path is the
            # ONLY tab-delimited tail (paths may contain tabs when -z is on),
            # so split the metadata off first, then the mode/type/sha triple.
            meta, rel = entry.split("\t", 1)
            _mode, _type, blob_sha = meta.split(" ", 2)
            dst = tmp / rel[len(f"packages/{package}/"):]
            dst.parent.mkdir(parents=True, exist_ok=True)
            # cat-file must stay BINARY: blobs are arbitrary bytes and
            # write_bytes rejects the text-mode str output (DMR-054).
            blob = git(["cat-file", "blob", blob_sha], binary=True)
            if blob.returncode != 0:
                rec = base_record(command, package)
                rec.update({"exit_code": E_GIT, "error_class": "git",
                            "remediation": f"git cat-file failed for {rel}"})
                warn(f"!! cat-file failed for {rel}: {blob.stderr.strip()}")
                return E_GIT, rec
            dst.write_bytes(blob.stdout)
        add = git(["-C", str(tmp), "add", "-A"])
        if add.returncode != 0:
            rec = base_record(command, package)
            rec.update({"exit_code": E_GIT, "error_class": "git",
                        "remediation": "staging the patch worktree failed"})
            warn(f"!! staging failed: {add.stderr.strip()}")
            return E_GIT, rec
        staged = git(["-C", str(tmp), "diff", "--cached", "--stat", "HEAD"])
        n_files = len([ln for ln in staged.stdout.splitlines() if "|" in ln])
        if not staged.stdout.strip() or n_files == 0:
            info(f"== {package}: no content delta vs upstream tip {tip[:12]} — nothing to propagate")
            return E_OK, record_ok(command, package, cursor_updated=False)
        # DMR-070: --verify-suite gates the push on the touched package's own
        # suite (run in the monorepo checkout — HEAD carries exactly the delta
        # being propagated). A red suite refuses commit AND push.
        if verify_suite:
            ok, detail = run_verify_suite(package)
            if not ok:
                rec = base_record(command, package)
                rec.update(
                    {
                        "exit_code": E_VERIFY,
                        "error_class": ERROR_CLASS[E_VERIFY],
                        "remediation": "verify-suite failed — fix or revert the monorepo delta, "
                                       "then re-run; nothing was committed or pushed",
                        "verify_detail_tail": detail[-1500:],
                        "upstream_tip": tip[:12],
                    }
                )
                return E_VERIFY, rec
        stamp = git(["rev-parse", "--short", "HEAD"]).stdout.strip()
        message = (
            f"Monorepo propagation: {package} from Digital-Mailroom@{stamp}\n\n"
            f"{n_files} tracked file(s) carried from the monorepo (source of truth "
            "for development); subtree patch-push because the recorded cursor had "
            "no real graft ancestry (HUB-012/HUB-021)."
        )
        if dry_run:
            info(f"== DRY RUN {package}: would commit {n_files} file(s) on {tip[:12]} and push {url}")
            info(staged.stdout.rstrip())
            return E_OK, record_ok(command, package, cursor_updated=False)
        commit = git(["-C", str(tmp), "commit", "-m", message])
        if commit.returncode != 0:
            rec = base_record(command, package)
            rec.update({"exit_code": E_GIT, "error_class": "git",
                        "remediation": "committing the patch worktree failed"})
            warn(f"!! commit failed: {commit.stderr.strip()}")
            return E_GIT, rec
        push = git(["-C", str(tmp), "push", url, f"HEAD:refs/heads/{DEFAULT_BRANCH}"])
        if push.returncode != 0:
            probe = upstream_head(url, DEFAULT_BRANCH)
            code = E_NETWORK if probe is None else E_GIT
            rec = base_record(command, package)
            rec.update(
                {
                    "exit_code": code,
                    "error_class": ERROR_CLASS[code],
                    "remediation": ("check connectivity/auth for the upstream repo"
                                    if code == E_NETWORK
                                    else "push rejected by the upstream (auth/permissions?) — "
                                         "recover the patch worktree by hand or re-run"),
                    "upstream_tip": tip[:12],
                }
            )
            warn(f"!! push failed: {push.stderr.strip()}")
            return code, rec
        info(f"== {package}: propagated {n_files} file(s) to {url} (tip {tip[:12]})")
        return E_OK, record_ok(command, package, cursor_updated=False)
    finally:
        # DMR-064 leak hardening: verify the removal, prune stale registrations
        # on failure, and sweep the directory as a last resort.
        if tmp is not None:
            removed = git(["worktree", "remove", "--force", str(tmp)])
            if removed.returncode != 0:
                git(["worktree", "prune"])
            shutil.rmtree(tmp, ignore_errors=True)


def cmd_push(args: argparse.Namespace) -> int:
    require_subtree(args.command)
    assert_clean_tree(args.command, "push", args.allow_dirty)
    manifest = load_manifest(args.command)
    entries = manifest.setdefault("packages", {})
    worst = E_OK
    for package in selected_packages(args.command, args):
        url = url_for(package)
        if args.patch:
            tip = fetch_upstream(package)
            if tip is None:
                rec = base_record(args.command, package)
                rec.update(
                    {
                        "exit_code": E_NETWORK,
                        "error_class": "network",
                        "remediation": "check connectivity / upstream URL",
                    }
                )
                emit(rec)
                warn(f"!! could not fetch upstream tip for {package}")
                worst = max(worst, E_NETWORK)
                continue
            code, rec = patch_push(package, url, tip, dry_run=args.dry_run,
                                   verify_suite=args.verify_suite)
            if code == E_OK and not args.dry_run:
                # DMR-064: cursor entry saved IMMEDIATELY after the push lands —
                # an interrupt after this point cannot desync this package.
                entries[package] = {
                    "url": url,
                    "branch": DEFAULT_BRANCH,
                    "synced_sha": upstream_head(url, DEFAULT_BRANCH),
                    "synced_at": utc_now(),
                }
                save_manifest(manifest)
                rec = dict(rec)
                rec["cursor_updated"] = True
            emit(rec)
            worst = max(worst, code)
            continue
        info(f"== git subtree push --prefix packages/{package} {url} {DEFAULT_BRANCH}")
        if args.dry_run:
            info("== DRY RUN: no push performed")
            emit(record_ok(args.command, package, cursor_updated=False))
            continue
        result = git_foreground(
            ["subtree", "push", f"--prefix=packages/{package}", url, DEFAULT_BRANCH],
        )
        if result.returncode != 0:
            probe = upstream_head(url, DEFAULT_BRANCH)
            code = E_NETWORK if probe is None else E_GIT
            rec = base_record(args.command, package)
            rec.update(
                {
                    "exit_code": code,
                    "error_class": ERROR_CLASS[code],
                    "remediation": (
                        "check connectivity / upstream URL"
                        if code == E_NETWORK
                        else "non-fast-forward? see HUB-012: re-run with --patch to land the "
                             "delta as one fast-forward commit on the current upstream tip"
                    ),
                }
            )
            emit(rec)
            warn(
                f"!! push failed for {package} (non-fast-forward? see HUB-012). "
                "Re-run with --patch to land the delta as one fast-forward commit "
                "on the current upstream tip." if code == E_GIT
                else f"!! push failed for {package}: upstream unreachable"
            )
            worst = max(worst, code)
            continue
        entries[package] = {
            "url": url,
            "branch": DEFAULT_BRANCH,
            "synced_sha": upstream_head(url, DEFAULT_BRANCH),
            "synced_at": utc_now(),
        }
        save_manifest(manifest)
        rec = record_ok(args.command, package, cursor_updated=True)
        emit(rec)
    return worst


def cmd_snapshot(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.command)
    manifest["version"] = 1
    manifest.setdefault("note", "")
    manifest["note"] = (
        "Per-package sync cursor against the standalone Exios66/* repositories. "
        "Baseline per issue #2: monorepo aligned with the standalone repos as of "
        f"{BASELINE_SYNCED_AT} (2026-08-30 19:06 CST). Cursor writes are "
        "content-verified (HUB-021) — upstream tip must be contained in the "
        "package tree unless snapshot --force is passed."
    )
    entries = manifest.setdefault("packages", {})
    now = utc_now()
    worst = E_OK
    for package in selected_packages(args.command, args):
        url = url_for(package)
        head = upstream_head(url, DEFAULT_BRANCH)
        if head is None:
            rec = base_record(args.command, package)
            rec.update(
                {
                    "exit_code": E_NETWORK,
                    "error_class": "network",
                    "remediation": "check connectivity / upstream URL; the previous cursor "
                                   "entry is kept",
                }
            )
            emit(rec)
            warn(f"!! could not read upstream tip for {package}; keeping previous entry")
            worst = max(worst, E_NETWORK)
            continue
        if not rev_exists(head):
            fetched = fetch_upstream(package)
            if fetched is None:
                rec = base_record(args.command, package)
                rec.update(
                    {
                        "exit_code": E_NETWORK,
                        "error_class": "network",
                        "remediation": "upstream tip has no local objects and the fetch "
                                       "failed; the previous cursor entry is kept",
                    }
                )
                emit(rec)
                warn(
                    f"!! upstream tip {head[:12]} for {package} has no local objects "
                    "and the fetch failed; keeping previous entry"
                )
                worst = max(worst, E_NETWORK)
                continue
            head = fetched
        gaps = unimported_upstream_paths(head, package)
        if gaps and not args.force:
            sample = ", ".join(sorted(gaps)[:5])
            rec = base_record(args.command, package)
            rec.update(
                {
                    "exit_code": E_GIT,
                    "error_class": "git",
                    "remediation": "this is the HUB-018 cursor/content gap — pull first "
                                   "(or pass --force to accept the lie explicitly)",
                }
            )
            emit(rec)
            warn(
                f"!! refusing to snapshot {package}: upstream tip {head[:12]} is not "
                f"contained in packages/{package} ({len(gaps)} path(s) "
                f"missing/modified: {sample}). This is the HUB-018 cursor/content "
                "gap — pull first (or pass --force to accept the lie explicitly)."
            )
            worst = max(worst, E_GIT)
            continue
        if gaps:
            warn(
                f"!! {package}: snapshot forced past {len(gaps)} non-contained path(s) "
                "— the cursor now describes content the monorepo may not have"
            )
        entries[package] = {
            "url": url,
            "branch": DEFAULT_BRANCH,
            "synced_sha": head,
            "synced_at": now,
        }
        save_manifest(manifest)
        emit(record_ok(args.command, package, cursor_updated=True))
    save_manifest(manifest)
    info(f"snapshot written to {_rel_or_abs(MANIFEST)} at {now}")
    return worst


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--manifest", metavar="PATH",
        help="override the sync manifest path (default: scripts/packages_sync.json)",
    )
    parser.add_argument(
        "--repo-root", metavar="PATH",
        help="override the git working directory (default: the monorepo root)",
    )
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
    pull_group = pull.add_mutually_exclusive_group()
    pull_group.add_argument(
        "--open-pr", "--pr", dest="open_pr", action="store_true",
        help="on conflict: abort, import via a sync/<package>/import-<sha> branch and "
             "open a PR against main with gh instead of leaving the failure",
    )
    pull_group.add_argument(
        "--keep-conflicts", action="store_true",
        help="on conflict: leave the merge in the worktree for manual resolution "
             "(no auto-abort; the tree stays dirty)",
    )
    pull.add_argument(
        "--resolve", choices=("ours", "theirs"), default="ours",
        help="resolution strategy for --open-pr (default: ours = monorepo content "
             "wins, the HUB-021 containment doctrine; theirs DROPS monorepo content)",
    )
    pull.add_argument(
        "--verify-suite", action="store_true",
        help="DMR-070: run the touched package's test suite before advancing the cursor "
             "(pull) / pushing the import branch (pull --open-pr); SYNC_VERIFY_CMD overrides "
             "the default pytest invocation",
    )
    pull.add_argument("--json", action="store_true", help="machine-readable output (JSON Lines)")
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
    push.add_argument(
        "--verify-suite",
        action="store_true",
        help="DMR-070: run the touched package's test suite before pushing the patch; "
             "SYNC_VERIFY_CMD overrides the default pytest invocation",
    )
    push.add_argument("--json", action="store_true", help="machine-readable output (JSON Lines)")
    push.set_defaults(func=cmd_push)

    snap = sub.add_parser("snapshot", help="re-baseline the manifest at current upstream tips")
    add_common(snap)
    snap.add_argument(
        "--force",
        action="store_true",
        help="advance the cursor even when the upstream tip is not contained in "
        "the package tree (accepts the HUB-018 cursor/content gap explicitly)",
    )
    snap.add_argument("--json", action="store_true", help="machine-readable output (JSON Lines)")
    snap.set_defaults(func=cmd_snapshot)

    args = parser.parse_args(argv)
    if args.manifest:
        global MANIFEST  # noqa: PLW0603 — single-process override from --manifest
        MANIFEST = Path(args.manifest).resolve()
    if args.repo_root:
        global REPO_ROOT  # noqa: PLW0603 — single-process override from --repo-root
        REPO_ROOT = Path(args.repo_root).resolve()
    global JSON_MODE  # noqa: PLW0603
    JSON_MODE = bool(getattr(args, "json", False))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())