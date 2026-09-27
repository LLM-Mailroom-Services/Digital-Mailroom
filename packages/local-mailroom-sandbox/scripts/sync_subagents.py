#!/usr/bin/env python3
"""Regenerate harness stubs from config/subagents/family-roster.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mailroom_sandbox.subagents import sync_harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", default="all", choices=("cursor", "opencode", "all"))
    parser.add_argument("--package", default=None)
    parser.add_argument("--root", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve() if args.root else None
    result = sync_harness(
        args.harness,
        root=root,
        package=args.package,
        dry_run=args.dry_run,
    )
    items = result if isinstance(result, list) else [result]
    for block in items:
        for path in block.written:
            print(path)
        if block.skipped:
            print(f"skipped ({block.harness}):", ", ".join(block.skipped), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
