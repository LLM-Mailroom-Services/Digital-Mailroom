#!/usr/bin/env python3
"""Pick each class's decision-reviewer cutoff from a labelled reviewer run.

Answers are grouped by the class the reviewer predicted, since that class's
cutoff is the one that admits them. The cutoff is the lowest confidence at which
a class's accepted answers reach the target accuracy. Five seeded folds estimate
what that rule delivers: each fold is scored with a cutoff tuned on the other
four, so every answer is test data once. ``meets_target`` is true only when the
interval's lower bound clears the target. A class that never reaches the target
gets no cutoff, so it should not be configured as reviewed.
A run that is not done, or misses any locked document, is refused. Each class also
reports its answers at the top confidence: wrong ones there no cutoff can remove.
Every result also reports ``routing_at_cutoffs``: documents routed to human review,
sent on unattended and misrouted at the chosen cutoffs. ``--cutoffs-from`` scores a
held-out run at cutoffs calibrated on another run.

Truth: a run whose lock names a saved sorter pass (``reviewer.handoff_run:
data/handoff/<name>/<split>.jsonl``) is scored against that pass's verified targets
(``<split>.targets.jsonl``, written by scripts/patch_sorter_handoff.py): corrected labels,
contract keys normalized, and only rows with ``use_for_class`` / ``use_for_subclass``
(ambiguous and disputed rows, and the unannotated merger subclass, are not scored).
``--targets`` names a targets file; ``--labels`` scores the raw dataset labels instead.
Every result records which truth it used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.sand42_cards import wilson
from mailroom_sandbox.job.spec import run_dir
from mailroom_sandbox.overlay import live_doc_classes
from mailroom_sandbox.paths import repo_root

FOLDS = 5


class Truth:
    """What each document should be: verified targets, or the raw dataset labels.

    ``doc_class(id)`` is None for a row that must not be scored for its class;
    ``subclass(id)`` returns ``(scored, subclass)``.
    """

    def __init__(self, store: RunStore, targets: Path | None = None, *, labels: bool = False):
        self._rows = {str(row.get("id")): row for row in store.dataset_rows()}
        self._targets: dict[str, dict] | None = None
        self.source = "dataset labels"
        path = None if labels else (targets or default_targets(store))
        if path is not None:
            if not path.is_file():
                raise ValueError(f"targets file {path} not found")
            text = path.read_text(encoding="utf-8")
            self._targets = {str(t["id"]): t for t in (json.loads(x) for x in text.split("\n") if x.strip())}
            missing = [doc_id for doc_id in self._rows if doc_id not in self._targets]
            if missing:
                raise ValueError(f"targets file {path} has no row for {len(missing)} locked documents")
            rel = path.relative_to(repo_root()) if path.is_relative_to(repo_root()) else path
            self.source = f"targets {rel} sha256 {hashlib.sha256(text.encode()).hexdigest()}"

    def ids(self) -> list[str]:
        return list(self._rows)

    def doc_class(self, doc_id: str) -> str | None:
        if doc_id not in self._rows:
            return None
        if self._targets is None:
            return self._rows[doc_id].get("expected_doc_class")
        target = self._targets[doc_id]
        return target.get("target_doc_class") if target.get("use_for_class") else None

    def subclass(self, doc_id: str) -> tuple[bool, str | None]:
        if doc_id not in self._rows:
            return False, None
        if self._targets is None:
            return True, self._rows[doc_id].get("expected_subclass")
        target = self._targets[doc_id]
        return bool(target.get("use_for_subclass")), target.get("target_subclass")


def default_targets(store: RunStore) -> Path | None:
    """The verified targets next to the saved sorter pass the run's lock names, if any."""
    handoff_run = ((store.read_lock() or {}).get("reviewer") or {}).get("handoff_run")
    if not isinstance(handoff_run, str) or not handoff_run.endswith(".jsonl"):
        return None
    path = Path(handoff_run)
    path = path if path.is_absolute() else repo_root() / path
    targets = path.with_name(path.name.removesuffix(".jsonl") + ".targets.jsonl")
    return targets if targets.is_file() else None


def _incomplete(store: RunStore) -> str | None:
    """Why the run cannot stand for its whole locked draw, or None when it can."""
    if store.state() != "done":
        return f"run {store.run_id} is {store.state() or 'not started'}, not done"
    expected = {str(row.get("id")) for row in store.dataset_rows()}
    seen = {str(item.get("item_id")) for item in store.load_items()}
    missing = expected - seen
    if not expected or missing:
        return f"run {store.run_id} has no answer for {len(missing)} of {len(expected)} locked documents"
    return None


def _answer(item: dict, classes: set[str]) -> tuple[str, float] | None:
    """The answer's (doc_type, confidence) when it is usable: ok, in the taxonomy, a real confidence."""
    pred = item.get("pred") if isinstance(item.get("pred"), dict) else {}
    doc_type, confidence = pred.get("doc_type"), pred.get("confidence")
    if (item.get("ok") and doc_type in classes and isinstance(confidence, (int, float))
            and not isinstance(confidence, bool) and 0.0 <= confidence <= 1.0):
        return str(doc_type), float(confidence)
    return None


def _rows(store: RunStore, classes: set[str] | None = None,
          truth: Truth | None = None) -> dict[str, list[tuple[float, bool]]]:
    """Per predicted class: (confidence, correct).

    The decision reviewer applies the cutoff of the class it predicted, so that
    is the class whose evidence an answer is. A failed, unscored or
    out-of-taxonomy answer predicts no class and can clear no cutoff. A row the
    truth does not score (ambiguous or disputed target) is left out.
    """
    classes = set(live_doc_classes()) if classes is None else classes
    truth = truth or Truth(store, labels=True)
    expected = {doc_id: truth.doc_class(doc_id) for doc_id in truth.ids()}
    by_class: dict[str, list[tuple[float, bool]]] = {
        name: [] for name in sorted({value for value in expected.values() if value})}
    for item in store.load_items():
        want = expected.get(str(item.get("item_id")))
        answer = _answer(item, classes) if want is not None else None
        if answer is not None:
            by_class.setdefault(answer[0], []).append((answer[1], answer[0] == want))
    return by_class


def _accepted(rows: list[tuple[float, bool]], cutoff: float) -> tuple[int, int]:
    kept = [correct for confidence, correct in rows if confidence >= cutoff]
    return sum(kept), len(kept)


def _saturation(rows: list[tuple[float, bool]]) -> dict:
    """The answers at the highest confidence, which no cutoff can separate."""
    if not rows:
        return {"top_confidence": None, "top_confidence_documents": 0, "top_confidence_wrong": 0}
    top = max(confidence for confidence, _ in rows)
    right, kept = _accepted(rows, top)
    return {"top_confidence": top, "top_confidence_documents": kept, "top_confidence_wrong": kept - right}


def _cutoff(rows: list[tuple[float, bool]], target: float) -> float | None:
    for cutoff in sorted({confidence for confidence, _ in rows if confidence > 0}):
        right, kept = _accepted(rows, cutoff)
        if kept and right / kept >= target:
            return cutoff
    return None


def _cross_fit(rows: list[tuple[float, bool]], target: float, folds: int = FOLDS) -> tuple[int, int]:
    """(right, accepted) over all folds, each scored with a cutoff tuned on the others."""
    right = kept = 0
    for fold in range(folds):
        held = rows[fold::folds]
        cutoff = _cutoff([row for index, row in enumerate(rows) if index % folds != fold], target)
        if cutoff is not None:
            fold_right, fold_kept = _accepted(held, cutoff)
            right, kept = right + fold_right, kept + fold_kept
    return right, kept


def calibrate(store: RunStore, *, target: float = 0.95, seed: int = 42,
              classes: set[str] | None = None, truth: Truth | None = None) -> dict:
    """Cutoffs from a finished run; raises ``ValueError`` on a run that misses locked documents."""
    if not 0.0 < target <= 1.0:
        raise ValueError(f"target accuracy must be in (0, 1]; got {target}")
    reason = _incomplete(store)
    if reason:
        raise ValueError(reason)
    results = {}
    truth = truth or Truth(store, labels=True)
    for name, rows in sorted(_rows(store, classes, truth).items()):
        rows = sorted(rows)
        random.Random(seed).shuffle(rows)
        cutoff = _cutoff(rows, target)
        result = {"documents": len(rows), "cutoff": cutoff, **_saturation(rows)}
        if cutoff is not None:
            right, kept = _cross_fit(rows, target)
            interval = wilson(right, kept) if kept else None
            result.update({"holdout_documents": len(rows), "holdout_accepted": kept,
                           "holdout_accuracy": right / kept if kept else None,
                           "holdout_accuracy_ci": interval,
                           "holdout_share_accepted": kept / len(rows) if rows else None,
                           "meets_target": bool(interval and interval[0] >= target)})
        results[name] = result
    return {"run_id": store.run_id, "target_accuracy": target, "seed": seed, "truth": truth.source,
            "classes": results}


def routing(store: RunStore, cutoffs: dict[str, float | None], truth: Truth | None = None) -> dict:
    """What the reviewer does to every document of a run at ``cutoffs``.

    ``routed_to_human_review`` counts documents a person gets: a human verdict
    (question set 3.0.0 and later), a class with no cutoff, or a gated confidence
    below the class cutoff. ``misrouted`` counts documents sent on unattended with
    the wrong class. With a sorter handoff in the lock, ``verdicts`` scores the
    verdict against the truth: the sorter's class and subclass right is
    continue_sorter_correct, class right and subclass wrong is
    continue_with_subclass_correction, class wrong is reclassify. Rows the truth
    does not score count toward routing but not toward misrouted or verdicts.
    """
    from mailroom_sandbox.eval.human_review import reviewer_routes_to_human, summarize

    truth = truth or Truth(store, labels=True)
    usable = {name: float(value) for name, value in cutoffs.items() if value is not None}
    known = set(truth.ids())
    handoff = ((store.read_lock() or {}).get("reviewer") or {}).get("handoff") or {}
    flags, misrouted, unattended, unscored = [], 0, 0, 0
    verdicts: dict[str, dict[str, int]] = {}
    for item in store.load_items():
        doc_id = str(item.get("item_id"))
        if doc_id not in known:
            continue
        want = truth.doc_class(doc_id)
        pred = item.get("pred") if item.get("ok") else None
        routed = reviewer_routes_to_human(pred, usable)
        flags.append((routed, (pred or {}).get("doc_type")))
        if want is None:
            unscored += 1
            continue
        if not routed:
            unattended += 1
            misrouted += pred.get("doc_type") != want
        sorter = handoff.get(doc_id)
        if pred and sorter and pred.get("verdict"):
            scored, want_sub = truth.subclass(doc_id)
            if sorter.get("sorter_doc_type") != want:
                expect = "reclassify"
            elif scored and _same_subclass(want, sorter.get("sorter_doc_subclass"), want_sub) is False:
                expect = "continue_with_subclass_correction"
            else:
                expect = "continue_sorter_correct"
            cell = verdicts.setdefault(expect, {})
            cell[pred["verdict"]] = cell.get(pred["verdict"], 0) + 1
    out = {**summarize(flags, "reviewer"), "cutoffs": usable, "sent_on_unattended": unattended,
           "misrouted": misrouted, "not_scored": unscored, "truth": truth.source,
           "misrouted_rate_among_unattended": round(misrouted / unattended, 6) if unattended else None}
    if verdicts:
        out["verdicts_by_expected"] = verdicts
    return out


def _same_subclass(doc_class: str, predicted, expected) -> bool | None:
    """Whether two subclasses agree; contract labels compare as taxonomy keys. None if unknown."""
    if expected in (None, ""):
        return None
    if doc_class == "contract":
        from llm_dojo_scoring.equivalences import normalize_subtype

        return normalize_subtype(predicted) == normalize_subtype(expected)
    return predicted == expected


def subclass_report(store: RunStore, truth: Truth | None = None) -> dict:
    """Reviewer subclass accuracy per target class, over rows whose class it got right."""
    truth = truth or Truth(store, labels=True)
    known = set(truth.ids())
    per: dict[str, list[int]] = {}
    for item in store.load_items():
        doc_id = str(item.get("item_id"))
        pred = item.get("pred") if item.get("ok") else None
        want = truth.doc_class(doc_id) if doc_id in known else None
        if not pred or want is None or pred.get("doc_type") != want:
            continue
        scored, want_sub = truth.subclass(doc_id)
        same = _same_subclass(want, pred.get("doc_subclass") or pred.get("contract_subtype"), want_sub)
        if not scored or same is None:
            continue
        cell = per.setdefault(want, [0, 0])
        cell[0] += bool(same)
        cell[1] += 1
    right = sum(c[0] for c in per.values())
    total = sum(c[1] for c in per.values())
    return {"truth": truth.source, "subclass_correct": right, "subclass_scored": total,
            "subclass_accuracy": round(right / total, 6) if total else None,
            "by_class": {name: {"correct": c[0], "scored": c[1], "accuracy": round(c[0] / c[1], 6)}
                         for name, c in sorted(per.items())}}


def probe(store: RunStore, *, min_valid: int = 9, max_mean_seconds: float = 10.0,
          classes: set[str] | None = None) -> dict:
    """Whether a model is fit to calibrate: a finished run, taxonomy-valid answers, usable speed."""
    classes = set(live_doc_classes()) if classes is None else classes
    items = store.load_items()
    valid = sum(_answer(item, classes) is not None for item in items)
    latency = [float(item["latency_ms"]) / 1000.0 for item in items if item.get("latency_ms") is not None]
    mean_seconds = sum(latency) / len(latency) if latency else None
    incomplete = _incomplete(store)
    passed = (incomplete is None and valid >= min_valid
              and mean_seconds is not None and mean_seconds <= max_mean_seconds)
    return {"run_id": store.run_id, "documents": len(items), "valid_answers": valid,
            "mean_seconds_per_document": mean_seconds, "incomplete": incomplete, "passed": passed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True)
    parser.add_argument("--target", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--probe", action="store_true", help="check the model is fit to calibrate")
    parser.add_argument("--cutoffs-from", default=None, metavar="RUN",
                        help="score --run (e.g. a held-out validation run) at the cutoffs calibrated on RUN; "
                             "writes reports/reviewer-calibration/<run>.routing.json")
    truth_group = parser.add_mutually_exclusive_group()
    truth_group.add_argument("--targets", type=Path, default=None,
                             help="verified targets file (default: the one next to the lock's handoff_run)")
    truth_group.add_argument("--labels", action="store_true", help="score the raw dataset labels")
    args = parser.parse_args()
    out_dir = repo_root() / "reports" / "reviewer-calibration"
    store = RunStore(run_dir(args.run))
    if args.probe:
        verdict = probe(store)
        print(json.dumps(verdict, indent=2, sort_keys=True))
        return 0 if verdict["passed"] else 1
    try:
        truth = Truth(store, args.targets, labels=args.labels)
    except ValueError as exc:
        print(f"calibrate_reviewer: {exc}", file=sys.stderr)
        return 1
    if args.cutoffs_from:
        source = json.loads((out_dir / f"{args.cutoffs_from}.json").read_text(encoding="utf-8"))
        cutoffs = {name: cls.get("cutoff") for name, cls in source["classes"].items()}
        result = {"run_id": args.run, "cutoffs_from": args.cutoffs_from,
                  **routing(store, cutoffs, truth), "subclass": subclass_report(store, truth)}
        path = out_dir / f"{args.run}.routing.json"
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        print(f"wrote {path}")
        return 0
    try:
        result = calibrate(store, target=args.target, seed=args.seed, truth=truth)
    except ValueError as exc:
        print(f"calibrate_reviewer: {exc}", file=sys.stderr)
        return 1
    result["routing_at_cutoffs"] = routing(store, {name: cls.get("cutoff") for name, cls in result["classes"].items()},
                                           truth)
    result["subclass"] = subclass_report(store, truth)
    path = out_dir / f"{args.run}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"truth": truth.source, "classes": result["classes"], "subclass": result["subclass"]},
                     indent=2, sort_keys=True))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
