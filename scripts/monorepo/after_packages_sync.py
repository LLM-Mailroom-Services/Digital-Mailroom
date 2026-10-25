#!/usr/bin/env python3
"""Post-hook for Digital-Mailroom ``scripts/sync_packages.py`` after pull/push.

Install once in the monorepo (see INTEGRATION.md), then every package sync
can refresh family subagent manifests across checkouts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _sandbox_package_root(monorepo_root: Path) -> Path | None:
    candidate = monorepo_root / "packages" / "local-mailroom-sandbox"
    return candidate if candidate.is_dir() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--monorepo-root",
        default=".",
        help="Digital-Mailroom monorepo root (default: cwd)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    mono = Path(args.monorepo_root).expanduser().resolve()
    sandbox = _sandbox_package_root(mono)
    if sandbox is None:
        print("skip: packages/local-mailroom-sandbox not present", file=sys.stderr)
        return 0

    src = str(sandbox / "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    from mailroom_sandbox.subagents.propagate import propagate_family_checkouts

    result = propagate_family_checkouts(
        source_root=sandbox,
        monorepo_root=mono,
        dry_run=bool(args.dry_run),
    )
    payload = {
        "source_root": str(result.source_root),
        "monorepo_root": str(result.monorepo_root) if result.monorepo_root else None,
        "packages": [
            {
                "package": row.package,
                "dest_root": str(row.dest_root),
                "materialized": row.materialized,
                "sync_written": row.sync_written,
                "skipped": row.skipped,
                "error": row.error,
            }
            for row in result.packages
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for row in result.packages:
            state = "ok" if row.error is None else f"error: {row.error}"
            print(
                f"{row.package:<28} {state:<20} written={row.sync_written} "
                f"dest={row.dest_root}"
            )
    errors = [r for r in result.packages if r.error]
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
