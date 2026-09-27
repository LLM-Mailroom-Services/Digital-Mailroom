#!/usr/bin/env python3
"""Materialize + sync family subagents across mapped checkouts."""

from __future__ import annotations

import argparse
import json
import sys

from mailroom_sandbox.subagents.propagate import propagate_family_checkouts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monorepo-root", default=None)
    parser.add_argument("--package", action="append", dest="packages", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = propagate_family_checkouts(
        monorepo_root=args.monorepo_root,
        packages=args.packages,
        dry_run=bool(args.dry_run),
    )
    if args.json:
        print(
            json.dumps(
                {
                    "source_root": str(result.source_root),
                    "monorepo_root": str(result.monorepo_root) if result.monorepo_root else None,
                    "packages": [
                        {
                            "package": r.package,
                            "dest_root": str(r.dest_root),
                            "materialized": r.materialized,
                            "sync_written": r.sync_written,
                            "error": r.error,
                        }
                        for r in result.packages
                    ],
                },
                indent=2,
            )
        )
    else:
        for row in result.packages:
            err = f" ({row.error})" if row.error else ""
            print(f"{row.package}: {row.dest_root} sync={row.sync_written}{err}")
    return 1 if any(r.error for r in result.packages) else 0


if __name__ == "__main__":
    raise SystemExit(main())
