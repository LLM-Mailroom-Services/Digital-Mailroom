#!/usr/bin/env python3
"""Mirror Lucius-Morningstar/mailroom-dataset INTO a Langfuse dataset.

Default corpus is the **corrected full** ``mailroom-dataset`` Hub set (pinned
revision via ``MAILROOM_HF_REVISION`` / ``mailroom_ui.hf_corpus``). The smaller
``docclass-pilot`` examples pack remains available with ``--corpus pilot``.

Configs joined on ``filename``:

- ``default``       → item input  {filename, doc_text, prompt, metadata}
- ``ground_truth``  → item expected_output {expected, expected_subclass, …}

Items are upserted with deterministic ids, so re-runs refresh rather than
duplicate. Rows come from the HF datasets-server REST API (no huggingface_hub
dep on this path).

Usage:
    python scripts/sync_pilot_dataset.py                 # full merged corpus
    python scripts/sync_pilot_dataset.py --corpus pilot  # 48-strata examples
    python scripts/sync_pilot_dataset.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from mailroom_ui.hf_corpus import (  # noqa: E402
    DEFAULT_CONFIG,
    EXAMPLES_ID,
    FULL_CORPUS_ID,
    corpus_id,
    corpus_revision,
    fetch_rows,
    gt_config,
)

_CORPORA = {
    "merged": {
        "dataset": FULL_CORPUS_ID,
        "langfuse": "docclass-merged",
        "description": (
            "Corrected full corpus mirrored from Lucius-Morningstar/mailroom-dataset "
            "(configs: default + ground_truth)."
        ),
    },
    "pilot": {
        "dataset": EXAMPLES_ID,
        "langfuse": "docclass-pilot",
        "description": (
            "Class×subclass examples mirrored from Lucius-Morningstar/docclass-pilot "
            "(configs: default + ground_truth)."
        ),
    },
}


def _item_id(prefix: str, filename: str) -> str:
    return prefix + hashlib.sha1(filename.encode()).hexdigest()[:24]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Hub docclass corpus into Langfuse datasets."
    )
    parser.add_argument(
        "--corpus",
        choices=sorted(_CORPORA),
        default="merged",
        help="Hub corpus to mirror (default: merged = corrected full mailroom-dataset).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Count rows without writing.")
    parser.add_argument(
        "--omit-text",
        action="store_true",
        help="Omit doc_text from Langfuse item input (labels + metadata only; smaller).",
    )
    args = parser.parse_args()

    spec = _CORPORA[args.corpus]
    # Allow MAILROOM_HF_DATASET to override the merged id (pilot stays fixed).
    dataset = corpus_id() if args.corpus == "merged" else spec["dataset"]
    revision = corpus_revision() if args.corpus == "merged" else ""
    lf_name = spec["langfuse"]
    id_prefix = "dcm-" if args.corpus == "merged" else "dcp-"

    default_rows = fetch_rows(
        dataset=dataset, config=DEFAULT_CONFIG, split="train", revision=revision or None,
    ) + fetch_rows(
        dataset=dataset, config=DEFAULT_CONFIG, split="test", revision=revision or None,
    )
    gt_rows = fetch_rows(
        dataset=dataset, config=gt_config(), split="train", revision=revision or None,
    ) + fetch_rows(
        dataset=dataset, config=gt_config(), split="test", revision=revision or None,
    )
    gt_by_file = {r["filename"]: r for r in gt_rows if r.get("filename")}

    print(
        f"{dataset}@{revision or 'main'}: {len(default_rows)} default rows, "
        f"{len(gt_rows)} ground-truth rows, "
        f"{sum(1 for r in default_rows if r.get('filename') in gt_by_file)} joined"
    )

    unmatched = [r["filename"] for r in default_rows if r.get("filename") not in gt_by_file]
    if unmatched:
        print(
            f"  WARNING: {len(unmatched)} default rows without ground truth: "
            f"{unmatched[:5]}{'…' if len(unmatched) > 5 else ''}"
        )

    if args.dry_run:
        print("dry run — nothing written")
        return 0

    missing = [k for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(
            f"missing env vars: {', '.join(missing)} "
            "(copy .env.example -> .env and fill in)"
        )
    from langfuse import Langfuse

    client = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com"),
    )
    try:
        client.auth_check()
    except Exception as exc:
        sys.exit(f"Langfuse rejected the configured credentials ({str(exc)[:120]}).")

    dataset_obj = client.create_dataset(
        name=lf_name,
        description=spec["description"],
        metadata={
            "source": f"https://huggingface.co/datasets/{dataset}",
            "revision": revision or None,
            "sync": "scripts/sync_pilot_dataset.py",
            "corpus": args.corpus,
        },
    )

    created = skipped = 0
    known_items: dict[str, object] = {}
    try:
        ds_client = client.get_dataset(lf_name)
        for item in getattr(ds_client, "items", []) or []:
            sig = getattr(item, "id", None)
            if sig:
                known_items[sig] = item
    except Exception:
        pass

    for row in default_rows:
        fn = row.get("filename")
        if not fn:
            continue
        gt = gt_by_file.get(fn) or {}
        item_input = {
            "filename": fn,
            "prompt": row.get("prompt"),
            "metadata": row.get("metadata"),
        }
        if not args.omit_text and row.get("doc_text"):
            item_input["doc_text"] = row.get("doc_text")
        expected_output = {
            k: v
            for k, v in gt.items()
            if k != "filename" and v not in (None, "", [])
        } or None
        iid = _item_id(id_prefix, fn)
        if iid in known_items:
            skipped += 1
            continue
        client.create_dataset_item(
            dataset_name=lf_name,
            id=iid,
            input=item_input,
            expected_output=expected_output,
            metadata={
                "subclass": gt.get("expected_subclass"),
                "hf_split": gt.get("split"),
                "hf_revision": revision or None,
            },
        )
        created += 1

    client.flush()
    print(
        f"dataset '{lf_name}' ({dataset_obj.id}): "
        f"{created} items added, {skipped} already present"
    )
    host = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com").rstrip("/")
    print(f"Dataset live at {host}/datasets/{lf_name}")
    client.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
