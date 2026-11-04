#!/usr/bin/env python3
"""Save a sorter pass to the repository as a reusable handoff and sorter baseline.

Reads finished sorter runs (data/runtime/runs/<id>/, not committed) and writes one JSON line
per document, without the document text, to data/handoff/<name>/<split>.jsonl, plus
manifest.json with the runs, model, dataset revision, tokens, list cost and accuracy.
A reviewer run uses the file directly: ``reviewer.handoff_run: data/handoff/<name>/<split>.jsonl``.

    python scripts/export_sorter_handoff.py --name sorter-qwen3.7-flash --split train \
        --run sorter-handoff-qwen-train --run sorter-handoff-qwen-train-rest
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mailroom_sandbox.job.metrics import token_price
from mailroom_sandbox.paths import repo_root


def _lines(path: Path) -> list[str]:
    """JSONL lines split on newline only (document text holds U+2028 and other separators)."""
    with path.open(encoding="utf-8", newline="\n") as handle:
        return [line for line in handle.read().split("\n") if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--run", action="append", required=True, help="sorter run id; later runs win on overlap")
    args = parser.parse_args()
    root = repo_root()
    rows: dict[str, dict] = {}
    items: dict[str, dict] = {}
    source: dict[str, str] = {}
    runs = []
    model = revision = None
    for rid in args.run:
        d = root / "data" / "runtime" / "runs" / rid
        lock = json.loads((d / "spec.lock.json").read_text())
        checkpoint = json.loads((d / "checkpoint.json").read_text())
        model = model or lock["engine"]["model"]
        revision = revision or (lock.get("dataset") or {}).get("revision")
        for line in _lines(d / "dataset.jsonl"):
            row = json.loads(line)
            rows[row["id"]] = row
            revision = revision or row.get("source_revision")
        run_items = [json.loads(line) for line in _lines(d / "items.jsonl")]
        for item in run_items:
            items[str(item["item_id"])] = item
            source[str(item["item_id"])] = rid
        runs.append({"run_id": rid, "state": checkpoint.get("state"), "items": len(run_items),
                     "spec_hash": checkpoint.get("spec_hash"),
                     "stopped_by": (checkpoint.get("last_error") or {}).get("message")})
    out_dir = root / "data" / "handoff" / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{args.split}.jsonl"
    price_in, price_out = token_price(model) or (0.0, 0.0)
    tokens_in = tokens_out = right = answered = 0
    lines = []
    for doc_id in sorted(rows):
        row, item = rows[doc_id], items.get(doc_id)
        if item is None:
            continue
        pred = item.get("pred") or {}
        record = {
            "id": doc_id,
            "filename": row.get("filename"),
            "content_sha256": row.get("content_sha256"),
            "expected_doc_class": row.get("expected_doc_class"),
            "expected_subclass": row.get("expected_subclass"),
            "ok": bool(item.get("ok")) and not item.get("error"),
            "error": item.get("error"),
            "sorter_doc_type": pred.get("doc_type"),
            "sorter_doc_subclass": pred.get("doc_subclass") or pred.get("contract_subtype"),
            "sorter_contract_subtype": pred.get("contract_subtype"),
            "sorter_confidence": pred.get("confidence"),
            "sorter_reasoning": pred.get("reasoning"),
            "prompt_tokens": item.get("prompt_tokens"),
            "completion_tokens": item.get("completion_tokens"),
            "latency_ms": item.get("latency_ms"),
            "run_id": source[doc_id],
        }
        tokens_in += int(item.get("prompt_tokens") or 0)
        tokens_out += int(item.get("completion_tokens") or 0)
        if record["ok"]:
            answered += 1
            right += record["sorter_doc_type"] == record["expected_doc_class"]
        lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    from mailroom_sandbox.eval.human_review import for_isolated

    routed = for_isolated("sorter", [{"doc_type": json.loads(x)["sorter_doc_type"],
                                      "confidence": json.loads(x)["sorter_confidence"]}
                                     for x in lines if json.loads(x)["ok"]])
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.update({"name": args.name, "model": model, "dataset_revision": revision,
                     "dataset": "Lucius-Morningstar/mailroom-dataset (ground_truth)"})
    manifest.setdefault("splits", {})[args.split] = {
        "file": path.name, "sha256": hashlib.sha256(text.encode()).hexdigest(), "documents": len(lines),
        "dataset_documents": len(rows), "answered": answered, "class_correct": right,
        "class_accuracy": round(right / answered, 6) if answered else None,
        "prompt_tokens": tokens_in, "completion_tokens": tokens_out,
        "list_cost_usd": round(tokens_in * price_in / 1e6 + tokens_out * price_out / 1e6, 4),
        "usd_per_million_tokens": [price_in, price_out],
        "routed_to_human_review_sorter_alone": {k: routed[k] for k in ("routed_to_human_review", "routed_to_human_review_rate")},
        "runs": runs,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest["splits"][args.split], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
