#!/usr/bin/env python3
"""Sync specialist production prompts into config/prompts/ (DMR-074).

Exports the vendored llm-mailroom code-default text so run-30 Modal suites
can pin ``source: local`` without depending on Langfuse. Re-run after
``sandbox fetch-deps`` / monorepo ``sync_vendor.py``.

Usage (from sandbox root)::

    python scripts/sync_specialist_prompts.py
    python scripts/sync_specialist_prompts.py --check   # exit 1 if drift
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_SRC = ROOT / "vendor" / "llm-mailroom" / "src"
PROMPTS = ROOT / "config" / "prompts"

EXPORTS = (
    ("contracts_specialist_v33", "contracts"),
    ("merger_agreement_specialist_production", "merger"),
    ("corporate_records_specialist_production", "corporate"),
    ("correspondence_specialist_production", "correspondence"),
    ("insurance_claims_specialist_production", "insurance"),
)


def _load_texts() -> dict[str, str]:
    if str(VENDOR_SRC) not in sys.path:
        sys.path.insert(0, str(VENDOR_SRC))
    from langchain_agents.prompts import PROMPT_VERSIONS
    from agents import (
        corporate_records_specialist as corp,
        correspondence_specialist as corr,
        insurance_claims_specialist as ins,
        merger_agreement_specialist as merger,
    )

    return {
        "contracts_specialist_v33": PROMPT_VERSIONS["contracts_specialist_v33"],
        "merger_agreement_specialist_production": merger.SYSTEM_PROMPT,
        "corporate_records_specialist_production": corp.SYSTEM_PROMPT,
        "correspondence_specialist_production": corr.SYSTEM_PROMPT,
        "insurance_claims_specialist_production": ins.SYSTEM_PROMPT,
    }


def _sha(text: str) -> str:
    raw = text if text.endswith("\n") else text + "\n"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sync(*, check: bool = False) -> int:
    texts = _load_texts()
    drifted = []
    for stem, _kind in EXPORTS:
        text = texts[stem]
        path = PROMPTS / f"{stem}.txt"
        body = text if text.endswith("\n") else text + "\n"
        if check:
            if not path.is_file():
                drifted.append(f"missing {path}")
                continue
            if path.read_text(encoding="utf-8") != body:
                drifted.append(
                    f"drift {stem}: file={hashlib.sha256(path.read_bytes()).hexdigest()[:12]} "
                    f"vendor={_sha(text)[:12]}"
                )
            else:
                print(f"ok {stem} sha256={_sha(text)[:16]}…")
        else:
            path.write_text(body, encoding="utf-8")
            print(f"wrote {path} ({len(text)} chars, sha256={_sha(text)[:16]}…)")
    if check and drifted:
        for line in drifted:
            print(f"ERROR: {line}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail if config/prompts drifts from vendor")
    args = ap.parse_args(argv)
    return sync(check=bool(args.check))


if __name__ == "__main__":
    raise SystemExit(main())
