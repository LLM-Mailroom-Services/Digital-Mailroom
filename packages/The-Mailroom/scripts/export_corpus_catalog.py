"""Export a slim catalog of Lucius-Morningstar/mailroom-dataset for the
terminal GH Pages site + TUI.

Pages BOTH configs (default + ground_truth) via the canonical
``mailroom_ui.hf_corpus`` ladder and writes one JSON the site's corpus
commands consume:

    <out>/corpus.json
        meta:    dataset / revision / generated_at / per-split counts
        rows:    [{filename, split, index, gt_index, doc_class,
                   doc_subclass, sha256, chars}, ...]

``index`` / ``gt_index`` are row offsets into the Hub datasets-server
``/rows`` API for the default / ground_truth configs — the site fetches the
full doc_text + GT fields live, one row at a time, never the whole corpus.
The catalog keeps the bundle small (~2,000 slim rows) while listing, search,
and stats work fully offline.

Usage:
    python scripts/export_corpus_catalog.py [--out site/data] [--max-rows N]
                                            [--check]

``--check`` re-reads the written file and verifies counts + sha presence;
exit 1 on an empty or structurally broken catalog.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mailroom_ui import hf_corpus  # noqa: E402


def _meta(row: dict, key: str):
    meta = row.get("metadata")
    if isinstance(meta, dict):
        return meta.get(key)
    return None


def build_catalog(max_rows: int | None = None,
                  page_size: int = 100,
                  pace_s: float = 1.0) -> dict:
    rows: list[dict] = []
    for split in ("train", "test"):
        default = hf_corpus.fetch_rows(
            config=hf_corpus.DEFAULT_CONFIG, split=split,
            page_size=page_size, max_rows=max_rows, page_sleep=pace_s)
        gt = hf_corpus.fetch_rows(
            config=hf_corpus.GT_CONFIG, split=split,
            page_size=page_size, max_rows=max_rows, page_sleep=pace_s)
        gt_by_file = {str(r.get("filename")): r for r in gt}
        for i, r in enumerate(default):
            filename = str(r.get("filename") or f"row-{i}")
            gt_row = gt_by_file.get(filename)
            rows.append({
                "filename": filename,
                "split": split,
                "index": i,
                "gt_index": i if gt_row is not None else -1,
                # Class/subclass/sha live on the GROUND-TRUTH config
                # (default metadata carries provenance only).
                "doc_class": (gt_row or {}).get("expected"),
                "doc_subclass": (gt_row or {}).get("expected_subclass"),
                "sha256": (gt_row or {}).get("content_sha256"),
                "chars": len(r.get("doc_text") or ""),
            })
    splits: dict[str, int] = {"train": 0, "test": 0}
    for r in rows:
        splits[r["split"]] = splits.get(r["split"], 0) + 1
    return {
        "meta": {
            "dataset": hf_corpus.corpus_id(),
            "revision": hf_corpus.corpus_revision(),
            "configs": [hf_corpus.DEFAULT_CONFIG, hf_corpus.GT_CONFIG],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "splits": splits,
        },
        "rows": rows,
    }


def check_catalog(path: Path) -> int:
    """Verify the written catalog. Returns 0 when sound, 1 when broken."""
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        print(f"CHECK FAIL: cannot read {path}: {exc}")
        return 1
    rows = data.get("rows") or []
    if not rows:
        print("CHECK FAIL: catalog is empty")
        return 1
    splits = data.get("meta", {}).get("splits", {})
    bad_sha = [r["filename"] for r in rows if not r.get("sha256")]
    bad_gt = [r["filename"] for r in rows if r.get("gt_index", -1) < 0]
    if bad_sha:
        print(f"CHECK FAIL: {len(bad_sha)} rows missing sha256 "
              f"(e.g. {bad_sha[0]})")
        return 1
    if bad_gt:
        print(f"CHECK FAIL: {len(bad_gt)} rows missing a ground-truth index "
              f"(e.g. {bad_gt[0]})")
        return 1
    by_split: dict[str, int] = {}
    for r in rows:
        by_split[r["split"]] = by_split.get(r["split"], 0) + 1
    print(f"CHECK OK: {len(rows)} rows "
          f"(train {by_split.get('train', 0)} / test {by_split.get('test', 0)}) "
          f"= meta splits {splits}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="site/data",
                        help="output directory (default site/data)")
    parser.add_argument("--max-rows", type=int, default=None,
                        help="cap rows per split (dev/test runs)")
    parser.add_argument("--check", action="store_true",
                        help="verify an existing catalog and exit")
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / "corpus.json"

    if args.check:
        return check_catalog(target)

    print(f"== exporting corpus catalog -> {target} ==")
    print(f"   dataset {hf_corpus.corpus_id()} @ {hf_corpus.corpus_revision()[:12]} "
          f"(configs {hf_corpus.DEFAULT_CONFIG} + {hf_corpus.GT_CONFIG})")
    catalog = build_catalog(max_rows=args.max_rows, page_size=args.page_size)
    target.write_text(json.dumps(catalog, indent=1))
    return check_catalog(target)


if __name__ == "__main__":
    sys.exit(main())