#!/usr/bin/env python3
"""Render docs/prompts/ — the catalog of every eval-environment prompt version.

Generated from the vendored dojo lineage (``llm_dojo_scoring.prompts``): an index
(``docs/prompts/README.md``) and one page per role with each version's memo,
what changed against its predecessor, a unified diff and the full text.
Deterministic; ``--check`` exits 1 when the committed pages differ from what the
vendored dojo renders (CI / ``tests/test_prompt_catalog.py``).

Usage (from the sandbox root)::

    python scripts/render_prompt_catalog.py            # (re)write docs/prompts/
    python scripts/render_prompt_catalog.py --check    # exit 1 if out of date
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT / "src", ROOT / "vendor" / "llm-dojo-scoring" / "src", ROOT / "vendor" / "llm-mailroom" / "src"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if docs/prompts/ is out of date")
    args = parser.parse_args(argv)

    from mailroom_sandbox import prompt_catalog as catalog

    if args.check:
        problems = catalog.check()
        for line in problems:
            print(f"prompt catalog: {line}", file=sys.stderr)
        if problems:
            print("prompt catalog is out of sync: run `python scripts/render_prompt_catalog.py`", file=sys.stderr)
            return 1
        print(f"prompt catalog: {len(catalog.render_all())} page(s) in sync with the vendored dojo")
        return 0
    written = catalog.write()
    for path in written:
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
