#!/usr/bin/env python3
"""Org-migration reference audit (DMR-006).

Guards the migration of the hub identity from ``Exios66/mailroom-dev`` to
``LLM-Mailroom-Services/Digital-Mailroom``: every tracked file is scanned for
stale hub references, with a classified allowlist for the references that are
intentionally NOT migrated —

  * ``packages/**`` — the ten package mirrors stay ``Exios66/*`` upstream repos
    (their docs legitimately name the original hub);
  * ``governance/TASKS.md`` / ``AGENTS.md`` — HUB-era lineage and archive;
  * ``CHANGELOG.md`` — historical entries (but its link-definition footer MUST
    use the new repo; that rule overrides the allowlist);
  * ``board-site/index.html`` — the cross-board switcher links the original
    HUB board on purpose;
  * ``scripts/apply_hub064_board.py`` — a historical one-off migration script;
  * ``docs/reports/audits/org_migration_audit.*`` — the audit report itself.

Usage:
    python scripts/audit_references.py [--json]

Exit 1 when any non-allowlisted stale reference is found. Stdlib only.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

OLD_REPO = "Exios66/mailroom-dev"
OLD_BOARD = "mailroom-dev.vercel.app"
NEW_REPO = "LLM-Mailroom-Services/Digital-Mailroom"

PATTERNS = {
    "old-hub-repo": re.compile(re.escape(OLD_REPO)),
    "old-hub-board": re.compile(re.escape(OLD_BOARD)),
}

ALLOWLIST = {
    "old-hub-repo": [
        "packages/*",
        "packages/**",
        "governance/TASKS.md",
        "AGENTS.md",
        "CHANGELOG.md",
        "board-site/index.html",
        "scripts/apply_hub064_board.py",
        "scripts/audit_references.py",
        "docs/reports/audits/org_migration_audit.*",
    ],
    "old-hub-board": [
        "packages/*",
        "packages/**",
        "governance/TASKS.md",
        "CHANGELOG.md",
        "board-site/index.html",
        "scripts/audit_references.py",
        "docs/reports/audits/org_migration_audit.*",
    ],
}

CHANGELOG_FOOTER_RE = re.compile(
    r"^\[[^\]]+\]:\s+https://github\.com/" + re.escape(OLD_REPO)
)


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, check=False, text=True, capture_output=True
    )
    if result.returncode != 0:
        raise SystemExit(f"git ls-files failed: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def allowed(pattern: str, path: str) -> bool:
    return any(fnmatch.fnmatch(path, glob) for glob in ALLOWLIST[pattern])


def scan() -> list[dict]:
    findings: list[dict] = []
    for rel in tracked_files():
        if rel.endswith(".png") or rel.endswith(".pdf") or rel.endswith(".svg"):
            continue
        path = REPO_ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, rx in PATTERNS.items():
                if not rx.search(line):
                    continue
                if allowed(pattern, rel):
                    continue
                findings.append(
                    {
                        "file": rel,
                        "line": lineno,
                        "pattern": pattern,
                        "text": line.strip()[:200],
                    }
                )
            if rel == "CHANGELOG.md" and CHANGELOG_FOOTER_RE.match(line):
                findings.append(
                    {
                        "file": rel,
                        "line": lineno,
                        "pattern": "changelog-footer",
                        "text": line.strip()[:200],
                    }
                )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    findings = scan()
    payload = {
        "new_repo": NEW_REPO,
        "old_repo": OLD_REPO,
        "old_board": OLD_BOARD,
        "findings": findings,
        "clean": not findings,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if not findings else 1

    if findings:
        print(f"STALE REFERENCES  {len(findings)} non-allowlisted hit(s):")
        for f in findings:
            print(f"  {f['pattern']:15} {f['file']}:{f['line']}  {f['text']}")
        print("fix them or extend the classified allowlist in scripts/audit_references.py")
        return 1
    print(f"reference audit clean: no non-allowlisted {OLD_REPO} / {OLD_BOARD} references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
