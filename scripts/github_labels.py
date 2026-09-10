#!/usr/bin/env python3
"""GitHub label taxonomy sync driver (HUB-014).

Keeps the repository's GitHub labels in lockstep with the declarative
taxonomy in ``.github/labels.json``. The manifest is the source of truth:
every label the governance workflow uses (``stage/*`` lane mirrors,
``attention/*`` tags, ``type/*``, ``priority/*``, ``domain/*`` and the
``kanban`` synced-card marker) is created or updated from it — never
hand-edited on GitHub.

Usage:
    python scripts/github_labels.py sync  [--dry-run] [--repo OWNER/NAME] [--json]
    python scripts/github_labels.py audit [--repo OWNER/NAME] [--json]

  sync   create missing labels, update drifted color/description, no-op on match
  audit  report drift without writing: manifest labels missing from the repo
         (exit 1) and repo labels absent from the manifest (informational)

Commands are read-only unless ``sync`` runs without ``--dry-run``. Requires
``gh`` authenticated against the target repo. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / ".github" / "labels.json"

DEFAULT_REPO = "LLM-Mailroom-Services/Digital-Mailroom"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO_ROOT, check=False, text=True, capture_output=True)


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        raise SystemExit(f"manifest missing: {MANIFEST}")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    labels = data.get("labels")
    if not isinstance(labels, list) or not labels:
        raise SystemExit(f"manifest has no labels: {MANIFEST}")
    names = [entry["name"] for entry in labels]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise SystemExit(f"manifest duplicate label names: {dupes}")
    return data


def default_repo() -> str:
    result = run(["git", "remote", "get-url", "origin"])
    url = result.stdout.strip() if result.returncode == 0 else ""
    if url.endswith(".git"):
        url = url[:-4]
    if "github.com" in url:
        return url.split("github.com")[-1].lstrip(":/")
    return DEFAULT_REPO


def repo_labels(repo: str) -> dict[str, dict]:
    result = run(["gh", "label", "list", "--repo", repo, "--json", "name,color,description", "--limit", "500"])
    if result.returncode != 0:
        raise SystemExit(f"gh label list failed: {result.stderr.strip()}")
    return {entry["name"]: entry for entry in json.loads(result.stdout or "[]")}


def norm(value: str | None) -> str:
    return (value or "").strip()


def diff_labels(manifest: dict, existing: dict[str, dict]) -> tuple[list[dict], list[dict], list[str]]:
    """Return (creates, updates, extras).

    creates: manifest labels absent from the repo.
    updates: manifest labels present but with drifted color/description.
    extras:  repo labels absent from the manifest (never touched — deletion
             is out of scope so open issues never lose their flair).
    """
    creates, updates = [], []
    for entry in manifest["labels"]:
        name, color, desc = entry["name"], norm(entry["color"]), norm(entry.get("description"))
        current = existing.get(name)
        if current is None:
            creates.append(entry)
            continue
        if norm(current.get("color")).lstrip("#") != color or norm(current.get("description")) != desc:
            updates.append(entry)
    extras = sorted(set(existing) - {e["name"] for e in manifest["labels"]})
    return creates, updates, extras


def cmd_sync(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    existing = repo_labels(args.repo)
    creates, updates, extras = diff_labels(manifest, existing)

    if args.json:
        print(json.dumps({"repo": args.repo, "create": [c["name"] for c in creates],
                          "update": [u["name"] for u in updates], "extras": extras,
                          "dry_run": args.dry_run}, indent=2))
    else:
        for entry in creates:
            print(f"create  {entry['name']}  #{entry['color']}")
        for entry in updates:
            print(f"update  {entry['name']}  #{entry['color']}")
        for name in extras:
            print(f"extra   {name}  (in repo, not in manifest — informational)")
        if not creates and not updates:
            print(f"in sync: {len(manifest['labels'])} labels match {args.repo}")

    if args.dry_run:
        print("dry run — nothing written", file=sys.stderr)
        return 0

    failures = 0
    update_names = {entry["name"] for entry in updates}
    for entry in creates + updates:
        cmd = ["gh", "label", "create", entry["name"], "--repo", args.repo,
               "--color", entry["color"], "--description", entry.get("description") or ""]
        if entry["name"] in update_names:
            cmd[2] = "edit"
        result = run(cmd)
        if result.returncode != 0:
            failures += 1
            print(f"FAILED  {entry['name']}: {result.stderr.strip()}", file=sys.stderr)
    verb = "created/updated" if (creates or updates) else "no changes to"
    print(f"synced {args.repo}: {len(creates)} created, {len(updates)} updated ({verb})")
    return 1 if failures else 0


def cmd_audit(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    existing = repo_labels(args.repo)
    creates, updates, extras = diff_labels(manifest, existing)
    missing = creates + updates  # audit counts drifted labels as missing-from-truth

    payload = {"repo": args.repo, "missing_or_drifted": [e["name"] for e in missing],
               "extras": extras, "in_sync": not missing}
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if not missing else 1

    if missing:
        print(f"DRIFT  {len(missing)} manifest label(s) missing or drifted in {args.repo}:")
        for entry in missing:
            kind = "drifted" if entry["name"] in existing else "missing"
            print(f"  {kind}  {entry['name']}")
        print("run: python scripts/github_labels.py sync --repo " + args.repo)
        return 1
    print(f"in sync: {len(manifest['labels'])} manifest labels present in {args.repo}")
    if extras:
        print(f"note: {len(extras)} repo label(s) not in manifest (informational): {', '.join(extras)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--repo", default=None, help="OWNER/NAME (default: git origin)")
        p.add_argument("--json", action="store_true", help="machine-readable output")

    p_sync = sub.add_parser("sync", help="create/update labels from the manifest")
    p_sync.add_argument("--dry-run", action="store_true", help="show actions without writing")
    add_common(p_sync)
    p_sync.set_defaults(func=cmd_sync)

    p_audit = sub.add_parser("audit", help="report manifest<->repo drift (exit 1 on missing/drifted)")
    add_common(p_audit)
    p_audit.set_defaults(func=cmd_audit)

    args = parser.parse_args(argv)
    if args.repo is None:
        args.repo = default_repo()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
