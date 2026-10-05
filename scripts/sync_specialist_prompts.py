#!/usr/bin/env python3
"""Sync specialist production prompts into config/prompts/ (DMR-074 / SAND-026).

Exports the vendored llm-mailroom code-default text so historical pins stay
byte-identical to vendor. Re-run after ``sandbox fetch-deps`` / monorepo
``sync_vendor.py``.

SAND-026 experiment pins live as parallel ``*_simplified`` stems. They
intentionally diverge from vendor (live schema + one field-level block).
Default sync **never writes** those files. ``--check`` still requires them
to exist so a checkout cannot drop the experiment surface.

Usage (from sandbox root)::

    python scripts/sync_specialist_prompts.py
    python scripts/sync_specialist_prompts.py --check
    python scripts/sync_specialist_prompts.py --overwrite-experiment
        # explicit opt-in: copy vendor text onto matching *_simplified stems
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_SRC = ROOT / "vendor" / "llm-mailroom" / "src"
PROMPTS = ROOT / "config" / "prompts"

# Vendor mirrors only. Default sync writes these stems and no others.
EXPORTS = (
    ("contracts_specialist_v33", "contracts"),
    ("merger_agreement_specialist_production", "merger"),
    ("corporate_records_specialist_production", "corporate"),
    ("correspondence_specialist_production", "correspondence"),
    ("insurance_claims_specialist_production", "insurance"),
)

# SAND-026 experiment pins. Default sync must not silently overwrite them
# even if a future edit adds a simplified stem to EXPORTS.
EXPERIMENT_FROM_VENDOR: dict[str, str] = {
    "contracts_specialist_v33": "contracts_specialist_v33_simplified",
    "merger_agreement_specialist_production": "merger_agreement_specialist_simplified",
    "corporate_records_specialist_production": "corporate_records_specialist_simplified",
    "correspondence_specialist_production": "correspondence_specialist_simplified",
    "insurance_claims_specialist_production": "insurance_claims_specialist_simplified",
}
EXPERIMENT_STEMS: frozenset[str] = frozenset(EXPERIMENT_FROM_VENDOR.values())


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


def _body(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _refuse_experiment_write(stem: str, *, overwrite_experiment: bool) -> str | None:
    if stem in EXPERIMENT_STEMS and not overwrite_experiment:
        return (
            f"refusing to write experiment pin {stem}.txt "
            "(pass --overwrite-experiment to copy vendor text onto a simplified stem)"
        )
    return None


def sync(*, check: bool = False, overwrite_experiment: bool = False) -> int:
    texts = _load_texts()
    drifted: list[str] = []
    errors: list[str] = []

    export_stems = {stem for stem, _kind in EXPORTS}
    collision = export_stems & EXPERIMENT_STEMS
    if collision and not overwrite_experiment:
        errors.append(
            "EXPORTS includes experiment stem(s) "
            f"{sorted(collision)}; default sync cannot overwrite simplified pins"
        )

    if check:
        for vendor_stem, experiment_stem in EXPERIMENT_FROM_VENDOR.items():
            path = PROMPTS / f"{experiment_stem}.txt"
            if not path.is_file():
                drifted.append(f"missing experiment pin {path}")
                continue
            vendor_text = texts.get(vendor_stem)
            if vendor_text is None:
                continue
            if path.read_text(encoding="utf-8") == _body(vendor_text):
                drifted.append(
                    f"{experiment_stem} is byte-identical to vendor {vendor_stem} "
                    "(simplified pin must diverge; do not copy vendor blindly)"
                )
            else:
                n = len(path.read_text(encoding="utf-8"))
                print(f"ok experiment {experiment_stem} ({n} chars, diverges from {vendor_stem})")

    for stem, _kind in EXPORTS:
        refusal = _refuse_experiment_write(stem, overwrite_experiment=overwrite_experiment)
        if refusal:
            errors.append(refusal)
            continue
        text = texts[stem]
        path = PROMPTS / f"{stem}.txt"
        body = _body(text)
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

    if overwrite_experiment and not check:
        for vendor_stem, experiment_stem in EXPERIMENT_FROM_VENDOR.items():
            text = texts[vendor_stem]
            path = PROMPTS / f"{experiment_stem}.txt"
            path.write_text(_body(text), encoding="utf-8")
            print(
                f"OVERWROTE experiment {path} from vendor {vendor_stem} "
                f"({len(text)} chars) — re-simplify before scoring"
            )

    if errors:
        for line in errors:
            print(f"ERROR: {line}", file=sys.stderr)
        return 1
    if check and drifted:
        for line in drifted:
            print(f"ERROR: {line}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="fail if vendor stems drift from vendor, or simplified stems are missing/identical",
    )
    ap.add_argument(
        "--overwrite-experiment",
        action="store_true",
        help=(
            "explicit opt-in: copy vendor text onto *_simplified stems "
            "(default sync never writes those files)"
        ),
    )
    args = ap.parse_args(argv)
    return sync(check=bool(args.check), overwrite_experiment=bool(args.overwrite_experiment))


if __name__ == "__main__":
    raise SystemExit(main())
