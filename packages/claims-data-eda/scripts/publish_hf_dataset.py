#!/usr/bin/env python3
"""Publish the rendered DE-SynPUF insurance_claim corpus to the Hugging Face Hub.

Target: Lucius-Morningstar/cms-desynpuf-insurance-claims
  * train/test split by the family-wide deterministic rule:
      md5(record_id) % 10 == 0  ->  test  (~10%)
  * stages an honest manifest + dataset card into gitignored data/hf_export/
  * uploads via huggingface_hub, then re-downloads and sha256-verifies each
    uploaded artifact against the local staging copy (VERIFY: GREEN)

Auth: HF_TOKEN from the environment (or a gitignored .env at the repo root).

Usage:
    python scripts/publish_hf_dataset.py --dry-run          # stage only
    python scripts/publish_hf_dataset.py                    # full publish
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
# hub#58: the centralized family upload helpers live in the sibling
# mailroom-corpus-eda package (a virtual member like this one — no build).
sys.path.insert(0, str(REPO.parent / "mailroom-corpus-eda" / "src"))

DUMP = REPO / "data" / "cms" / "pipeline.jsonl"
STAGE = REPO / "data" / "hf_export"
HF_REPO = "Lucius-Morningstar/cms-desynpuf-insurance-claims"

CARD = """---
license: other
license_name: cms-public-use
license_link: https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files
task_categories:
  - token-classification
  - text-classification
tags:
  - insurance-claims
  - medicare
  - synthetic-data
  - llm-evaluation
  - entity-extraction
size_categories:
  - n<1K
---

# CMS DE-SynPUF Insurance Claims (Rendered EOB Documents)

Pipeline-ready **insurance_claim** evaluation corpus derived from the CMS
2008-2010 Data Entrepreneurs' Synthetic Public Use File (DE-SynPUF), Sample 1.
One row = one Medicare claim rendered as a plain-text EOB-style document with
ground-truth extraction fields aligned to the `llm-mailroom`
`InsuranceClaimExtraction` schema.

## Provenance

* Source: CMS DE-SynPUF Sample 1 (fully synthetic; "very limited inferential
  research utility" per CMS). No real PHI exists in this corpus.
* Sample-1 archives for the 2010 Beneficiary Summary, Carrier Claims (A/B) and
  Prescription Drug Events were no longer hosted by CMS and were recovered from
  Internet Archive Wayback Machine captures; sha256 manifests live in the
  producing repository (`claims-data-eda`, data/raw/MANIFEST.json).

## Schema

| field | type | notes |
|---|---|---|
| filename | string | stable per claim (`<record_id>.txt`) |
| doc_text | string | rendered Medicare Summary Notice / pharmacy statement |
| prompt | string | empty (eval runners supply prompts) |
| expected | string | constant `insurance_claim` |
| expected_subclass | string | `inpatient` \\| `outpatient` \\| `carrier` \\| `pde` |
| metadata.record_id | string | stable join key |
| metadata.ground_truth | object | InsuranceClaimExtraction-aligned GT |

## Ground-truth contract

Every scalar GT value appears **verbatim** in `doc_text` (machine-auditable;
see `spot_check.csv` in the producing repo). Known limitations, by construction:

* `coverage_determination` is always `"approved"` -- SynPUF contains only
  adjudicated-paid FFS claims; **no denial ground truth exists here**.
* `adjuster` is always null (no adjusters exist in SynPUF).
* `insured_party` is a deterministic pseudonym derived from DESYNPUF_ID.

## Split

Deterministic: `md5(record_id) % 10 == 0` -> test (~10%), else train.
"""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_token() -> str | None:
    tok = os.environ.get("HF_TOKEN")
    if tok:
        return tok
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("HF_TOKEN="):
                return line.split("=", 1)[1].strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = [json.loads(l) for l in DUMP.open()] if DUMP.exists() else []
    if not rows:
        print("!! pipeline.jsonl missing/empty -- run scripts/build_pipeline_dump.py first", file=sys.stderr)
        return 1

    # ---- schema guard --------------------------------------------------
    base_keys = set(rows[0])
    gt_keys = set(rows[0]["metadata"]["ground_truth"])
    bad = [r["metadata"]["record_id"] for r in rows
           if set(r) != base_keys or set(r["metadata"]["ground_truth"]) != gt_keys]
    if bad:
        print(f"!! SCHEMA GUARD: {len(bad)} rows deviate (e.g. {bad[:3]}) -- refusing to publish", file=sys.stderr)
        return 2

    # ---- deterministic family split -------------------------------------
    def is_test(r) -> bool:
        rid = r["metadata"]["record_id"]
        return hashlib.md5(rid.encode()).hexdigest()[-8:] and int(hashlib.md5(rid.encode()).hexdigest(), 16) % 10 == 0

    train = [r for r in rows if not is_test(r)]
    test = [r for r in rows if is_test(r)]

    STAGE.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, part in (("train", train), ("test", test)):
        p = STAGE / f"{name}.jsonl"
        with p.open("w") as fh:
            for r in part:
                fh.write(json.dumps(r, sort_keys=True) + "\n")
        paths[name] = p

    card = STAGE / "README.md"
    card.write_text(CARD)
    manifest = {
        "repo": HF_REPO,
        "rows_total": len(rows),
        "rows_train": len(train),
        "rows_test": len(test),
        "subclasses": sorted({r["expected_subclass"] for r in rows}),
        "artifacts": {n: {"sha256": sha256_file(p), "bytes": p.stat().st_size} for n, p in paths.items()},
        "card_sha256": sha256_file(card),
    }
    (STAGE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))

    if args.dry_run:
        print("\nDRY RUN: staged into data/hf_export/ -- nothing uploaded")
        return 0

    # ---- upload (centralized helpers, hub#58) ---------------------------
    # The corpus family is published through the CENTRALIZED mailroom_eda
    # helpers (root AGENTS.md: 'never ad-hoc upload code'). claims-data-eda is
    # a non-installable virtual member, so the sibling src is added to the
    # path at import time below (same mechanism as the other scripts that
    # reach into the family).
    token = load_token()
    if not token:
        print("!! HF_TOKEN missing (env or .env)", file=sys.stderr)
        return 3
    from mailroom_eda import hf_interface

    api = hf_interface.get_hf_api(token)
    hf_interface.create_dataset_repo(api, HF_REPO)
    api.upload_file(path_or_fileobj=str(card), path_in_repo="README.md",
                    repo_id=HF_REPO, repo_type="dataset")
    hf_interface.upload_folder(api, STAGE, HF_REPO,
                               commit_message="claims publish",
                               allow_patterns=["*.jsonl", "manifest.json"])

    # ---- VERIFY: GREEN ---------------------------------------------------
    ok = True
    for name, p in paths.items():
        local = sha256_file(p)
        result = hf_interface.verify_hub_sha256(api, HF_REPO, f"{name}.jsonl", local)
        status = "GREEN" if result["verified"] is True else "RED"
        ok &= status == "GREEN"
        print(f"VERIFY [{name}]: {status}  ({p.stat().st_size:,} bytes)")
    print("\nPUBLISH COMPLETE" if ok else "\nPUBLISH FAILED VERIFICATION")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
