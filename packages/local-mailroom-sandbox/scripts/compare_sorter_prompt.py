#!/usr/bin/env python3
"""Validate a new sorter prompt against the saved V14 pass, scored on the verified targets.

Two steps, no model call in either:

``inputs`` writes ``data/runtime/handoff/<split>-sorter-errors.jsonl`` (the dataset rows the
``sorter-v15-qwen-*`` run specs read): every document the saved pass got wrong against the
verified targets (class, or subclass with the class right), plus a seeded control sample of
documents it got right, stratified by class, so a fix that breaks a right answer shows up.
Document text comes from the locked ``dataset.jsonl`` of any run over the same split.

``score`` compares a finished run of the new prompt with the saved pass on the same
documents: per document fixed / broken / still wrong / still right, for class and subclass,
grouped by the V14 error pattern. Writes ``reports/sorter-handoff/<run>.compare.json``.

    python scripts/compare_sorter_prompt.py --split train inputs \\
        --dataset-run reviewer-calibration-luna-decisions-v3.1.0-train
    sandbox run start --config config/runs/sorter-v15-qwen-train-errors.yaml --initials XX
    python scripts/compare_sorter_prompt.py --split train score --run sorter-v15-qwen-train-errors
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
from pathlib import Path

from mailroom_sandbox.paths import repo_root

HANDOFF = "sorter-qwen3.7-flash"
CONTROL_PER_CLASS = 40


def _lines(path: Path) -> list[dict]:
    """JSONL rows split on newline only (document text holds U+2028 and other separators)."""
    with path.open(encoding="utf-8", newline="\n") as handle:
        return [json.loads(line) for line in handle.read().split("\n") if line.strip()]


def _targets(root: Path, name: str, split: str) -> dict[str, dict]:
    return {row["id"]: row for row in _lines(root / "data" / "handoff" / name / f"{split}.targets.jsonl")}


def _norm_contract(value):
    from llm_dojo_scoring.equivalences import normalize_subtype

    return normalize_subtype(value) if value else value


def pattern(target: dict) -> str | None:
    """The V14 error a target row shows, or None when the saved pass was right (or unscored)."""
    if not target.get("use_for_class"):
        return None
    if not target.get("sorter_class_correct"):
        return f"class {target['target_doc_class']} -> {target['sorter_doc_type']}"
    if target.get("use_for_subclass") and target.get("sorter_subclass_correct") is False:
        return f"subclass {target['target_doc_class']}/{target['target_subclass']} -> {target['sorter_doc_subclass']}"
    return None


def select(targets: dict[str, dict], *, control_per_class: int = CONTROL_PER_CLASS, seed: int = 42) -> dict[str, str]:
    """Document id -> why it is in the validation set (an error pattern, or ``control``)."""
    chosen = {doc_id: p for doc_id, t in targets.items() if (p := pattern(t))}
    right: dict[str, list[str]] = collections.defaultdict(list)
    for doc_id, t in sorted(targets.items()):
        if doc_id not in chosen and t.get("use_for_class") and t.get("use_for_subclass"):
            right[t["target_doc_class"]].append(doc_id)
    rng = random.Random(seed)
    for cls in sorted(right):
        for doc_id in rng.sample(right[cls], min(control_per_class, len(right[cls]))):
            chosen[doc_id] = "control"
    return chosen


def cmd_inputs(args: argparse.Namespace) -> int:
    root = repo_root()
    targets = _targets(root, args.name, args.split)
    chosen = select(targets, control_per_class=args.control_per_class, seed=args.seed)
    rows: dict[str, dict] = {}
    for rid in args.dataset_run:
        for row in _lines(root / "data" / "runtime" / "runs" / rid / "dataset.jsonl"):
            rows.setdefault(row["id"], row)
    missing = sorted(set(chosen) - set(rows))
    if missing:
        print(f"compare_sorter_prompt: {len(missing)} selected documents are not in the dataset runs given")
        return 1
    out = root / "data" / "runtime" / "handoff" / f"{args.split}-sorter-errors.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(rows[doc_id], ensure_ascii=False, sort_keys=True) + "\n" for doc_id in sorted(chosen))
    out.write_text(text, encoding="utf-8")
    why = collections.Counter("control" if p == "control" else p.split(" ", 1)[0] for p in chosen.values())
    chars = sum(len(rows[doc_id].get("doc_text") or "") for doc_id in chosen)
    print(json.dumps({"file": str(out.relative_to(root)), "documents": len(chosen), "by_reason": dict(why),
                      "sha256": hashlib.sha256(text.encode()).hexdigest(), "doc_chars": chars}, indent=2))
    return 0


def _run_answers(root: Path, run_id: str) -> dict[str, dict]:
    out = {}
    for item in _lines(root / "data" / "runtime" / "runs" / run_id / "items.jsonl"):
        pred = item.get("pred") or {}
        if item.get("ok") and not item.get("error") and pred.get("doc_type"):
            sub = pred.get("doc_subclass") or pred.get("contract_subtype")
            out[str(item["item_id"])] = {"doc_type": pred["doc_type"],
                                         "doc_subclass": _norm_contract(sub) if pred["doc_type"] == "contract" else sub}
    return out


def compare(targets: dict[str, dict], chosen: dict[str, str], answers: dict[str, dict]) -> dict:
    """Class and subclass outcome of the new prompt against the saved pass, per V14 pattern."""
    tally: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    totals = collections.Counter()
    for doc_id, why in sorted(chosen.items()):
        t = targets[doc_id]
        new = answers.get(doc_id)
        if new is None:
            tally[why]["no_answer"] += 1
            totals["no_answer"] += 1
            continue
        for level in ("class", "subclass"):
            if level == "class":
                if not t.get("use_for_class"):
                    continue
                before, after = bool(t["sorter_class_correct"]), new["doc_type"] == t["target_doc_class"]
            else:
                if not t.get("use_for_subclass"):
                    continue
                before = bool(t["sorter_subclass_correct"])
                after = new["doc_type"] == t["target_doc_class"] and new["doc_subclass"] == t["target_subclass"]
            outcome = {(False, True): "fixed", (True, False): "broken",
                       (False, False): "still_wrong", (True, True): "still_right"}[(before, after)]
            tally[why][f"{level}_{outcome}"] += 1
            totals[f"{level}_{outcome}"] += 1
            totals[f"{level}_scored"] += 1
            totals[f"{level}_right_before"] += before
            totals[f"{level}_right_after"] += after
    return {"documents": len(chosen), "answered": sum(doc_id in answers for doc_id in chosen),
            "totals": dict(totals), "by_pattern": {k: dict(v) for k, v in sorted(tally.items())}}


def cmd_score(args: argparse.Namespace) -> int:
    root = repo_root()
    targets = _targets(root, args.name, args.split)
    chosen = select(targets, control_per_class=args.control_per_class, seed=args.seed)
    answers = _run_answers(root, args.run)
    result = {"run_id": args.run, "baseline": f"data/handoff/{args.name}/{args.split}.targets.jsonl",
              **compare(targets, chosen, answers)}
    out = root / "reports" / "sorter-handoff" / f"{args.run}.compare.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"], indent=2, sort_keys=True))
    print(f"wrote {out.relative_to(root)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default=HANDOFF, help="saved sorter pass under data/handoff/")
    parser.add_argument("--split", default="train")
    parser.add_argument("--control-per-class", type=int, default=CONTROL_PER_CLASS)
    parser.add_argument("--seed", type=int, default=42)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_in = sub.add_parser("inputs", help="write the validation dataset rows")
    p_in.add_argument("--dataset-run", action="append", required=True,
                      help="run whose locked dataset.jsonl holds the document text (repeatable)")
    p_sc = sub.add_parser("score", help="compare a finished run with the saved pass")
    p_sc.add_argument("--run", required=True)
    args = parser.parse_args()
    return cmd_inputs(args) if args.cmd == "inputs" else cmd_score(args)


if __name__ == "__main__":
    raise SystemExit(main())
